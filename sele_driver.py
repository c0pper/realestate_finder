from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

driver = webdriver.Firefox()  # or webdriver.Firefox(), etc.

try:
    # Open the target URL
    driver.get("https://www.google.com")  # Replace with the actual URL

    # Wait for the page to load
    time.sleep(3)  # Adjust based on the page load time

    # Find and click the button to open the dialog
    open_dialog_button = driver.find_element(By.CSS_SELECTOR, ".nd-button.re-primaryFeatures__openDialogButton")
    open_dialog_button.click()

    # Wait for the dialog to appear
    time.sleep(1)  # Adjust as needed

    # Access the dialog content
    dialog_content = driver.find_element(By.CSS_SELECTOR, ".nd-dialogFrame__content")
    print(dialog_content.get_attribute('innerHTML'))  # Prints the content of the dialog

finally:
    # Close the WebDriver
    driver.quit()