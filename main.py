import requests
import argparse
import re
from tabulate import tabulate
from bs4 import BeautifulSoup
from urllib.parse import quote
import webbrowser
import sqlite3
import sys
import datetime

DEBUG = False

def debug_print(line):
    if DEBUG:
        print(line)

def process_line(line):
    match = re.match(r'^(\d+)\s+(.*)', line)
    if not match:
        return []
    count = int(match.group(1))
    name = str(match.group(2))
    ret = []
    for i in range(0, count):
        ret.append(name)
    return ret

def parse_deck(deck_file):
    ret = []
    with open(deck_file) as f:
        for line in f:
            line = line.strip()
            ret.extend(process_line(line))
    return ret

def is_basic_land(card):
    if card == 'Plains': return True
    if card == 'Mountain': return True
    if card == 'Swamp': return True
    if card == 'Forest': return True
    if card == 'Island': return True
    return False

def add_to_output(card_obj, output):
    for each in output:
        if each['name'] == card_obj['name']:
            each['quantity'] += 1
            return 0.0
    website = ''
    price = 0.0
    mage_price = float(card_obj['blmage_price'])
    tcg_price = float(card_obj['tcg_price'])

    if tcg_price > 0.0 and mage_price > 0.0:
        # both have valid prices
        if mage_price < tcg_price:
            website = card_obj['blmage_url']
            price = mage_price
        else:
            website = card_obj['tcg_url']
            price = tcg_price

    if card_obj['blmage_price'] == 0:
        website = card_obj['tcg_url']
        price = card_obj['tcg_price']
    else:
        website = card_obj['blmage_url']
        price = card_obj['blmage_price']

    ret = 0.0
    price = float(price)
    if (price == 0.0):
        price = 'UNK'
    else:
        # no need to worry about quantity, this is called for each card, including duplicates
        ret = price
        price = f'${price:,.2f}'

    output.append({'name': card_obj['name'], 'quantity': 1,
                   'price_each': price, 'website': website, 'updated': card_obj['timestamp']})
    return ret


def lookup_avg_price(name):
    name = name.replace(' ', '+')
    url = f'https://api.scryfall.com/cards/named?fuzzy={name}'
    r = requests.get(url)
    if r.status_code != 200:
        return -1.0
    data = r.json()
    if 'prices' not in data:
        return -1.0
    if 'usd' not in data['prices']:
        return -1.0
    pr = data['prices']['usd']
    if pr is None:
        return -1.0
    return float(pr)

def lookup_tcg(name):
    return f'https://www.tcgplayer.com/search/magic/product?productLineName=magic&q={quote(name)}&view=grid&direct=true'

def lookup_mage(name):
    url = f'https://bootlegmage.com/?s={quote(name)}'
    r = requests.get(url)
    if r.status_code != 200:
        return ['', 0.0]
    soup = BeautifulSoup(r.text, 'html.parser')
    products = soup.find_all(class_='woocommerce-loop-product__link')
    for each in products:
        title = each.find(class_='woocommerce-loop-product__title')
        price = each.find_all(class_='woocommerce-Price-amount')
        if (len(price) == 2):
            # on sale
            price = price[1].get_text().replace('$', '')
        else:
            price = price[0].get_text().replace('$', '')
        if str(title.get_text().lower()).startswith(name.lower()):
            return [url, price]
    return ['', 0.0]

def print_output(output, price_total):
    print(tabulate(output, headers="keys", tablefmt="rounded_grid"))
    print(f'Approx deck total price (minus shipping): ${price_total:,.2f}')

def get_platform_firefox_path():
    if sys.platform == 'linux':
        return '/usr/bin/firefox'
    if sys.platform == 'darwin':
        return '/Applications/Firefox.app/Contents/MacOS/firefox'
    if sys.platform == 'win32':
        return 'C:\Program Files\Mozilla Firefox\firefox.exe'

def open_urls_in_firefox(output):
    firefox_path = get_platform_firefox_path()
    webbrowser.register('firefox', None, webbrowser.BackgroundBrowser(firefox_path))

    urls = []

    for obj in output:
        urls.append(obj['website'])

    for url in urls:
        webbrowser.get('firefox').open_new_tab(url)

def card_exists_in_db(cursor, name):
    cursor.execute('SELECT * FROM cards WHERE name = ?', (name,))
    row = cursor.fetchone()
    return row is not None

def add_to_database(card_obj, cursor, conn):
    cursor.execute('INSERT INTO cards (name, tcg_url, tcg_price, blmage_url, blmage_price, timestamp) ' +
                'VALUES (?, ?, ?, ?, ?, ?)',
                (card_obj['name'], card_obj['tcg_url'], card_obj['tcg_price'],
                 card_obj['blmage_url'], card_obj['blmage_price'],
                 datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

def get_card_obj_from_db(cursor, card_name):
    ret = {}
    ret['name'] = card_name
    cursor.execute('SELECT * FROM cards WHERE name = ?', (card_name,))
    row = cursor.fetchone()
    if row is not None:
        ret['blmage_url'] = row[2]
        ret['blmage_price'] = row[3]
        ret['tcg_url'] = row[4]
        ret['tcg_price'] = row[5]
        ret['timestamp'] = row[6]
    return ret

def is_card_lookup_expired(cursor, card_name):
    cursor.execute('SELECT * FROM cards WHERE name = ?', (card_name,))
    row = cursor.fetchone()
    if row is not None:
        t = row[6]
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        time_difference = datetime.datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S') - \
            datetime.datetime.strptime(t, '%Y-%m-%d %H:%M:%S')
        if time_difference.days < 5:
            return False
    return True

def make_card_obj(card_name):
    card_obj = {}
    card_obj['name'] = card_name
    card_obj['quantity'] = 1
    card_obj['timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    card_obj['blmage_url'] = ''
    card_obj['blmage_price'] = 0
    card_obj['tcg_url'] = lookup_tcg(card_obj['name'])
    card_obj['tcg_price'] = lookup_avg_price(card_obj['name'])
    if not is_basic_land(card_obj['name']):
        # only check mage if not a basic land
        prox = lookup_mage(card_obj['name'])
        card_obj['blmage_url'] = prox[0]
        card_obj['blmage_price'] = prox[1]
    return card_obj

def check_card(card_name, cursor, conn, output):
    if card_exists_in_db(cursor, card_name):
        # card exists, we previously looked it up
        if not is_card_lookup_expired(cursor, card_name):
            # card exists, and lookup is not expired
            obj = get_card_obj_from_db(cursor, card_name)
            return add_to_output(obj, output)

    # card does not exist in db, or lookup is expired
    card_obj = make_card_obj(card_name)
    add_to_database(card_obj, cursor, conn)
    return add_to_output(card_obj, output)

def main():
    parser = argparse.ArgumentParser(
        description='An easy way to price and build a deck between buying singles and BLs/proxies from USEA/BLMage'
    )
    parser.add_argument('--open', '-o', action='store_true', help='Open the resulting URLs in Firefox (This may open ~100 tabs)')

    parser.add_argument('--input', '-i', type=str, required=True, help='Input file:\n'+
                        '\t[exported as "Text" and "1 Card Name" and "No Headers" from Archidekt]\n'+
                        '\tOR\n'+
                        '\t[exported as a .txt from Tappedout]\n'+
                        '\tOR\n'+
                        '\t[exported as MTGA format from Moxfield]'
    )
    args = parser.parse_args()

    deck_file = args.input
    firefox = args.open

    debug_print(f'deck: {deck_file}, firefox: {firefox}')

    output = []

    conn = sqlite3.connect('cards.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        blmage_url TEXT NOT NULL,
        blmage_price REAL DEFAULT 0,
        tcg_url TEXT NOT NULL,
        tcg_price REAL DEFAULT 0,
        timestamp TEXT
    )
    ''')
    conn.commit()

    price_total = 0.0

    deck = parse_deck(deck_file)
    print(f'Please wait while cards are looked up...This can take 1-2 minutes')
    for card_name in deck:
        price_total += check_card(card_name, cursor, conn, output)

    print_output(output, price_total)

    if firefox:
        open_urls_in_firefox(output)

    conn.close()


if __name__ == '__main__':
    main()
