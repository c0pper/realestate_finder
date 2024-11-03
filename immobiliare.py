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
from logging_setup import setup_logging
logger = setup_logging()

search_url = os.getenv("SEARCH_URL_IMMOBILIARE")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}

load_dotenv()

class ImmobiliareScraper():
    def __init__(self, search_url:str, listings_dir: str, driver) -> None:
        self.search_url = search_url
        self.listings_dir = Path(listings_dir)
        self.listings_dir.mkdir(exist_ok=True)
        self.driver = driver


    def extract_main_info(self, soup):
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
    def extract_detailed_features(self, announcement_url):  
        features = {} 
        self.driver.get(announcement_url)

        # Wait for the page to load
        time.sleep(2)  # Adjust based on the page load time

        # Click the "Accept Cookies" button if it is present
        try:
            time.sleep(0.5)
            accept_cookies_button = self.driver.find_element(By.ID, "didomi-notice-agree-button")
            accept_cookies_button.click()
            time.sleep(0.5)  # Wait for the action to complete
        except Exception as e:
            logger.info("No cookies consent button found")

        try:
            all_features = self.driver.find_element(By.CSS_SELECTOR, ".re-primaryFeatures__openDialogButton")
            # Find the button to open the dialog

            # Scroll the button into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", all_features)
            time.sleep(0.5)
            # Then, scroll an additional 100 pixels down
            self.driver.execute_script("window.scrollBy(0, -300);")

            # Wait a moment for the scroll to finish
            time.sleep(0.5)

            # Click the button to open the dialog
            open_dialog_button = self.driver.find_element(By.CSS_SELECTOR, ".nd-button.re-primaryFeatures__openDialogButton")
            open_dialog_button.click()

            # Wait for the dialog to appear
            time.sleep(0.5)  # Adjust as needed

            # Access the dialog content
            dialog_content = self.driver.find_element(By.CSS_SELECTOR, ".nd-dialogFrame__content")

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

        return features

    # Extract surface details
    def extract_surface_details(self, soup):
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
    def extract_badges(self, soup):
        try:
            badges_section = soup.find("div", class_="re-featuresBadges")
            badges = badges_section.find_all("div", class_="nd-badge")
            
            badge_list = [badge.text.strip() for badge in badges]
            
            return badge_list
        except AttributeError as e:
            logger.info(f"No badges found: {e}")
            return None

    # Extract cost details
    def extract_cost_details(self, soup):
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
    def scrape_listing(self, url):

            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.content, "html.parser")
            
            main_info = self.extract_main_info(soup)
            detailed_features = self.extract_detailed_features(url)
            surface_details = self.extract_surface_details(soup)
            badges = self.extract_badges(soup)
            cost_details = self.extract_cost_details(soup)
            


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


    def scrape_listings(self):
        page_num = 1  # Start from the first page
        logger.info(f"Checking page {page_num}")

        while True:
            # Update the URL with the current page number
            paginated_url = f"{self.search_url}&pag={page_num}"

            # response = requests.get(paginated_url, headers={"User-Agent": "Mozilla/5.0"})
            # if response.status_code != 200:
            #     logger.error(f"Failed to fetch page {page_num}. Status code: {response.status_code}")
            #     break
            self.driver.get(paginated_url)

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            listings = soup.find_all("div", class_="in-listingCard")
            if not listings:
                logger.info("No more listings found. Exiting pagination.")
                break

            for idx, listing in enumerate(listings, start=1):
                title_tag = listing.find("a", class_="in-listingCardTitle")
                listing_url = title_tag['href'] if title_tag else "N/A"
                listing_id = listing_url.split('annunci/')[1].replace("/", "")  # Extract the listing ID from the URL
                listing_file = self.listings_dir / f"immobiliare-{listing_id}.json"

                if not listing_file.exists():
                    logger.info(f"Scraping listing data for {listing_url} [{idx}/{len(listings)} listings on page {page_num}]")
                    listing_data = self.scrape_listing(listing_url)

                    with open(listing_file, 'w', encoding='utf-8') as f:
                        json.dump(listing_data, f, ensure_ascii=False, indent=4)
                        logger.info(f"\tSaved listing data for {self.__class__.__name__}-{listing_id} to {listing_file}")
                else:
                    pass
                    # logger.info(f"Listing data for {self.__class__.__name__}-{listing_id} already exists, skipping.")
            
            page_num += 1

        # Filter the listings
        filtered_data = self.filter_listings()

        # Check if there are any new listings
        with open("old_listings.txt", "r") as f:
            old_listings = f.read().splitlines()

        new_listings = [listing for listing in filtered_data if not f"immobiliare-{listing['url'].split('annunci/')[1].replace('/', '')}" in old_listings]

        # Append new listing IDs to old_listings.txt
        if new_listings:
            with open("old_listings.txt", "a") as f:
                for listing in new_listings:
                    listing_id = f"immobiliare-{listing['url'].split('annunci/')[1].replace('/', '')}"
                    f.write(f"{listing_id}\n")

        return new_listings


    def filter_listings(self):
        filtered_listings = []
        
        # Iterate through all JSON files in the given directory
        for file_path in self.listings_dir.glob("*.json"):
            if file_path.name.startswith("immobiliare"):
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
    immobiliare_scraper = ImmobiliareScraper(search_url=search_url, listings_dir="listings")
    immobiliare_scraper.scrape_listings()
    
