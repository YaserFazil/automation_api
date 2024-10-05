from mitmproxy import http

def response(flow: http.HTTPFlow) -> None:
    # Intercepting and logging responses
    print(f"\n[RESPONSE] {flow.request.url}")
    print(f"Status Code: {flow.response.status_code}")
    print(f"Headers: {flow.response.headers}")
    # if flow.response.content:
    print(f"Response Body: {flow.response.content.decode('utf-8', errors='replace')}")

# This function will handle the request and replace the fnsku code
def request(flow: http.HTTPFlow) -> None:
    # Check if the request is to the desired endpoint
    if ("match-visualsearch-ca.amazon.com" or "match-visualsearch-ca.amazon.com:443") in flow.request.pretty_url:
        
        # Log original request URL and body
        print(f"Original Request URL: {flow.request.pretty_url}")
        print(f"Original Request Body: {flow.request.content.decode()}")

        # Decode the request content and look for the fnsku code
        old_fnsku = "X002KPT22B"
        new_fnsku = "X003VRZZWD"

        # Check if the old FNSKU code is present in the request body or URL
        if old_fnsku in flow.request.content.decode():
            # Modify the request body (assuming it's form-encoded or JSON)
            modified_content = flow.request.content.decode().replace(old_fnsku, new_fnsku)
            flow.request.set_text(modified_content)
            print(f"Modified Request Body: {modified_content}")

        elif old_fnsku in flow.request.pretty_url:
            # Modify the request URL if FNSKU is part of the query parameters
            modified_url = flow.request.pretty_url.replace(old_fnsku, new_fnsku)
            flow.request.url = modified_url
            print(f"Modified Request URL: {modified_url}")



if __name__ == "__main__":
    from mitmproxy.tools.main import mitmdump
    # Use mitmdump to run this script as a proxy server
    mitmdump(['-q', '-s', __file__])
