# Pirate Deck

## Description
Pirate Deck is a simple tool that helps you find the cheapest prices for Magic: The Gathering (MTG) cards, including 'bootleg' / proxy cards.

When provided a deck list, it will search tcgplayer and blmage finding the cheapest prices using data from scryfall.

Cards, the best locations to buy them, and their prices are cached and refreshed if older than 5 days.

## Installation
To use Pirate Deck, follow these steps:

1. Clone the repository: `git clone https://github.com/HellerCommaA/pirate_deck.git`
2. Navigate to the project directory: `cd pirate-deck`
3. Install virtualenv: `python -m pip install virtualenv`
4. Create a virtualenv: `virtualenv .`
5. Activate the virtualenv: `source bin/activate` or `Scripts\activate` on windows
6. Install requirements: `pip install -r requirements.txt`
7. Run: `python main.py`

## Usage
A few arguments are available:
* `-i / --input` **required** Provide a path to a text file of your decklist
    * There are multiple ways to generate a list.  If your favorite deck builder is not listed, Pirate Deck requires `1 Name of Card` format. Quantity space Name of Card, with no additional 'section' entries.
    * You can also generate lists from the following export options on popular websites:
        * exported as "Text" and "1 Card Name" and "No Headers" from Archidekt
        * exported as a .txt from Tappedout
        * exported as MTGA format from Moxfield
* `-m / --mass-import` **optional** Once cards are collected and priced out, will generate an easy to use list for copy and pasting on TCG's mass import tool.
* `-o / --open` **optional** Optinally opens new tabs in Firefox (and only firefox, sorry) once complete for each card. Note that quantity does not transfer to the tab, so be sure to double check your list. If this option is selected with `-m`, will only open links to mage as it's assumed you're using the import tool on tcg.
