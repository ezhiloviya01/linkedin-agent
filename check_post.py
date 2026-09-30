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


def check_post(post):
    prompt = f"""
You are a LinkedIn content guardrail checker.

Check the following LinkedIn post against the client's configuration.

Client configuration:
{json.dumps(client_config, indent=2)}

Post:
{post}

Return exactly:

PASS
or
FAIL

Then give a short reason.

Check especially:
- Topics to avoid
- Content rules
- Unsupported claims
- Confidential or private information
- Offensive content
- Unrelated content
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    return response.text