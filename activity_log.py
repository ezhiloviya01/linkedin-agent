from datetime import datetime


def log_activity(action, status, post):
    with open("activity_log.txt", "a", encoding="utf-8") as file:
        file.write(
            f"[{datetime.now()}] | "
            f"Action: {action} | "
            f"Status: {status}\n"
            f"Post: {post}\n"
            f"{'-' * 60}\n"
        )