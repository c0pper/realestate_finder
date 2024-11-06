from datetime import datetime
import json
import os
from pathlib import Path
import re
import pandas as pd

from utils import get_driver
from logging_setup import setup_logging


def extract_date(date_str):
    # Match dates in various formats
    date_pattern = r'(\d{1,2})\s(\w+)\s(\d{4})|(\d{1,2})/(\d{1,2})/(\d{4})'
    match = re.search(date_pattern, date_str)
    month_mapping = {
        "gennaio": 1,
        "febbraio": 2,
        "marzo": 3,
        "aprile": 4,
        "maggio": 5,
        "giugno": 6,
        "luglio": 7,
        "agosto": 8,
        "settembre": 9,
        "ottobre": 10,
        "novembre": 11,
        "dicembre": 12,
    }
    if match:
        if match.group(1):  # Matches the first pattern (e.g., 2 Novembre 2024)
            day = int(match.group(1))
            month_str = match.group(2).lower()
            year = int(match.group(3))
            month = month_mapping.get(month_str)  # Get month number from the mapping
            return datetime(year, month, day).date()
        elif match.group(4):  # Matches the second pattern (e.g., 25/03/2024)
            day = int(match.group(4))
            month = int(match.group(5))
            year = int(match.group(6))
            return datetime(year, month, day).date()
    return None  # Return None if no date is found


def normalize(key, value):
    if key == "url":
        if value == "https://www.casa.it/immobili/49563499/":
            return key, value
    to_int_words = ["piano", "locali"]
    if any([word in key for word in to_int_words]) or key == "superficie":
        if "rialzato" in value:
            return key, 0
        if "ultimo" in value:
            return key, 99
        value = value.split(",")[0]
        digits = re.findall(r'\d+', value)
        return key, int("".join(digits))
    elif key == "badges" or key == "altre caratteristiche":
        key = "perks"
        if value:
            return key, value if isinstance(value, str) else ", ".join(value)
        else: 
            return key, value
    elif "disponibilità" in key or "rogito" in key:
        key = "disponibilità al rogito"
        return key, value
    elif key == "text":
        key = "descrizione"
        return key, value
    elif key == "price":
        value = value.split(",")[0]
        digits = re.findall(r'\d+', value)
        return key, int("".join(digits))
    elif key == "spese condominio" or key == "spese condominiali":
        key = "spese condominiali / mese"
        value = value.split(",")[0]
        if not value:
            return key, "Unknown"
        if "nessun" in value.lower():
            value = "uknown"
            return key, 0
        digits = re.findall(r'\d+', value)
        return key, int("".join(digits))
    elif key == "riscaldamento" or key == "aria condizionata" or key == "climatizzazione":
        key = "climatizzazione"
        return key, value
    elif key == "arredamento" or key == "arredato":
        key = "arredamento"
        return key, value
    elif "update" in key:
        return key, extract_date(value)
    elif "title" in key:
        return key, value
    else:
        return key, value




# Recursive function to flatten nested dictionaries
def flatten_dict(d, parent_key='', sep='__'):
    items = []
    for k, v in d.items():
        k = k.lower()
        new_key = k #f"{parent_key}{sep}{k}".lower() if parent_key else k
        if isinstance(v, dict):
            # Recursively flatten if the value is a dictionary
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            k, v = normalize(new_key, v)
            items.append((k, v))
    return dict(items)

# Function to flatten the main structure and dynamically handle nested dictionaries
def flatten_data(data):
    flat_data = {}
    
    # Flatten top-level keys and dynamically handle nested structures
    for key, value in data.items():
        key = key.lower()
        if isinstance(value, dict):
            # If value is a dictionary, flatten it with `flatten_dict`
            flat_data.update(flatten_dict(value, parent_key=key))
        else:
            # If not a dictionary, add it directly
            key, v = normalize(key, value)
            flat_data[key] = v
    
    return flat_data



if __name__ == "__main__":
    from casa import CasaScraper
    from immobiliare import ImmobiliareScraper
    logger = setup_logging()

    logger.info(f'Getting Immo Scraper')
    immo_scraper = ImmobiliareScraper(
        search_url=os.getenv("SEARCH_URL_IMMOBILIARE"),
        listings_dir="listings",
    )

    logger.info(f'Getting Casa Scraper')
    casa_scraper = CasaScraper(
        search_url=os.getenv("SEARCH_URL_CASA"),
        listings_dir="listings",
    )

    logger.info(f'Exporting from jsons')
    immo_scraper.export_filtered()
    casa_scraper.export_filtered()

    logger.info('Concatenating dataframes')
    combined_df = pd.concat([immo_scraper.df, casa_scraper.df], ignore_index=True)

    # Export to Excel
    try:
        combined_df.drop("prezzo", axis=1, inplace=True)
    except KeyError:
        pass

    combined_df.drop("reference", axis=1, inplace=True)
    combined_df.to_excel("combined_listings.xlsx", index=False)
    logger.info('Exported combined listings to Excel')
