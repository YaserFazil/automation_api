from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from time import sleep
from dotenv import load_dotenv
import os
from io import BytesIO
from PIL import Image
import requests
import re
import random

load_dotenv()

capabilities = dict(
    platformName="Android",
    # deviceName="cloud_arm",
    automationName="uiautomator2",
    # ensureWebviewsHavePages=True,
    # nativeWebScreenshot=True,
    # newCommandTimeout=3600,
    # connectHardwareKeyboard=True,
)

appium_server_url = os.getenv("APPIUM_SERVER_ENDPOINT")

try_again_btn = '//android.widget.TextView[@resource-id="com.amazon.mShop.android.shopping:id/a9vs_ss_try_again"]'
type_to_search = '//android.widget.TextView[@resource-id="com.amazon.mShop.android.shopping:id/a9vs_ss_text_search"]'
copy_clipboard = (
    '//android.widget.LinearLayout[@resource-id="android:id/chooser_action_row"]'
)
copy_clipboard = (
    '//android.widget.FrameLayout[@content-desc="Copy"]/android.widget.ImageView'
)
share_action = '//android.view.View[@resource-id="ssf-share-action"]'

max_opens = 5
opens = 0


class runAndroidAutomation:
    def setUp(self) -> None:
        self.driver = webdriver.Remote(
            appium_server_url,
            options=UiAutomator2Options().load_capabilities(capabilities),
        )

    def share_finder(self, share_xpath=share_action):
        asin = None
        max_attempts = 3
        attempts = 0

        while attempts < max_attempts:
            attempts += 1
            asin = self.get_text_from_clipboard(share_xpath)
            if asin:
                break

        return asin

    def get_text_from_clipboard(self, share_xpath):
        try:
            # Wait for the share icon to load (adjust the timeout and CSS selector as needed)
            share_icon = WebDriverWait(self.driver, 6).until(
                EC.presence_of_element_located((AppiumBy.XPATH, share_xpath))
            )
            share_icon.click()
            copy_icon = WebDriverWait(self.driver, 6).until(
                EC.presence_of_element_located((AppiumBy.XPATH, copy_clipboard))
            )
            copy_icon.click()
            clipboard = self.driver.get_clipboard_text()
            print("Clipboard Text: ", clipboard)
            return clipboard
        except TimeoutException:
            print(
                "TimeoutException at get_text_from_clipboard function. No share or copy icon found in 6 seconds!"
            )
            return None
        except Exception as e:
            print("Error while running get_text_from_clipboard function: ", e)
            return None

    def tearDown(self) -> None:
        if self.driver:
            self.driver.quit()

    def reopen_app(self) -> None:
        try:
            app_terminated = self.driver.terminate_app(
                "com.amazon.mShop.android.shopping"
            )
            if app_terminated:
                open_app = WebDriverWait(self.driver, 6).until(
                    EC.presence_of_element_located(
                        (
                            AppiumBy.XPATH,
                            '//android.widget.TextView[@content-desc="Amazon Shopping"]',
                        )
                    )
                )
                open_app.click()
                sleep(2)
                return True
            else:
                return False
        except TimeoutException:
            print(
                "TimeoutException while opening the Amazon Shopping app. No Amazon Shopping app found in 6 seconds!"
            )
            return False
        except Exception as e:
            print("Exception while closing the app: ", e)
            return False

    def start_canada(self, fnsku) -> None:
        global max_opens
        global opens

        try:
            # Reopen the app if the max number of opens is reached
            if opens == max_opens:
                if self.reopen_app():
                    opens = 0

            # Try to click on the camera icon to take a picture
            try:
                take_pic = WebDriverWait(self.driver, 6).until(
                    EC.presence_of_element_located(
                        (
                            AppiumBy.XPATH,
                            '//android.widget.ImageView[@resource-id="com.amazon.mShop.android.shopping:id/chrome_action_bar_camera_icon"]',
                        )
                    )
                )
                take_pic.click()
            except TimeoutException:
                print(
                    "TimeoutException while taking pic. No Camera Icon found in 6 seconds!"
                )
                if self.reopen_app():
                    opens = 0
            except Exception:
                if self.reopen_app():
                    opens = 0

            # Click on the barcode icon
            barcode = WebDriverWait(self.driver, 6).until(
                EC.presence_of_element_located(
                    (
                        AppiumBy.XPATH,
                        '(//android.widget.ImageView[@resource-id="com.amazon.mShop.android.shopping:id/secondary_mode_image"])[3]',
                    )
                )
            )
            barcode.click()

            max_attempts = 1
            attempts = 0

            while attempts < max_attempts:
                try:
                    # Attempt to find and click the product element
                    product = WebDriverWait(self.driver, 6).until(
                        EC.presence_of_element_located(
                            (
                                AppiumBy.XPATH,
                                '//android.view.View[@resource-id="search"]/android.view.View[3]',
                            )
                        )
                    )
                    product.click()
                    break
                except TimeoutException:
                    attempts += 1
                    try:
                        xpath_product = '//android.view.View[@resource-id="search"]/android.view.View[4]'
                        # Scroll until the element is found using UiScrollable
                        self.driver.find_element(
                            AppiumBy.ANDROID_UIAUTOMATOR,
                            "new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView("
                            'new UiSelector().xpath("{}"))'.format(xpath_product),
                        )
                        another_product = WebDriverWait(self.driver, 6).until(
                            EC.presence_of_element_located(
                                (
                                    AppiumBy.XPATH,
                                    xpath_product,
                                )
                            )
                        )
                        another_product.click()
                    except Exception as e:
                        print("Continue")
                        continue

            # Handle failure case if all attempts are exhausted
            if attempts == max_attempts:
                try:
                    scn_product_type = '//android.webkit.WebView[@text="Amazon.ca"]/android.view.View/android.view.View/android.view.View[3]'
                    product = WebDriverWait(self.driver, 6).until(
                        EC.presence_of_element_located(
                            (
                                AppiumBy.XPATH,
                                scn_product_type,
                            )
                        )
                    )
                    product.click()
                except TimeoutException:
                    try:
                        thr_product_type = '//android.webkit.WebView[@text="Amazon.ca"]/android.view.View/android.view.View/android.view.View[2]'
                        product = WebDriverWait(self.driver, 6).until(
                            EC.presence_of_element_located(
                                (
                                    AppiumBy.XPATH,
                                    thr_product_type,
                                )
                            )
                        )
                        product.click()
                    except TimeoutException:
                        try:
                            fourt_product_type = '//android.webkit.WebView[@text="Amazon.ca"]/android.view.View/android.view.View/android.view.View[2]'
                            product = WebDriverWait(self.driver, 6).until(
                                EC.presence_of_element_located(
                                    (
                                        AppiumBy.XPATH,
                                        fourt_product_type,
                                    )
                                )
                            )
                            product.click()
                        except TimeoutException:
                            print(
                                "Failed to find and click the product element after several attempts"
                            )
                            return {
                                "status": "failed",
                                "msg": "Reached max attempts for trying! No product found",
                            }

            # Get ASIN from page source
            clipboard_text = self.share_finder('//android.widget.Image[@text="Share"]')
            asin = get_asin_from_text(clipboard_text)
            self.tearDown()
            opens += 1

            if asin:
                return {"status": "success", "code": asin}
            else:
                return {"status": "failed", "msg": "Not found ASIN"}

        except Exception as e:
            opens += 1
            print(f"Error1: {e}")
            return {"status": "failed", "msg": f"Error1: Asin Not Found"}


# Replace these with your actual username and password
username = os.getenv("GENYMOTION_USERNAME")
password = os.getenv("GENYMOTION_PASSWORD")
genymotion_ip_address = os.getenv("GENYMOTION_INSTANCE_IP")


def image_injection(image_b):
    url = f"https://{genymotion_ip_address}/api/v1/camera/image"
    auth = (username, password)
    headers = {"accept": "application/json", "Content-Type": "image/*"}
    response = requests.put(url, auth=auth, headers=headers, data=image_b, verify=False)

    if response.status_code == 200:
        return {
            "status": "success",
            "msg": "Congrats! Image updated on Genymotion Emulator",
        }
    else:
        return {"status": "failed", "msg": f"Response Content: {response}"}


def fetch_barcode(data, dpi=444):
    base_url = "https://barcode.tec-it.com/barcode.ashx"
    params = {
        "data": data,
        "code": "Code128",
        "translate-esc": "on",
        "unit": "Fit",
        "imagetype": "Png",
        "rotation": 90,
        "dpi": 333,
    }
    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        barcode_image = Image.open(BytesIO(response.content))

        # Create a white background image
        background = Image.new("RGB", (1400, 1100), "white")

        # Calculate the position to center the barcode image on the background
        position = (
            (background.width - barcode_image.width) // 2,
            (background.height - barcode_image.height) // 2,
        )

        # Paste the barcode image onto the background
        background.paste(barcode_image, position)

        # Convert the final image to bytes
        byte_arr = BytesIO()
        background.save(byte_arr, format="PNG")
        background_bytes = byte_arr.getvalue()

        # Load the image from bytes
        image = Image.open(BytesIO(background_bytes))

        # Rotate the image (e.g., 90 degrees)
        rotated_image = image.rotate(360, expand=True)

        # Save the rotated image as 'barcode.png'
        rotated_image.save("./images/barcode.png", format="PNG")
        print("Barcode image saved as 'barcode.png'")

        # Return success response
        return {
            "status": "success",
            "msg": "Congrats! Image updated on Genymotion Emulator",
        }
    else:
        print(f"Failed to fetch barcode. Status code: {response.status_code}")
        return {"status": "failed", "msg": f"Response Content: {response}"}


def fetch_barcode_old(data, dpi=444):
    base_url = "https://barcode.tec-it.com/barcode.ashx"
    params = {
        "data": data,
        "code": "Code128",
        "translate-esc": "on",
        "unit": "Fit",
        "imagetype": "Png",
        "rotation": 90,
        "dpi": 444,
    }
    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        barcode_image = Image.open(BytesIO(response.content))
        # barcode_image = barcode_image.resize((155, 350))
        # Rotate the background image 270 degrees
        # barcode_image = barcode_image.rotate(90)
        # barcode_image = barcode_image.resize((35, 120))
        # Create a white background image
        background = Image.new("RGB", (1400, 1100), "white")

        # Calculate the position to center the barcode image on the background
        position = (
            (background.width - barcode_image.width) // 2,
            (background.height - barcode_image.height) // 2,
        )

        # Paste the barcode image onto the background
        background.paste(barcode_image, position)
        # background = background.resize((500, 216))

        # Convert the final image to bytes
        byte_arr = BytesIO()
        background.save(byte_arr, format="PNG")
        background_bytes = byte_arr.getvalue()
        # Load the image from bytes
        image = Image.open(BytesIO(background_bytes))

        # Rotate the image (e.g., 90 degrees)
        rotated_image = image.rotate(360, expand=True)

        # Save the rotated image back to bytes
        rotated_byte_arr = BytesIO()
        rotated_image.save(rotated_byte_arr, format="PNG")
        rotated_background_bytes = rotated_byte_arr.getvalue()
        # image_injection(rotated_background_bytes)
        print("Barcode image saved as 'barcode.png'")
        return {
            "status": "success",
            "msg": "Congrats! Image updated on Genymotion Emulator",
        }
    else:
        print(f"Failed to fetch barcode. Status code: {response.status_code}")
        return {"status": "failed", "msg": f"Response Content: {response}"}


def expand_url(short_url):
    try:
        response = requests.get(short_url, allow_redirects=True)
        return response.url
    except requests.RequestException as e:
        print(f"Error expanding URL: {e}")
        return None


def extract_asin_from_url(url):
    # Define a regex pattern to match the ASIN in the expanded URL
    pattern = r"/([A-Za-z0-9]{10})(?:[/?]|$)"

    # Search for the pattern in the given URL
    match = re.search(pattern, url)
    # If a match is found, extract the ASIN
    if match:
        asin = match.group(1)
        return asin
    else:
        return None


def get_asin_from_text(text):
    try:
        # First, try to find a short URL in the text
        short_url_pattern = r"https://a\.co/d/[A-Za-z0-9]+"
        short_url_match = re.search(short_url_pattern, text)

        print("Shared URL of the product: ", text)
        if short_url_match:
            short_url = short_url_match.group(0)
            expanded_url = expand_url(short_url)
            if expanded_url:
                asin = extract_asin_from_url(expanded_url)
                if asin:
                    print("ASIN from short URL: ", asin)
                    return asin
                else:
                    raise Exception
            else:
                raise Exception
        else:
            raise Exception
            # If expanding the short URL doesn't work, we still try the next pattern
    except Exception as e:
        print("trying full amazon url")
        try:
            # If no short URL found or URL expansion didn't work, try the full Amazon URL pattern
            amazon_url_pattern = r"https://www\.amazon\.ca+/dp/([A-Z0-9]+)"
            amazon_url_match = re.search(amazon_url_pattern, text)

            if amazon_url_match:
                full_url = amazon_url_match.group(1)
                print("Here is the full url: ", full_url)
                asin = extract_asin_from_url(full_url)
                asin = full_url
                if asin:
                    print("ASIN from full URL: ", asin)
                    return asin
        except Exception as e:
            print("not worked")
            # If neither pattern matches, return None
            return None


from serpapi import GoogleSearch


def glens_results(image_url):
    serpapi_api_key = os.getenv("SERPAPI_COM_API_KEY")
    params = {
        "api_key": serpapi_api_key,
        "engine": "google_lens",
        "url": f"{image_url}",
        "hl": "en",
        "country": "ca",
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    print("Glens results: ", results)
    title = results["visual_matches"][0]["title"]
    return title
