import io
from flask import Flask, request, jsonify
import boto3
from botocore.exceptions import NoCredentialsError
import os
import math
import zipfile
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from funcs import runAndroidAutomation, fetch_barcode, glens_results
from threading import Lock
from decorators import check_api
import requests
import json
import datetime
from chatgpt import *
from upc_backup_automation import *
from mitmproxy import http

import threading
import subprocess
load_dotenv()

app = Flask(__name__)

lock = Lock()
# Initialize S3 client
s3 = boto3.client("s3", region_name="ca-central-1")

# Replace 'your-bucket-name' with your actual S3 bucket name
BUCKET_NAME = os.getenv("BUCKET_NAME")


# Average compression speed in MB/s (adjust as needed)
COMPRESSION_SPEED_MB_PER_SEC = 1500


PUBLIC_BUCKET_URL = os.getenv("PUBLIC_BUCKET_URL")

canada_lock = Lock()  # Lock for Canadian automation
usa_lock = Lock()     # Lock for USA automation


# # Decoding helper function
# def decode_content(content):
#     """Attempt to decode the content using various encodings."""
#     encodings = ['utf-8', 'ISO-8859-1', 'latin1']
#     for enc in encodings:
#         try:
#             return content.decode(enc), enc
#         except UnicodeDecodeError:
#             continue
#     return None, None  # If none of the encodings work, return None

# # Interception and JSON saving function
# def response(flow: http.HTTPFlow) -> None:
#     # Check if the request is to the desired endpoint
#     if "match-visualsearch-ca.amazon.com" in flow.request.url:
#         # Intercepting and logging responses
#         print(f"\n[RESPONSE] {flow.request.url}")
#         print(f"Status Code: {flow.response.status_code}")
#         print(f"Headers: {flow.response.headers}")
        
#         # Try to decode the response body
#         decoded_body, encoding = decode_content(flow.response.content)
#         if decoded_body:
#             print(f"Response Body (decoded with {encoding}): {decoded_body}")
            
#             # Attempt to parse the decoded body as JSON
#             try:
#                 json_data = json.loads(decoded_body)  # Ensure it's in a JSON format
#                 # Define the path where you want to save the JSON file
#                 json_file_path = os.path.join('./', 'response.json')
                
#                 # Empty the file before writing (open in 'w' mode truncates the file)
#                 with open(json_file_path, 'w', encoding='utf-8') as json_file:
#                     # Save the JSON data to the file
#                     json.dump(json_data, json_file, ensure_ascii=False, indent=4)
                
#                 print(f"JSON saved to {json_file_path}")
#             except json.JSONDecodeError:
#                 print("Failed to decode response body as JSON")
#         else:
#             print(f"Response Body: Could not decode, binary content detected")

import time
from threading import Lock
lock_response = Lock()
# Flask route to fetch the saved JSON file
@app.route('/get_response', methods=['GET'])
def get_response():
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
                    
                    return jsonify(data), 200
                else:
                    # If the file is empty, wait for 3 seconds before checking again
                    time.sleep(3)
                    attempts+=1
        else:
            return jsonify({"error": "No data found"}), 404


# Function to run mitmdump as a background process
def run_mitmproxy():
    subprocess.call(['mitmdump', '-q', '-s', './test.py'])  # Use the correct script path


# Running mitmdump in a separate thread
def start_mitmdump_in_background():
    mitmproxy_thread = threading.Thread(target=run_mitmproxy)
    mitmproxy_thread.daemon = True  # Allows the thread to close when the Flask app exits
    mitmproxy_thread.start()

# Upload images in {username}/images folder in AWS S3 Bucket
@app.route("/upload", methods=["POST"])
def upload_files():
    username = request.form.get("username")
    if "files" not in request.files or not username:
        return jsonify({"error": "No files or username provided"}), 400

    files = request.files.getlist("files")
    upload_results = []

    for file in files:
        if file:
            try:
                file_name = file.filename
                s3_path = f"{username}/images/{file_name}"
                s3.upload_fileobj(file, BUCKET_NAME, s3_path)
                upload_results.append(
                    {"file_name": file_name, "s3_path": f"s3://{BUCKET_NAME}/{s3_path}"}
                )
            except NoCredentialsError:
                return jsonify({"error": "Credentials not available"}), 500
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    return (
        jsonify({"message": "Files uploaded successfully", "files": upload_results}),
        200,
    )


# Get stats of {username}/images folder inside AWS S3 bucket
@app.route("/stats", methods=["GET"])
def get_folder_stats():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "Username not provided"}), 400

    try:
        paginator = s3.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(
            Bucket=BUCKET_NAME, Prefix=f"{username}/images/"
        )

        image_names = []
        total_size = 0
        object_count = 0

        for page in page_iterator:
            if "Contents" in page:
                objects = page["Contents"]
                # Extract the image names
                image_names.extend(
                    item["Key"].split("images/")[1]
                    for item in objects
                    if "images/" in item["Key"]
                )
                object_count += len(objects)
                total_size += sum(obj["Size"] for obj in objects)

        total_size_mb = total_size / (1024 * 1024)
        estimated_time_to_zip = (
            total_size_mb / COMPRESSION_SPEED_MB_PER_SEC
            if COMPRESSION_SPEED_MB_PER_SEC > 0
            else 0
        )

        return (
            jsonify(
                {
                    "username": username,
                    "object_count": object_count - 1,
                    "total_size_bytes": total_size,
                    "total_size_kb": total_size / 1024,
                    "total_size_mb": total_size_mb,
                    "total_size_gb": total_size / (1024 * 1024 * 1024),
                    "estimated_time_to_zip_minutes": math.ceil(
                        estimated_time_to_zip * 60
                    ),
                    "images_list": image_names,
                }
            ),
            200,
        )
    except NoCredentialsError:
        return jsonify({"error": "Credentials not available"}), 500
    except Exception as e:
        print(f"Error when getting stats: {e}")
        return jsonify({"error": str(e)}), 500


# Endpoint to check if images.zip exists in {username} folder inside AWS S3 bucket
@app.route("/check_zip", methods=["GET"])
def check_zip_file():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "Username not provided"}), 400

    zip_file_key = f"{username}/images.zip"
    try:
        response = s3.head_object(Bucket=BUCKET_NAME, Key=zip_file_key)
        # If head_object does not raise an exception, the file exists
        zip_file_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{zip_file_key}"
        return jsonify({"is_available": True, "download_link": zip_file_url}), 200
    except s3.exceptions.ClientError as e:
        # If a 404 error is raised, the file does not exist
        if e.response["Error"]["Code"] == "404":
            return jsonify({"is_available": False}), 200
        else:
            # Handle other errors
            print(f"Error when checking for zip file: {e}")
            return jsonify({"error": str(e)}), 500


@app.route("/zip", methods=["GET"])
def zip_images_folder():
    username = request.args.get("username")
    email = request.args.get("email")
    if not username and not email:
        return jsonify({"error": "Username or Email not provided"}), 400

    try:
        # Create in-memory buffer for zip file
        zip_buffer = io.BytesIO()

        # Create a zip file with ZIP64 extensions enabled
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, True) as zipf:
            # List images in S3 folder
            paginator = s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(
                Bucket=BUCKET_NAME, Prefix=f"{username}/images/"
            ):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        image_key = obj["Key"]
                        print("Here is the zipping image: ", image_key)
                        # Get image data from S3
                        response = s3.get_object(Bucket=BUCKET_NAME, Key=image_key)
                        # Add image data to zip file
                        zipf.writestr(
                            os.path.basename(image_key), response["Body"].read()
                        )

        # Rewind buffer to start
        zip_buffer.seek(0)

        # Upload the zip file to S3
        s3_zip_key = f"{username}/images.zip"
        s3.upload_fileobj(zip_buffer, BUCKET_NAME, s3_zip_key)

        # Generate pre-signed URL for downloading the zip file
        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": s3_zip_key},
            ExpiresIn=3600,  # Link expires in 1 hour
        )

        # Generate public link for downloading the zip file
        download_link = PUBLIC_BUCKET_URL + s3_zip_key
        send_email(
            recipient=email,
            body=f"Congrats! Your images zipped successfully! <a href='{download_link}'>Click here</a> to download your images.zip file.",
        )
        return jsonify({"download_link": download_link}), 200
    except NoCredentialsError:
        send_email(
            email,
            body=f"Error occured while zipping your images. Please contact the Admin. Error: Credentials not available",
        )
        return jsonify({"error": "Credentials not available"}), 500
    except Exception as e:
        send_email(
            email,
            body=f"Error occured while zipping your images. Please try again later or contact the Admin. Error: {e}",
        )
        return jsonify({"error": str(e)}), 500


def send_email(
    recipient,
    subject="Soniclister Images Zipping process update",
    body="Congrats! Your images zipped successfully! <a href='http://example.com'>Click here</a> to view your images.",
):
    sender = os.getenv("SENDER_GMAIL")
    password = os.getenv("SENDER_GMAIL_APP_PASSWORD")
    try:
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp_server:
            smtp_server.login(sender, password)
            smtp_server.sendmail(sender, recipient, msg.as_string())
            smtp_server.quit()
        print("Message sent!")
    except Exception as e:
        print(e)


@app.route("/empty-folder", methods=["DELETE"])
def empty_images_folder():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "Username not provided"}), 400

    try:
        # Define the prefix for the user's images folder
        folder_prefix = f"{username}/images/"

        # List all objects in the folder
        objects_to_delete = []
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=folder_prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    objects_to_delete.append({"Key": obj["Key"]})

        if objects_to_delete:
            # Batch delete all objects
            delete_chunks = [
                objects_to_delete[i : i + 1000]
                for i in range(0, len(objects_to_delete), 1000)
            ]
            for chunk in delete_chunks:
                s3.delete_objects(Bucket=BUCKET_NAME, Delete={"Objects": chunk})

        s3.delete_object(Bucket=BUCKET_NAME, Key=f"{username}/images.zip")

        return (
            jsonify({"message": "Images folder emptied and recreated successfully"}),
            200,
        )

    except NoCredentialsError:
        return jsonify({"error": "Credentials not available"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/", methods=["GET"])
def hello_world():
    return "Hello, World!"


def fnsku_to_asin_logic_us_amz(product_code, entry_id, memento_lib_id, memento_token):
    with usa_lock:
        # Define the endpoint
        url = f"{os.getenv('NGROK_US_LAPTOP_ENDPOINT')}/product-scraper"

        # Define the parameters for the GET request
        params = {
            "product_code": product_code,
            "entryId": entry_id,
            "memento_lib_id": memento_lib_id,
            "mementoToken": memento_token,
        }

        # Make the GET request with the parameters
        response = requests.get(url, params=params)

        return response.status_code


def fnsku_to_asin_logic(fnskus):
    with canada_lock:
        results = []
        for fnsku in fnskus:
            try:
                print("FNSKU: ", fnsku)
                # fetch_barcode(fnsku)
                automation = runAndroidAutomation()
                # automation.setUp()
                max_attempts = 1
                attempts = 0
                asin = {"status": "None", "msg": "Initial attempt"}
                while attempts < max_attempts and asin["status"] != "success":
                    asin = automation.start_canada(fnsku)
                    attempts += 1
                    if asin["status"] == "success":
                        results.append(
                            {
                                "status": "success",
                                "msg": "Congrats! Your FNSKU code converted to ASIN",
                                "asin": asin["code"],
                                "fnsku": fnsku,
                            }
                        )
                        break
                    elif attempts >= max_attempts:
                        results.append(
                            {
                                "status": "failed",
                                "msg": f"Error: {asin['msg']}",
                                "fnsku": fnsku,
                            }
                        )
            except Exception as e:
                results.append(
                    {"status": "failed", "msg": f"Error: {e}", "fnsku": fnsku}
                )
        return results


def upc_to_asin_logic(code):
    url = "https://app.rocketsource.io/api/v3/convert"

    payload = json.dumps({"marketplace": "CA", "ids": [code]})
    headers = {
        "Content-Type": "application/json",
        "Authorization": f'Bearer {os.environ.get("ROCKETSOURCE_API_BEA_TOKEN")}',
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    response = response.json()
    print("UPC to ASIN response: ", response)
    return response


@app.route("/fnsku-converter", methods=["GET"])
def convert_fnsku_to_asin():
    fnskus = request.args.getlist("fnsku")
    if not fnskus:
        return jsonify(
            {"status": "failed", "msg": "At least one FNSKU Code is required!"}
        )

    results = fnsku_to_asin_logic(fnskus)
    return jsonify(results)


def image_gsearch(query, num):
    try:
        api_key = os.getenv("GSEARCH_API_KEY")
        cx = "96037465e37034601"
        request_url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cx}&q={query}&searchType=image&num={num}"

        response = requests.get(request_url)
        print("Response code: ", response)
        if response.status_code == 200:
            data = response.json()
            if "items" in data and len(data["items"]) > 0:
                image_urls = {}
                for i, item in enumerate(data["items"][:10]):
                    image_url = item["link"]
                    cleaned_image_url = (
                        image_url.replace(",", ".jpg").split(".jpg")[0] + ".jpg"
                    )
                    field_name = f"Online Image {i + 1}"
                    image_urls[field_name] = cleaned_image_url
                return image_urls
        return {"status": "failed", "msg": "NO images, something went wrong!"}
    except Exception as e:
        print("Here is the error: ", e)
        return None


@app.route("/custom-gsearch", methods=["GET"])
@check_api
def custom_gsearch():
    try:
        query = request.args.get("q")
        search_type = request.args.get("searchType")
        results_num = request.args.get("num")
        if not query and not search_type and not results_num:
            return jsonify(
                {
                    "status": "failed",
                    "msg": "Search Query, Search Type and Results Nums are Required ( q=your-search-query, searchType=image, num=10 ) !",
                }
            )
        results = None
        if search_type == "image":
            results = image_gsearch(query, results_num)

        return results
    except Exception as e:
        print("Here is the error in custom_gsearch:", e)
        return jsonify({"status": "failed", "msg": "something went wrong!"})


def get_price_history(asin):
    keepa_api_key = os.getenv("KEEPA_API_KEY")
    url = f"https://api.keepa.com/product?key={keepa_api_key}&domain=6&asin={asin}"

    response = requests.request("GET", url)

    response = response.text

    json_data = json.loads(response)
    csv_data = json_data["products"][0]["csv"][1]

    # Iterate in reverse to find the last available price
    for i in range(len(csv_data) - 1, 0, -2):
        if csv_data[i] != -1:
            last_available_timestamp = csv_data[i - 1]
            last_available_price = csv_data[i]
            break

    def convert_unix_to_human_time(unix_epoch_time):
        # Convert Unix epoch time to human-readable time
        human_time = datetime.datetime.fromtimestamp(unix_epoch_time)
        return human_time.strftime("%Y-%m-%d %H:%M:%S")

    unix_epoch_time = last_available_timestamp + 21564000
    unix_epoch_time = unix_epoch_time * 60
    human_time = convert_unix_to_human_time(unix_epoch_time)

    return {"timestamp": human_time, "price": last_available_price / 100}


def product_scraperapi(asin):
    scraperapi_api_key = os.getenv("SCRAPERAPI_API_KEY")
    results = None
    url = f"https://api.scraperapi.com/structured/amazon/product?api_key={scraperapi_api_key}&asin={asin}&country=amazon.ca&tld=ca&output=json"

    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)

    response = json.loads(response.text)
    if "full_description" in response and "pricing" in response and "name" in response:
        results = {
            "asin": asin,
            "title": response["name"],
            "description": response["full_description"],
            "price": response["pricing"],
            "image": response["images"][0],
            "status": "success",
        }

    elif (
        "full_description" not in response
        and "pricing" in response
        and "name" in response
    ):
        results = {
            "asin": asin,
            "title": response["name"],
            "price": response["pricing"],
            "image": response["images"][0],
            "status": "success",
        }

    elif (
        "full_description" not in response
        and "pricing" not in response
        and "name" in response
    ):
        last_price = get_price_history(asin)
        results = {
            "asin": asin,
            "title": response["name"],
            "price": f"${last_price['price']}",
            "image": response["images"][0],
            "status": "success",
        }

    elif (
        "full_description" in response
        and "pricing" not in response
        and "name" in response
    ):
        last_price = get_price_history(asin)
        results = {
            "asin": asin,
            "title": response["name"],
            "description": response["full_description"],
            "price": f"${last_price['price']}",
            "image": response["images"][0],
            "status": "success",
        }

    return results


def update_memento_entry(
    memento_lib_id,
    memento_token,
    memento_entryid,
    entry_title="",
    entry_msrp="",
    entry_image="",
    entry_description="",
    scrape_status="Scrape Failed",
):
    try:
        url = f"https://api.mementodatabase.com/v1/libraries/{memento_lib_id}/entries/{memento_entryid}?token={memento_token}"
        # Determine scrape status based on the entry_title
        # scrape_status = "Scrape Failed" if entry_title == "" else "Scrape Successful"
        if entry_title != "":
            scrape_status = "Scrape Successful"
        payload = json.dumps(
            {
                "fields": [
                    {
                        "id": 53,
                        "name": "Title",
                        "type": "text",
                        "value": entry_title,
                    },
                    {
                        "id": 12,
                        "name": "Description",
                        "type": "text",
                        "value": f"{entry_description}",
                    },
                    {"id": 13, "name": "MSRP", "type": "text", "value": entry_msrp},
                    {
                        "id": 27,
                        "name": "Auto-Image",
                        "type": "image",
                        "value": [entry_image],
                    },
                    {
                        "id": 58,
                        "name": "Scrape Status",
                        "type": "choice",
                        "value": scrape_status,
                    },
                ]
            }
        )
        headers = {"Content-Type": "application/json"}
        response = requests.request("PATCH", url, headers=headers, data=payload)
        print(response.text)
        return True
    except Exception as e:
        print("Error updating memento entry 1:", e)
        return False


@app.route("/product-scraper", methods=["GET"])
@check_api
def product_scraper():
    product_code = request.args.get("product_code")
    entry_id = request.args.getlist("entryId")
    memento_lib_id = request.args.get("memento_lib_id")
    memento_token = request.args.get("mementoToken")
    memento_entryid = entry_id[0]
    print("Here is the entry id: ", entry_id)
    if not product_code:
        return jsonify({"status": "failed", "msg": "Product Code is required!"})
    results = []
    usamazon = False
    usamazon_status_code = 0
    asin = None
    # Check if the code is ASIN
    if product_code.startswith("B0") and len(product_code) == 10:
        asin = product_code

    # Check if the code is FNSKU
    elif product_code.startswith("X0") and len(product_code) == 10:
        results = fnsku_to_asin_logic([product_code])
        print("Here is result you wanted: ", results)
        if results[0]["status"] == "success":
            asin = results[0]["asin"]
        else:
            usamazon_status_code = fnsku_to_asin_logic_us_amz(
                [product_code], memento_entryid, memento_lib_id, memento_token
            )
            print("Us AMZ Status Code: ", usamazon_status_code)
            usamazon = True

    # Check if the code is UPC (12 digits)
    elif product_code.isdigit():
        results = upc_to_asin_logic(product_code)
        if (
            product_code in results
            and results[product_code]
            and results[product_code][0] != "No ASIN found"
            and len(results[product_code][0]) == 1
        ):
            asin = results[product_code][0]
        else:
            asin = None

    if asin and usamazon == False:
        results = product_scraperapi(asin)
    elif asin is None and usamazon == False:
        results = get_product_info_selenium(product_code)

    if results != [] and usamazon == False:
        if "title" in results and "description" in results:
            description = rewrite_product_description(
                f"{results['title']} {results['description']}"
            )
            updated_entry = update_memento_entry(
                memento_lib_id,
                memento_token,
                memento_entryid,
                results["title"],
                results["price"],
                results["image"],
                description,
            )
        elif "title" in results and "description" not in results:
            description = rewrite_product_description(f"{results['title']}")
            updated_entry = update_memento_entry(
                memento_lib_id,
                memento_token,
                memento_entryid,
                results["title"],
                results["price"],
                results["image"],
                description,
            )
        if "shopping_results" in results:
            scrape_status = (
                "Scrape Successful, MSRP Pending Selection, Alternate Data Available"
            )
            if results["price"] is not None:
                scrape_status = "Scrape Successful, Alternate Data Available"
            insert_products_mementodb(
                memento_lib_id, memento_token, memento_entryid, results, scrape_status
            )
    elif results == [] and usamazon_status_code != 200:
        print("Hello it's failed usamazon automation request")
        update_memento_entry(memento_lib_id, memento_token, memento_entryid)
    return (
        jsonify({"message": "You have access to this endpoint", "items": results}),
        200,
    )


@app.route("/search-products", methods=["GET"])
@check_api
def search_products():
    query = request.args.get("title")
    # image = request.args.get("image")
    # image_lib = request.args.get("lib")
    if not query:
        return jsonify({"status": "failed", "msg": "title is required parameter!"})
    # if image is not None:
    #     memento_lib_id = request.args.get("memento_lib_id")
    #     memento_token = request.args.get("mementoToken")
    #     memento_entryid = request.args.get("entryId")
    #     image = image.strip("[]").split(", ")[0]
    #     print("Image: ", image, type(image))
    #     query = glens_results(image)
    #     description = rewrite_product_description(query)
    #     update_memento_entry(
    #         memento_lib_id=memento_lib_id,
    #         memento_token=memento_token,
    #         memento_entryid=memento_entryid,
    #         entry_title=query,
    #         entry_description=description,
    #     )
    #     print("Title from glens: ", query)
    #     sleep(5)
    memento_lib_id = request.args.get("memento_lib_id")
    memento_token = request.args.get("mementoToken")
    memento_entryid = request.args.get("entryId")
    # scraperapi_api_key = os.getenv("SCRAPERAPI_API_KEY")
    # amazon_search_url = f"https://api.scraperapi.com/structured/amazon/search?api_key={scraperapi_api_key}&country=ca&tld=ca&output=json&query={query}"
    # gshopping_search_url = f"https://api.scraperapi.com/structured/google/shopping?api_key={scraperapi_api_key}&country=ca&query={query}"
    # response = requests.request("GET", gshopping_search_url)
    # response = json.loads(response.text)

    headers = {
        "X-API-KEY": os.getenv("SERPER_DEV_API_KEY"),
        "Content-Type": "application/json",
    }
    # Get images for products from google
    google_images_search_url = "https://google.serper.dev/images"

    imgs_payload = json.dumps({"q": query, "location": "Canada", "gl": "ca", "num": 20})

    imgs_response = requests.request(
        "POST", google_images_search_url, headers=headers, data=imgs_payload
    )

    first_imgs_response = json.loads(imgs_response.text)

    # Get products from google
    gshopping_search_url = "https://google.serper.dev/shopping"

    payload = json.dumps({"q": query, "location": "Canada", "gl": "ca"})

    response = requests.request(
        "POST", gshopping_search_url, headers=headers, data=payload
    )
    first_response = json.loads(response.text)
    scrape_status = "Scrape Failed"
    search_data = {}
    main_results = []
    if len(first_response["shopping"]) > 0:
        # Combine corresponding dictionaries from first_imgs_response and first_response, prioritizing imageUrl from first_imgs_response
        for dict1, dict2 in zip(
            first_imgs_response["images"], first_response["shopping"]
        ):
            combined_dict = {
                **dict2,
                **dict1,
            }  # Combine dictionaries, with dict1 overwriting dict2 where keys overlap
            main_results.append(
                combined_dict
            )  # Add the combined dict to the main array
        search_data["shopping_results"] = main_results
        scrape_status = "Manual Entry Data Scraped"
    insert_products_mementodb(
        memento_lib_id, memento_token, memento_entryid, search_data, scrape_status
    )
    return jsonify({"status": "success"}), 200


from products_payload import *
import re

def clean_price(price_str):
    # Use regex to find all numerical parts of the string, including decimal points
    cleaned_price = re.findall(r'\d+(?:\.\d{1,2})?', price_str)
    
    if cleaned_price:
        return cleaned_price[0]  # Return the first valid price found
    return "None"  # Return None if no price is found

def insert_products_mementodb(
    memento_lib_id, memento_token, memento_entryid, data, scrape_status="Scrape Failed"
):
    try:
        url = f"https://api.mementodatabase.com/v1/libraries/{memento_lib_id}/entries/{memento_entryid}?token={memento_token}"
        images = []
        msrps = []

        # Default value for fields
        fields = [
            {
                "id": 58,
                "name": "Scrape Status",
                "type": "choice",
                "value": scrape_status,
            }
        ]

        if len(data["shopping_results"]) > 0:
            for result in data["shopping_results"]:
                images.append(result["imageUrl"])
                cleaned_price = clean_price(result["price"])
                msrps.append(cleaned_price)

            images_list = create_entries_products_for_images(images)
            msrps_list = create_entries_products_for_msrps(msrps)
            fields = images_list + msrps_list + fields

        payload = json.dumps({"fields": fields})
        headers = {"Content-Type": "application/json"}
        response = requests.request("PATCH", url, headers=headers, data=payload)
        return True
    except Exception as e:
        print("Error updating memento entry 2:", e)
        return False


if __name__ == "__main__":
    # Start mitmdump in the background
    # start_mitmdump_in_background()
    app.run(debug=True)
