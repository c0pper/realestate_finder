from datetime import datetime
import re
from pathlib import Path
import json
import shutil

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
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
    logger.info(f'Getting driver')
    options = Options()
    if is_raspberry_pi():
        profile = FirefoxProfile("/home/pi/docker/bots/realestate_finder/ff_profile/17ruxrsh.fake_prof")
        
        profile.set_preference("browser.cache.disk.enable", False)
        profile.set_preference("browser.cache.memory.enable", False)
        profile.set_preference("browser.cache.offline.enable", False)
        profile.set_preference("network.http.use-cache", False)
        profile.set_preference("browser.privatebrowsing.autostart", True)
        
        options.profile = profile
        options.headless = True
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')

        service = Service(executable_path='/usr/local/bin/geckodriver')
        driver = webdriver.Firefox(options=options, service=service)
    else:
        # ff_profile = "/app/ff_profile/17ruxrsh.fake_prof"
        ff_profile = "/home/simo/.mozilla/firefox/17ruxrsh.fake_prof"
        options.profile = ff_profile
        options.headless = True
        driver = webdriver.Firefox(options=options)
    return driver


def already_refreshed():
    """Check if the program already ran today."""
    executions_path = Path("/home/simo/code/realestate_finder/executions.json")
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Load existing executions or create a new file if it doesn't exist
    if executions_path.exists():
        with executions_path.open("r") as f:
            executions = json.load(f)
    else:
        executions = {}

    # Check if today's date is already in executions
    if today_str in executions:
        logger.info("Already checked listings for today.")
        return True
    else:
        # Update executions.json with today’s date
        executions[today_str] = "refreshed"
        with executions_path.open("w") as f:
            json.dump(executions, f)
        return False


def copy_ff_profile():
    logger.info(f"Refreshing fake FF profile...")
    # Define source and destination paths
    src = Path("/home/simo/.mozilla/firefox/auq1dm16.default-release/")
    dest = Path("/home/simo/.mozilla/firefox/17ruxrsh.fake_prof/")

    counter = 0
    excluded_folders = {"chrome", "storage"}
    items = [item for item in src.iterdir() if item.name not in excluded_folders]

    # Copy each file and directory from src to dest, overwriting existing files
    items = list(src.iterdir())
    for item in items:
        dest_item = dest / item.name
        if item.is_dir():
            # If it's a directory, copy it and overwrite if it exists
            if dest_item.exists():
                shutil.rmtree(dest_item)
            shutil.copytree(item, dest_item)
        else:
            # If it's a file, copy and overwrite it
            try:
                shutil.copy2(item, dest_item)
            except FileNotFoundError as e:
                logger.warning(e)

        # Increment the counter and log every 20 items
        counter += 1
        if counter % 20 == 0:
            logger.info(f"Copied {counter}/{len(items)} items so far...")