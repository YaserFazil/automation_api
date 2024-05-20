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

load_dotenv()

app = Flask(__name__)


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
                    "object_count": object_count,
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
        send_email(email)
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
    body="Congrats! Your images zipped successfully!",
):
    sender = os.getenv("SENDER_GMAIL")
    password = os.getenv("SENDER_GMAIL_APP_PASSWORD")
    try:
        msg = MIMEText(body)
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

        # Recreate the empty folder by creating a zero-byte object with the folder's prefix
        s3.put_object(Bucket=BUCKET_NAME, Key=folder_prefix)

        return (
            jsonify({"message": "Images folder emptied and recreated successfully"}),
            200,
        )

    except NoCredentialsError:
        return jsonify({"error": "Credentials not available"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def hello_world():
    return "Hello, World!"


if __name__ == "__main__":
    app.run(debug=True)
