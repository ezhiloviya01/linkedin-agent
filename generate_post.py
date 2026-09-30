import json
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

# Load client configuration
with open("client_config.json", "r", encoding="utf-8") as file:
    client_config = json.load(file)

# Connect to Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def generate_post(topic):
    prompt = f"""
You are a LinkedIn content writer for the following company.

Company name:
{client_config["client_name"]}

Business description:
{client_config["business_description"]}

Products / Services:
{client_config["products_services"]}

Target audience:
{client_config["target_audience"]}

Brand voice:
{client_config["brand_voice"]}

Topics to post about:
{client_config["topics_to_post"]}

Topics to avoid:
{client_config["topics_to_avoid"]}

Content rules:
{client_config["content_rules"]}

Create one LinkedIn post about this topic:

{topic}

Follow the company's brand voice and content rules.
Do not include explanations about how you created the post.
Return only the LinkedIn post.
"""

    response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=prompt
)

    return response.text


if __name__ == "__main__":
    topic = input("Enter a topic for the LinkedIn post: ")

    post = generate_post(topic)

    print("\n--- GENERATED LINKEDIN POST ---\n")
    print(post)