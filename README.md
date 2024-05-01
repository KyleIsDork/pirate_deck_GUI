# Pirate Deck

## Description
Pirate Deck is a simple tool that helps you find the cheapest prices for Magic: The Gathering (MTG) cards, including 'bootleg' / proxy cards.

When provided a deck list, it will search tcgplayer and blmage finding the cheapest prices using data from scryfall.

Cards, the best locations to buy them, and their prices are cached and refreshed if older than 5 days.

## Installation
To use Pirate Deck, follow these steps:

1. Navigate to releases https://github.com/KyleIsDork/pirate_deck_GUI/releases/tag/release
2. Download the latest version

## Build
1. Run `pip install pyinstaller` in a privileged terminal
2. Navigate to the directory where the code is installed and run `pyinstaller --onefile --windowed main.py`
3. After PyInstaller completes, it creates two folders: `build` and `dist`. The dist folder contains your .exe file.

## Usage
1. Grab your decklist and export it to a text file
   * There are multiple ways to generate a list.  If your favorite deck builder is not listed, Pirate Deck requires `1 Name of Card` format. Quantity space Name of Card, with no additional 'section' entries.
    * You can also generate lists from the following export options on popular websites:
        * exported as "Text" and "1 Card Name" and "No Headers" from Archidekt
        * exported as a .txt from Tappedout
        * exported as MTGA format from Moxfield
* Use the `Select Deck File` button to load the file, selecting it from your system explorer
* `Generate Mass Import File` **optional** Once cards are collected and priced out, will generate an easy to use list for copy and pasting on TCG's mass import tool.
* `Open URLs in Firefox` **optional** Optionally opens new tabs in Firefox (and only firefox, sorry) once complete for each card. Note that quantity does not transfer to the tab, so be sure to double check your list.
