import os
import psycopg2
from psycopg2 import extras
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

def get_db_url():
    """Vercel Postgres URL ko clean aur format karne ke liye helper."""
    url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
    
    if not url:
        return None
        
    # Fix 1: psycopg2 'postgresql://' mangta hai, 'postgres://' nahi
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    # Fix 2: Supabase ya extra params jo error dete hain unhe hatao
    # Hum sirf base URL use karenge aur sslmode manually add karenge
    base_url = url.split("?")[0]
    return f"{base_url}?sslmode=require"

def get_connection():
    url = get_db_url()
    if not url:
        raise ValueError("Database URL missing! Dashboard se Postgres connect karein.")
    return psycopg2.connect(url)

def init_db():
    con = None
    try:
        con = get_connection()
        cur = con.cursor()
        # USERS Table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password TEXT
        )
        """)
        # MESSAGES Table
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
        # BLOCKS Table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS blocks (
            blocker TEXT, 
            blocked TEXT
        )
        """)
        con.commit()
        cur.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        if con:
            con.close()

# ---------------- USERS ----------------
def create_user(username, email, password):
    con = None
    try:
        con = get_connection()
        cur = con.cursor()
        hashed = generate_password_hash(password)
        cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
                    (username, email, hashed))
        con.commit()
        return True
    except Exception as e:
        print(f"Create user error: {e}")
        return False
    finally:
        if con:
            con.close()

def verify_login(email, password):
    con = None
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT username, password FROM users WHERE email=%s", (email,))
        row = cur.fetchone()
        if row and check_password_hash(row[1], password):
            return row[0]
        return None
    except Exception as e:
        print(f"Login Error: {e}")
        return None
    finally:
        if con:
            con.close()

def user_exists(username):
    con = None
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT 1 FROM users WHERE username=%s", (username,))
        exists = cur.fetchone() is not None
        return exists
    except:
        return False
    finally:
        if con:
            con.close()

# ---------------- MESSAGES ----------------
def store_message(sender, receiver, msg):
    con = None
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            INSERT INTO messages (sender, receiver, msg, timestamp)
            VALUES (%s, %s, %s, %s)
        """, (sender, receiver, msg, datetime.datetime.now()))
        con.commit()
    except Exception as e:
        print(f"Store Message Error: {e}")
    finally:
        if con:
            con.close()

def get_messages_between(u1, u2):
    con = None
    try:
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
        return [{"from": r['sender'], "to": r['receiver'], "msg": r['msg'], "time": r['timestamp']} for r in rows]
    except Exception as e:
        print(f"Fetch Messages Error: {e}")
        return []
    finally:
        if con:
            con.close()

def get_unread_count(user, other):
    con = None
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM messages WHERE sender=%s AND receiver=%s AND is_read=0", (other, user))
        count = cur.fetchone()[0]
        return count
    except:
        return 0
    finally:
        if con:
            con.close()

# ---------------- CONVERSATIONS ----------------
def get_conversations(username):
    con = None
    try:
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
        return users
    except:
        return []
    finally:
        if con:
            con.close()

def get_last_message(u1, u2):
    con = None
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT msg, timestamp FROM messages
            WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s)
            ORDER BY timestamp DESC LIMIT 1
        """, (u1, u2, u2, u1))
        row = cur.fetchone()
        return {"msg": row[0], "time": row[1]} if row else None
    except:
        return None
    finally:
        if con:
            con.close()

def delete_conversation(user, chat_with):
    con = None
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("UPDATE messages SET deleted_by_sender=1 WHERE sender=%s AND receiver=%s", (user, chat_with))
        cur.execute("UPDATE messages SET deleted_by_receiver=1 WHERE sender=%s AND receiver=%s", (chat_with, user))
        cur.execute("DELETE FROM messages WHERE deleted_by_sender=1 AND deleted_by_receiver=1")
        con.commit()
    finally:
        if con:
            con.close()

def block_user(blocker, blocked):
    con = None
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("INSERT INTO blocks (blocker, blocked) VALUES (%s, %s)", (blocker, blocked))
        con.commit()
    finally:
        if con:
            con.close()

def is_blocked(blocker, blocked):
    con = None
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT 1 FROM blocks WHERE blocker=%s AND blocked=%s", (blocker, blocked))
        result = cur.fetchone() is not None
        return result
    except:
        return False
    finally:
        if con:
            con.close()