import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB = "chat.db"

def get_connection():
    # check_same_thread=False is needed for SQLite in Flask
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    con = get_connection()
    cur = con.cursor()
    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        email TEXT UNIQUE,
        password TEXT
    )
    """)
    # MESSAGES - Added deleted columns here
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        sender TEXT, 
        receiver TEXT, 
        msg TEXT, 
        is_read INTEGER DEFAULT 0, 
        timestamp DATETIME,
        deleted_by_sender INTEGER DEFAULT 0,
        deleted_by_receiver INTEGER DEFAULT 0
    )
    """)
    # BLOCKS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS blocks (
        blocker TEXT, 
        blocked TEXT
    )
    """)
    con.commit()
    con.close()

init_db()

# ---------------- USERS ----------------
def create_user(username, email, password):
    try:
        con = get_connection()
        cur = con.cursor()
        hashed = generate_password_hash(password)
        cur.execute("INSERT INTO users (username, email, password) VALUES (?,?,?)", 
                   (username, email, hashed))
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        con.close()

def verify_login(email, password):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT username, password FROM users WHERE email=?", (email,))
    row = cur.fetchone()
    con.close()
    if row and check_password_hash(row[1], password):
        return row[0]
    return None

def user_exists(username):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT 1 FROM users WHERE username=?", (username,))
    exists = cur.fetchone() is not None
    con.close()
    return exists

# ---------------- MESSAGES ----------------
def store_message(sender, receiver, msg):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO messages (sender, receiver, msg, timestamp)
        VALUES (?, ?, ?, ?)
    """, (sender, receiver, msg, datetime.datetime.now()))
    con.commit()
    con.close()

def get_messages_between(u1, u2):
    con = get_connection()
    cur = con.cursor()
    # Mark as read
    cur.execute("UPDATE messages SET is_read=1 WHERE sender=? AND receiver=? AND is_read=0", (u2, u1))
    
    cur.execute("""
        SELECT sender, receiver, msg, timestamp FROM messages
        WHERE ((sender=? AND receiver=? AND deleted_by_sender=0)
           OR (sender=? AND receiver=? AND deleted_by_receiver=0))
        ORDER BY timestamp ASC
    """, (u1, u2, u2, u1))
    
    rows = cur.fetchall()
    con.commit()
    con.close()
    return [{"from": s, "to": r, "msg": m, "time": t} for s, r, m, t in rows]

def get_unread_count(user, other):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM messages WHERE sender=? AND receiver=? AND is_read=0", (other, user))
    count = cur.fetchone()[0]
    con.close()
    return count

# ---------------- CONVERSATIONS ----------------
def get_conversations(username):
    con = get_connection()
    cur = con.cursor()
    # Unique users nikalne ke liye sender aur receiver dono check karein
    cur.execute("""
        SELECT DISTINCT uid FROM (
            SELECT receiver AS uid FROM messages WHERE sender=?
            UNION
            SELECT sender AS uid FROM messages WHERE receiver=?
        )
    """, (username, username))
    users = [row[0] for row in cur.fetchall()]
    con.close()
    return users

def get_last_message(u1, u2):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        SELECT msg, timestamp FROM messages
        WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
        ORDER BY timestamp DESC LIMIT 1
    """, (u1, u2, u2, u1))
    row = cur.fetchone()
    con.close()
    return {"msg": row[0], "time": row[1]} if row else None

def delete_conversation(user, chat_with):
    con = get_connection()
    cur = con.cursor()
    cur.execute("UPDATE messages SET deleted_by_sender=1 WHERE sender=? AND receiver=?", (user, chat_with))
    cur.execute("UPDATE messages SET deleted_by_receiver=1 WHERE sender=? AND receiver=?", (chat_with, user))
    cur.execute("DELETE FROM messages WHERE deleted_by_sender=1 AND deleted_by_receiver=1")
    con.commit()
    con.close()

def block_user(blocker, blocked):
    con = get_connection()
    cur = con.cursor()
    cur.execute("INSERT INTO blocks (blocker, blocked) VALUES (?,?)", (blocker, blocked))
    con.commit()
    con.close()

def is_blocked(blocker, blocked):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT 1 FROM blocks WHERE blocker=? AND blocked=?", (blocker, blocked))
    result = cur.fetchone() is not None
    con.close()
    return result