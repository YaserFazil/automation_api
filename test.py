from mitmproxy import http

def decode_content(content):
    """Attempt to decode the content using various encodings."""
    encodings = ['utf-8', 'ISO-8859-1', 'latin1']
    for enc in encodings:
        try:
            return content.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return None, None  # If none of the encodings work, return None


# from time import sleep
# # This function will handle the request and replace the fnsku code
# def request(flow: http.HTTPFlow) -> None:
#     # Check if the request is to the desired endpoint
#     if "match-visualsearch-ca.amazon.com" in flow.request.pretty_url:
        
#         # Log original request URL
#         print(f"Original Request URL: {flow.request.pretty_url}")
#         # Log the request headers and query parameters
        # print(f"Request Headers: {flow.request.headers}")
        # print(f"Request Query Params: {flow.request.query}")

        # # sleep(1)
        # # Attempt to decode the request body
        # decoded_body, encoding = decode_content(flow.request.content)
        # # sleep(1)
        # if decoded_body:
        #     print(f"Original Request Body (decoded with {encoding})")
        #     # sleep(1)
        #     # FNSKU code replacement logic
        #     old_fnsku = "X003VRZZWD"
        #     new_fnsku = "X0047SRB45"
        #     # Check if the old FNSKU code is present in the request body
        #     if old_fnsku in decoded_body:
        #         modified_content = decoded_body.replace(old_fnsku, new_fnsku)
        #         sleep(1)
        #         # Handle re-encoding after replacement
        #         encoded_content = modified_content.encode(encoding)  # Re-encode the body using the original encoding
        #         # sleep(1)
        #         flow.request.content = encoded_content  # Set the re-encoded body back to the request
        #         sleep(1)
        #         # flow.request.text = modified_content              
        #         # sleep(1)
        #         print(f"Modified Request Body (re-encoded with {encoding}): {modified_content}")
        #         print("Request body modified")
        # else:
        #     # Handle binary data (if decoding failed)
        #     print(f"Original Request Body: Could not decode, binary content detected")
        #     # print(f"Request Body (hex): {flow.request.content.hex()}")

import json
import os

def response(flow: http.HTTPFlow) -> None:
    # Check if the request is to the desired endpoint
    if "match-visualsearch-ca.amazon.com" in flow.request.url:
        # Intercepting and logging responses
        print(f"\n[RESPONSE] {flow.request.url}")
        print(f"Status Code: {flow.response.status_code}")
        print(f"Headers: {flow.response.headers}")
        
        # Try to decode the response body
        decoded_body, encoding = decode_content(flow.response.content)
        if decoded_body:
            print(f"Response Body (decoded with {encoding}): {decoded_body}")
            
            # Attempt to parse the decoded body as JSON
            try:
                json_data = json.loads(decoded_body)  # Ensure it's in a JSON format
                # Define the path where you want to save the JSON file
                json_file_path = os.path.join('./', 'response.json')
                
                # Empty the file before writing (open in 'w' mode truncates the file)
                with open(json_file_path, 'w', encoding='utf-8') as json_file:
                    # Save the JSON data to the file
                    json.dump(json_data, json_file, ensure_ascii=False, indent=4)
                
                print(f"JSON saved to {json_file_path}")
            except json.JSONDecodeError:
                print("Failed to decode response body as JSON")
        else:
            print(f"Response Body: Could not decode, binary content detected")
    else:
        # Intercepting and logging responses
        print(f"\n[RESPONSE] {flow.request.url}")
        print(f"request body content: ", flow.request.content)
        print(f"Headers: {flow.response.headers}")
        print(f"Here is response body: ",  flow.response.content)

if __name__ == "__main__":
    from mitmproxy.tools.main import mitmdump
    # Use mitmdump with the '-q' flag to suppress mitmproxy logs and only show your print statements
    mitmdump(['-q', '-s', __file__])
