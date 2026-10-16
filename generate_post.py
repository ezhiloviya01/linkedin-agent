
import json
import os

from dotenv import load_dotenv
from google import genai
# from google.genai import errors

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def generate_post(topic):
    # Load the latest client configuration
    with open("client_config.json", "r", encoding="utf-8") as file:
        client_config = json.load(file)

    prompt = f"""
You are a LinkedIn content writer for the following company.

COMPANY PROFILE
Company name:
{client_config.get("client_name", "")}

Business description:
{client_config.get("business_description", "")}

Industry:
{client_config.get("industry", "")}

Company size:
{client_config.get("company_size", "")}

Products and services:
{json.dumps(client_config.get("products_services", ""))}

CONTENT PREFERENCES
Main content goals:
{json.dumps(client_config.get("content_goals", []))}

Preferred post types:
{json.dumps(client_config.get("post_types", []))}

Posting frequency:
{client_config.get("posting_frequency", "")}

Preferred writing styles:
{json.dumps(client_config.get("post_styles", []))}

Target audiences:
{json.dumps(client_config.get("target_audience", []))}

Preferred post formats:
{json.dumps(client_config.get("post_formats", []))}

BACKEND-CONTROLLED GUARDRAILS
Content rules:
{json.dumps(client_config.get("content_rules", []), indent=2)}

Topics to avoid:
{json.dumps(client_config.get("topics_to_avoid", []), indent=2)}

REQUEST
Create one LinkedIn post draft about:
{topic}

INSTRUCTIONS
- Align the post with the selected content goals and post types.
- Write for the selected target audiences.
- Follow all selected writing styles.
- Respect the preferred post formats when drafting the content.
- Consider the posting frequency as part of the overall content strategy.
- Keep the content relevant to the company's industry and services.
- Do not invent statistics, facts, customer stories, or unsupported claims.
- Do not reveal confidential or private information.
- Follow every backend-controlled guardrail.
- Do not publish the post. Generate a draft for human review.
- Return only the LinkedIn post draft, without explanations.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.7-flash",
            contents=prompt
        )
        return response.text or "Gemini returned an empty response. Please try again."

    
    except Exception as exc:
        print("Gemini error:", repr(exc))
        return (
            "Post generation failed. Please check the VS Code terminal "
            "for the error details."
        )



if __name__ == "__main__":
    topic = input("Enter a topic for the LinkedIn post: ")
    post = generate_post(topic)

    print("\n--- GENERATED LINKEDIN POST ---\n")
    print(post)
