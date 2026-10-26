
import sqlite3

conn = sqlite3.connect("scheduled_posts.db")

columns = {
    row[1]
    for row in conn.execute("PRAGMA table_info(scheduled_posts)")
}

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

for name, data_type in required_columns.items():
    if name not in columns:
        conn.execute(
            f"ALTER TABLE scheduled_posts ADD COLUMN {name} {data_type}"
        )
        print(f"Added column: {name}")

conn.commit()

print("Current columns:")
for row in conn.execute("PRAGMA table_info(scheduled_posts)"):
    print(row[1])

conn.close()
print("Database update complete.")
