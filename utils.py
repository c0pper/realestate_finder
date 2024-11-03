import re
from pathlib import Path
import json

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
import json
from pathlib import Path
from dotenv import load_dotenv
import os
import logging

from selenium import webdriver
from logging_setup import setup_logging
logger = setup_logging()

load_dotenv()


search_url = os.getenv("SEARCH_URL_IMMOBILIARE")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}




def is_raspberry_pi():
    try:
        with open('/proc/cpuinfo', 'r') as cpuinfo:
            if 'Raspberry Pi' in cpuinfo.read():
                return True
    except FileNotFoundError:
        pass
    return False


def get_driver():
    options = Options()
    if is_raspberry_pi():
        # ff_profile = "/app/ff_profile/17ruxrsh.fake_prof"
        # options.profile = ff_profile
        options.headless = True  # Run in headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        service = Service(executable_path='/usr/local/bin/geckodriver')
        driver = webdriver.Firefox(options=options, service=service)
    else:
        # ff_profile = "/app/ff_profile/17ruxrsh.fake_prof"
        # ff_profile = "/home/simo/.mozilla/firefox/17ruxrsh.fake_prof"
        # options.profile = ff_profile
        # options.headless = True
        driver = webdriver.Firefox(options=options)
    return driver


def filter_listings(directory_path):
    filtered_listings = []
    
    # Iterate through all JSON files in the given directory
    for file_path in Path(directory_path).glob("*.json"):
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            
            # Get 'disponibilità' and 'stato' from 'Generale' section in 'detailed_features'
            disponibilita = data.get("detailed_features", {}).get("Generale", {}).get("Disponibilità", "").lower()
            stato = data.get("detailed_features", {}).get("Generale", {}).get("Stato", "").lower()
            piano = data.get("detailed_features", {}).get("Panoramica", {}).get("Piano", "0").split(",")[0]
            if "rialzato" in piano:
                piano = "1"
            match = re.search(r'\d+', piano)
            if match:
                piano = match.group(0)
            else:
                piano = 0  # or handle cases where no number is found
            balcone = data.get("detailed_features", {}).get("Composizione dell'immobile", {}).get("Balcone", "").lower()

            description = data.get("main_info", {}).get("description", {}).get("title", "") + "\n" + data.get("main_info", {}).get("description", {}).get("text", "")
            
            # Check if 'disponibilità' is 'libero' and 'stato' is not 'da ristrutturare'
            if disponibilita == "libero" and stato != "da ristrutturare" and int(piano) > 1 and balcone == "sì":
                if not any(word in description for word in ["nuda", "soppalco", "asta"]):
                    filtered_listings.append(data)
                else:
                    logger.warning(f'{data["url"]} is either nuda proprietà, has soppalco or is asta')
            else:
                logger.warning(f'{data["url"]} is either not libero, da ristrutturare, piano <= 1 or no balcone')
    
    return filtered_listings


