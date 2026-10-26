
import requests
from dotenv import load_dotenv
from activity_log import log_activity

load_dotenv(override=True)

LINKEDIN_POSTS_URL = "https://api.linkedin.com/rest/posts"


def publish_post(post):
    """Publish immediately using the current Flask session."""
    from flask import session

    access_token = session.get("LINKEDIN_ACCESS_TOKEN")
    member_id = session.get("LINKEDIN_MEMBER_ID")

    if not access_token:
        return "Publishing failed: LinkedIn access token not found."

    if not member_id:
        return "Publishing failed: LinkedIn member ID not found."

    return publish_post_with_credentials(
        post,
        access_token,
        member_id
    )


def publish_post_with_credentials(post, access_token, member_id):
    """Publish using explicit LinkedIn credentials, for background jobs."""
    if not post:
        return "Publishing failed: Post content is empty."

    if not access_token:
        return "Publishing failed: LinkedIn access token not found."

    if not member_id:
        return "Publishing failed: LinkedIn member ID not found."

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

    try:
        response = requests.post(
            LINKEDIN_POSTS_URL,
            headers=headers,
            json=data,
            timeout=30
        )

        if response.status_code in (200, 201, 202):
            log_activity("Publish Post", "SUCCESS", post)
            return "Post published successfully on LinkedIn."

        log_activity("Publish Post", "FAILED", post)
        return (
            f"Publishing failed: HTTP {response.status_code} - "
            f"{response.text}"
        )

    except requests.RequestException as exc:
        log_activity("Publish Post", "FAILED", post)
        return f"Publishing failed due to a network error: {exc}"
