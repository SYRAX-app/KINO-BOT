import sqlite3
import threading

DB_NAME = "bot_database.db"
lock = threading.Lock()


def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                joined_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY,
                title TEXT,
                type TEXT DEFAULT 'channel'
            )
        """)
        try:
            cur.execute("ALTER TABLE channels ADD COLUMN type TEXT DEFAULT 'channel'")
        except sqlite3.OperationalError:
            pass
        cur.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                code TEXT PRIMARY KEY,
                file_id TEXT,
                caption TEXT,
                added_at TEXT
            )
        """)
        try:
            cur.execute("ALTER TABLE videos ADD COLUMN caption TEXT")
        except sqlite3.OperationalError:
            pass
        cur.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                code TEXT,
                requested_at TEXT
            )
        """)
        conn.commit()
        conn.close()


# ---------- users ----------
def add_user(user_id):
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO users (user_id, joined_at) VALUES (?, datetime('now'))",
            (user_id,),
        )
        conn.commit()
        conn.close()


def get_users_count():
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        conn.close()
        return count


# ---------- channels / bots ----------
def add_channel(channel_id, title="", type_="channel"):
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO channels (channel_id, title, type) VALUES (?, ?, ?)",
            (channel_id, title, type_),
        )
        conn.commit()
        conn.close()


def remove_channel(channel_id):
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        conn.commit()
        conn.close()


def get_channels(type_=None):
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        if type_:
            cur.execute("SELECT channel_id, title, type FROM channels WHERE type = ?", (type_,))
        else:
            cur.execute("SELECT channel_id, title, type FROM channels")
        rows = cur.fetchall()
        conn.close()
        return rows


# ---------- videos ----------
def add_video(code, file_id, caption=""):
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO videos (code, file_id, caption, added_at) VALUES (?, ?, ?, datetime('now'))",
            (code, file_id, caption),
        )
        conn.commit()
        conn.close()


def get_video(code):
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT file_id, caption FROM videos WHERE code = ?", (code,))
        row = cur.fetchone()
        conn.close()
        return row if row else None


def get_videos_count():
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM videos")
        count = cur.fetchone()[0]
        conn.close()
        return count


def code_exists(code):
    return get_video(code) is not None


def delete_video(code):
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM videos WHERE code = ?", (code,))
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        return deleted


def get_all_video_codes():
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT code FROM videos ORDER BY added_at DESC")
        rows = [r[0] for r in cur.fetchall()]
        conn.close()
        return rows


# ---------- requests ----------
def log_request(user_id, code):
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO requests (user_id, code, requested_at) VALUES (?, ?, datetime('now'))",
            (user_id, code),
        )
        conn.commit()
        conn.close()


def get_requests_count():
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM requests")
        count = cur.fetchone()[0]
        conn.close()
        return count