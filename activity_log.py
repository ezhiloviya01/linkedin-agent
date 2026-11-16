from scheduler import db_connection


def log_activity(action, status, post):
    try:
        with db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO activity_logs (action, status, post)
                    VALUES (%s, %s, %s)
                    """,
                    (action, status, str(post) if post is not None else None)
                )

    except Exception as e:
        print(f"Failed to save activity log: {e}")