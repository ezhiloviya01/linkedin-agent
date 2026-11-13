
from scheduler import (
    init_db,
    claim_due_posts,
    get_linkedin_credentials,
    mark_published,
    mark_publish_failed
)
from publish import publish_post_with_credentials


def check_schedules():
    """Publish approved posts whose scheduled time has arrived."""
    init_db()

    try:
        due_posts = claim_due_posts()
    except Exception:
        print("Could not retrieve due posts.")
        raise

    print(f"Found {len(due_posts)} due post(s).")

    for post in due_posts:
        post_id = post["id"]

        try:
            credentials = get_linkedin_credentials(post["user_id"])

            if not credentials:
                result = "Publishing failed: Please reconnect your LinkedIn account."
                mark_publish_failed(post_id, result)
                print(f"Post {post_id} failed: LinkedIn credentials unavailable.")
                continue

            result = publish_post_with_credentials(
                post["post_text"],
                credentials["access_token"],
                credentials["member_id"]
            )

            if result == "Post published successfully on LinkedIn.":
                mark_published(post_id)
                print(f"Post {post_id} published successfully.")
            else:
                mark_publish_failed(post_id, result)
                print(f"Post {post_id} failed: {result}")

        except Exception as exc:
            mark_publish_failed(post_id, str(exc))
            print(f"Post {post_id} failed: {exc}")


if __name__ == "__main__":
    check_schedules()
