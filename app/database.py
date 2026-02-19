import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "social_saver.db")


def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            whatsapp_number TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration: add name column if it doesn't exist yet (for existing DBs)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN name TEXT")
    except Exception:
        pass  # Column already exists

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            original_url TEXT NOT NULL,
            platform TEXT NOT NULL,
            extracted_text TEXT,
            ai_summary TEXT,
            category TEXT,
            thumbnail_url TEXT,
            tags TEXT,
            saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Migration: add tags column if it doesn't exist yet (for existing DBs)
    try:
        cursor.execute("ALTER TABLE saved_links ADD COLUMN tags TEXT")
    except Exception:
        pass  # Column already exists

    # Enforce no duplicate URLs per user at the DB level
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_user_url ON saved_links (user_id, original_url)"
    )

    conn.commit()
    conn.close()
