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
    os.getenv("COPY_CLIPBOARD_XPATH")
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
                open_app = WebDriverWait(self.driver, 3).until(
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
            # # Reopen the app if the max number of opens is reached
            # if opens == max_opens:
            #     if self.reopen_app():
            #         opens = 0

            # # Try to click on the camera icon to take a picture
            # try:
            #     take_pic = WebDriverWait(self.driver, 6).until(
            #         EC.presence_of_element_located(
            #             (
            #                 AppiumBy.XPATH,
            #                 '//android.widget.ImageView[@resource-id="com.amazon.mShop.android.shopping:id/chrome_action_bar_camera_icon"]',
            #             )
            #         )
            #     )
            #     take_pic.click()
            # except TimeoutException:
            #     print(
            #         "TimeoutException while taking pic. No Camera Icon found in 6 seconds!"
            #     )
            #     if self.reopen_app():
            #         opens = 0
            #         take_pic = WebDriverWait(self.driver, 6).until(
            #             EC.presence_of_element_located(
            #                 (
            #                     AppiumBy.XPATH,
            #                     '//android.widget.ImageView[@resource-id="com.amazon.mShop.android.shopping:id/chrome_action_bar_camera_icon"]',
            #                 )
            #             )
            #         )
            #         take_pic.click()
            # except Exception:
            #     if self.reopen_app():
            #         opens = 0
            #         take_pic = WebDriverWait(self.driver, 6).until(
            #             EC.presence_of_element_located(
            #                 (
            #                     AppiumBy.XPATH,
            #                     '//android.widget.ImageView[@resource-id="com.amazon.mShop.android.shopping:id/chrome_action_bar_camera_icon"]',
            #                 )
            #             )
            #         )
            #         take_pic.click()

            # # Click on the barcode icon
            # barcode = WebDriverWait(self.driver, 6).until(
            #     EC.presence_of_element_located(
            #         (
            #             AppiumBy.XPATH,
            #             '(//android.widget.ImageView[@resource-id="com.amazon.mShop.android.shopping:id/secondary_mode_image"])[3]',
            #         )
            #     )
            # )
            # barcode.click()




            # Get ASIN from traffic
            opens += 1
            asin = search_barcode(fnsku)
            # self.driver.back()
            # self.driver.back()
            # self.driver.press_keycode(4)
            # self.driver.press_keycode(4)
            # self.tearDown()
        
            if asin:
                return {"status": "success", "code": asin}
            else:
                return {"status": "failed", "msg": "Not found ASIN"}

        except Exception as e:
            opens += 1
            print(f"Error1: {e}")
            return {"status": "failed", "msg": f"Error1: Asin Not Found"}
        
        finally:
            # self.driver.press_keycode(4)
            # self.driver.press_keycode(4)
            self.tearDown()            

import time
from threading import Lock
import json
lock_response = Lock()
# Flask route to fetch the saved JSON file
def get_json_response():
    with lock_response:
        json_file_path = os.path.join('./', 'response.json')
        
        # Check if the file exists
        if os.path.exists(json_file_path):
            max_attempts = 3
            attempts = 0
            # Wait until the file is not empty
            while attempts < max_attempts:
                # Check the file size
                if os.path.getsize(json_file_path) > 0:
                    with open(json_file_path, 'r', encoding='utf-8') as json_file:
                        data = json.load(json_file)
                    
                    # Empty the JSON file after reading its content
                    with open(json_file_path, 'w', encoding='utf-8') as json_file:
                        json_file.truncate(0)  # Clear the contents of the file
                    
                    return data
                else:
                    # If the file is empty, wait for 3 seconds before checking again
                    time.sleep(3)
                    attempts+=1
        else:
            return {"error": "No data found"}


def get_asin_from_response():    
    try:
        response = get_json_response()
        
        if "error" not in response:
            # Successful request, JSON data returned
            data = response
            print("Fetched response JSON data:")
            print(data)
            # Navigate through the JSON structure to get the converted barcodes (ASIN)
            try:
                search_result = data['occipital']['searchResult']
                if search_result:
                    asin = search_result[0]['properties']['convertedBarcodes'][0]
                    print(f"ASIN: {asin}")
                    return asin
                else:
                    print("No search result found.")
                    return None
            except KeyError as e:
                print(f"Key not found: {e}")
                return None
        else:
            print(f"Error: no data recieved")
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

def fetch_barcode(data, dpi=444):
    base_url = "https://barcode.tec-it.com/barcode.ashx"
    params = {
        "data": data,
        "code": "Code128",
        "translate-esc": "on",
        "unit": "Fit",
        "imagetype": "Png",
        "rotation": 0,
        "dpi": 222,
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



import requests
import json
import time
import math 
import hashlib

SEARCH_BARCODE_HEADERS = {
    'User-Agent': 'okhttp/4.9.1',
}

SEARCH_BARCODE_ENDPOINT = 'https://match-visualsearch-ca.amazon.com/vsearch/2.0'

def gen_authtoken(timestamp):
    secret = 'efb8826e4544bbab8992d757ec8b1116'
    username = 'amzn-mbl-cscan-ca'
    application = 'amzn-mbl-cscan-ca'

    sha512_hash = hashlib.sha512()
    data = secret + username + application + str(timestamp)
    sha512_hash.update(data.encode())

    return sha512_hash.hexdigest().upper()

def search_barcode(barcode):
    #TODO: Implement https://match-visualsearch-ca.amazon.com/vsearch/2.0 Body request
    timestamp = math.floor(time.time())
    authtoken = gen_authtoken(timestamp)
    print(authtoken)

    body_params = {
        'clientMessageVersion': '1.0',
        'orientation': '90',
        'uiMode': 'barcode_scanner',
        'application': 'amzn-mbl-cscan-ca',
        'lang': 'en_CA',
        'ts': timestamp,
        'username': 'amzn-mbl-cscan-ca',
        'groupingId': '5045eb49-d8bb-4cc5-ad5e-6796e894b876',
        'query_metadata' : '',
        'vsearch_params_json': '',
        'authtoken': authtoken
    }

    query_metdata = {
        "amznSessionId":"135-7799391-5389824",
        "clientVersion":"28.16.0.100",
        "cardsVersion":"1.0",
        "clientMessageVersion":"1.0",
        "amznDirectedCustomerId":"",
        "clientDeviceId":"06820589-f27d-40a0-ac10-b837d8b231ff", # changes
        "clientDevice":"Android - TECNO KF6i", # changes 
        "deviceManufacturer":"TECNO MOBILE", # changes 
        "clientDeviceVersion":"11",
        "intentScore":"6.000000",
        "clientId":"616076d7-be9c-4274-a566-ca80ddf70946", # changes
        "intentId":"0","initialPayloadSize":"0",
        "version":"0.9",
        "extra":"0",
    }

    vsearch_params_json = {
        "occipital":{
            "params":{
                "barcode":barcode,
                "barcodeType":"CODE_128"
            }
        }
    }

    body_params['query_metadata'] = json.dumps(query_metdata)
    body_params['vsearch_params_json'] = json.dumps(vsearch_params_json)

    res = requests.post(SEARCH_BARCODE_ENDPOINT, 
                        headers=SEARCH_BARCODE_HEADERS, data=body_params)
    
    if res.ok:
        converted_barcode = res.json()['occipital']['searchResult'][0]['properties']['convertedBarcodes'][0]
        print(f'Converted barcode : {converted_barcode}')

        return converted_barcode
    else:
        print(res.status_code)
        print(res.text)
    
    return ''

# if __name__ == '__main__':
#     search_barcode("x003kmqteh".upper())