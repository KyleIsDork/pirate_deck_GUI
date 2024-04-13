import requests
import argparse
import re
from tabulate import tabulate
import time
from bs4 import BeautifulSoup
from urllib.parse import quote

global DEBUG
DEBUG = True

def debug_print(line):
    if DEBUG:
        print(line)

# GET https://www.acardgameshop.com/?s=Flooded Strand&post_type=product

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
            return
    output.append({'name': card_obj['name'], 'quantity': 1, 'website': card_obj['website']})

def lookup_tcg(name):
    return f'https://www.tcgplayer.com/search/magic/product?productLineName=magic&q={quote(name)}&view=grid&direct=true'

def lookup_cking(name):
    return f'https://www.cardkingdom.com/catalog/search?search=header&filter[name]={quote(name)}'

def lookup_mage(name):
    url = f'https://bootlegmage.com/?s={quote(name)}'
    r = requests.get(url)
    if r.status_code != 200:
        return ''
    soup = BeautifulSoup(r.text, 'html.parser')
    products = soup.find_all(class_='woocommerce-loop-product__title')
    for title in products:
        if str(title.get_text()).startswith(name):
            return url
    return ''

def lookup_usea(name):
    return 'TODO usea'

def lookup_single(name, use_lgs, use_tcg, use_cking):
    if use_lgs:
        return 'LGS'
    if use_tcg:
        return lookup_tcg(name)
    if use_cking:
        return lookup_cking(name)
    return 'ERROR'

def lookup_proxy(name, use_mage, use_usea):
    if use_mage:
        return lookup_mage(name)
    if use_usea:
        return lookup_usea(name)
    return ''

def print_output(output):
    print(tabulate(output, headers="keys", tablefmt="rounded_grid"))

def main():
    parser = argparse.ArgumentParser(
        description='An easy way to price and build a deck between buying singles and BLs/proxies from USEA/BLMage'
    )

    proxy_group = parser.add_mutually_exclusive_group()
    proxy_group.required = True
    proxy_group.add_argument('--usea', '-u', action='store_true', help='Use USEA')
    proxy_group.add_argument('--blmage', '-b', action='store_true', help='Use BLMage')

    singles_group = parser.add_mutually_exclusive_group()
    singles_group.required = True
    singles_group.add_argument('--lgs', '-l', action='store_true', help='Use your friendly LGS for singles (this will just print out a list)')
    singles_group.add_argument('--tcg', '-t', action='store_true', help='Use tcgplayer.com for singles (this will print links)')
    singles_group.add_argument('--cking', '-k', action='store_true', help='Use cardkingdom.com for singles (this will print links)')

    parser.add_argument('--input', '-i', type=str, required=True, help='Input file:\n'+
                        '\t[exported as "Text" and "1 Card Name" and "No Headers" from Archidekt]\n'+
                        '\tOR\n'+
                        '\t[exported as a .txt from Tappedout]\n'+
                        '\tOR\n'+
                        '\t[exported as MTGA format from Moxfield]'
    )
    args = parser.parse_args()

    use_mage = args.blmage
    use_usea = args.usea

    use_lgs = args.lgs
    use_tcg = args.tcg
    use_cking = args.cking

    deck_file = args.input


    debug_print(f'mage: {use_mage}, usea: {use_usea}, deck {deck_file}')
    debug_print(f'lgs: {use_lgs}, tcgplayer: {use_tcg}, cardkingdom: {use_cking}')

    # cache of [ {'name': 'Plains', 'website': 'google.com'}, ...]
    # we'd already looked up
    looked_up_cards_cache = []

    # output list of [ {'name': 'Plains', 'quantity': 3, 'website': 'google.com'}, ... ]
    # for easy printing
    output = []

    deck = parse_deck(deck_file)
    print(f'Please wait while cards are looked up...This can take 1-2 minutes')
    for card in deck:
        found = False
        for each in looked_up_cards_cache:
            if each.name == card:
                # already cached
                add_to_output(each, output)
                found = True
                break
        if found:
            # card was already looked up
            # card already exists in cache
            # card was added to output
            # next card
            continue

        card_obj = {}
        card_obj['name'] = card
        card_obj['quantity'] = 1
        if is_basic_land(card_obj['name']):
            card_obj['website'] = lookup_single(card_obj['name'], use_lgs, use_tcg, use_cking)
        else:
            temp = lookup_proxy(card_obj['name'], use_mage, use_usea)
            if temp == '':
                # didnt find exact match
                temp = lookup_single(card_obj['name'], use_lgs, use_tcg, use_cking)
                if temp == '':
                    # didn't find single
                    card_obj['website'] = 'UNKNOWN, TRY MANUAL SEARCH'
                else:
                    # found single
                    card_obj['website'] = temp
            else:
                # found proxy
                card_obj['website'] = temp
        add_to_output(card_obj, output)

    print_output(output)


if __name__ == '__main__':
    main()
