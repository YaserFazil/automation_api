from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
)
import os
import requests
import json


def get_product_info_selenium(upc_code):
    # URL construction
    url = f"https://www.barcodelookup.com/{upc_code}"

    # Path to your ChromeDriver executable
    chrome_driver_path = "./chromedriver.exe"  # Update this to your ChromeDriver path

    # Setup Chrome options to behave like a regular browser
    chrome_options = Options()
    # chrome_options.add_argument(
    #     "--headless"
    # )  # Uncomment if you want to run headless
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    # Create a new instance of Chrome
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Open the URL
        driver.get(url)

        # Try to find the product title element
        try:
            title_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "h4"))
            )
            product_title = title_element.text.strip()
        except (TimeoutException, NoSuchElementException):
            # If the title is not found, return None since it's required
            return None

        # Try to find the product image element
        try:
            image_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "largeProductImage"))
            )
            image_url = image_element.find_element(By.TAG_NAME, "img").get_attribute(
                "src"
            )
        except (TimeoutException, NoSuchElementException):
            image_url = None

        # Try to find the product description element
        try:
            description_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.product-meta-data span.product-text")
                )
            )
            product_description = description_element.text.strip()
        except (TimeoutException, NoSuchElementException):
            product_description = None

        # Try to find the product price (MSRP) element
        try:
            price_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "store-link"))
            )
            product_price = price_element.text.strip()
        except (TimeoutException, NoSuchElementException):
            product_price = None

        # Print out the extracted information
        print(f"Product Title: {product_title}")
        print(f"Product Image URL: {image_url}")
        print(f"Product Description: {product_description}")
        print(f"Product Price (MSRP): {product_price}")

        # Structure the data as a dictionary and return it
        product_info = {
            "title": product_title,
            "image": image_url,
            "description": product_description,
            "price": product_price,
        }

        # Optionally, you can continue with the API call for further information
        scraperapi_api_key = os.getenv("SCRAPERAPI_API_KEY")
        gshopping_search_url = f"https://api.scraperapi.com/structured/google/shopping?api_key={scraperapi_api_key}&country=ca&query={product_title}"
        response = requests.get(gshopping_search_url)
        response_data = json.loads(response.text)
        product_info["shopping_results"] = response_data.get("shopping_results", [])[
            :10
        ]

        return product_info

    except Exception as e:
        return f"An error occurred: {str(e)}"

    finally:
        try:
            driver.delete_all_cookies()
            driver.quit()
            # Ensure the underlying Chrome process is also terminated
            if driver.service.process:
                driver.service.process.terminate()
        except WebDriverException as e:
            print(f"Error during cleanup: {str(e)}")


# Example usage:
upc_code = "0056500372994"
upc_code = "056500370389"
product_info = get_product_info_selenium(upc_code)
print(product_info)
