import logging
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

import pandas as pd

from casa import CasaScraper
from immobiliare import ImmobiliareScraper
from llm import json_to_human
from utils import already_refreshed, copy_ff_profile, get_driver
from logging_setup import setup_logging
logger = setup_logging()

load_dotenv()



def send_email(subject, body, to_email, from_email, password):
    # Set up the email server
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()  # Enable security
    server.login(from_email, password)  # Login to the email account
    
    # Create the email
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    # Send the email
    server.send_message(msg)
    server.quit()
    print("Email sent successfully!")


if __name__ == "__main__":
    if not already_refreshed():
        copy_ff_profile()
        driver = get_driver()

        logger.info(f'Getting Immo Scraper')
        immo_scraper = ImmobiliareScraper(
            search_url=os.getenv("SEARCH_URL_IMMOBILIARE"),
            listings_dir="listings",
            driver=driver
        )

        logger.info(f'Getting Casa Scraper')
        casa_scraper = CasaScraper(
            search_url=os.getenv("SEARCH_URL_CASA"),
            listings_dir="listings",
            driver=driver
        )


        new_listings = []
        logger.info(f'Getting Immo listings')
        new_listings.extend(immo_scraper.scrape_listings())

        logger.info(f'Getting Casa listings')
        new_listings.extend(casa_scraper.scrape_listings())

        driver.quit()

        if new_listings:
            logger.info(f'New listings: {[l["main_info"]["title"] for l in new_listings]}')

            body = ""
            for l in new_listings:
                human_desc = json_to_human(l)
                listing_url = l["url"]
                title = l["main_info"]["title"]
                body += f'{title}\n{human_desc}\n\nLink: {listing_url}\n\n------\n\n'

            # Configure your details
            from_email = "93simonster@gmail.com"
            to_email = "93simonster@gmail.com"
            password = os.getenv("GMAIL_APP_PW")

            subject = "New Listings Available"

            send_email(subject, body, to_email, from_email, password)
    else:
        pass