from mitmproxy import http

def response(flow: http.HTTPFlow) -> None:
    # Intercepting and logging responses
    print(f"\n[RESPONSE] {flow.request.url}")
    print(f"Status Code: {flow.response.status_code}")
    print(f"Headers: {flow.response.headers}")
    
    # Try to decode the response body, fallback to binary if decoding fails
    try:
        response_body = flow.response.content.decode('utf-8', errors='replace')
        print(f"Response Body: {response_body}")
    except UnicodeDecodeError:
        print(f"Response Body (binary): {flow.response.content.hex()}")


# This function will handle the request and replace the fnsku code
def request(flow: http.HTTPFlow) -> None:
    # Check if the request is to the desired endpoint
    if "match-visualsearch-ca.amazon.com" in flow.request.pretty_url:
        
        # Log original request URL and try to decode the request body
        print(f"Original Request URL: {flow.request.pretty_url}")
        
        try:
            original_body = flow.request.content.decode('utf-8')
            print(f"Original Request Body: {original_body}")

            # FNSKU code replacement logic
            old_fnsku = "X002KPT22B"
            new_fnsku = "X003VRZZWD"

            # Check if the old FNSKU code is present in the request body
            if old_fnsku in original_body:
                modified_content = original_body.replace(old_fnsku, new_fnsku)
                flow.request.set_text(modified_content)
                print(f"Modified Request Body: {modified_content}")
            else:
                print("Default old fnsku isn't in the body!")
        
        except UnicodeDecodeError:
            print("Original Request Body: Could not decode, binary data detected.")

        # # Check if the old FNSKU code is in the URL
        # if old_fnsku in flow.request.pretty_url:
        #     modified_url = flow.request.pretty_url.replace(old_fnsku, new_fnsku)
        #     flow.request.url = modified_url
        #     print(f"Modified Request URL: {modified_url}")


if __name__ == "__main__":
    from mitmproxy.tools.main import mitmdump
    # Use mitmdump with the '-q' flag to suppress mitmproxy logs and only show your print statements
    mitmdump(['-q', '-s', __file__])
