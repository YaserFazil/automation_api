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

def response(flow: http.HTTPFlow) -> None:
    # Intercepting and logging responses
    print(f"\n[RESPONSE] {flow.request.url}")
    print(f"Status Code: {flow.response.status_code}")
    print(f"Headers: {flow.response.headers}")
    
    # Try to decode the response body
    decoded_body, encoding = decode_content(flow.response.content)
    if decoded_body:
        # print(f"Response Body (decoded with {encoding}): {decoded_body}")
        print(f"Response Body (decoded with {encoding})")

    else:
        print(f"Response Body: Could not decode, binary content detected")

# This function will handle the request and replace the fnsku code
def request(flow: http.HTTPFlow) -> None:
    # Check if the request is to the desired endpoint
    if "match-visualsearch-ca.amazon.com" in flow.request.pretty_url:
        
        # Log original request URL
        print(f"Original Request URL: {flow.request.pretty_url}")
        
        # Attempt to decode the request body
        decoded_body, encoding = decode_content(flow.request.content)
        if decoded_body:
            print(f"Original Request Body (decoded with {encoding})")
            
            # FNSKU code replacement logic
            old_fnsku = "X003VRZZWD"
            new_fnsku = "X00BD7439J"

            # Check if the old FNSKU code is present in the request body
            if old_fnsku in decoded_body:
                modified_content = decoded_body.replace(old_fnsku, new_fnsku)
                flow.request.set_text(modified_content)
                print(f"Modified Request Body: {modified_content}")
                print("Request body modified")
        else:
            # Handle binary data (if decoding failed)
            print(f"Original Request Body: Could not decode, binary content detected")
            # print(f"Request Body (hex): {flow.request.content.hex()}")

if __name__ == "__main__":
    from mitmproxy.tools.main import mitmdump
    # Use mitmdump with the '-q' flag to suppress mitmproxy logs and only show your print statements
    mitmdump(['-q', '-s', __file__])
