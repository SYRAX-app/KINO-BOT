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
                type TEXT DEFAULT 'channel',
                invite_link TEXT
            )
        """)
        # Eski bazalarda yangi ustunlar bo'lmasligi mumkin
        try:
            cur.execute("ALTER TABLE channels ADD COLUMN type TEXT DEFAULT 'channel'")
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE channels ADD COLUMN invite_link TEXT")
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
        # Yopiq (so'rov bilan qo'shiladigan) kanallarga yuborilgan
        # "qo'shilish so'rovlari" shu yerda saqlanadi. Admin tasdiqlashini
        # kutmasdan, so'rov yuborilganning o'zi "obuna bo'ldi" deb hisoblanadi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS join_requests (
                user_id INTEGER,
                channel_id TEXT,
                requested_at TEXT,
                PRIMARY KEY (user_id, channel_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                added_by INTEGER,
                added_at TEXT
            )
        """)
        conn.commit()
        conn.close()


# ---------- admins ----------
def add_admin(user_id, added_by=None):
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO admins (user_id, added_by, added_at) VALUES (?, ?, datetime('now'))",
            (int(user_id), int(added_by) if added_by else None),
        )
        conn.commit()
        changed = cur.rowcount > 0
        conn.close()
        return changed


def remove_admin(user_id):
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM admins WHERE user_id = ?", (int(user_id),))
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        return deleted


def get_admins():
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT user_id, added_by, added_at FROM admins ORDER BY added_at ASC")
        rows = cur.fetchall()
        conn.close()
        return rows


def is_admin_db(user_id):
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM admins WHERE user_id = ?", (int(user_id),))
        row = cur.fetchone()
        conn.close()
        return row is not None


def admins_count():
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM admins")
        n = cur.fetchone()[0]
        conn.close()
        return n



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
def add_channel(channel_id, title="", type_="channel", invite_link=None):
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO channels (channel_id, title, type, invite_link) VALUES (?, ?, ?, ?)",
            (channel_id, title, type_, invite_link),
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
            cur.execute("SELECT channel_id, title, type, invite_link FROM channels WHERE type = ?", (type_,))
        else:
            cur.execute("SELECT channel_id, title, type, invite_link FROM channels")
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


# ---------- join requests (yopiq kanallar uchun) ----------
def add_join_request(user_id, channel_id):
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO join_requests (user_id, channel_id, requested_at) VALUES (?, ?, datetime('now'))",
            (user_id, str(channel_id)),
        )
        conn.commit()
        conn.close()


def has_join_request(user_id, channel_id):
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM join_requests WHERE user_id = ? AND channel_id = ?",
            (user_id, str(channel_id)),
        )
        row = cur.fetchone()
        conn.close()
        return row is not None