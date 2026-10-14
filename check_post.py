import json
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

# Fixed guardrails controlled by the backend
BACKEND_GUARDRAILS = [
    "Do not make unsupported or misleading claims",
    "Do not include confidential or private information",
    "Do not include offensive content",
    "Keep content professional and helpful",
    "Do not attack competitors",
    "Check that the post is relevant to the client's business",
    "Human approval is required before publishing"
]

# Connect to Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def check_post(post):
    # Reject an empty post
    if not post or not post.strip():
        return "FAIL\nThe post is empty. Please provide content to check."

    # Load the latest client configuration
    try:
        with open("client_config.json", "r", encoding="utf-8") as file:
            client_config = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        print("Client configuration error:", repr(exc))
        return "FAIL\nUnable to load the client configuration."

    prompt = f"""
You are a strict LinkedIn content guardrail checker.

Evaluate the proposed post against BOTH:
1. The client's business configuration.
2. The fixed backend guardrails.

CLIENT CONFIGURATION:
{json.dumps(client_config, indent=2)}

BACKEND GUARDRAILS:
{json.dumps(BACKEND_GUARDRAILS, indent=2)}

PROPOSED POST:
{post}

Return your decision on the first line as exactly PASS or FAIL.
On the second line, provide a short reason.

Return FAIL if the post violates a guardrail, contains unsupported claims,
includes confidential information, or is clearly unrelated to the client's business.
Do not assume that a claim is true without supporting information.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

        result = (response.text or "").strip()

        # Fail closed if the response is missing or unclear
        lines = result.splitlines()
        first_line = lines[0].strip().upper() if lines else ""

        if first_line not in ("PASS", "FAIL"):
            return (
                "FAIL\n"
                "Guardrail check could not return a valid decision. "
                "Please try again."
            )

        reason = "\n".join(lines[1:]).strip()

        if not reason:
            reason = "No additional explanation was provided."

        return f"{first_line}\n{reason}"

    except Exception as exc:
        # Log the technical details in the VS Code terminal
        print("Gemini guardrail error:", repr(exc))

        # Do not approve a post when the check could not complete
        return (
            "CHECK_ERROR\n"
            "The AI guardrail service is temporarily unavailable. "
            "Please wait a minute and try again. The post has not been approved."
        )


if __name__ == "__main__":
    test_post = input("Enter a LinkedIn post to check: ")
    print("\n--- GUARDRAIL RESULT ---\n")
    print(check_post(test_post))