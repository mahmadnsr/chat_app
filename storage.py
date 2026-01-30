import os
import psycopg2
from psycopg2 import extras
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Vercel automatically ye environment variable provide karta hai
# Isse 'POSTGRES_URL' ya 'DATABASE_URL' se uthaya ja sakta hai
DATABASE_URL = os.getenv('POSTGRES_URL')

def get_connection():
    # SSL mode 'require' zaroori hai cloud databases ke liye
    return psycopg2.connect(DATABASE_URL, sslmode='require')

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
    # MESSAGES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        sender TEXT, 
        receiver TEXT, 
        msg TEXT, 
        is_read INTEGER DEFAULT 0, 
        timestamp TIMESTAMP,
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
    cur.close()
    con.close()

# Database tables create karne ke liye
init_db()

# ---------------- USERS ----------------
def create_user(username, email, password):
    try:
        con = get_connection()
        cur = con.cursor()
        hashed = generate_password_hash(password)
        # Postgres mein '?' ki jagah '%s' use hota hai
        cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
                    (username, email, hashed))
        con.commit()
        return True
    except psycopg2.IntegrityError:
        return False
    finally:
        cur.close()
        con.close()

def verify_login(email, password):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT username, password FROM users WHERE email=%s", (email,))
    row = cur.fetchone()
    cur.close()
    con.close()
    if row and check_password_hash(row[1], password):
        return row[0]
    return None

def user_exists(username):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT 1 FROM users WHERE username=%s", (username,))
    exists = cur.fetchone() is not None
    cur.close()
    con.close()
    return exists

# ---------------- MESSAGES ----------------
def store_message(sender, receiver, msg):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO messages (sender, receiver, msg, timestamp)
        VALUES (%s, %s, %s, %s)
    """, (sender, receiver, msg, datetime.datetime.now()))
    con.commit()
    cur.close()
    con.close()

def get_messages_between(u1, u2):
    con = get_connection()
    cur = con.cursor(cursor_factory=extras.DictCursor)
    # Mark as read
    cur.execute("UPDATE messages SET is_read=1 WHERE sender=%s AND receiver=%s AND is_read=0", (u2, u1))
    
    cur.execute("""
        SELECT sender, receiver, msg, timestamp FROM messages
        WHERE ((sender=%s AND receiver=%s AND deleted_by_sender=0)
           OR (sender=%s AND receiver=%s AND deleted_by_receiver=0))
        ORDER BY timestamp ASC
    """, (u1, u2, u2, u1))
    
    rows = cur.fetchall()
    con.commit()
    cur.close()
    con.close()
    return [{"from": r['sender'], "to": r['receiver'], "msg": r['msg'], "time": r['timestamp']} for r in rows]

def get_unread_count(user, other):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM messages WHERE sender=%s AND receiver=%s AND is_read=0", (other, user))
    count = cur.fetchone()[0]
    cur.close()
    con.close()
    return count

# ---------------- CONVERSATIONS ----------------
def get_conversations(username):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        SELECT DISTINCT uid FROM (
            SELECT receiver AS uid FROM messages WHERE sender=%s
            UNION
            SELECT sender AS uid FROM messages WHERE receiver=%s
        ) AS subquery
    """, (username, username))
    users = [row[0] for row in cur.fetchall()]
    cur.close()
    con.close()
    return users

def get_last_message(u1, u2):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        SELECT msg, timestamp FROM messages
        WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s)
        ORDER BY timestamp DESC LIMIT 1
    """, (u1, u2, u2, u1))
    row = cur.fetchone()
    cur.close()
    con.close()
    return {"msg": row[0], "time": row[1]} if row else None

def delete_conversation(user, chat_with):
    con = get_connection()
    cur = con.cursor()
    cur.execute("UPDATE messages SET deleted_by_sender=1 WHERE sender=%s AND receiver=%s", (user, chat_with))
    cur.execute("UPDATE messages SET deleted_by_receiver=1 WHERE sender=%s AND receiver=%s", (chat_with, user))
    cur.execute("DELETE FROM messages WHERE deleted_by_sender=1 AND deleted_by_receiver=1")
    con.commit()
    cur.close()
    con.close()

def block_user(blocker, blocked):
    con = get_connection()
    cur = con.cursor()
    cur.execute("INSERT INTO blocks (blocker, blocked) VALUES (%s, %s)", (blocker, blocked))
    con.commit()
    cur.close()
    con.close()

def is_blocked(blocker, blocked):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT 1 FROM blocks WHERE blocker=%s AND blocked=%s", (blocker, blocked))
    result = cur.fetchone() is not None
    cur.close()
    con.close()
    return result