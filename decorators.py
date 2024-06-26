from functools import wraps
from flask import request, jsonify
import boto3
from botocore.exceptions import ClientError


# Initialize the DynamoDB client
dynamodb = boto3.resource("dynamodb", region_name="ca-central-1")
users_table = dynamodb.Table("users")


def check_api(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Retrieve the API key from the request header
        api_key_sent = request.headers.get("api-key")
        soniclister_api_key = request.args.get("soniclister-api-key")
        print(soniclister_api_key)
        if not api_key_sent and not soniclister_api_key:
            print("api key missing", request.headers)
            return jsonify({"error": "API key header is missing"}), 401

        # Check if the API key exists in the DynamoDB 'users' table
        try:
            if soniclister_api_key:
                api_key_sent = soniclister_api_key
            response = users_table.get_item(Key={"id": api_key_sent})
            user = response.get("Item")
            if not user:
                return jsonify({"error": "Invalid API key"}), 401

            # Check if the user is active
            if not user.get("is_active", False):
                return jsonify({"error": "User account is inactive"}), 403

            # Check if the requests made exceed allowed requests
            requests_made = user.get("requests_made", 0)
            allowed_requests = user.get("allowed_requests", 0)
            if requests_made >= allowed_requests:
                return jsonify({"error": "Request limit exceeded"}), 429

        except ClientError as e:
            return jsonify({"error": "Server error, please try again later"}), 500

        # Proceed with the original function
        return func(*args, **kwargs)

    return wrapper
