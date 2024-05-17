import io
from flask import Flask, request, jsonify
import boto3
from botocore.exceptions import NoCredentialsError
import os
import math
import zipfile
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


# Initialize S3 client
s3 = boto3.client("s3", region_name="ca-central-1")

# Replace 'your-bucket-name' with your actual S3 bucket name
BUCKET_NAME = os.getenv("BUCKET_NAME")


# Average compression speed in MB/s (adjust as needed)
COMPRESSION_SPEED_MB_PER_SEC = 500


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
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=f"{username}/images/")
        if "Contents" in response:
            object_count = len(response["Contents"])
            total_size = sum(obj["Size"] for obj in response["Contents"])
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
                        "total_size_mb": total_size / (1024 * 1024),
                        "total_size_gb": total_size / (1024 * 1024 * 1024),
                        "estimated_time_to_zip_minutes": math.ceil(
                            estimated_time_to_zip * 60
                        ),
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "username": username,
                        "object_count": 0,
                        "total_size_bytes": 0,
                        "total_size_kb": 0,
                        "total_size_mb": 0,
                        "total_size_gb": 0,
                        "estimated_time_to_zip_minutes": 0,
                    }
                ),
                200,
            )
    except NoCredentialsError:
        return jsonify({"error": "Credentials not available"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/zip", methods=["GET"])
def zip_images_folder():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "Username not provided"}), 400

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

        return jsonify({"download_link": download_link}), 200
    except NoCredentialsError:
        return jsonify({"error": "Credentials not available"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def hello_world():
    return "Hello, World!"


if __name__ == "__main__":
    app.run()
