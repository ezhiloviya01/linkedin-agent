
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from zoneinfo import ZoneInfo

from scheduler import (
    init_db,
    claim_due_posts,
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
    except Exception:
        print("Could not retrieve due posts.")
        raise

    for post in due_posts:
        post_id = post["id"]

        try:
            result = publish_post_with_credentials(
                post["post_text"],
                post["access_token"],
                post["member_id"]
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
    running_scheduler = start_scheduler()
    print("Background scheduler started. Checking approved posts every minute.")

    try:
        check_schedules()
        while True:
            import time
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        running_scheduler.shutdown()
        print("Background scheduler stopped.")
