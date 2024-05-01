import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import webbrowser
import sqlite3
import sys
import datetime
import time
import re
import argparse
from tabulate import tabulate

# Configuration for CustomTkinter
ctk.set_appearance_mode("System")  # Adjust based on the system theme
ctk.set_default_color_theme("blue")  # Choose a color theme

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
    return [name] * count

def parse_deck(deck_file):
    ret = []
    with open(deck_file) as f:
        for line in f:
            line = line.strip()
            ret.extend(process_line(line))
    return ret

def is_basic_land(card):
    return card in ['Plains', 'Mountain', 'Swamp', 'Forest', 'Island']

def add_to_output(card_obj, output, output_text):
    for each in output:
        if each['name'] == card_obj['name']:
            each['quantity'] += 1
            output_text.insert(tk.END, f"Updated {card_obj['name']} in output with new quantity: {each['quantity']}\n")
            return 0.0  # Assuming price doesn't need recalculation for duplicates

    # Check both prices and determine the best price and corresponding website
    tcg_price = float(card_obj['tcg_price']) if card_obj['tcg_price'] else float('inf')
    mage_price = float(card_obj['blmage_price']) if card_obj['blmage_price'] else float('inf')

    if tcg_price < mage_price:
        price = tcg_price
        website = card_obj['tcg_url']
    elif mage_price < float('inf'):  # This ensures mage_price is valid and lower or only valid price
        price = mage_price
        website = card_obj['blmage_url']
    else:
        price = 'UNK'  # No valid prices
        website = ''

    price_formatted = f'${price:,.2f}' if price != 'UNK' else 'UNK'

    # Append card data with the chosen price and website
    output.append({'name': card_obj['name'], 'quantity': 1, 'price_each': price_formatted, 'website': website, 'updated': card_obj['timestamp']})
    output_text.insert(tk.END, f"Added {card_obj['name']} to output with price {price_formatted} at {website}\n")
    return price if price != 'UNK' else 0.0

def lookup_avg_price(name):
    name = name.replace(' ', '+')
    url = f'https://api.scryfall.com/cards/named?fuzzy={name}'
    r = requests.get(url)
    if r.status_code != 200:
        return 0.0
    data = r.json()
    return float(data.get('prices', {}).get('usd', 0.0))

def lookup_tcg(name):
    return f'https://www.tcgplayer.com/search/magic/product?productLineName=magic&q={quote(name)}&view=grid&direct=true'

def mage_filter(name):
    name = name.replace(',', ' ').replace('&', ' ')
    return name

def lookup_mage(name):
    name = mage_filter(name)
    url = f'https://bootlegmage.com/?s={quote(name)}'
    r = requests.get(url)
    if r.status_code != 200:
        return ['', 0.0]
    soup = BeautifulSoup(r.text, 'html.parser')
    products = soup.find_all(class_='woocommerce-loop-product__link')
    for each in products:
        title = each.find(class_='woocommerce-loop-product__title')
        price = each.find_all(class_='woocommerce-Price-amount')
        price = price[-1].get_text().strip('$')
        if title.get_text().lower().startswith(name.lower()):
            return [url, float(price)]
    return ['', 0.0]

def add_to_database(card_obj, cursor, conn):
    cursor.execute('''
    INSERT INTO cards (name, blmage_url, blmage_price, tcg_url, tcg_price, timestamp)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (card_obj['name'], card_obj['blmage_url'], card_obj['blmage_price'], card_obj['tcg_url'], card_obj['tcg_price'], card_obj['timestamp']))
    conn.commit()

def print_output(output, price_total, output_text):
    from tabulate import tabulate
    output_text.insert(tk.END, tabulate(output, headers="keys", tablefmt="grid") + "\n")
    output_text.insert(tk.END, f"Approx deck total price (minus shipping): ${price_total:,.2f}\n")
    
def get_platform_firefox_path():
    if sys.platform == 'linux':
        return '/usr/bin/firefox'
    if sys.platform == 'darwin':
        return '/Applications/Firefox.app/Contents/MacOS/firefox'
    if sys.platform == 'win32':
        return r'C:\Program Files\Mozilla Firefox\firefox.exe'

def open_urls_in_firefox(output, mass_import):
    firefox_path = get_platform_firefox_path()
    webbrowser.register('firefox', None, webbrowser.BackgroundBrowser(firefox_path))

    urls = [card['website'] for card in output if not mass_import or (mass_import and card['website'].startswith('https://bootlegmage.com'))]
    
    for url in urls:
        webbrowser.get('firefox').open_new_tab(url)
        time.sleep(1)
        
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
    row = cursor.fetchone
    if row is not None:
        t = row[6]
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        time_difference = datetime.datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S') - \
            datetime.datetime.strptime(t, '%Y-%m-%d %H:%S')
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
    
def fix_card_name(name):
    name = re.sub(r' //.*', '', name)
    return name
    
def make_mass_import(output, output_text):
    out = 'Paste this into the TCGPlayer mass import tool: https://store.tcgplayer.com/massentry\n\n'
    for card in output:
        if card['website'].startswith('https://bootlegmage.com'):
            continue
        fixed_name = fix_card_name(card['name'])
        out += f'{card["quantity"]} {fixed_name}\n'
    
    output_text.insert(tk.END, out + "\n")



def main(deck_file, firefox, mass_import, output_text):
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
    for card_name in deck:
        card_obj = make_card_obj(card_name)
        price_total += add_to_output(card_obj, output, output_text)

    print_output(output, price_total, output_text)

    if firefox:
        open_urls_in_firefox(output, mass_import)

    if mass_import:
        make_mass_import(output, output_text)

    conn.close()


def run_gui():
    root = ctk.CTk()  # Change root to CustomTkinter window
    root.title("Deck Pricing Tool")

    deck_file_path = tk.StringVar(root)
    open_firefox = tk.BooleanVar(root)
    mass_import = tk.BooleanVar(root)

    output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=80, height=20)
    output_text.pack(pady=10, padx=10)

    def open_file():
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if file_path:
            deck_file_path.set(file_path)
            output_text.insert(tk.END, f"Selected deck file: {file_path}\n")

    def execute_program():
        if not deck_file_path.get():
            messagebox.showerror("Error", "Please select a deck file.")
            return
        if not confirm_run():  # Ask user confirmation before proceeding
            return
        output_text.delete('1.0', tk.END)  # Clear the text area before output
        main(deck_file_path.get(), open_firefox.get(), mass_import.get(), output_text)
        if mass_import.get():  # Check if the mass import option is selected
            make_mass_import(output, output_text)  # Call the modified make_mass_import function
        
    def confirm_run():
        response = messagebox.askyesno("Confirm Run", "This may take 1-2 minutes. If you have selected the \"Open URLs in Firefox\" option, it may open upwards of 100 tabs.\n\nDo not click the window, as it may become unresponsive. If the window is unresponsive, the program is working as intended.\n\nDo you want to continue?")
        return response


    open_button = ctk.CTkButton(root, text="Select Deck File", command=open_file)
    open_button.pack(pady=(10, 0))  # Additional padding for better layout

    firefox_checkbox = ctk.CTkCheckBox(root, text="Open URLs in Firefox", variable=open_firefox)
    firefox_checkbox.pack(pady=(10, 0))  # Additional padding for better layout

    mass_import_checkbox = ctk.CTkCheckBox(root, text="Generate Mass Import File", variable=mass_import)
    mass_import_checkbox.pack(pady=(10, 0))  # Additional padding for better layout

    run_button = ctk.CTkButton(root, text="Run", command=execute_program)
    run_button.pack(pady=(10, 0))  # Additional padding for better layout

    root.mainloop()

if __name__ == "__main__":
    run_gui()