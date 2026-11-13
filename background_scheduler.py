
from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo

from scheduler import (
    init_db,
    claim_due_posts,
    get_linkedin_credentials,
    mark_published,
    mark_publish_failed
)

from publish import publish_post_with_credentials

TIMEZONE = ZoneInfo("Asia/Kolkata")


def check_schedules():
    """Publish approved posts whose scheduled time has arrived."""
    init_db()

    try:
        due_posts = claim_due_posts()
    except Exception as exc:
        print(f"Could not retrieve due posts: {exc}")
        raise

    for post in due_posts:
        post_id = post["id"]

        try:
            # Retrieve credentials and check token expiry.
            credentials = get_linkedin_credentials(
                post["member_id"] or post["user_id"]
                )

            if credentials is None:
                error_message = (
                    "LinkedIn access token is missing or expired. "
                    "Please reconnect your LinkedIn account."
                )

                mark_publish_failed(post_id, error_message)
                print(f"Scheduled post {post_id} failed: {error_message}")
                continue

            result = publish_post_with_credentials(
                post["post_text"],
                credentials["access_token"],
                credentials["member_id"]
            )

            if result == "Post published successfully on LinkedIn.":
                mark_published(post_id)
                print(f"Scheduled post {post_id} published successfully.")
            else:
                mark_publish_failed(post_id, result)
                print(f"Scheduled post {post_id} failed: {result}")

        except Exception as exc:
            mark_publish_failed(post_id, str(exc))
            print(f"Scheduled post {post_id} failed: {exc}")


def start_scheduler():
    """Check for due approved posts every minute."""
    init_db()

    scheduler = BackgroundScheduler(timezone=TIMEZONE)

    scheduler.add_job(
        check_schedules,
        trigger="interval",
        minutes=1,
        id="publish_due_posts",
        replace_existing=True,
        max_instances=1
    )

    scheduler.start()
    return scheduler


if __name__ == "__main__":
    print("Checking for approved posts due for publishing...")

    try:
        check_schedules()
        print("Scheduler check completed.")
    except Exception as exc:
        print(f"Scheduler check failed: {exc}")
        raise