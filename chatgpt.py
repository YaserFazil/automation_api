from openai import OpenAI
import base64
import requests
import os
from dotenv import load_dotenv

load_dotenv()


def rewrite_product_description(description: str) -> str:
    """
    Rewrites the product description using GPT-4o.

    Args:
        description (str): The unfiltered product description.

    Returns:
        str: The rewritten product description in simple sentences.
    """
    # Set up your OpenAI API credentials here
    api_key = os.getenv("OPENAI_API_KEY")

    # Initialize the OpenAI API client
    client = OpenAI(api_key=api_key)

    # Define the prompt for GPT-4o
    prompt = f"Rewrite the description using the information in it in simple plain sentences. Maximum of 3 sentences. Description: {description}"

    response = client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt=prompt,
        temperature=1,
        max_tokens=256,
        top_p=1,
    )
    response = response.choices[0].text.strip()
    return response


def get_item_name_from_image(image):

    # OpenAI API Key
    api_key = os.getenv("OPENAI_API_KEY")
    api_key = "sk-proj-HygGpCTeAiVKMDpLxUxDT3BlbkFJNZrVy8hRBmvCowqnTHMJ"

    # Function to encode the image
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    # Path to your image
    image_path = image

    # Getting the base64 string
    base64_image = encode_image(image_path)

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Only return the name of the object or the item in the image without any explanation and brands names.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
        "max_tokens": 300,
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
    )

    print(response.json())


# get_item_name_from_image("./item.jpg")



