
import sqlite3
import os
from datetime import datetime

DB_FILE = 'bot_database.db'

def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined TEXT,
            messages INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            channel_id INTEGER PRIMARY KEY,
            channel_username TEXT UNIQUE,
            channel_title TEXT,
            added_date TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            group_id INTEGER PRIMARY KEY,
            group_username TEXT UNIQUE,
            group_title TEXT,
            added_date TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name):
    """Add new user to database"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, joined)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, datetime.now().isoformat()))
        conn.commit()
    except Exception as e:
        print(f"Error adding user: {e}")
    finally:
        conn.close()

def get_user(user_id):
    """Get user from database"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            'user_id': user[0],
            'username': user[1],
            'first_name': user[2],
            'joined': user[3],
            'messages': user[4],
            'banned': user[5],
            'status': user[6]
        }
    return None

def ban_user(user_id):
    """Ban user"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE users SET banned = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return True

def unban_user(user_id):
    """Unban user"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE users SET banned = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return True

def increment_messages(user_id):
    """Increment message count"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE users SET messages = messages + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    """Get all users"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    conn.close()
    
    result = {}
    for user in users:
        result[str(user[0])] = {
            'user_id': user[0],
            'username': user[1],
            'first_name': user[2],
            'joined': user[3],
            'messages': user[4],
            'banned': user[5],
            'status': user[6]
        }
    return result

def get_banned_users():
    """Get all banned users"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE banned = 1')
    users = cursor.fetchall()
    conn.close()
    
    result = []
    for user in users:
        result.append({
            'user_id': user[0],
            'username': user[1],
            'first_name': user[2],
            'joined': user[3],
            'messages': user[4],
            'banned': user[5],
            'status': user[6]
        })
    return result

def get_stats():
    """Get bot statistics"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE banned = 1')
    banned = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(messages) FROM users')
    total_messages = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        'total_users': total,
        'banned_users': banned,
        'active_users': total - banned,
        'total_messages': total_messages
    }

def init_settings_table():
    """Initialize settings table"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

def set_setting(key, value):
    """Set a setting value"""
    init_settings_table()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def get_setting(key, default=''):
    """Get a setting value"""
    init_settings_table()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else default

def add_channel(channel_username, channel_title):
    """Add required channel"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO channels (channel_username, channel_title, added_date)
            VALUES (?, ?, ?)
        ''', (channel_username, channel_title, datetime.now().isoformat()))
        conn.commit()
        result = True
    except sqlite3.IntegrityError:
        result = False
    finally:
        conn.close()
    
    return result

def remove_channel(channel_username):
    """Remove required channel"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM channels WHERE channel_username = ?', (channel_username,))
    conn.commit()
    conn.close()
    return True

def get_all_channels():
    """Get all required channels"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT channel_id, channel_username, channel_title, added_date FROM channels ORDER BY added_date DESC')
    channels = cursor.fetchall()
    conn.close()
    
    result = []
    for ch in channels:
        result.append({
            'channel_id': ch[0],
            'username': ch[1],
            'title': ch[2],
            'added_date': ch[3]
        })
    
    return result

def channel_exists(channel_username):
    """Check if channel already exists"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT 1 FROM channels WHERE channel_username = ?', (channel_username,))
    exists = cursor.fetchone() is not None
    conn.close()
    
    return exists

def increment_channel_join(channel_username):
    """Increment join count for channel"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE channels SET joined_count = joined_count + 1 WHERE channel_username = ?', (channel_username,))
    conn.commit()
    conn.close()

def deactivate_expired_channels():
    """Deactivate channels that have reached their expiry date"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    current_time = datetime.now().isoformat()
    cursor.execute('UPDATE channels SET is_active = 0 WHERE expiry_date IS NOT NULL AND expiry_date <= ? AND is_active = 1', (current_time,))
    conn.commit()
    conn.close()

def check_channel_limits():
    """Check and deactivate channels that have reached their join limit"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE channels SET is_active = 0 WHERE join_limit > 0 AND joined_count >= join_limit AND is_active = 1')
    conn.commit()
    conn.close()

def add_group(group_id, group_username, group_title):
    """Add group"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO groups (group_id, group_username, group_title, added_date)
            VALUES (?, ?, ?, ?)
        ''', (group_id, group_username, group_title, datetime.now().isoformat()))
        conn.commit()
        result = True
    except sqlite3.IntegrityError:
        result = False
    finally:
        conn.close()
    
    return result

def remove_group(group_id):
    """Remove group"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM groups WHERE group_id = ?', (group_id,))
    conn.commit()
    conn.close()
    return True

def get_all_groups():
    """Get all groups"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT group_id, group_username, group_title, added_date FROM groups ORDER BY added_date DESC')
    groups = cursor.fetchall()
    conn.close()
    
    result = []
    for grp in groups:
        result.append({
            'group_id': grp[0],
            'username': grp[1],
            'title': grp[2],
            'added_date': grp[3]
        })
    
    return result

def group_exists(group_id):
    """Check if group exists"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT 1 FROM groups WHERE group_id = ?', (group_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    
    return exists
