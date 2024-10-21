import os
import requests
import json
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from chatgpt import rewrite_product_title_to_query
load_dotenv()

def get_product_info_upc(upc_code):
    # URL construction
    url = f"https://www.barcodelookup.com/{upc_code}"
    apikey = os.getenv("ZENROWS_API_KEY")
    params = {
        'url': url,
        'apikey': apikey,
        'js_render': 'true',
        'wait': '2000',
        'premium_proxy': 'true',
    }


    try:

        response = requests.get('https://api.zenrows.com/v1/', params=params)
        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')

        # Try to find the product title element
        # Extract the first h4 tag's text value
        h4_tag = soup.find('h4')
        product_title = h4_tag.text.strip() if h4_tag else None

        # Try to find the product image element
        # Get the image src by its ID "largeProductImage"
        img_element = soup.find(id='largeProductImage')
        img_tag = img_element.find('img')
        image_url = img_tag['src'] if img_tag else None

        # Try to find the product description element
        # Extract text using the CSS selector "div.product-meta-data span.product-text"
        product_text = soup.select_one('div.product-meta-data span.product-text')
        product_description = product_text.text.strip() if product_text else None

        # Try to find the product price (MSRP) element
        # Get the first price by class name "store-link"
        price_tag = soup.find('span', class_='store-link')
        product_price = price_tag.text.strip() if price_tag else None

        # Print out the extracted information
        print(f"Product Title: {product_title}")
        print(f"Product Image URL: {image_url}")
        print(f"Product Description: {product_description}")
        print(f"Product Price (MSRP): {product_price}")

        # Structure the data as a dictionary and return it
        product_info = {
            "title": product_title,
            "image": image_url,
            "description": product_description,
            "price": product_price,
        }
        product_search_query = rewrite_product_title_to_query(product_title)

        headers = {
            "X-API-KEY": os.getenv("SERPER_DEV_API_KEY"),
            "Content-Type": "application/json",
        }
        # Get images for products from google
        google_images_search_url = "https://google.serper.dev/images"

        imgs_payload = json.dumps(
            {"q": product_search_query, "location": "Canada", "gl": "ca", "num": 20}
        )

        imgs_response = requests.request(
            "POST", google_images_search_url, headers=headers, data=imgs_payload
        )

        first_imgs_response = json.loads(imgs_response.text)

        # Get products from google
        gshopping_search_url = "https://google.serper.dev/shopping"

        payload = json.dumps({"q": product_search_query, "location": "Canada", "gl": "ca"})

        response = requests.request(
            "POST", gshopping_search_url, headers=headers, data=payload
        )
        first_response = json.loads(response.text)
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
            first_response["shopping"] = main_results
        product_info["shopping_results"] = first_response.get("shopping", [])[:10]

        return product_info

    except Exception as e:
        print("An error occurred: ", str(e))
        return None



# Example usage:
# upc_code = "0056500372994"
# upc_code = "056500370389"
# product_info = get_product_info_selenium(upc_code)
# print(product_info)
