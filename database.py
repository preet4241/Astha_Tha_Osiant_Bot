import sqlite3
import os
from datetime import datetime

DB_FILE = 'bot_database.db'

def get_db_file():
    """Get database file path"""
    return DB_FILE

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
            added_date TEXT,
            is_active INTEGER DEFAULT 1
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

def init_tools_table():
    """Initialize tools status table"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tools (
            tool_name TEXT PRIMARY KEY,
            is_active INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def set_tool_status(tool_name, is_active):
    """Set tool active/inactive status"""
    init_tools_table()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO tools (tool_name, is_active) VALUES (?, ?)', (tool_name, 1 if is_active else 0))
    conn.commit()
    conn.close()

def get_tool_status(tool_name):
    """Get tool active status"""
    init_tools_table()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT is_active FROM tools WHERE tool_name = ?', (tool_name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] == 1 if result else False

def get_all_active_tools():
    """Get all active tools"""
    init_tools_table()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT tool_name FROM tools WHERE is_active = 1')
    tools = cursor.fetchall()
    conn.close()
    return [tool[0] for tool in tools]

def init_tool_apis_table():
    """Initialize tool APIs table"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tool_apis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name TEXT NOT NULL,
            api_url TEXT NOT NULL,
            added_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_tool_api(tool_name, api_url):
    """Add API URL for a tool"""
    init_tool_apis_table()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tool_apis (tool_name, api_url, added_date) VALUES (?, ?, ?)', 
                   (tool_name, api_url, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return True

def remove_tool_api(tool_name, api_id):
    """Remove API from a tool"""
    init_tool_apis_table()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tool_apis WHERE id = ? AND tool_name = ?', (api_id, tool_name))
    conn.commit()
    conn.close()
    return True

def get_tool_apis(tool_name):
    """Get all APIs for a tool"""
    init_tool_apis_table()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, api_url, added_date FROM tool_apis WHERE tool_name = ?', (tool_name,))
    apis = cursor.fetchall()
    conn.close()
    return [{'id': api[0], 'url': api[1], 'added_date': api[2]} for api in apis]

# Removed get_random_tool_api - now using get_tool_apis directly in bot.py

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

def add_channel(channel_username, channel_title, channel_id=None):
    """Add a channel for force-subscribe"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # If channel_id is provided, use it; otherwise use username as fallback
    if channel_id is None:
        channel_id = hash(channel_username) % 1000000000

    try:
        cursor.execute('''
            INSERT OR REPLACE INTO channels (channel_id, channel_username, channel_title, added_date)
            VALUES (?, ?, ?, ?)
        ''', (channel_id, channel_username, channel_title, datetime.now().isoformat()))
        conn.commit()
        result = True
    except sqlite3.IntegrityError:
        result = False
    except Exception as e:
        print(f"Error adding channel: {e}")
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
    """Add group or reactivate if already exists"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        # Check if group exists (even if inactive)
        cursor.execute('SELECT is_active FROM groups WHERE group_id = ?', (group_id,))
        existing = cursor.fetchone()

        if existing:
            # Group exists, reactivate it
            cursor.execute('''
                UPDATE groups 
                SET is_active = 1, group_username = ?, group_title = ?, added_date = ?
                WHERE group_id = ?
            ''', (group_username, group_title, datetime.now().isoformat(), group_id))
        else:
            # New group, insert it
            cursor.execute('''
                INSERT INTO groups (group_id, group_username, group_title, added_date, is_active)
                VALUES (?, ?, ?, ?, 1)
            ''', (group_id, group_username, group_title, datetime.now().isoformat()))

        conn.commit()
        result = True
    except Exception as e:
        print(f"Error adding/reactivating group: {e}")
        result = False
    finally:
        conn.close()

    return result

def remove_group(group_id):
    """Mark group as removed (deactivate, don't delete)"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute('UPDATE groups SET is_active = 0 WHERE group_id = ?', (group_id,))
        conn.commit()
    except Exception as e:
        print(f"Error updating group active status: {e}")
        # Try adding column if it doesn't exist
        try:
            cursor.execute('ALTER TABLE groups ADD COLUMN is_active INTEGER DEFAULT 1')
            conn.commit()
            cursor.execute('UPDATE groups SET is_active = 0 WHERE group_id = ?', (group_id,))
            conn.commit()
        except Exception as e2:
            print(f"Error adding is_active column: {e2}")
    finally:
        conn.close()

    return True

def is_group_active(group_id):
    """Check if group is active (not removed)"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT is_active FROM groups WHERE group_id = ?', (group_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return result[0] == 1
        return False
    except Exception as e:
        # If column doesn't exist, assume all groups are active
        conn.close()
        return True

def get_all_groups():
    """Get all active groups (not removed)"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT group_id, group_username, group_title, added_date FROM groups WHERE is_active = 1 ORDER BY added_date DESC')
        groups = cursor.fetchall()
    except Exception as e:
        # If is_active column doesn't exist, get all groups
        print(f"Error fetching active groups: {e}")
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
    """Check if group exists and is active"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT 1 FROM groups WHERE group_id = ? AND is_active = 1', (group_id,))
        exists = cursor.fetchone() is not None
    except Exception as e:
        # If is_active column doesn't exist, just check existence
        print(f"Error checking group existence: {e}")
        cursor.execute('SELECT 1 FROM groups WHERE group_id = ?', (group_id,))
        exists = cursor.fetchone() is not None

    conn.close()

    return exists

def set_backup_channel(channel_id, channel_username, channel_title):
    """Set backup channel for database backups"""
    set_setting('backup_channel_id', str(channel_id))
    set_setting('backup_channel_username', channel_username)
    set_setting('backup_channel_title', channel_title)
    return True

def get_backup_channel():
    """Get backup channel details"""
    channel_id = get_setting('backup_channel_id', '')
    if not channel_id:
        return None

    return {
        'channel_id': int(channel_id),
        'username': get_setting('backup_channel_username', ''),
        'title': get_setting('backup_channel_title', '')
    }

def set_backup_interval(minutes):
    """Set backup interval in minutes"""
    set_setting('backup_interval', str(minutes))
    return True

def get_backup_interval():
    """Get backup interval in minutes (default 1440 = 24 hours)"""
    return int(get_setting('backup_interval', '1440'))

def set_last_backup_time(timestamp):
    """Set last backup timestamp"""
    set_setting('last_backup_time', timestamp)

def get_last_backup_time():
    """Get last backup timestamp"""
    return get_setting('last_backup_time', '')