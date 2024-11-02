from datetime import date
import re
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import json

from selenium.webdriver.common.by import By
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

search_url = os.getenv("SEARCH_URL_CASA")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}


class CasaScraper():
    def __init__(self, search_url:str, listings_dir: str, driver) -> None:
        self.search_url = search_url
        self.listings_dir = Path(listings_dir)
        self.listings_dir.mkdir(exist_ok=True)
        self.driver = driver

    def get_soup_with_selenium(self, url):
        self.driver.get(url)
        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        return soup

    def refuse_cookies(self):
        # Click the "Continue without accepting" button if it is present
        try:
            time.sleep(0.5)
            continue_without_agreeing_button = self.driver.find_element(By.CLASS_NAME, "didomi-continue-without-agreeing")
            continue_without_agreeing_button.click()
            time.sleep(0.5)  # Wait for the action to complete
        except Exception as e:
            logger.info("No 'Continue without accepting' button found")

    def extract_main_info(self, soup):
        try:
            # Extract title
            title = soup.find("h1").text.strip()

            # Find the reference, title, and description text if they exist
            reference_tag = soup.select_one(".re-contentDescriptionHeading__reference span")
            title_tag = soup.select_one(".re-contentDescriptionHeading__title")

            # Extract text from the tags if they are found
            reference = reference_tag.text if reference_tag else "N/A"
            desc_title = title_tag.text if title_tag else "N/A"
            desc_text = soup.select_one(".descr__desc").text

            last_update_text = soup.find("div", class_="updatedAt").text
            price = "€ " + soup.find("p", class_="csapdp-infos__price").find("span", class_="value").text
            
            return {
                "title": title,
                "location": '',
                "price": price,
                "description": {
                    "reference": reference,
                    "title": desc_title,
                    "text": desc_text
                },
                "last_update": last_update_text,
            }
        except AttributeError as e:
            logger.info(f"Failed to extract main info: {e}")
            return None

    # Extract detailed features
    def extract_detailed_features(self, soup):  
        main_features_container = soup.find("div", class_="grid boxed chars__box grid grid--direction-column")
        
        def extract_feature(container):
            data = {}
            for item in container.find_all("li", class_="chars_item"):
                label = item.find("p", class_="chars__lbl").get_text(strip=True)
                value = item.find("div", class_="chars__cnt").get_text(strip=True)
                data[label] = value
            return data

        # Extract "Caratteristiche" section
        general_features = main_features_container.find("ul", class_="chars__list mb--ml tp-s--m c-txt--f0 bt--s")
        general = extract_feature(general_features)

        # Extract "Efficienza energetica" section
        efficienza_energetica = main_features_container.find_all("ul", class_="chars__list mb--ml tp-s--m c-txt--f0 bt--s")[1]
        energy = extract_feature(efficienza_energetica)

        # Extract "Costi" section
        costi = main_features_container.find("ul", class_="chars__list tp-s--m c-txt--f0 bt--s")
        costs = extract_feature(costi)
        
        return {
            "general": general,
            "energy": energy,
            "cost_details": costs 
        }

    # Function to scrape all required information from the listing URL
    def scrape_listing(self, url):

        # response = requests.get(url, headers=headers)
        # soup = BeautifulSoup(response.content, "html.parser")
        soup = self.get_soup_with_selenium(url)
        
        main_info = self.extract_main_info(soup)
        detailed_features = self.extract_detailed_features(soup)
        # surface_details = self.extract_surface_details(soup)
        # badges = self.extract_badges(soup)
        # cost_details = self.extract_cost_details(soup)
        


        listing_data = {
            "date_scraped": date.today().isoformat(),
            "url": url,
            "main_info": main_info,
            "detailed_features": detailed_features,
        }
        
        return listing_data


    def scrape_listings(self):
        page_num = 1  # Start from the first page

        while True:
            # Update the URL with the current page number
            paginated_url = self.search_url.replace("page=1", f"page={page_num}")

            soup = self.get_soup_with_selenium(paginated_url)
            self.refuse_cookies()
            listings = soup.find_all("div", class_="csaSrpcard__cnt-card")
            if not listings:
                logger.info("No more listings found. Exiting pagination.")
                break

            for idx, listing in enumerate(listings, start=1):
                listing_url = "https://www.casa.it" + listing.find("a", class_="csaSrpcard__det__title--a")["href"]
                listing_id = listing_url.split('immobili/')[1].replace("/", "") 
                listing_file = self.listings_dir / f"casa-{listing_id}.json"

                if not listing_file.exists():
                    logger.info(f"Scraping listing data for {listing_url} [{idx}/{len(listings)} listings on page {page_num}]")
                    listing_data = self.scrape_listing(listing_url)

                    with open(listing_file, 'w', encoding='utf-8') as f:
                        json.dump(listing_data, f, ensure_ascii=False, indent=4)
                        logger.info(f"\tSaved listing data for {listing_id} to {listing_file}")
                else:
                    logger.info(f"Listing data for {listing_id} already exists, skipping.")
            
            page_num += 1

        # Filter the listings
        filtered_data = self.filter_listings()

        # Check if there are any new listings
        with open("old_listings.txt", "r") as f:
            old_listings = f.read().splitlines()

        new_listings = [listing for listing in filtered_data if not f"casa-{listing['url'].split('immobili/')[1].replace('/', '')}" in old_listings]

        # Append new listing IDs to old_listings.txt
        if new_listings:
            with open("old_listings.txt", "a") as f:
                for listing in new_listings:
                    listing_id = f"casa-{listing['url'].split('immobili/')[1].replace('/', '')}"
                    f.write(f"{listing_id}\n")

        return new_listings
    
    def filter_listings(self):
        filtered_listings = []
        
        # Iterate through all JSON files in the given directory
        for file_path in self.listings_dir.glob("*.json"):
            if file_path.name.startswith("casa"):
                with open(file_path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    
                    # Get 'disponibilità' and 'stato' from 'Generale' section in 'detailed_features'
                    general_features = data.get("detailed_features", {}).get("general", {})
                    disponibilita = general_features.get("Stato al rogito", "").lower()
                    stato = data.get("detailed_features", {}).get("energy", {}).get("Stato", "").lower()

                    
                    # Extract and process 'Piano' information
                    piano = general_features.get("Piano", "0").split("°")[0]
                    if "rialzato" in piano.lower():
                        piano = "1"
                    elif "ultimo" in piano.lower():
                        piano = "999"
                    else:
                        match = re.search(r'\d+', piano)
                        piano = match.group(0) if match else "0"  # Default to 0 if no number is found
                        
                    # Check for 'balcone' presence in 'Altre caratteristiche'
                    balcone = "balcone" in general_features.get("Altre caratteristiche", "").lower()

                    # Combine title and description for filtering keywords
                    title = data.get("main_info", {}).get("title", "")
                    description_text = data.get("main_info", {}).get("description", {}).get("text", "")
                    description = f"{title}\n{description_text}"
                    
                
                    # Define keywords with word boundaries for regex
                    unwanted_keywords = [r'\bnuda\b', r'\bsoppalco\b', r'\basta\b', r'\bnon mutuabile\b']
                    pattern = re.compile('|'.join(unwanted_keywords), re.IGNORECASE)

                    # Apply filtering criteria
                    if disponibilita == "libero" and stato != "da ristrutturare" and int(piano) > 1 and balcone:
                        if not pattern.search(description):
                            filtered_listings.append(data)
                        else:
                            logger.warning(f'{data["url"]} is either nuda proprietà, has soppalco or is an auction')
                    else:
                        logger.warning(f'{data["url"]} is either not libero, da ristrutturare, piano <= 1 or no balcone')
            
        return filtered_listings




if __name__ == "__main__":
    casa_scraper = CasaScraper(search_url=search_url, listings_dir="listings")
    casa_scraper.scrape_listings()
    
