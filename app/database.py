import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "social_saver.db")
DATABASE_URL = os.getenv("DATABASE_URL")  # Set on Render → PostgreSQL; absent locally → SQLite


# ── PostgreSQL compatibility wrappers ──────────────────────────────────────
# Makes psycopg2 look like sqlite3 so the rest of the codebase needs no changes.

class _PGCursorWrapper:
    """psycopg2 RealDictCursor with sqlite3-style API (? placeholders)."""
    def __init__(self, cur):
        self._cur = cur

    def execute(self, sql, params=()):
        self._cur.execute(sql.replace("?", "%s"), params or ())
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()


class _PGConnectionWrapper:
    """psycopg2 connection with sqlite3-style .execute() / .cursor() / .commit() / .close()."""
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(sql.replace("?", "%s"), params or ())
        return cur  # RealDictCursor — supports .fetchone() / .fetchall()

    def cursor(self):
        return _PGCursorWrapper(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


# ── Public API ─────────────────────────────────────────────────────────────

def get_db():
    """Return a DB connection — PostgreSQL on Render, SQLite locally."""
    if DATABASE_URL:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        return _PGConnectionWrapper(conn)
    # Local development — SQLite
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they don't exist. Safe to re-run on every startup."""
    if DATABASE_URL:
        # PostgreSQL — use direct psycopg2 with autocommit (avoids cursor-lifecycle issues)
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT,
                whatsapp_number TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS name TEXT")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS saved_links (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                original_url TEXT NOT NULL,
                platform TEXT NOT NULL,
                extracted_text TEXT,
                ai_summary TEXT,
                category TEXT,
                thumbnail_url TEXT,
                tags TEXT,
                saved_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("ALTER TABLE saved_links ADD COLUMN IF NOT EXISTS tags TEXT")
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_user_url ON saved_links (user_id, original_url)"
        )
        cur.close()
        conn.close()
        return

    # SQLite (local development)
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
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN name TEXT")
    except Exception:
        pass

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
    try:
        cursor.execute("ALTER TABLE saved_links ADD COLUMN tags TEXT")
    except Exception:
        pass

    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_user_url ON saved_links (user_id, original_url)"
    )

    conn.commit()
    conn.close()
