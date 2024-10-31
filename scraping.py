from datetime import date, datetime
import time
import requests

from bs4 import BeautifulSoup
from pathlib import Path
import json

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.common.exceptions import NoSuchElementException
import json
from pathlib import Path
from dotenv import load_dotenv
import os
import logging

load_dotenv()


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)

PREZZO_MASSIMO = os.getenv("PREZZO_MASSIMO")
url = f"https://www.immobiliare.it/vendita-case/napoli/con-piani-intermedi/?prezzoMinimo=160000&prezzoMassimo={PREZZO_MASSIMO}&superficieMinima=60&localiMinimo=3&balconeOterrazzo%5B0%5D=balcone&fasciaPiano%5B0%5D=30&idMZona%5B0%5D=78&idMZona%5B1%5D=10324&idMZona%5B2%5D=10323&idMZona%5B3%5D=79&idMZona%5B4%5D=81&idQuartiere%5B0%5D=12824&idQuartiere%5B1%5D=261&idQuartiere%5B2%5D=270&idQuartiere%5B3%5D=12814&idQuartiere%5B4%5D=273&idQuartiere%5B5%5D=283&idQuartiere%5B6%5D=12825&idQuartiere%5B7%5D=294&id=121783439&imm_source=bookmarkricerche"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}

listings_dir = Path("listings")
listings_dir.mkdir(exist_ok=True)


def is_raspberry_pi():
    try:
        with open('/proc/cpuinfo', 'r') as cpuinfo:
            if 'Raspberry Pi' in cpuinfo.read():
                return True
    except FileNotFoundError:
        pass
    return False


def get_driver():
    if is_raspberry_pi():
        options = Options()
        options.headless = True  # Run in headless mode
        driver = webdriver.Firefox(options=options, service=Service(executable_path='/usr/local/bin/geckodriver'))
    else:
        driver = webdriver.Firefox()
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
            piano = int(data.get("detailed_features", {}).get("Panoramica", {}).get("Piano", "0"))
            balcone = data.get("detailed_features", {}).get("Composizione dell'immobile", {}).get("Balcone", "").lower()

            description = data.get("main_info", {}).get("description", {}).get("title", "") + "\n" + data.get("main_info", {}).get("description", {}).get("text", "")
            
            # Check if 'disponibilità' is 'libero' and 'stato' is not 'da ristrutturare'
            if disponibilita == "libero" and stato != "da ristrutturare" and piano > 1 and balcone == "sì":
                if not any(word in description for word in ["nuda", "soppalco", "asta"]):
                    filtered_listings.append(data)
                    logger.warning(f'{data["url"]} is either nuda proprietà, has soppalco or is asta')
            else:
                logger.warning(f'{data["url"]} is either not libero, da ristrutturare, piano <= 1 or no balcone')
    
    return filtered_listings



def extract_main_info(soup):
    try:
        # Extract title
        title = soup.find("h1", class_="re-title__title").text.strip()

        # Find the reference, title, and description text if they exist
        reference_tag = soup.select_one(".re-contentDescriptionHeading__reference span")
        title_tag = soup.select_one(".re-contentDescriptionHeading__title")
        description_tag = soup.select_one(".in-readAll--lessContent div")

        # Extract text from the tags if they are found
        reference = reference_tag.text if reference_tag else "N/A"
        desc_title = title_tag.text if title_tag else "N/A"
        desc_text = description_tag.get_text(separator=" ", strip=True) if description_tag else "N/A"

        # Extract location
        location_parts = soup.select("a.re-title__link span.re-title__location")
        location = " - ".join([loc.text.strip() for loc in location_parts])
        
        last_update_element = soup.select_one(".re-lastUpdate__text")
        if last_update_element:
            last_update_text = last_update_element.get_text(strip=True)
        else:
            last_update_text = "N/A"

        # Extract price
        price = soup.find("div", class_="re-overview__price").span.text.strip()
        
        return {
            "title": title,
            "location": location,
            "price": price,
            "description": {
                "reference": reference,
                "title": desc_title,
                "text": desc_text
            },
            "last_update": last_update_text
        }
    except AttributeError as e:
        logger.info(f"Failed to extract main info: {e}")
        return None

# Extract detailed features
def extract_detailed_features(announcement_url):  
    features = {} 
    driver = get_driver()
    driver.get(announcement_url)

    # Wait for the page to load
    time.sleep(2)  # Adjust based on the page load time

    # Click the "Accept Cookies" button if it is present
    try:
        time.sleep(0.5)
        accept_cookies_button = driver.find_element(By.ID, "didomi-notice-agree-button")
        accept_cookies_button.click()
        time.sleep(0.5)  # Wait for the action to complete
    except Exception as e:
        logger.info("No cookies consent button found")

    try:
        all_features = driver.find_element(By.CSS_SELECTOR, ".re-primaryFeatures__openDialogButton")
        # Find the button to open the dialog

        # Scroll the button into view
        driver.execute_script("arguments[0].scrollIntoView(true);", all_features)
        time.sleep(0.5)
        # Then, scroll an additional 100 pixels down
        driver.execute_script("window.scrollBy(0, -300);")

        # Wait a moment for the scroll to finish
        time.sleep(0.5)

        # Click the button to open the dialog
        open_dialog_button = driver.find_element(By.CSS_SELECTOR, ".nd-button.re-primaryFeatures__openDialogButton")
        open_dialog_button.click()

        # Wait for the dialog to appear
        time.sleep(0.5)  # Adjust as needed

        # Access the dialog content
        dialog_content = driver.find_element(By.CSS_SELECTOR, ".nd-dialogFrame__content")

        # Extract features
        sections = dialog_content.find_elements(By.CLASS_NAME, "re-primaryFeaturesDialogSection")
    except NoSuchElementException:
        sections = []
        logger.warning(f"\t[!] No detailed features found for {announcement_url}")
    
    if sections:
        for section in sections:
            title = section.find_element(By.CLASS_NAME, "re-primaryFeaturesDialogSection__title").text
            features[title] = {}
            feature_items = section.find_elements(By.CLASS_NAME, "re-primaryFeaturesDialogSection__feature")
            
            for feature in feature_items:
                feature_title = feature.find_element(By.TAG_NAME, "dt").text
                feature_description = feature.find_element(By.TAG_NAME, "dd").text
                features[title][feature_title] = feature_description
    else:
        features["error"] = "no features found"

    driver.quit()

    return features

# Extract surface details
def extract_surface_details(soup):
    try:
        surface_section = soup.find("div", {"data-tracking-key": "surface-details"})
        details = {}
        elements = surface_section.find_all("dl", class_="re-surfaceElement__details")
        
        for element in elements:
            dt_elements = element.find_all("dt")
            dd_elements = element.find_all("dd")
            
            for dt, dd in zip(dt_elements, dd_elements):
                details[dt.text.strip()] = dd.text.strip()
        
        return details
    except AttributeError as e:
        logger.info(f"Failed to extract surface details: {e}")
        return None

# Extract badges
def extract_badges(soup):
    try:
        badges_section = soup.find("div", class_="re-featuresBadges")
        badges = badges_section.find_all("div", class_="nd-badge")
        
        badge_list = [badge.text.strip() for badge in badges]
        
        return badge_list
    except AttributeError as e:
        logger.info(f"No badges found: {e}")
        return None

# Extract cost details
def extract_cost_details(soup):
    try:
        cost_section = soup.find("div", {"data-tracking-key": "costs"})
        cost_items = cost_section.find_all("div", class_="re-featuresItem")
        
        cost_details = {}
        for item in cost_items:
            title = item.find("dt", class_="re-featuresItem__title").text.strip()
            description = item.find("dd", class_="re-featuresItem__description").text.strip()
            cost_details[title] = description
        
        return cost_details
    except AttributeError as e:
        logger.info(f"Failed to extract cost details: {e}")
        return None


# Function to scrape all required information from the listing URL
def scrape_listing(url):

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")
        
        main_info = extract_main_info(soup)
        detailed_features = extract_detailed_features(url)
        surface_details = extract_surface_details(soup)
        badges = extract_badges(soup)
        cost_details = extract_cost_details(soup)
        


        listing_data = {
            "date_scraped": date.today().isoformat(),
            "url": url,
            "main_info": main_info,
            "detailed_features": detailed_features,
            "surface_details": surface_details,
            "badges": badges,
            "cost_details": cost_details
        }
        
        return listing_data


def scrape_listings(url, listings_dir):
    page_num = 1  # Start from the first page

    while True:
        # Update the URL with the current page number
        paginated_url = f"{url}&pag={page_num}"

        response = requests.get(paginated_url, headers={"User-Agent": "Mozilla/5.0"})

        if response.status_code != 200:
            logger.error(f"Failed to fetch page {page_num}. Status code: {response.status_code}")
            break

        soup = BeautifulSoup(response.content, "html.parser")
        listings = soup.find_all("div", class_="in-listingCard")
        if not listings:
            logger.info("No more listings found. Exiting pagination.")
            break

        for idx, listing in enumerate(listings, start=1):
            title_tag = listing.find("a", class_="in-listingCardTitle")
            listing_url = title_tag['href'] if title_tag else "N/A"
            listing_id = listing_url.split('annunci/')[1].replace("/", "")  # Extract the listing ID from the URL
            listing_file = listings_dir / f"{listing_id}.json"

            if not listing_file.exists():
                logger.info(f"Scraping listing data for {listing_url} [{idx}/{len(listings)} listings on page {page_num}]")
                listing_data = scrape_listing(listing_url)

                with open(listing_file, 'w', encoding='utf-8') as f:
                    json.dump(listing_data, f, ensure_ascii=False, indent=4)
                    logger.info(f"\tSaved listing data for {listing_id} to {listing_file}")
            else:
                logger.info(f"Listing data for {listing_id} already exists, skipping.")
        
        page_num += 1

    # Filter the listings
    filtered_data = filter_listings(listings_dir)

    # Check if there are any new listings
    with open("old_listings.txt", "r") as f:
        old_listings = f.read().splitlines()

    new_listings = [listing for listing in filtered_data if not f"{listing['url'].split('annunci/')[1].replace('/', '')}" in old_listings]

    # Append new listing IDs to old_listings.txt
    if new_listings:
        with open("old_listings.txt", "a") as f:
            for listing in new_listings:
                listing_id = listing['url'].split('annunci/')[1].replace('/', '')
                f.write(f"{listing_id}\n")

    
    return new_listings




if __name__ == "__main__":
    scrape_listings(url, listings_dir)
    
