import os
import requests
from dotenv import load_dotenv
from activity_log import log_activity
load_dotenv()
def publish_post(post):
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    member_id = os.getenv("LINKEDIN_MEMBER_ID")

    if not access_token:
        return "Publishing failed: LinkedIn access token not found."

    if not member_id:
        return "Publishing failed: LinkedIn member ID not found."

    # Publish the post
    url = "https://api.linkedin.com/rest/posts"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202601"
    }

    data = {
        "author": f"urn:li:person:{member_id}",
        "commentary": post,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED"
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False
    }

    response = requests.post(
        url,
        headers=headers,
        json=data
    )

    if response.status_code in (200, 201):
        log_activity("Publish Post", "SUCCESS", post)
    return "Post published successfully on LinkedIn."

    log_activity("Publish Post", "FAILED", post)
    return f"Publishing failed: {response.status_code} - {response.text}"