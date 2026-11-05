import sqlite3
import json
import os
import psycopg2
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from datetime import datetime, timedelta, timezone

load_dotenv()

TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY")
fernet = Fernet(TOKEN_ENCRYPTION_KEY.encode()) if TOKEN_ENCRYPTION_KEY else None

DATABASE = os.getenv("DATABASE_PATH", "scheduled_posts.db")

def encrypt_token(token):
    if not token:
        return token
    if fernet is None:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is missing from .env")
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(token):
    if not token:
        return token
    if fernet is None:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is missing from .env")
    return fernet.decrypt(token.encode()).decode()

def save_linkedin_credentials(member_id, access_token, expires_in):
    token_expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat()

    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            INSERT INTO linkedin_credentials
            (user_id, access_token, token_expires_at, member_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                access_token = excluded.access_token,
                token_expires_at = excluded.token_expires_at,
                member_id = excluded.member_id,
                updated_at = CURRENT_TIMESTAMP
        """, (
            member_id,
            encrypt_token(access_token),
            token_expires_at,
            member_id
        ))
def get_linkedin_credentials(member_id):
    with sqlite3.connect(DATABASE) as conn:
        row = conn.execute("""
            SELECT access_token, token_expires_at, member_id
            FROM linkedin_credentials
            WHERE user_id = ?
        """, (member_id,)).fetchone()

    if row is None:
        return None

    access_token = decrypt_token(row[0])
    token_expires_at = row[1]

    if not token_expires_at:
        return None

    expiry_time = datetime.fromisoformat(token_expires_at)

    if expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) >= expiry_time - timedelta(minutes=5):
        return None

    return {
        "access_token": access_token,
        "token_expires_at": token_expires_at,
        "member_id": row[2]
    }




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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS linkedin_credentials (
                user_id TEXT PRIMARY KEY,
                access_token TEXT NOT NULL,
                token_expires_at TEXT,
                member_id TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS client_configs (
                user_id TEXT PRIMARY KEY,
                config_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Check and update LinkedIn credentials table
        credential_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(linkedin_credentials)"
            )
        }

        if "token_expires_at" not in credential_columns:
            conn.execute(
                "ALTER TABLE linkedin_credentials ADD COLUMN token_expires_at TEXT"
            )

        # Check and update scheduled_posts table
        required_columns = {
            "user_id": "TEXT NOT NULL DEFAULT ''",
            "scheduled_at": "TEXT",
            "access_token": "TEXT",
            "member_id": "TEXT",
            "approved_at": "TEXT",
            "published_at": "TEXT",
            "last_error": "TEXT",
            "created_at": "TEXT",
        }

        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(scheduled_posts)"
            )
        }

        for name, data_type in required_columns.items():
            if name not in columns:
                conn.execute(
                    f"ALTER TABLE scheduled_posts ADD COLUMN {name} {data_type}"
                )
                print(f"Added column: {name}")


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
            timezone, scheduled_at, encrypt_token(access_token), member_id
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
            SELECT id, user_id, post_text
            FROM scheduled_posts
            WHERE status = 'approved'
              AND scheduled_at IS NOT NULL
              AND scheduled_at <= strftime('%Y-%m-%dT%H:%M:%S+00:00','now')
        """).fetchall()

        claimed = []

        for post_id, user_id, post_text in rows:
            cursor = conn.execute("""
                UPDATE scheduled_posts
                SET status = 'publishing'
                WHERE id = ? AND status = 'approved'
            """, (post_id,))

            if cursor.rowcount == 1:
                claimed.append({
                    "id": post_id,
                    "user_id": user_id,
                    "post_text": post_text
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



def get_failed_scheduled_posts(user_id=None):
    with sqlite3.connect(DATABASE) as conn:
        query = """
            SELECT id, user_id, post_text, scheduled_day,
                   scheduled_time, timezone, status, last_error
            FROM scheduled_posts
            WHERE status = 'failed'
        """
        params = ()

        if user_id is not None:
            query += " AND user_id = ?"
            params = (str(user_id),)

        query += " ORDER BY id DESC"
        rows = conn.execute(query, params).fetchall()

    return [
        {
            "id": r[0],
            "user_id": r[1],
            "post_text": r[2],
            "scheduled_day": r[3],
            "scheduled_time": r[4],
            "timezone": r[5],
            "status": r[6],
            "last_error": r[7],
        }
        for r in rows
    ]

def save_client_config(user_id, config):
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing from environment")

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS client_configs (
                    user_id TEXT PRIMARY KEY,
                    config_json JSONB NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                INSERT INTO client_configs (user_id, config_json)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    config_json = EXCLUDED.config_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (str(user_id), json.dumps(config)))


def get_client_config(user_id):
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing from environment")

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT config_json
                FROM client_configs
                WHERE user_id = %s
            """, (str(user_id),))

            row = cur.fetchone()

    if row is None:
        return None

    return row[0]