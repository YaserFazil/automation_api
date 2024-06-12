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
    '//android.widget.Button[@resource-id="android:id/chooser_copy_button"]'
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
        while True:

            asin = self.get_text_from_clipboard(share_xpath)
            if asin:
                break

        return asin

    def get_text_from_clipboard(self, share_xpath):
        try:
            share_icon = self.driver.find_element(
                by=AppiumBy.XPATH,
                value=share_xpath,
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
                sleep(2)
                return True
            else:
                return False
        except Exception as e:
            print("Exception while closing the app: ", e)
            return False

    def change_to_usa(self) -> None:
        try:
            global opens
            app_reopened = self.reopen_app()
            if app_reopened:
                opens = 0
            sleep(2)
            account_btn = self.driver.find_element(
                by=AppiumBy.XPATH,
                value='//android.widget.HorizontalScrollView[@resource-id="com.amazon.mShop.android.shopping:id/bottom_tab_nav_bar"]/android.widget.LinearLayout/androidx.appcompat.app.ActionBar.Tab[2]',
            )
            account_btn.click()
            sleep(2)
            country_btn = self.driver.find_element(
                by=AppiumBy.XPATH,
                value='//android.view.ViewGroup[@content-desc="anx_me_country_and_language"]/android.widget.ImageView',
            )
            country_btn.click()
            sleep(2)
            usa = self.driver.find_element(
                by=AppiumBy.XPATH,
                value='//android.widget.RadioButton[@text="United States - English Amazon.com"]',
            )

            usa.click()
            sleep(2)

            done_btn = self.driver.find_element(
                by=AppiumBy.XPATH,
                value='//android.widget.Button[@text="Done"]',
            )
            done_btn.click()
            return True
        except:
            return False

    def change_to_canada(self) -> None:
        try:
            global opens
            app_reopened = self.reopen_app()
            if app_reopened:
                opens = 0
            sleep(2)
            account_btn = self.driver.find_element(
                by=AppiumBy.XPATH,
                value='//android.widget.HorizontalScrollView[@resource-id="com.amazon.mShop.android.shopping:id/bottom_tab_nav_bar"]/android.widget.LinearLayout/androidx.appcompat.app.ActionBar.Tab[3]',
            )
            account_btn.click()
            sleep(2)
            country_btn = self.driver.find_element(
                by=AppiumBy.XPATH,
                value='//android.view.ViewGroup[@content-desc="anx_me_country_and_language"]/android.widget.ImageView',
            )
            country_btn.click()
            sleep(2)
            canada = self.driver.find_element(
                by=AppiumBy.XPATH,
                value='//android.widget.RadioButton[@text="Canada - English Amazon.ca"]',
            )

            canada.click()
            sleep(2)

            done_btn = self.driver.find_element(
                by=AppiumBy.XPATH,
                value='//android.widget.Button[@text="Done"]',
            )
            done_btn.click()
            return True
        except:
            return False

    def start_us(self, fnsku) -> None:
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

            max_attempts = 1
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
                    # try:
                    #     sleep(2)
                    #     print("Fetch barcode to try search again")
                    #     fetch_barcode(fnsku, random.choice((96, 135)))
                    #     print("Barcode fetched to try search again")
                    #     not_searchable = self.driver.find_element(
                    #         by=AppiumBy.XPATH, value=try_again_btn
                    #     )
                    #     print("Try again search element found")
                    #     sleep(2)
                    #     not_searchable.click()
                    #     print("Try again search clicked")
                    # except Exception as e:
                    print("Continue", e)
                    continue
                    # sleep(2)
                    # print(f"Attempt {attempts} failed: {e}")
                    # sleep(1)  # Optional: wait for a second before retrying
            sleep(2)
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
            return {"status": "failed", "msg": f"Error2: {e}"}

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
                take_pic = self.driver.find_element(
                    by=AppiumBy.XPATH,
                    value='//android.widget.ImageView[@resource-id="com.amazon.mShop.android.shopping:id/chrome_action_bar_camera_icon"]',
                )
                take_pic.click()
            except Exception:
                if self.reopen_app():
                    opens = 0

            sleep(5)

            # Click on the barcode icon
            barcode = self.driver.find_element(
                by=AppiumBy.XPATH,
                value='(//android.widget.ImageView[@resource-id="com.amazon.mShop.android.shopping:id/secondary_mode_image"])[3]',
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
                        value='//android.webkit.WebView[@text="Amazon.ca"]/android.view.View/android.view.View/android.view.View[3]',
                    )
                    product.click()
                    break
                except Exception as e:
                    attempts += 1
                    try:
                        fetch_barcode(fnsku, random.choice((96, 135)))

                        not_searchable = self.driver.find_element(
                            by=AppiumBy.XPATH,
                            value='//android.widget.Button[@text="Try Again"]',  # Adjusted example for try again button
                        )
                        sleep(2)
                        not_searchable.click()
                    except Exception as e:
                        try:
                            no_results = self.driver.find_element(
                                by=AppiumBy.XPATH,
                                value='//android.widget.TextView[@text="Results Check each product page for other buying options."]',
                            )
                            result = {
                                "status": "failed",
                                "msg": f"No product found.",
                                "fnsku": fnsku,
                            }
                            return result
                        except:
                            try:
                                no_results = self.driver.find_element(
                                    by=AppiumBy.XPATH,
                                    value='//android.widget.TextView[@text="Results Check each product page for other buying options. Price and other details may vary based on product size and colour."]',
                                )
                                result = {
                                    "status": "failed",
                                    "msg": f"No product found.",
                                    "fnsku": fnsku,
                                }
                                return result
                            except:
                                print("Continue")
                                continue
            sleep(2)

            # Handle failure case if all attempts are exhausted
            if attempts == max_attempts:
                try:
                    scn_product_type = '//android.webkit.WebView[@text="Amazon.ca"]/android.view.View/android.view.View/android.view.View[3]'
                    product = self.driver.find_element(
                        by=AppiumBy.XPATH, value=scn_product_type
                    )
                    product.click()
                except Exception:
                    try:
                        thr_product_type = '//android.webkit.WebView[@text="Amazon.ca"]/android.view.View/android.view.View/android.view.View[2]'
                        product = self.driver.find_element(
                            by=AppiumBy.XPATH, value=thr_product_type
                        )
                        product.click()
                    except Exception:
                        print(
                            "Failed to find and click the product element after several attempts"
                        )
                        return {
                            "status": "failed",
                            "msg": "Reached max attempts for trying! No product found",
                        }

            sleep(2)

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
        rotated_image.save("./barcode.png", format="PNG")
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
