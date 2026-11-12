
import json
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import psycopg2
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY")
fernet = Fernet(TOKEN_ENCRYPTION_KEY.encode()) if TOKEN_ENCRYPTION_KEY else None


def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing from the environment")
    return psycopg2.connect(database_url)


@contextmanager
def db_connection():
    """Commit on success, roll back on error, and always close the connection."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def encrypt_token(token):
    if not token:
        return token
    if fernet is None:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is missing from the environment")
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(token):
    if not token:
        return token
    if fernet is None:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is missing from the environment")
    return fernet.decrypt(token.encode()).decode()


def init_db():
    """Create or update application tables in Neon PostgreSQL."""
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_posts (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL DEFAULT '',
                    post_text TEXT NOT NULL,
                    scheduled_day TEXT NOT NULL,
                    scheduled_time TEXT NOT NULL,
                    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
                    status TEXT NOT NULL DEFAULT 'pending_approval',
                    approved_at TIMESTAMPTZ,
                    published_at TIMESTAMPTZ,
                    last_error TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    scheduled_at TIMESTAMPTZ,
                    member_id TEXT
                )
            """)

            cur.execute("""
                ALTER TABLE scheduled_posts
                ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT ''
            """)
            cur.execute("""
                ALTER TABLE scheduled_posts
                ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ
            """)
            cur.execute("""
                ALTER TABLE scheduled_posts
                ADD COLUMN IF NOT EXISTS member_id TEXT
            """)
            cur.execute("""
                ALTER TABLE scheduled_posts
                ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ
            """)
            cur.execute("""
                ALTER TABLE scheduled_posts
                ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ
            """)
            cur.execute("""
                ALTER TABLE scheduled_posts
                ADD COLUMN IF NOT EXISTS last_error TEXT
            """)
            cur.execute("""
                ALTER TABLE scheduled_posts
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ
                DEFAULT CURRENT_TIMESTAMP
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS posting_schedules (
                    user_id TEXT PRIMARY KEY,
                    days_and_times JSONB NOT NULL,
                    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS linkedin_credentials (
                    user_id TEXT PRIMARY KEY,
                    access_token TEXT NOT NULL,
                    token_expires_at TIMESTAMPTZ,
                    member_id TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                ALTER TABLE linkedin_credentials
                ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ
            """)
            cur.execute("""
                ALTER TABLE linkedin_credentials
                ADD COLUMN IF NOT EXISTS member_id TEXT
            """)

            # Preserve the existing Neon client_configs table and its records.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS client_configs (
                    user_id TEXT PRIMARY KEY,
                    config_json JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)


def save_linkedin_credentials(member_id, access_token, expires_in):
    token_expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
    )

    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO linkedin_credentials
                    (user_id, access_token, token_expires_at, member_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    token_expires_at = EXCLUDED.token_expires_at,
                    member_id = EXCLUDED.member_id,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                str(member_id),
                encrypt_token(access_token),
                token_expires_at,
                str(member_id)
            ))


def get_linkedin_credentials(member_id):
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT access_token, token_expires_at, member_id
                FROM linkedin_credentials
                WHERE user_id = %s
            """, (str(member_id),))

            row = cur.fetchone()

    if row is None:
        return None

    encrypted_token, expiry, stored_member_id = row

    if not expiry:
        return None

    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) >= expiry - timedelta(minutes=5):
        return None

    return {
        "access_token": decrypt_token(encrypted_token),
        "token_expires_at": expiry.isoformat(),
        "member_id": stored_member_id
    }


def add_scheduled_post(
    post_text,
    scheduled_day,
    scheduled_time,
    timezone="Asia/Kolkata",
    user_id="",
    scheduled_at=None,
    member_id=None
):
    """Insert a scheduled post into PostgreSQL."""

    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO scheduled_posts
                    (
                        user_id,
                        post_text,
                        scheduled_day,
                        scheduled_time,
                        timezone,
                        status,
                        scheduled_at,
                        member_id
                    )
                VALUES (%s, %s, %s, %s, %s,
                        'pending_approval', %s, %s)
                RETURNING id
            """, (
                str(user_id),
                post_text,
                scheduled_day,
                scheduled_time,
                timezone,
                scheduled_at,
                str(member_id) if member_id else None
            ))

            return cur.fetchone()[0]


def save_schedule(user_id, days_and_times, timezone="Asia/Kolkata"):
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO posting_schedules
                    (user_id, days_and_times, timezone)
                VALUES (%s, %s::jsonb, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    days_and_times = EXCLUDED.days_and_times,
                    timezone = EXCLUDED.timezone,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                str(user_id),
                json.dumps(days_and_times),
                timezone
            ))


def get_schedule(user_id):
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT days_and_times, timezone
                FROM posting_schedules
                WHERE user_id = %s
            """, (str(user_id),))

            row = cur.fetchone()

    if row is None:
        return None

    value = row[0]

    if isinstance(value, str):
        value = json.loads(value)

    return {
        "days_and_times": value,
        "timezone": row[1]
    }


def approve_scheduled_post(post_id, user_id):
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE scheduled_posts
                SET status = 'approved',
                    approved_at = CURRENT_TIMESTAMP,
                    last_error = NULL
                WHERE id = %s
                  AND user_id = %s
                  AND status = 'pending_approval'
            """, (post_id, user_id))

            return cur.rowcount == 1


def reject_scheduled_post(post_id, user_id):
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE scheduled_posts
                SET status = 'rejected'
                WHERE id = %s
                  AND user_id = %s
                  AND status = 'pending_approval'
            """, (post_id, user_id))

            return cur.rowcount == 1


def get_pending_scheduled_posts(user_id=None):
    query = """
        SELECT
            id,
            user_id,
            post_text,
            scheduled_day,
            scheduled_time,
            timezone,
            status
        FROM scheduled_posts
        WHERE status = 'pending_approval'
    """

    params = ()

    if user_id is not None:
        query += " AND user_id = %s"
        params = (str(user_id),)

    query += " ORDER BY id"

    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "user_id": row[1],
            "post_text": row[2],
            "scheduled_day": row[3],
            "scheduled_time": row[4],
            "timezone": row[5],
            "status": row[6]
        }
        for row in rows
    ]


def claim_due_posts():
    """Atomically claim due posts to prevent duplicate publishing."""
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                WITH due_posts AS (
                    SELECT id
                    FROM scheduled_posts
                    WHERE status = 'approved'
                      AND scheduled_at IS NOT NULL
                      AND scheduled_at <= CURRENT_TIMESTAMP
                    ORDER BY scheduled_at, id
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE scheduled_posts AS posts
                SET status = 'publishing'
                FROM due_posts
                WHERE posts.id = due_posts.id
                RETURNING
                    posts.id,
                    posts.user_id,
                    posts.member_id,
                    posts.post_text
            """)
            rows = cur.fetchall()
    return [
        {
            "id": row[0],
            "user_id": row[1],
            "member_id": row[2],
            "post_text": row[3]
        }
        for row in rows
    ]

def mark_published(post_id):
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE scheduled_posts
                SET status = 'published',
                    published_at = CURRENT_TIMESTAMP,
                    last_error = NULL
                WHERE id = %s
            """, (post_id,))


def mark_publish_failed(post_id, error):
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE scheduled_posts
                SET status = 'failed',
                    last_error = %s
                WHERE id = %s
            """, (str(error), post_id))


def get_failed_scheduled_posts(user_id=None):
    query = """
        SELECT
            id,
            user_id,
            post_text,
            scheduled_day,
            scheduled_time,
            timezone,
            status,
            last_error
        FROM scheduled_posts
        WHERE status = 'failed'
    """

    params = ()

    if user_id is not None:
        query += " AND user_id = %s"
        params = (str(user_id),)

    query += " ORDER BY id DESC"

    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "user_id": row[1],
            "post_text": row[2],
            "scheduled_day": row[3],
            "scheduled_time": row[4],
            "timezone": row[5],
            "status": row[6],
            "last_error": row[7]
        }
        for row in rows
    ]


def save_client_config(user_id, config):
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO client_configs (user_id, config_json)
                VALUES (%s, %s::jsonb)
                ON CONFLICT (user_id) DO UPDATE SET
                    config_json = EXCLUDED.config_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                str(user_id),
                json.dumps(config)
            ))


def get_client_config(user_id):
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT config_json
                FROM client_configs
                WHERE user_id = %s
            """, (str(user_id),))

            row = cur.fetchone()

    if row is None:
        return None

    value = row[0]

    if isinstance(value, str):
        value = json.loads(value)

    return value