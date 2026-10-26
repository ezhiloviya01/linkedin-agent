
import sqlite3
import json

DATABASE = "scheduled_posts.db"


def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT '',
                post_text TEXT NOT NULL,
                scheduled_day TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
                status TEXT NOT NULL DEFAULT 'pending_approval',
                approved_at TEXT,
                published_at TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posting_schedules (
                user_id TEXT PRIMARY KEY,
                days_and_times TEXT NOT NULL,
                timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Add exact date/time and credentials for background publishing.
        columns = {
            row[1] for row in
            conn.execute("PRAGMA table_info(scheduled_posts)")
        }
        if "scheduled_at" not in columns:
            conn.execute(
                "ALTER TABLE scheduled_posts ADD COLUMN scheduled_at TEXT"
            )
        if "access_token" not in columns:
            conn.execute(
                "ALTER TABLE scheduled_posts ADD COLUMN access_token TEXT"
            )
        if "member_id" not in columns:
            conn.execute(
                "ALTER TABLE scheduled_posts ADD COLUMN member_id TEXT"
            )


def add_scheduled_post(
    post_text, scheduled_day, scheduled_time,
    timezone="Asia/Kolkata", user_id="",
    scheduled_at=None, access_token=None, member_id=None
):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute("""
            INSERT INTO scheduled_posts (
                user_id, post_text, scheduled_day, scheduled_time,
                timezone, status, scheduled_at, access_token, member_id
            )
            VALUES (?, ?, ?, ?, ?, 'pending_approval', ?, ?, ?)
        """, (
            str(user_id), post_text, scheduled_day, scheduled_time,
            timezone, scheduled_at, access_token, member_id
        ))
        return cursor.lastrowid


def save_schedule(user_id, days_and_times, timezone="Asia/Kolkata"):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            INSERT INTO posting_schedules
                (user_id, days_and_times, timezone)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                days_and_times = excluded.days_and_times,
                timezone = excluded.timezone,
                updated_at = CURRENT_TIMESTAMP
        """, (str(user_id), json.dumps(days_and_times), timezone))


def get_schedule(user_id):
    with sqlite3.connect(DATABASE) as conn:
        row = conn.execute("""
            SELECT days_and_times, timezone
            FROM posting_schedules WHERE user_id = ?
        """, (str(user_id),)).fetchone()
    if row is None:
        return None
    return {"days_and_times": json.loads(row[0]), "timezone": row[1]}


def approve_scheduled_post(post_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute("""
            UPDATE scheduled_posts
            SET status = 'approved',
                approved_at = CURRENT_TIMESTAMP, last_error = NULL
            WHERE id = ? AND status = 'pending_approval'
        """, (post_id,))
        return cursor.rowcount == 1


def reject_scheduled_post(post_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute("""
            UPDATE scheduled_posts SET status = 'rejected'
            WHERE id = ? AND status = 'pending_approval'
        """, (post_id,))
        return cursor.rowcount == 1


def get_pending_scheduled_posts(user_id=None):
    with sqlite3.connect(DATABASE) as conn:
        query = """
            SELECT id, user_id, post_text, scheduled_day,
                   scheduled_time, timezone, status
            FROM scheduled_posts WHERE status = 'pending_approval'
        """
        params = ()
        if user_id is not None:
            query += " AND user_id = ?"
            params = (str(user_id),)
        query += " ORDER BY id"
        rows = conn.execute(query, params).fetchall()

    return [
        {
            "id": r[0], "user_id": r[1], "post_text": r[2],
            "scheduled_day": r[3], "scheduled_time": r[4],
            "timezone": r[5], "status": r[6]
        }
        for r in rows
    ]


def claim_due_posts():
    """Claim approved posts due now, preventing duplicate publishing."""
    with sqlite3.connect(DATABASE) as conn:
        rows = conn.execute("""
            SELECT id, post_text, access_token, member_id
            FROM scheduled_posts
            WHERE status = 'approved'
              AND scheduled_at IS NOT NULL
              AND scheduled_at <= strftime('%Y-%m-%dT%H:%M:%S+00:00','now')
        """).fetchall()

        claimed = []
        for post_id, post_text, token, member_id in rows:
            cursor = conn.execute("""
                UPDATE scheduled_posts SET status = 'publishing'
                WHERE id = ? AND status = 'approved'
            """, (post_id,))
            if cursor.rowcount == 1:
                claimed.append({
                    "id": post_id, "post_text": post_text,
                    "access_token": token, "member_id": member_id
                })
        return claimed


def mark_published(post_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            UPDATE scheduled_posts
            SET status = 'published', published_at = CURRENT_TIMESTAMP,
                last_error = NULL
            WHERE id = ?
        """, (post_id,))


def mark_publish_failed(post_id, error):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            UPDATE scheduled_posts SET status = 'failed', last_error = ?
            WHERE id = ?
        """, (str(error), post_id))


if __name__ == "__main__":
    init_db()
    print("Scheduling database initialized successfully.")
