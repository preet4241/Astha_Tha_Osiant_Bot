import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_FILE = 'bot_database.db'

@contextmanager
def get_db_conn():
    """Context manager for database connections to ensure proper closing and avoid locks."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL')  # Enable WAL mode for better concurrency
    conn.execute('PRAGMA busy_timeout=5000') # Wait up to 5s if DB is locked
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize SQLite database"""
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined TEXT,
                messages INTEGER DEFAULT 0,
                banned INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                ban_reason TEXT,
                ban_date TEXT
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
                group_username TEXT,
                group_title TEXT,
                added_date TEXT,
                is_active INTEGER DEFAULT 1,
                invite_link TEXT,
                added_by_id INTEGER,
                added_by_username TEXT,
                is_private INTEGER DEFAULT 1,
                permission_warnings INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('CREATE TABLE IF NOT EXISTS official_groups (group_id INTEGER PRIMARY KEY)')
        cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS tools (tool_name TEXT PRIMARY KEY, is_active INTEGER DEFAULT 0)')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tool_apis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL,
                api_url TEXT NOT NULL,
                added_date TEXT,
                response_fields TEXT
            )
        ''')
        conn.commit()
        
        # Migrations
        try:
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'ban_reason' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN ban_reason TEXT')
            if 'ban_date' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN ban_date TEXT')
            if 'last_active' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN last_active TEXT')
            if 'is_active' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1')
            
            cursor.execute("PRAGMA table_info(groups)")
            columns = [col[1] for col in cursor.fetchall()]
            for col, dtype in [('invite_link', 'TEXT'), ('added_by_id', 'INTEGER'), 
                               ('added_by_username', 'TEXT'), ('is_private', 'INTEGER DEFAULT 1'),
                               ('permission_warnings', 'INTEGER DEFAULT 0'), ('is_active', 'INTEGER DEFAULT 1')]:
                if col not in columns:
                    cursor.execute(f'ALTER TABLE groups ADD COLUMN {col} {dtype}')
            
            cursor.execute("PRAGMA table_info(tool_apis)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'response_fields' not in columns:
                cursor.execute('ALTER TABLE tool_apis ADD COLUMN response_fields TEXT')
            conn.commit()
        except Exception as e:
            print(f"[DB] Migration notice: {e}")

# Official Groups functions
def add_official_group(group_id):
    with get_db_conn() as conn:
        conn.execute('INSERT OR REPLACE INTO official_groups (group_id) VALUES (?)', (group_id,))
        conn.commit()

def remove_official_group(group_id):
    with get_db_conn() as conn:
        conn.execute('DELETE FROM official_groups WHERE group_id = ?', (group_id,))
        conn.commit()

def is_group_official(group_id):
    with get_db_conn() as conn:
        res = conn.execute('SELECT 1 FROM official_groups WHERE group_id = ?', (group_id,)).fetchone()
        return bool(res)

def get_official_groups():
    with get_db_conn() as conn:
        rows = conn.execute('''
            SELECT g.group_id, g.group_username, g.group_title, g.invite_link, g.added_date 
            FROM groups g
            JOIN official_groups og ON g.group_id = og.group_id
            WHERE g.is_active = 1
        ''').fetchall()
        return [{'group_id': r[0], 'username': r[1], 'title': r[2], 'invite_link': r[3], 'added_date': r[4]} for r in rows]

def add_user(user_id, username, first_name):
    with get_db_conn() as conn:
        try:
            conn.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, joined)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, datetime.now().isoformat()))
            conn.commit()
        except Exception as e:
            print(f"Error adding user: {e}")

def get_user(user_id):
    with get_db_conn() as conn:
        user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
        if user:
            return {
                'user_id': user[0], 'username': user[1], 'first_name': user[2], 'joined': user[3],
                'messages': user[4], 'banned': user[5], 'status': user[6],
                'ban_reason': user[7] if len(user) > 7 else None,
                'ban_date': user[8] if len(user) > 8 else None
            }
        return None

def ban_user(user_id, reason=None):
    with get_db_conn() as conn:
        conn.execute('UPDATE users SET banned = 1, ban_reason = ?, ban_date = ? WHERE user_id = ?', 
                     (reason, datetime.now().isoformat() if reason else None, user_id))
        conn.commit()
        return True

def unban_user(user_id):
    with get_db_conn() as conn:
        conn.execute('UPDATE users SET banned = 0, ban_reason = NULL, ban_date = NULL WHERE user_id = ?', (user_id,))
        conn.commit()
        return True

def increment_messages(user_id):
    with get_db_conn() as conn:
        conn.execute('UPDATE users SET messages = messages + 1, last_active = ? WHERE user_id = ?', (datetime.now().isoformat(), user_id))
        conn.commit()

def update_user_activity(user_id):
    with get_db_conn() as conn:
        conn.execute('UPDATE users SET last_active = ?, is_active = 1 WHERE user_id = ?', (datetime.now().isoformat(), user_id))
        conn.commit()

def set_user_active_status(user_id, status):
    with get_db_conn() as conn:
        conn.execute('UPDATE users SET is_active = ? WHERE user_id = ?', (1 if status else 0, user_id))
        conn.commit()

def is_user_active(user_id):
    with get_db_conn() as conn:
        res = conn.execute('SELECT is_active FROM users WHERE user_id = ?', (user_id,)).fetchone()
        return bool(res and res[0])

def get_all_users_for_report():
    with get_db_conn() as conn:
        rows = conn.execute('SELECT user_id, username, first_name, last_active, is_active FROM users').fetchall()
        return [{'user_id': r[0], 'username': r[1], 'first_name': r[2], 'last_active': r[3], 'is_active': r[4]} for r in rows]

def get_all_users():
    with get_db_conn() as conn:
        users = conn.execute('SELECT * FROM users').fetchall()
        result = {}
        for user in users:
            result[str(user[0])] = {
                'user_id': user[0], 'username': user[1], 'first_name': user[2], 'joined': user[3],
                'messages': user[4], 'banned': user[5], 'status': user[6],
                'ban_reason': user[7] if len(user) > 7 else None,
                'ban_date': user[8] if len(user) > 8 else None
            }
        return result

def get_stats():
    with get_db_conn() as conn:
        total = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        banned = conn.execute('SELECT COUNT(*) FROM users WHERE banned = 1').fetchone()[0]
        total_messages = conn.execute('SELECT SUM(messages) FROM users').fetchone()[0] or 0
        return {
            'total_users': total, 'banned_users': banned,
            'active_users': total - banned, 'total_messages': total_messages
        }

def set_setting(key, value):
    with get_db_conn() as conn:
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        conn.commit()

def get_setting(key, default=''):
    with get_db_conn() as conn:
        result = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
        return result[0] if result else default

def set_tool_status(tool_name, is_active):
    with get_db_conn() as conn:
        conn.execute('INSERT OR REPLACE INTO tools (tool_name, is_active) VALUES (?, ?)', (tool_name, 1 if is_active else 0))
        conn.commit()

def get_tool_status(tool_name):
    with get_db_conn() as conn:
        result = conn.execute('SELECT is_active FROM tools WHERE tool_name = ?', (tool_name,)).fetchone()
        return result[0] == 1 if result else False

def get_all_active_tools():
    with get_db_conn() as conn:
        tools = conn.execute('SELECT tool_name FROM tools WHERE is_active = 1').fetchall()
        return [tool[0] for tool in tools]

def add_tool_api(tool_name, api_url, response_fields=None):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO tool_apis (tool_name, api_url, added_date, response_fields) VALUES (?, ?, ?, ?)', 
                       (tool_name, api_url, datetime.now().isoformat(), response_fields))
        api_id = cursor.lastrowid
        conn.commit()
        return api_id

def get_tool_apis(tool_name):
    with get_db_conn() as conn:
        try:
            apis = conn.execute('SELECT id, api_url, added_date, response_fields FROM tool_apis WHERE tool_name = ?', (tool_name,)).fetchall()
            return [{'id': a[0], 'url': a[1], 'added_date': a[2], 'response_fields': a[3]} for a in apis]
        except:
            apis = conn.execute('SELECT id, api_url, added_date FROM tool_apis WHERE tool_name = ?', (tool_name,)).fetchall()
            return [{'id': a[0], 'url': a[1], 'added_date': a[2], 'response_fields': None} for a in apis]

def remove_tool_api(tool_name, api_id):
    with get_db_conn() as conn:
        conn.execute('DELETE FROM tool_apis WHERE id = ? AND tool_name = ?', (api_id, tool_name))
        conn.commit()
        return True

def add_channel(channel_username, channel_title, channel_id=None):
    # Sanitize inputs
    if channel_username:
        channel_username = str(channel_username).strip().replace("'", "''")
    if channel_title:
        channel_title = str(channel_title).strip().replace("'", "''")
        
    if channel_id is None:
        channel_id = hash(channel_username) % 1000000000
    with get_db_conn() as conn:
        try:
            conn.execute('''
                INSERT OR REPLACE INTO channels (channel_id, channel_username, channel_title, added_date)
                VALUES (?, ?, ?, ?)
            ''', (channel_id, channel_username, channel_title, datetime.now().isoformat()))
            conn.commit()
            return True
        except Exception:
            return False

def remove_channel(channel_username):
    with get_db_conn() as conn:
        conn.execute('DELETE FROM channels WHERE channel_username = ?', (channel_username,))
        conn.commit()
        return True

def get_all_channels():
    with get_db_conn() as conn:
        channels = conn.execute('SELECT channel_id, channel_username, channel_title, added_date FROM channels ORDER BY added_date DESC').fetchall()
        return [{'channel_id': c[0], 'username': c[1], 'title': c[2], 'added_date': c[3]} for c in channels]

def add_group(group_id, group_username, group_title, invite_link=None, added_by_id=None, added_by_username=None, is_private=1):
    with get_db_conn() as conn:
        try:
            existing = conn.execute('SELECT is_active FROM groups WHERE group_id = ?', (group_id,)).fetchone()
            if existing:
                conn.execute('''
                    UPDATE groups 
                    SET is_active = 1, group_username = ?, group_title = ?, added_date = ?, invite_link = ?, added_by_id = ?, added_by_username = ?, is_private = ?, permission_warnings = 0
                    WHERE group_id = ?
                ''', (group_username, group_title, datetime.now().isoformat(), invite_link, added_by_id, added_by_username, is_private, group_id))
            else:
                conn.execute('''
                    INSERT INTO groups (group_id, group_username, group_title, added_date, is_active, invite_link, added_by_id, added_by_username, is_private)
                    VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
                ''', (group_id, group_username, group_title, datetime.now().isoformat(), invite_link, added_by_id, added_by_username, is_private))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding group: {e}")
            return False

def channel_exists(channel_username):
    """Check if channel already exists"""
    with get_db_conn() as conn:
        exists = conn.execute('SELECT 1 FROM channels WHERE channel_username = ?', (channel_username,)).fetchone()
        return exists is not None

def increment_channel_join(channel_username):
    """Increment join count for channel"""
    with get_db_conn() as conn:
        conn.execute('UPDATE channels SET joined_count = joined_count + 1 WHERE channel_username = ?', (channel_username,))
        conn.commit()

def deactivate_expired_channels():
    """Deactivate channels that have reached their expiry date"""
    with get_db_conn() as conn:
        current_time = datetime.now().isoformat()
        conn.execute('UPDATE channels SET is_active = 0 WHERE expiry_date IS NOT NULL AND expiry_date <= ? AND is_active = 1', (current_time,))
        conn.commit()

def check_channel_limits():
    """Check and deactivate channels that have reached their join limit"""
    with get_db_conn() as conn:
        conn.execute('UPDATE channels SET is_active = 0 WHERE join_limit > 0 AND joined_count >= join_limit AND is_active = 1')
        conn.commit()

def group_exists(group_id):
    """Check if group exists and is active"""
    with get_db_conn() as conn:
        res = conn.execute('SELECT 1 FROM groups WHERE group_id = ? AND is_active = 1', (group_id,)).fetchone()
        return res is not None

def update_group_status(group_id, is_active):
    """Update active status of a group"""
    with get_db_conn() as conn:
        conn.execute('UPDATE groups SET is_active = ? WHERE group_id = ?', (1 if is_active else 0, group_id))
        conn.commit()

def get_active_groups_count():
    """Get count of active groups"""
    with get_db_conn() as conn:
        res = conn.execute('SELECT COUNT(*) FROM groups WHERE is_active = 1').fetchone()
        return res[0] if res else 0

def update_api_response_fields(api_id, response_fields):
    """Update response field mapping for an API"""
    with get_db_conn() as conn:
        conn.execute('UPDATE tool_apis SET response_fields = ? WHERE id = ?', (response_fields, api_id))
        conn.commit()
        return True

def get_api_response_fields(api_id):
    """Get response field mapping for an API"""
    with get_db_conn() as conn:
        result = conn.execute('SELECT response_fields FROM tool_apis WHERE id = ?', (api_id,)).fetchone()
        return result[0] if result and result[0] else None

def get_all_banned_users():
    """Get all banned users as a list"""
    with get_db_conn() as conn:
        users = conn.execute('SELECT * FROM users WHERE banned = 1').fetchall()
        result = []
        for user in users:
            result.append({
                'user_id': user[0], 'username': user[1], 'first_name': user[2], 'joined': user[3],
                'messages': user[4], 'banned': user[5], 'status': user[6],
                'ban_reason': user[7] if len(user) > 7 else None,
                'ban_date': user[8] if len(user) > 8 else None
            })
        return result

def get_banned_users():
    return get_all_banned_users()

def set_backup_channel(channel_id, channel_username, channel_title):
    """Set the backup channel details"""
    with get_db_conn() as conn:
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', ('backup_channel_id', str(channel_id)))
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', ('backup_channel_username', channel_username))
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', ('backup_channel_title', channel_title))
        conn.commit()

def get_backup_channel():
    """Get the backup channel details"""
    with get_db_conn() as conn:
        cid = conn.execute('SELECT value FROM settings WHERE key = ?', ('backup_channel_id',)).fetchone()
        cuser = conn.execute('SELECT value FROM settings WHERE key = ?', ('backup_channel_username',)).fetchone()
        ctitle = conn.execute('SELECT value FROM settings WHERE key = ?', ('backup_channel_title',)).fetchone()
        
        if cid and cuser and ctitle:
            return {
                'channel_id': int(cid[0]),
                'username': cuser[0],
                'title': ctitle[0]
            }
        return None

def set_backup_interval(minutes):
    """Set backup interval in minutes"""
    with get_db_conn() as conn:
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', ('backup_interval', str(minutes)))
        conn.commit()

def get_backup_interval():
    """Get backup interval in minutes"""
    with get_db_conn() as conn:
        res = conn.execute('SELECT value FROM settings WHERE key = ?', ('backup_interval',)).fetchone()
        return int(res[0]) if res else 1440

def set_last_backup_time():
    """Update last backup timestamp"""
    with get_db_conn() as conn:
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', ('last_backup_time', datetime.now().isoformat()))
        conn.commit()

def get_last_backup_time():
    """Get last backup timestamp"""
    with get_db_conn() as conn:
        res = conn.execute('SELECT value FROM settings WHERE key = ?', ('last_backup_time',)).fetchone()
        return res[0] if res else None

def get_last_backup_msg_id():
    """Get last backup message ID"""
    with get_db_conn() as conn:
        res = conn.execute('SELECT value FROM settings WHERE key = ?', ('last_backup_msg_id',)).fetchone()
        return int(res[0]) if res else None

def set_last_backup_msg_id(msg_id):
    """Set last backup message ID"""
    with get_db_conn() as conn:
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', ('last_backup_msg_id', str(msg_id)))
        conn.commit()

def get_db_file():
    """Get database file path"""
    return DB_FILE

def get_user_warnings(user_id):
    """Get warning count for a user (placeholder as it's missing in original schema)"""
    return 0

def add_warning(user_id):
    """Placeholder for add_warning"""
    return 0

def reset_warnings(user_id):
    """Placeholder for reset_warnings"""
    return True

def remove_warning(user_id):
    """Placeholder for remove_warning"""
    return True

def clear_warnings(user_id):
    """Placeholder for clear_warnings"""
    return True

def remove_group(group_id):
    """Mark group as removed (deactivate, don't delete)"""
    with get_db_conn() as conn:
        conn.execute('UPDATE groups SET is_active = 0 WHERE group_id = ?', (group_id,))
        conn.commit()
        return True

def get_all_groups():
    with get_db_conn() as conn:
        groups = conn.execute('SELECT group_id, group_username, group_title, added_date, is_active, invite_link, added_by_id, added_by_username, is_private FROM groups WHERE is_active = 1 ORDER BY added_date DESC').fetchall()
        return [{'group_id': g[0], 'username': g[1], 'title': g[2], 'added_date': g[3], 'is_active': g[4], 'invite_link': g[5], 'added_by_id': g[6], 'added_by_username': g[7], 'is_private': g[8]} for g in groups]

def get_group_details(group_id):
    with get_db_conn() as conn:
        row = conn.execute('SELECT group_id, group_username, group_title, added_date, invite_link, is_active, added_by_id, added_by_username, is_private, permission_warnings FROM groups WHERE group_id = ?', (group_id,)).fetchone()
        if row:
            return {'group_id': row[0], 'username': row[1], 'title': row[2], 'added_date': row[3], 'invite_link': row[4], 'is_active': row[5], 'added_by_id': row[6], 'added_by_username': row[7], 'is_private': row[8], 'permission_warnings': row[9]}
        return None

def update_group_invite_link(group_id, invite_link):
    with get_db_conn() as conn:
        conn.execute('UPDATE groups SET invite_link = ? WHERE group_id = ?', (invite_link, group_id))
        conn.commit()
        return True

def increment_permission_warning(group_id):
    with get_db_conn() as conn:
        conn.execute('UPDATE groups SET permission_warnings = permission_warnings + 1 WHERE group_id = ?', (group_id,))
        count = conn.execute('SELECT permission_warnings FROM groups WHERE group_id = ?', (group_id,)).fetchone()[0]
        conn.commit()
        return count

def get_removed_groups():
    with get_db_conn() as conn:
        groups = conn.execute('SELECT group_id, group_username, group_title, added_date, invite_link, added_by_id, added_by_username, is_private FROM groups WHERE is_active = 0 ORDER BY added_date DESC').fetchall()
        return [{'group_id': g[0], 'username': g[1], 'title': g[2], 'added_date': g[3], 'invite_link': g[4], 'added_by_id': g[5], 'added_by_username': g[6], 'is_private': g[7]} for g in groups]

def is_group_active(group_id):
    with get_db_conn() as conn:
        res = conn.execute('SELECT is_active FROM groups WHERE group_id = ?', (group_id,)).fetchone()
        return bool(res and res[0])
