import boto3
from botocore.exceptions import ClientError
import uuid
# Initialize the DynamoDB client
dynamodb = boto3.resource("dynamodb", region_name="ca-central-1")
product_codes_table = dynamodb.Table("product_codes")

def add_product_code(asin, upc="", fnsku="", ein=""):
    """
    Adds a product code entry to the DynamoDB table.

    Parameters:
    - asin: str, Amazon Standard Identification Number
    - upc: str, Universal Product Code
    - fnsku: str, Fulfillment Network Stock Keeping Unit
    - ein: str, Employer Identification Number

    Returns:
    - response: dict, the response from DynamoDB if successful
    """
    try:
        unique_id = str(uuid.uuid4())  # Generate a unique ID
        response = product_codes_table.put_item(
            Item={
                "id": unique_id,  # Unique ID for the item
                "asin": asin,
                "upc": upc,
                "fnsku": fnsku,
                "ein": ein
            }
        )
        print("Product code added successfully:", response)
        return response
    except ClientError as e:
        print("Error adding product code:", e.response["Error"]["Message"])
        return None
    

def scan_for_product_code(code_type, code_value):
    try:
        # Use scan to search for the code_type (fnsku or upc) and code_value
        response = product_codes_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr(code_type).eq(code_value)
        )
        items = response.get('Items', [])
        
        if items:
            # Return the first match if found (assuming unique entries for fnsku/upc)
            item = items[0]
            if 'asin' in item:
                print(f"ASIN found in DynamoDB for {code_type}:", item['asin'])
                return item['asin']
            else:
                print(f"ASIN not found for {code_type}, calling {code_type}_to_asin_logic")
                return None
        else:
            print(f"{code_type} not found in DynamoDB, calling {code_type}_to_asin_logic")
            return None
    except ClientError as e:
        print("DynamoDB error:", e.response["Error"]["Message"])
        return None