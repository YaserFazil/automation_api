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
    with lock:
        # Define the endpoint
        url = "https://e664-2607-fea8-edd-2000-d482-7a5a-9b71-bc19.ngrok-free.app/product-scraper"

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
    with lock:
        results = []
        for fnsku in fnskus:
            try:
                print("FNSKU: ", fnsku)
                fetch_barcode(fnsku)
                automation = runAndroidAutomation()
                automation.setUp()
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
        "Authorization": f'Bearer {os.getenv("ROCKETSOURCE_API_BEA_TOKEN")}',
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
):
    try:
        url = f"https://api.mementodatabase.com/v1/libraries/{memento_lib_id}/entries/{memento_entryid}?token={memento_token}"
        # Determine scrape status based on the entry_title
        scrape_status = "Scrape Failed" if entry_title == "" else "Scrape Successful"
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
        if product_code in results and results[product_code]:
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
        {"message": "You have access to this endpoint", "items": results},
        200,
    )


from time import sleep


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
    scraperapi_api_key = os.getenv("SCRAPERAPI_API_KEY")
    amazon_search_url = f"https://api.scraperapi.com/structured/amazon/search?api_key={scraperapi_api_key}&country=ca&tld=ca&output=json&query={query}"
    gshopping_search_url = f"https://api.scraperapi.com/structured/google/shopping?api_key={scraperapi_api_key}&country=ca&query={query}"
    response = requests.request("GET", gshopping_search_url)
    response = json.loads(response.text)
    scrape_status = "Scrape Failed"
    if len(response["shopping_results"]) > 0:
        scrape_status = "Manual Entry Data Scraped"
    insert_products_mementodb(
        memento_lib_id, memento_token, memento_entryid, response, scrape_status
    )
    return response


from products_payload import *


def insert_products_mementodb(
    memento_lib_id, memento_token, memento_entryid, data, scrape_status="Scrape Failed"
):
    try:
        url = f"https://api.mementodatabase.com/v1/libraries/{memento_lib_id}/entries/{memento_entryid}?token={memento_token}"
        images = []
        msrps = []
        if len(data["shopping_results"]) > 0:
            for result in data["shopping_results"]:
                images.append(result["thumbnail"])
                msrps.append(result["extracted_price"])
            images_list = create_entries_products_for_images(images)
            msrps_list = create_entries_products_for_msrps(msrps)
            fields = (
                images_list
                + msrps_list
                + [
                    {
                        "id": 58,
                        "name": "Scrape Status",
                        "type": "choice",
                        "value": scrape_status,
                    }
                ]
            )
        payload = json.dumps({"fields": fields})
        headers = {"Content-Type": "application/json"}
        response = requests.request("PATCH", url, headers=headers, data=payload)
        return True
    except Exception as e:
        print("Error updating memento entry 2:", e)
        return False


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
