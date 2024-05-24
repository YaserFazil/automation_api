from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
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
    deviceName="cloud_arm",
    automationName="uiautomator2",
    ensureWebviewsHavePages=True,
    nativeWebScreenshot=True,
    newCommandTimeout=3600,
    connectHardwareKeyboard=True,
)

appium_server_url = os.getenv("APPIUM_SERVER_ENDPOINT")

try_again_btn = '//android.widget.TextView[@resource-id="com.amazon.mShop.android.shopping:id/a9vs_ss_try_again"]'
type_to_search = '//android.widget.TextView[@resource-id="com.amazon.mShop.android.shopping:id/a9vs_ss_text_search"]'
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

    def share_finder(self):
        asin = None
        while True:

            asin = self.get_text_from_clipboard()
            if asin:
                break

        return asin

    def get_text_from_clipboard(self):
        try:
            share_icon = self.driver.find_element(
                by=AppiumBy.XPATH,
                value=share_action,
            )
            share_icon.click()
            sleep(5)
            copy_icon = self.driver.find_element(
                by=AppiumBy.XPATH, value=copy_clipboard
            )
            copy_icon.click()
            clipboard = self.driver.get_clipboard_text()
            return clipboard
        except:
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
                sleep(5)
                open_app = self.driver.find_element(
                    by=AppiumBy.XPATH,
                    value='//android.widget.TextView[@content-desc="Amazon Shopping"]',
                )
                open_app.click()
                sleep(3)
                return True
            else:
                return False
        except Exception as e:
            print("Exception while closing the app: ", e)
            return False

    def start(self, fnsku) -> None:
        global max_opens
        global opens
        try:
            if opens == max_opens:
                app_reopened = self.reopen_app()
                if app_reopened:
                    opens = 0
            try:
                take_pic = self.driver.find_element(
                    by=AppiumBy.XPATH,
                    value='//android.widget.ImageView[@resource-id="com.amazon.mShop.android.shopping:id/chrome_action_bar_camera_icon"]',
                )
                take_pic.click()
            except:
                app_reopened = self.reopen_app()
                if app_reopened:
                    opens = 0
            sleep(5)
            barcode = self.driver.find_element(
                by=AppiumBy.XPATH,
                value='//android.widget.FrameLayout[@content-desc="btn_barcode"]',
            )
            barcode.click()
            sleep(5)

            max_attempts = 5
            attempts = 0

            while attempts < max_attempts:
                try:
                    # Attempt to find and click the product element
                    product = self.driver.find_element(
                        by=AppiumBy.XPATH,
                        value='//android.view.View[@resource-id="search"]/android.view.View[3]/android.view.View',
                    )
                    product.click()
                    break  # If the operation succeeds, break out of the loop
                except Exception as e:
                    attempts += 1
                    try:
                        sleep(3)
                        print("Fetch barcode to try search again")
                        fetch_barcode(fnsku, random.choice((96, 135)))
                        print("Barcode fetched to try search again")
                        not_searchable = self.driver.find_element(
                            by=AppiumBy.XPATH, value=try_again_btn
                        )
                        print("Try again search element found")
                        sleep(3)
                        not_searchable.click()
                        print("Try again search clicked")
                    except Exception as e:
                        print("Continue", e)
                        continue
                    sleep(3)
                    print(f"Attempt {attempts} failed: {e}")
                    sleep(1)  # Optional: wait for a second before retrying

            # If the loop finishes without breaking, handle the failure case
            if attempts == max_attempts:
                try:
                    scn_product_type = '//android.view.View[@resource-id="search"]/android.view.View[4]'
                    # Attempt to find and click the product element
                    product = self.driver.find_element(
                        by=AppiumBy.XPATH,
                        value=scn_product_type,
                    )
                    product.click()
                except:
                    try:
                        thr_product_type = '//android.view.View[@resource-id="search"]/android.view.View[2]'
                        # Attempt to find and click the product element
                        product = self.driver.find_element(
                            by=AppiumBy.XPATH,
                            value=thr_product_type,
                        )
                        product.click()
                    except:
                        # Code to handle the failure
                        print(
                            "Failed to find and click the product element after several attempts"
                        )
                        # Include the code you want to run in case of failure here
                        return {
                            "status": "failed",
                            "msg": "Reached max attempts for trying!",
                        }

            sleep(2)

            # Get ASIN from page source
            clipboard_text = self.share_finder()
            asin = get_asin_from_text(clipboard_text)
            self.tearDown()
            opens += 1
            if asin is not None:
                return {"status": "success", "code": asin}
            else:
                return {"status": "failed", "msg": "Not found ASIN"}
        except Exception as e:
            opens += 1
            return {"status": "failed", "msg": f"Error: {e}"}


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


def fetch_barcode(data, dpi=96):
    base_url = "https://barcode.tec-it.com/barcode.ashx"
    params = {
        "data": data,
        "code": "Code128",
        "translate-esc": "on",
        "unit": "Min",
        "imagetype": "JPG",
        "rotation": 90,
        "dpi": dpi,
    }
    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        barcode_image = Image.open(BytesIO(response.content))

        # Rotate the background image 270 degrees
        # barcode_image = barcode_image.rotate(90)
        barcode_image = barcode_image.resize((100, 25))
        # Create a white background image
        background = Image.new("RGB", (453, 267), "white")

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

        image_injection(background_bytes)
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
    # Find the short URL in the text
    short_url_pattern = r"https://a\.co/d/[A-Za-z0-9]+"
    short_url_match = re.search(short_url_pattern, text)

    if short_url_match:
        short_url = short_url_match.group(0)
        expanded_url = expand_url(short_url)
        if expanded_url:
            asin = extract_asin_from_url(expanded_url)
            return asin
        else:
            return None
    else:
        return None
