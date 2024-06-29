from openai import OpenAI


def rewrite_product_description(description: str) -> str:
    """
    Rewrites the product description using GPT-4o.

    Args:
        description (str): The unfiltered product description.

    Returns:
        str: The rewritten product description in simple sentences.
    """
    # Set up your OpenAI API credentials here
    api_key = "sk-proj-ZX52gNkDpURsvyy1WWofT3BlbkFJyXFDYV6616fbBFG5eWPU"

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
