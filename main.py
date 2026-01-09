# -*- coding: utf-8 -*-
from telethon import TelegramClient, events, Button
from telethon.tl.types import ChannelParticipantsAdmins, ChatAdminRights
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChatBannedRights
import os
import random
import asyncio
import re
import json
import aiohttp
import shutil
from datetime import datetime, timedelta, timezone
import pytz
import asyncio
import threading
from flask import Flask, render_template
from messages import get_random_hello_message, detect_greeting_type, get_response_for_greeting
from kick_out import check_message_for_bad_words, add_bad_words, remove_bad_words, get_bad_words_count, get_bad_words_file_content, parse_bad_words_input

app = Flask(__name__)
bot_status = {"running": False, "start_time": None}
from database import (
    init_db,
    add_user, get_user, ban_user, unban_user,
    get_all_users, get_stats, increment_messages,
    set_setting, get_setting, add_channel, remove_channel,
    get_all_channels, channel_exists, add_group, remove_group,
    get_all_groups, group_exists, is_group_active, get_removed_groups, get_group_details, update_group_invite_link, increment_permission_warning,
    set_tool_status, get_tool_status, get_all_active_tools,
    get_tool_apis, add_tool_api, remove_tool_api,
    update_api_response_fields, get_api_response_fields,
    set_backup_channel, get_backup_channel, set_backup_interval,
    get_backup_interval, set_last_backup_time, get_last_backup_time,
    get_db_file, get_user_warnings, add_warning, remove_warning, clear_warnings,
    update_user_activity, is_user_active, set_user_active_status, get_all_users_for_report
)

api_id = int(os.getenv('API_ID', '0'))
api_hash = os.getenv('API_HASH', '')
bot_token = os.getenv('BOT_TOKEN', '')
owner_id = int(os.getenv('OWNER_ID', '0'))

# Initialize database
init_db()

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# Core Status Check Logic
async def run_daily_report_and_ping():
    """Logic to generate report, update status and notify groups"""
    print("[LOG] Running status check and ping system...")
    try:
        # 1. Generate Report and Update Status
        users = get_all_users_for_report()
        report_msg = "📊 **Activity Status Report**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        active_count = 0
        deactive_count = 0
        
        # Consider user active if they interacted in the last 24 hours
        cutoff = datetime.now() - timedelta(days=1)
        
        for user in users:
            is_currently_active = False
            if user['last_active']:
                try:
                    last_active_dt = datetime.fromisoformat(user['last_active'])
                    if last_active_dt > cutoff:
                        is_currently_active = True
                except: pass
            
            set_user_active_status(user['user_id'], is_currently_active)
            status_emoji = "✅ Active" if is_currently_active else "❌ Deactive"
            if is_currently_active:
                active_count += 1
            else:
                deactive_count += 1
            
            user_ref = f"@{user['username']}" if user['username'] and user['username'] != 'unknown' else f"[{user['first_name']}](tg://user?id={user['user_id']})"
            report_msg += f"• {user_ref}: {status_emoji}\n"
        
        report_msg += f"\n━━━━━━━━━━━━━━━━━━━━━\n📈 Summary:\n✅ Active: {active_count}\n❌ Deactive: {deactive_count}"
        
        # Send report to owner
        try:
            await client.send_message(owner_id, report_msg)
        except Exception as e:
            print(f"[LOG] Error sending report: {e}")
        
        # 2. Notify all connected groups
        groups = get_all_groups()
        group_msg = "📢 **Bot Maintenance & Update**\n\nSabhi users dhyan dein! Bot ko use karne ke liye aapka active hona zaroori hai.\n\n👇 Bot start karne ke liye niche button pe click karein!"
        bot_user = await client.get_me()
        buttons = [[Button.url("🚀 Start Bot", f"https://t.me/{bot_user.username}")]]
        
        for grp in groups:
            try:
                await client.send_message(grp['group_id'], group_msg, buttons=buttons)
            except Exception as e:
                print(f"[LOG] Error sending group notification to {grp['group_id']}: {e}")
        
        return True, report_msg
    except Exception as e:
        print(f"[LOG] Run status check error: {e}")
        return False, str(e)

# Daily Ping System
async def daily_ping_task():
    """Background task to send daily report and group notifications at 12:00 AM IST"""
    while True:
        try:
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)
            
            # Calculate time until next midnight
            next_run = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            wait_seconds = (next_run - now).total_seconds()
            
            print(f"[LOG] Daily ping task sleeping for {wait_seconds} seconds")
            await asyncio.sleep(wait_seconds)
            
            await run_daily_report_and_ping()
                    
        except Exception as e:
            print(f"[LOG] Daily ping task error: {e}")
            await asyncio.sleep(60)

# Add to startup
async def startup_tasks():
    asyncio.create_task(daily_ping_task())

# Call startup_tasks after client starts
client.loop.create_task(startup_tasks())

broadcast_temp = {}
broadcast_stats = {}
start_text_temp = {}
channel_action_temp = {}
channel_page_temp = {}
group_action_temp = {}
group_page_temp = {}
user_action_temp = {}
user_action_type = {}
tool_session = {}
tool_api_action = {}
backup_channel_temp = {}
api_field_mapping_temp = {}  # Store pending API field mappings: {user_id: {'api_id': id, 'tool_name': name, 'step': 'fields'}}
panel_owner = {}  # Track which user owns which panel message: {(chat_id, msg_id): user_id}
broadcast_start_times = {} # Track broadcast start times for timeout
group_commands = {}  # Track ongoing group commands: {chat_id: {user_id: command_info}}
chat_tool_session = {}  # Scoped tool sessions: {(chat_id, user_id): tool_name}
last_interaction_time = {}  # Track last message time: {(chat_id, user_id): datetime}
bad_words_action_temp = {}  # Bad words management: {user_id: 'add' or 'remove'}

async def safe_answer(event, text="", alert=False):
    """Safely answer callback query, handling stale query IDs"""
    try:
        await event.answer(text, alert=alert)
    except Exception as e:
        if "QueryIdInvalid" in str(type(e).__name__) or "QueryIdInvalid" in str(e):
            pass  # Stale query, ignore
        else:
            print(f"[LOG] Callback answer error: {e}")

TOOL_CONFIG = {
    'number_info': {
        'name': '📱 Number Info',
        'prompt': '📱 Enter Mobile Number:\n\nFormat: 10 digit number\nExample: 7999520665',
        'placeholder': '{number}',
    },
    'aadhar_info': {
        'name': '🆔 Aadhar Info',
        'prompt': '🆔 Enter Aadhar Number:\n\nFormat: 12 digit number\nExample: 123456789012',
        'placeholder': '{aadhar}',
    },
    'aadhar_family': {
        'name': '👨‍👩‍👧‍👦 Aadhar to Family',
        'prompt': '👨‍👩‍👧‍👦 Enter Aadhar Number:\n\nFormat: 12 digit number\nExample: 123456789012',
        'placeholder': '{aadhar}',
    },
    'vehicle_info': {
        'name': '🚗 Vehicle Info',
        'prompt': '🚗 Enter Vehicle Number:\n\nFormat: Indian Vehicle Number\nExample: MH12AB1234',
        'placeholder': '{vehicle}',
    },
    'ifsc_info': {
        'name': '🏦 IFSC Info',
        'prompt': '🏦 Enter IFSC Code:\n\nFormat: 11 character code\nExample: SBIN0001234',
        'placeholder': '{ifsc}',
    },
    'pak_num': {
        'name': '🇵🇰 Pak Num Info',
        'prompt': '🇵🇰 Enter Pakistan Number:\n\nFormat: 10-11 digit number\nExample: 03001234567',
        'placeholder': '{number}',
    },
    'pincode_info': {
        'name': '📍 Pin Code Info',
        'prompt': '📍 Enter Pin Code:\n\nFormat: 6 digit code\nExample: 400001',
        'placeholder': '{pincode}',
    },
    'imei_info': {
        'name': '📱 IMEI Info',
        'prompt': '📱 Enter IMEI Number:\n\nFormat: 15 digit number\nExample: 123456789012345',
        'placeholder': '{imei}',
    },
    'ip_info': {
        'name': '🌐 IP Info',
        'prompt': '🌐 Enter IP Address:\n\nFormat: IPv4 or IPv6\nExample: 8.8.8.8',
        'placeholder': '{ip}',
    },
}

def validate_phone_number(text):
    """Validate and normalize Indian phone number"""
    cleaned = re.sub(r'[^\d]', '', text)
    if cleaned.startswith('91') and len(cleaned) == 12:
        cleaned = cleaned[2:]
    if cleaned.startswith('0') and len(cleaned) == 11:
        cleaned = cleaned[1:]
    if len(cleaned) == 10 and cleaned[0] in '6789':
        return cleaned
    return None

def validate_aadhar(text):
    """Validate Aadhar number (12 digits)"""
    cleaned = re.sub(r'[^\d]', '', text)
    if len(cleaned) == 12:
        return cleaned
    return None

def validate_vehicle(text):
    """Validate Indian vehicle number"""
    cleaned = re.sub(r'[^A-Za-z0-9]', '', text).upper()
    if re.match(r'^[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{1,4}$', cleaned):
        return cleaned
    return None

def validate_ifsc(text):
    """Validate IFSC code (11 characters)"""
    cleaned = text.strip().upper()
    if re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', cleaned):
        return cleaned
    return None

def validate_pak_number(text):
    """Validate Pakistan phone number"""
    cleaned = re.sub(r'[^\d]', '', text)
    if cleaned.startswith('92') and len(cleaned) == 12:
        cleaned = cleaned[2:]
    if len(cleaned) == 10 or len(cleaned) == 11:
        return cleaned
    return None

def validate_pincode(text):
    """Validate Indian PIN code (6 digits)"""
    cleaned = re.sub(r'[^\d]', '', text)
    if len(cleaned) == 6:
        return cleaned
    return None

def validate_imei(text):
    """Validate IMEI number (15 digits)"""
    cleaned = re.sub(r'[^\d]', '', text)
    if len(cleaned) == 15:
        return cleaned
    return None

def validate_ip(text):
    """Validate IP address"""
    cleaned = text.strip()
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ipv4_pattern, cleaned):
        parts = cleaned.split('.')
        if all(0 <= int(p) <= 255 for p in parts):
            return cleaned
    if ':' in cleaned:
        return cleaned
    return None

VALIDATORS = {
    'number_info': validate_phone_number,
    'aadhar_info': validate_aadhar,
    'aadhar_family': validate_aadhar,
    'vehicle_info': validate_vehicle,
    'ifsc_info': validate_ifsc,
    'pak_num': validate_pak_number,
    'pincode_info': validate_pincode,
    'imei_info': validate_imei,
    'ip_info': validate_ip,
}

async def check_tool_group_access(event):
    """Check if tool can be used in this context. Only works in authorized groups and for active users."""
    user_id = event.sender_id
    if user_id:
        # Update user activity on every interaction
        update_user_activity(user_id)
        
        # Check if user is active
        if not is_user_active(user_id):
            return False, "⚠️ Aapka status **Deactive** hai. Aap tools ka use nahi kar sakte. Kripya bot ko start karein aur active rahein!"

    if not event.is_group:
        # User tried to use tool in private chat - show them the groups
        authorized_groups = get_all_groups()
        if not authorized_groups:
            return False, "🚫 No groups are currently connected!\n\nPlease contact the bot owner."
        
        msg = "🚫 Tools only work in connected groups!\n\n"
        msg += f"📋 Connected Groups ({len(authorized_groups)}):\n\n"
        buttons = []
        
        for grp in authorized_groups:
            try:
                join_url = None
                link_type = None
                
                # First try stored invite link
                if grp.get('invite_link'):
                    join_url = grp['invite_link']
                    link_type = "private"
                
                # If no stored link, check username
                if not join_url:
                    grp_username = grp.get('username', '')
                    if grp_username and not str(grp_username).lstrip('-').isdigit():
                        join_url = f"https://t.me/{grp_username.lstrip('@')}"
                        link_type = "public"
                
                # If still no link, try to get from group entity
                if not join_url:
                    try:
                        from telethon.tl.functions.messages import GetFullChatRequest
                        from telethon.tl.functions.channels import GetFullChannelRequest
                        
                        entity = await client.get_entity(grp['group_id'])
                        
                        # Check if it's a channel/supergroup or regular group
                        if hasattr(entity, 'megagroup') or hasattr(entity, 'broadcast'):
                            full = await client(GetFullChannelRequest(entity))
                            if hasattr(full.full_chat, 'exported_invite') and full.full_chat.exported_invite:
                                join_url = full.full_chat.exported_invite.link
                                link_type = "private"
                        else:
                            full = await client(GetFullChatRequest(grp['group_id']))
                            if hasattr(full.full_chat, 'exported_invite') and full.full_chat.exported_invite:
                                join_url = full.full_chat.exported_invite.link
                                link_type = "private"
                    except Exception as e:
                        print(f"[LOG] ⚠️ Could not get existing invite link for group {grp['group_id']}: {e}")
                        
                        # Last resort: try to generate one
                        try:
                            from telethon.tl.functions.messages import ExportChatInviteRequest
                            entity = await client.get_entity(grp['group_id'])
                            invite = await client(ExportChatInviteRequest(entity))
                            join_url = invite.link
                            link_type = "private"
                        except Exception as gen_err:
                            print(f"[LOG] ⚠️ Could not generate invite link for group {grp['group_id']}: {gen_err}")
                
                if join_url:
                    if link_type == "private":
                        button_text = f"🔗 {grp['title']} (Private)"
                    else:
                        button_text = f"📍 {grp['title']}"
                    buttons.append([Button.url(button_text, join_url)])
                    msg += f"✅ {grp['title']}\n"
                else:
                    msg += f"• {grp['title']} (Make bot admin)\n"
            except Exception as e:
                print(f"[LOG] ⚠️ Could not get invite link for group {grp['group_id']}: {e}")
                msg += f"• {grp['title']}\n"
        
        if buttons:
            return False, (msg, buttons)
        else:
            msg += "\n⚠️ No buttons can be shown. Make bot admin in the group or re-add the group with an invite link."
            return False, msg
    
    chat = await event.get_chat()
    authorized_groups = get_all_groups()
    
    for grp in authorized_groups:
        if grp['group_id'] == chat.id:
            return True, None
    
    return False, "❌ This group is not authorized. Please add the bot to this group."

async def call_tool_api(tool_name, validated_input):
    """Call the API for a tool and return JSON response. Try multiple APIs on error."""
    # Get all APIs for this tool
    all_apis = get_tool_apis(tool_name)

    if not all_apis:
        return None, "No API configured for this tool. Please add an API first."

    # Shuffle APIs to distribute load randomly
    import random
    random.shuffle(all_apis)

    last_error = None

    # Try each API until one succeeds
    for api_info in all_apis:
        api_url = api_info['url']
        response_fields = api_info.get('response_fields')
        url = api_url.replace(TOOL_CONFIG[tool_name]['placeholder'], validated_input)

        try:
            print(f"[LOG] 🔄 Trying API: {api_url[:50]}...")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            print(f"[LOG] ✅ API Success: {api_url[:50]}")
                            
                            # Apply field mapping if configured
                            if response_fields:
                                filtered_data = extract_json_fields(data, response_fields)
                                return filtered_data, None
                            return data, None
                        except Exception as json_err:
                            last_error = f"JSON Parse Error: {str(json_err)}"
                            print(f"[LOG] ❌ JSON error from API: {last_error}")
                            continue
                    else:
                        last_error = f"API Error: Status {response.status}"
                        print(f"[LOG] ❌ API returned status {response.status}, trying next API...")
                        continue
        except asyncio.TimeoutError:
            last_error = "API Timeout: Request took too long"
            print(f"[LOG] ⏱️ API timeout, trying next API...")
            continue
        except Exception as e:
            last_error = f"API Error: {str(e)}"
            print(f"[LOG] ❌ API error: {last_error}, trying next API...")
            continue

    # If all APIs failed, return the last error
    print(f"[LOG] ❌ All APIs failed for {tool_name}")
    return None, f"All APIs failed. Last error: {last_error}"

async def send_back_button_delayed(client, chat_id, msg_id, back_callback, delay=2):
    """Send back button after delay"""
    await asyncio.sleep(delay)
    try:
        buttons = [[Button.inline('👈 Back', back_callback)]]
        await client.edit_message(chat_id, msg_id, buttons=buttons)
    except:
        pass

async def schedule_message_delete(message, delay_seconds=180):
    """Schedule a message for auto-deletion after specified delay"""
    async def delete_msg():
        await asyncio.sleep(delay_seconds)
        try:
            await message.delete()
        except:
            pass
    asyncio.create_task(delete_msg())

async def send_error_message(event, text, delete_after=60):
    """Send error message that auto-deletes after specified seconds (default 60)"""
    try:
        msg = await event.respond(text)
        await schedule_message_delete(msg, delete_after)
        try:
            await event.delete()
        except:
            pass
        return msg
    except Exception as e:
        print(f"[LOG] Error sending error message: {e}")
        return None

async def get_or_create_invite_link(entity_id, entity_title, entity_username=None):
    """Get stored invite link for channel/group."""
    try:
        # Check if it's already a full URL (for private links)
        if entity_username and entity_username.startswith('https://t.me/'):
            return entity_username, "private"
        
        # Check if it's a private link code
        if entity_username and (entity_username.startswith('+') or entity_username.startswith('joinchat/')):
            return f"https://t.me/{entity_username}", "private"
        
        # If username exists and is public (not numeric), it's a public entity
        if entity_username and not str(entity_username).lstrip('-').isdigit():
            clean_name = str(entity_username).lstrip('@')
            return f"https://t.me/{clean_name}", "public"
        
        # For private entities, check if we have a stored invite link
        all_groups = get_all_groups()
        for grp in all_groups:
            if grp['group_id'] == entity_id:
                if grp.get('invite_link'):
                    return grp['invite_link'], "private"
                break
        
        all_channels = get_all_channels()
        for ch in all_channels:
            if ch['channel_id'] == entity_id:
                if ch.get('username'):
                    ch_username = ch['username']
                    if ch_username.startswith('https://t.me/'):
                        return ch_username, "private"
                    elif ch_username.startswith(('+', 'joinchat/')):
                        return f"https://t.me/{ch_username}", "private"
                    else:
                        return f"https://t.me/{ch_username.lstrip('@')}", "public"
                break
        
        return None, None
    except Exception as e:
        print(f"[LOG] ❌ Error in get_or_create_invite_link for {entity_title}: {e}")
        return None, None

def detect_json_keys(data, max_depth=3, current_depth=0):
    """Recursively detect all available keys in JSON data"""
    keys = set()
    if current_depth >= max_depth:
        return keys
    
    if isinstance(data, dict):
        for k, v in data.items():
            if k not in ['success', 'developer', 'credit_by', 'powered_by', 'timestamp']:
                keys.add(k)
                if isinstance(v, (dict, list)):
                    nested = detect_json_keys(v, max_depth, current_depth + 1)
                    keys.update(nested)
    elif isinstance(data, list) and len(data) > 0:
        nested = detect_json_keys(data[0], max_depth, current_depth + 1)
        keys.update(nested)
    
    return keys

def format_json_as_text(data, query=None):
    """Format JSON data as readable text (not JSON code block)"""
    if data is None:
        return "No data found"
    
    text = ""
    # Add Query and Header if this is the top level call
    if query:
        text += f"🔍 **Your Query**: `{query}`\n"
        text += "📝 **Information Found**:\n"
        text += "━━━━━━━━━━━━━━━━━━━━━\n"
    
    # If it's a list, format each item
    if isinstance(data, list):
        if not data:
            return text + "No data found"
        list_text = ""
        for i, item in enumerate(data, 1):
            if isinstance(item, (dict, list)):
                if len(data) > 1:
                    list_text += f"\n📍 **Record {i}**\n"
                list_text += format_json_as_text(item)
                list_text += "\n"
            else:
                list_text += f"• `{item}`\n"
        text += list_text.strip()
        return text.strip()

    dict_text = ""
    if isinstance(data, dict):
        if not data:
            return text + "No details available"
            
        # Try to find common data containers first
        data_keys = ['data', 'Data', 'Data1', 'data1', 'result', 'info', 'details', 'response', 'items', 'records', 'objects']
        found_container = False
        container_data = None
        for k in data_keys:
            if k in data and isinstance(data[k], (list, dict)) and data[k]:
                container_data = data[k]
                found_container = True
                break
        
        if found_container:
            # Process container content
            dict_text += format_json_as_text(container_data)
        else:
            # No container found, show all relevant fields from top level
            for key in sorted(data.keys()):
                value = data[key]
                if key.lower() not in ['success', 'developer', 'credit_by', 'powered_by', 'timestamp', 'status', 'error', 'msg', 'message']:
                    formatted_key = key.replace('_', ' ').title()
                    if isinstance(value, dict):
                        if value:
                            dict_text += f"\n📍 **{formatted_key}**\n"
                            dict_text += format_json_as_text(value) + "\n"
                    elif isinstance(value, list):
                        if value:
                            dict_text += f"\n📍 **{formatted_key}**\n"
                            dict_text += format_json_as_text(value) + "\n"
                    else:
                        # Clean up formatting: remove trailing backticks or quotes if they exist in value
                        clean_value = str(value).strip('`').strip()
                        # Handling empty email or specific empty fields
                        if not clean_value and key.lower() == 'email':
                            clean_value = "Not Provided"
                        
                        if clean_value:
                            dict_text += f"• **{formatted_key}**: `{clean_value}`\n"
                        else:
                            dict_text += f"• **{formatted_key}**: `Not Available`\n"
        text += dict_text
    else:
        text += str(data)
    
    if "\n" in text and "@Cyber_as" not in text:
        text = text.strip()
        text += "\n\n━━━━━━━━━━━━━━━━━━━━━\n"
        text += "Owner: @Cyber_as\n"
        text += "Developed by: @KissuHQ"
        
    return text.strip()

def get_greeting():
    from datetime import timezone
    utc_now = datetime.now(timezone.utc)
    ist_hour = (utc_now.hour + 5) % 24
    if utc_now.minute >= 30:
        ist_hour = (ist_hour + 1) % 24
    
    if 5 <= ist_hour < 12:
        return "🌅 Good Morning"
    elif 12 <= ist_hour < 17:
        return "☀️ Good Afternoon"
    elif 17 <= ist_hour < 21:
        return "🌆 Good Evening"
    else:
        return "🌙 Good Night"

def get_default_owner_text():
    return "{greeting} Boss! 👑\n\n🤖 BOT Status: ✅ Online\n👥 Users: {total_users} | Active: {active_users}\n\n🎛️ Control Desk:"

def get_default_user_text():
    return "{greeting} {first_name}! 😊\n\n🔹 What would you like to do?"

def get_default_welcome_messages():
    """Return list of default welcome messages for groups"""
    return [
        "🏛️ Welcome to the Hall of Fame @{username}! {group_name} is proud of you!",
        "🎉 Warm welcome to @{username}! {group_name} just got better with you!",
        "🌟 Welcome aboard @{username}! {group_name} welcomes you with open arms!",
        "👋 Hey @{username}! {group_name} is happy you joined!",
        "🎊 Welcome to paradise @{username}! {group_name} is now even better!",
        "✨ Greetings @{username}! {group_name} is honored by your presence!",
        "🎭 Welcome to the show @{username}! {group_name} is ready to entertain you!",
        "🚀 @{username} blast off! {group_name} is taking you on an epic journey!",
        "💎 Welcome dear member @{username}! {group_name} treasures your arrival!",
        "🎪 Come in @{username}! {group_name} welcomes you to the big show!"
    ]

def get_tool_back_button(tool_name):
    """Get the back button callback data for a tool"""
    mapping = {
        'number_info': b'tool_number_info',
        'aadhar_info': b'tool_aadhar_info',
        'aadhar_family': b'tool_aadhar_family',
        'vehicle_info': b'tool_vehicle_info',
        'ifsc_info': b'tool_ifsc_info',
        'pak_num': b'tool_pak_num',
        'pincode_info': b'tool_pincode_info',
        'imei_info': b'tool_imei_info',
        'ip_info': b'tool_ip_info',
    }
    return mapping.get(tool_name, b'setting_tools_handler')

def get_nested_value(data, path):
    """Get value from nested dict/list using dot notation path like 'data.0.name'"""
    try:
        keys = path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list):
                try:
                    idx = int(key)
                    current = current[idx] if 0 <= idx < len(current) else None
                except ValueError:
                    # Key is not an index, try to find in list items
                    for item in current:
                        if isinstance(item, dict) and key in item:
                            current = item.get(key)
                            break
                    else:
                        return None
            else:
                return None
            if current is None:
                return None
        return current
    except:
        return None

def extract_json_fields(data, fields):
    """Extract specific fields from JSON data based on field list.
    Supports: simple keys, dotted paths (data.0.name), and nested structures.
    Skips fields that don't exist (graceful handling).
    Also searches common data container keys like Data1, data, result, response, etc.
    """
    if not data:
        return data
        
    # If no fields are provided, return everything
    if not fields or fields == "[]" or fields == '""' or fields == "null":
        return data
    
    try:
        if isinstance(fields, str):
            if fields.startswith('[') and fields.endswith(']'):
                field_list = json.loads(fields)
            else:
                field_list = [f.strip() for f in fields.split(',') if f.strip()]
        else:
            field_list = fields
    except:
        return data
    
    if not field_list:
        return data
    
    result = {}
    has_paths = any('.' in f for f in field_list)
    
    if has_paths:
        for field in field_list:
            value = get_nested_value(data, field)
            if value is not None:
                key = field.split('.')[-1]
                result[key] = value
    else:
        if isinstance(data, dict):
            data_container_keys = ['data', 'Data', 'Data1', 'data1', 'result', 'Result', 
                                   'response', 'Response', 'info', 'Info', 'details', 'Details',
                                   'records', 'Records', 'items', 'Items', 'results', 'Results',
                                   'objects', 'list', 'data_list']
            
            container_data = None
            for container_key in data_container_keys:
                if container_key in data and data[container_key]:
                    container_data = data[container_key]
                    break
            
            if container_data is not None:
                if isinstance(container_data, list):
                    result_list = []
                    for item in container_data:
                        if isinstance(item, dict):
                            filtered_item = {k: v for k, v in item.items() if k in field_list}
                            if filtered_item:
                                result_list.append(filtered_item)
                        else:
                            result_list.append(item)
                    if result_list:
                        result = result_list if len(result_list) > 1 else result_list[0]
                elif isinstance(container_data, dict):
                    result = {k: v for k, v in container_data.items() if k in field_list}
            
            if not result:
                result = {k: v for k, v in data.items() if k in field_list}
        elif isinstance(data, list):
            result = []
            for item in data:
                if isinstance(item, dict):
                    filtered = {k: v for k, v in item.items() if k in field_list}
                    if filtered:
                        result.append(filtered)
                else:
                    result.append(item)
        else:
            result = data
    
    return result if result else data

def get_random_welcome_message(username, group_name):
    """Get a random welcome message - includes both default and custom messages"""
    messages = get_default_welcome_messages()

    # Get custom welcome messages from database
    custom_msg = get_setting('group_welcome_text', '')
    if custom_msg:
        # Add custom message to the pool
        messages.append(custom_msg)

    # Pick random message from combined pool
    selected = random.choice(messages)
    return selected.format(username=username, group_name=group_name)

async def smart_broadcast_logic(owner_id, event, mode, target_user_id=None):
    """Broadcast logic: Handles message input with 1-minute timeout"""
    try:
        # Check if this is a broadcast operation
        if mode not in ['bot', 'group', 'all', 'personally']:
            return
            
        # We are already in the "waiting for message" state (broadcast_temp[sender.id] was set)
        # The user has 60 seconds to SEND the message to the bot
        # This function is called AFTER the message is received, but the design 
        # needs to handle the WAITING period.
        
        # Let's refine the logic to start the broadcast immediately since we HAVE the message
        await actual_broadcast_logic(owner_id, event, mode, target_user_id)
            
    except Exception as e:
        print(f"[LOG] ❌ Error in smart_broadcast_logic: {e}")

async def actual_broadcast_logic(owner_id, event, mode, target_user_id=None):
    targets = []
    if mode == 'bot':
        targets = [{'id': u['user_id'], 'type': 'user', 'data': u} for u in get_all_users().values() if not u.get('banned')]
    elif mode == 'group':
        targets = [{'id': g['group_id'], 'type': 'group', 'data': g} for g in get_all_groups()]
    elif mode == 'all':
        targets = [{'id': u['user_id'], 'type': 'user', 'data': u} for u in get_all_users().values() if not u.get('banned')]
        targets.extend([{'id': g['group_id'], 'type': 'group', 'data': g} for g in get_all_groups()])
    elif mode == 'personally':
        user_data = get_user(target_user_id)
        targets = [{'id': target_user_id, 'type': 'user', 'data': user_data}]

    sent, failed = 0, 0
    sent_list, failed_list = [], []
    stats = get_stats()
    
    status_msg = await client.send_message(owner_id, f"🚀 Starting {mode} broadcast to {len(targets)} targets...")
    
    for i, target in enumerate(targets):
        try:
            msg_to_send = event.message
            # Apply placeholders if it's a text message or has a caption
            if target['type'] == 'user' and target['data']:
                user_data = target['data']
                # Create a pseudo-sender object for format_text
                class PseudoSender:
                    def __init__(self, d):
                        self.id = d.get('user_id')
                        self.first_name = d.get('first_name')
                        self.username = d.get('username')
                
                pseudo_sender = PseudoSender(user_data)
                
                if msg_to_send.text:
                    try:
                        msg_to_send.text = format_text(msg_to_send.text, pseudo_sender, stats, user_data)
                    except: pass
                if hasattr(msg_to_send, 'caption') and msg_to_send.caption:
                    try:
                        msg_to_send.caption = format_text(msg_to_send.caption, pseudo_sender, stats, user_data)
                    except: pass

            await client.send_message(target['id'], msg_to_send)
            sent += 1
            name = target['data'].get('first_name') or target['data'].get('title') or "Unknown"
            sent_list.append(f"SUCCESS | {target['type'].upper()} | {target['id']} | {name}")
            
            if target['type'] == 'group':
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(0.05)
                
            if i % 10 == 0:
                await status_msg.edit(f"⏳ Broadcasting... {sent}/{len(targets)} sent")
        except Exception as e:
            failed += 1
            failed_list.append(f"FAILED | {target['type'].upper()} | {target['id']} | Error: {str(e)}")
            await asyncio.sleep(0.1)

    broadcast_stats[owner_id] = {'sent': sent_list, 'failed': failed_list, 'sent_count': sent, 'failed_count': failed}
    await status_msg.edit(f"✅ Broadcast Complete!\n\nSent: {sent}\nFailed: {failed}", buttons=[[Button.inline('📋 Detail', b'broadcast_detail'), Button.inline('🔙 Back', b'owner_broadcast')]])

async def run_ping_broadcast(owner_id):
    all_users = list(get_all_users().values())
    active, inactive = 0, 0
    report = []
    
    status_msg = await client.send_message(owner_id, f"📡 Pinging {len(all_users)} users...")
    
    for user in all_users:
        if user.get('banned'): continue
        try:
            msg = await client.send_message(user['user_id'], "📡 **Ping!** (Auto-deleting...)")
            await msg.delete()
            active += 1
            report.append(f"ACTIVE | {user['user_id']} | @{user.get('username', 'N/A')}")
        except:
            inactive += 1
            report.append(f"INACTIVE | {user['user_id']} | @{user.get('username', 'N/A')}")
        await asyncio.sleep(0.05)

    filename = f"ping_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, 'w') as f:
        f.write(f"📊 PING REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"━━━━━━━━━━━━━━━━━━━━━\n")
        f.write(f"Total Checked: {len(all_users)}\n")
        f.write(f"Active Users: {active}\n")
        f.write(f"Inactive Users: {inactive}\n")
        f.write(f"━━━━━━━━━━━━━━━━━━━━━\n\n")
        f.write("\n".join(report))
    
    await client.send_file(owner_id, filename, caption=f"📡 **Ping Report**\n\n✅ Active: {active}\n❌ Inactive: {inactive}\nTotal: {len(all_users)}")
    await status_msg.delete()
    if os.path.exists(filename): os.remove(filename)

def format_text(text, sender, stats, user=None):
    """Format text with placeholders"""
    now = datetime.now()
    day = now.strftime("%A")
    date_str = now.strftime("%d-%m-%Y")
    time_str = now.strftime("%I:%M:%S %p")
    
    placeholders = {
        'greeting': get_greeting(),
        'first_name': sender.first_name or 'User',
        'username': sender.username or 'user',
        'user_id': sender.id,
        'total_users': stats.get('total_users', 0),
        'active_users': stats.get('active_users', 0),
        'banned_users': stats.get('banned_users', 0),
        'total_messages': stats.get('total_messages', 0),
        'date': date_str,
        'time': time_str,
        'day': day,
        'bot_name': 'Multi-Tool Bot'
    }
    
    if user:
        placeholders.update({
            'user_messages': user.get('messages', 0),
            'joined_date': user.get('joined', 'Unknown')[:10]
        })

    try:
        return text.format(**placeholders)
    except:
        res = text
        for k, v in placeholders.items():
            res = res.replace('{' + k + '}', str(v))
        return res

async def check_user_access(sender_id):
    """Check if user is banned or needs to join channels"""
    user_data = get_user(sender_id)
    if user_data and user_data.get('banned'):
        return {'allowed': False, 'reason': 'banned'}

    # Check sub-force channels
    channels = get_all_channels()
    if channels:
        not_joined = []
        for ch in channels:
            try:
                channel_username = ch['username']
                is_private = channel_username.startswith('+') or 'joinchat/' in channel_username or channel_username.startswith('https://t.me/+') or channel_username.startswith('https://t.me/joinchat/')
                
                # Try to verify membership for ALL channels (public and private)
                try:
                    from telethon.tl.functions.channels import GetParticipantRequest
                    from telethon.errors.rpcerrorlist import UserNotParticipantError, ChannelPrivateError
                    
                    # Get entity by channel ID for better reliability
                    try:
                        channel_entity = await client.get_entity(ch['channel_id'])
                    except:
                        # Fallback to username if ID fails
                        try:
                            channel_entity = await client.get_entity(channel_username)
                        except:
                            # Cannot get entity, add to not_joined list
                            print(f"[LOG] ⚠️ Cannot get entity for {ch['username']}, marking as not joined")
                            not_joined.append(ch)
                            continue
                    
                    participant = await client(GetParticipantRequest(
                        channel=channel_entity,
                        participant=sender_id
                    ))
                    # User is a participant, check if banned
                    if participant.participant.__class__.__name__ == 'ChannelParticipantBanned':
                        not_joined.append(ch)
                    # User is a valid member, continue to next channel
                    print(f"[LOG] ✅ User is member of {ch['username']}")
                    
                except UserNotParticipantError:
                    # User is not in channel
                    print(f"[LOG] ❌ User not in channel {ch['username']}")
                    not_joined.append(ch)
                    
                except ChannelPrivateError:
                    # Channel is private and bot is not admin - cannot verify
                    # Add to not_joined so user sees join button
                    print(f"[LOG] ⚠️ Private channel {ch['username']}, bot not admin - adding to not_joined")
                    not_joined.append(ch)
                    
                except Exception as check_error:
                    error_str = str(check_error).lower()
                    if 'user_not_participant' in error_str:
                        print(f"[LOG] ❌ User not participant in {ch['username']}")
                        not_joined.append(ch)
                    elif 'chat_admin_required' in error_str or 'channel_private' in error_str or 'phone number' in error_str:
                        # Bot cannot verify this channel - add to not_joined
                        print(f"[LOG] ⚠️ Cannot verify channel {ch['username']}: {check_error}, adding to not_joined")
                        not_joined.append(ch)
                    else:
                        # Unknown error, assume not joined for safety
                        print(f"[LOG] ⚠️ Check error for {ch['username']}: {check_error}")
                        not_joined.append(ch)
                    
            except Exception as e:
                print(f"[LOG] ❌ Error checking channel {ch['username']}: {e}")
                # Skip channels that cause errors in verification
                continue

        if not_joined:
            return {'allowed': False, 'reason': 'not_subscribed', 'channels': not_joined}

    return {'allowed': True}

async def check_message_timeout(event):
    """Enforce 1-minute timeout per (chat_id, user_id) pair"""
    user_id = event.sender_id
    chat_id = event.chat_id
    key = (chat_id, user_id)
    now = datetime.now()
    
    if key in last_interaction_time:
        diff = (now - last_interaction_time[key]).total_seconds()
        if diff < 5:
            wait_time = int(5 - diff)
            await send_error_message(event, f"⏳ Please wait {wait_time} seconds before sending another message.", delete_after=5)
            return False
            
    last_interaction_time[key] = now
    return True

@client.on(events.NewMessage)
async def activity_tracker(event):
    if event.sender_id:
        update_user_activity(event.sender_id)

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id
    if user_id:
        # Check if user is banned
        user_data = get_user(user_id)
        if user_data and user_data.get('banned'):
            # Keep banned status, but update activity if we want to track it
            # User remains banned, so we don't activate them
            pass
        else:
            # Activate user immediately on /start
            update_user_activity(user_id)
            set_user_active_status(user_id, True)
            
    # Check if in group and group is removed
    if event.is_group:
        chat = await event.get_chat()
        if not is_group_active(chat.id):
            print(f"[LOG] ⏭️ /start ignored - Group {chat.title} is removed")
            raise events.StopPropagation

    sender = await event.get_sender()
    if not sender:
        print(f"[LOG] ⚠️ /start received but no sender info")
        return

    print(f"[LOG] 🚀 /start command from {sender.first_name} (@{sender.username or 'no_username'}) ID: {sender.id}")
    add_user(sender.id, sender.username or 'unknown', sender.first_name or 'User')

    # Check user access (banned or sub-force)
    if sender.id != owner_id:
        access_check = await check_user_access(sender.id)
        if not access_check['allowed']:
            if access_check['reason'] == 'banned':
                print(f"[LOG] 🚫 Banned user {sender.id} tried to use /start")
                await event.respond('🚫 Bhai tu BANNED hai is bot se! ❌')
                raise events.StopPropagation
            elif access_check['reason'] == 'not_subscribed':
                msg = '⚠️ Pehle in channels ko join karo bhai:\n\n'
                buttons = []
                for ch in access_check['channels']:
                    ch_username = ch['username']
                    
                    # Get or create invite link for the channel
                    join_url, link_type = await get_or_create_invite_link(ch['channel_id'], ch['title'], ch_username)
                    
                    if join_url:
                        if ch_username.startswith('https://t.me/') or ch_username.startswith('+') or ch_username.startswith('joinchat/'):
                            display_name = f"{ch['title']} (Private)"
                            button_text = f"🔗 Join {ch['title']}"
                        else:
                            display_name = f"@{ch_username.lstrip('@')}"
                            button_text = f"📺 Join {ch['title']}"
                        
                        msg += f"📺 {display_name}\n"
                        buttons.append([Button.url(button_text, join_url)])
                    else:
                        msg += f"❌ {ch['title']} (No link available)\n"
                
                buttons.append([Button.inline('✅ Check Again', b'check_subscription')])
                await event.respond(msg, buttons=buttons)
                raise events.StopPropagation

    stats = get_stats()

    if sender.id == owner_id:
        print(f"[LOG] 👑 Owner {sender.id} accessed bot")
        buttons = [
            [Button.inline('🛠️ Tools', b'owner_tools')],
            [Button.inline('👥 Users', b'owner_users'), Button.inline('📢 Broadcast', b'owner_broadcast')],
            [Button.inline('📊 Status', b'owner_status'), Button.inline('⚙️ Settings', b'owner_settings')],
        ]
        custom_text = get_setting('owner_start_text', get_default_owner_text())
        owner_text = format_text(custom_text, sender, stats, None)
        msg = await event.respond(owner_text, buttons=buttons)
        panel_owner[(event.chat_id, msg.id)] = sender.id
    else:
        user_data = get_user(sender.id)
        # Create user panel layout as requested:
        # Row 1: Add me to group (URL button)
        # Row 2: Profile, Groups (Callback buttons)
        # Row 3: Help, About (Callback buttons)
        bot_user = await client.get_me()
        add_to_group_url = f"https://t.me/{bot_user.username}?startgroup=true"
        
        buttons = [
            [Button.url('➕ Add me to group', add_to_group_url)],
            [Button.inline('👤 Profile', b'user_profile'), Button.inline('👥 Groups', b'user_groups')],
            [Button.inline('❓ Help', b'user_help'), Button.inline('ℹ️ About', b'user_about')],
        ]
        custom_text = get_setting('user_start_text', get_default_user_text())
        user_text = format_text(custom_text, sender, stats, user_data)
        msg = await event.respond(user_text, buttons=buttons)
        panel_owner[(event.chat_id, msg.id)] = sender.id

    raise events.StopPropagation

@client.on(events.CallbackQuery)
async def callback_handler(event):
    sender = await event.get_sender()
    if not sender:
        return
    data = event.data

    # Panel access control - verify panel owner
    panel_key = (event.chat_id, event.message_id)
    is_owner = sender.id == owner_id
    
    # Decoded callback data for routing
    callback_data = data.decode() if isinstance(data, bytes) else data
    
    # Strictly verify panel ownership for user-specific panels
    if callback_data.startswith('user_'):
        if panel_key in panel_owner:
            actual_owner_id = panel_owner[panel_key]
            if actual_owner_id != sender.id and not is_owner:
                await safe_answer(event, "❌ Yeh panel tumhara nahi hai! Apna panel open karne ke liye /start type karo.", alert=True)
                return
        else:
            # If we don't have record of the panel but it's a user callback, 
            # we should reject it to be safe in groups.
            if not is_owner:
                 await safe_answer(event, "❌ Session expired or invalid panel. Please use /start again.", alert=True)
                 return

    # Routing logic
    if not is_owner:
        user_data = get_user(sender.id)
        if user_data and user_data.get('banned'):
            await safe_answer(event, "🚫 You are BANNED!", alert=True)
            return
        
        # User-specific callback handling
        if callback_data == 'user_profile':
            user = get_user(sender.id)
            if user:
                joined_date = user['joined'][:10] if user['joined'] else 'Unknown'
                status_emoji = '✅' if not user['banned'] else '🚫'
                status_text = 'ACTIVE' if not user['banned'] else 'BANNED'
                profile_text = f"👤 **YOUR PROFILE**\n\nName: {user['first_name']}\nUsername: @{user['username']}\nID: {user['user_id']}\nMessages: {user['messages']}\nJoined: {joined_date}\nStatus: {status_emoji} {status_text}"
            else:
                profile_text = "❌ Profile not found!"
            await event.edit(profile_text, buttons=[[Button.inline('🔙 Back', b'user_back')]])
            return

        elif callback_data == 'user_groups':
            msg = "🚧 **GROUPS FEATURE**\n\nThis feature is currently under development. Please check back later!"
            await event.edit(msg, buttons=[[Button.inline('👈 Back', b'user_back')]])
            return

        elif callback_data == 'user_help':
            default_help = """❓ **HELP DESK**

👋 Hello {first_name}! Welcome to the multi-tool information hub.

🤖 **Bot Commands:**
/start - Restart the bot & main menu
/profile - Check your stats
/help - Show this guide

🛠️ **Available Lookup Tools:**
• 📱 Number Info - Find caller details
• 🆔 Aadhar Info - Identity lookup
• 🚗 Vehicle Info - RC & Insurance status
• 🏦 IFSC Info - Bank details finder
• 🇵🇰 Pak Num - International lookup
• 📍 Pin Code - Area & Post office info

📌 **How to use:**
Simply click on a tool from the menu and follow the instructions. Results are provided in a clean, readable format.

💡 **Tip:** Tools work only in connected groups! Join our groups from the menu."""
            current_help = get_setting('user_help_text', default_help)
            user_data = get_user(sender.id)
            formatted_help = format_text(current_help, sender, get_stats(), user_data)
            await event.edit(formatted_help, buttons=[[Button.inline('🔙 Back', b'user_back')]])
            return

        elif callback_data == 'user_about':
            default_about = """ℹ️ **ABOUT THE BOT**

🤖 **Ultimate Multi-Tool Bot**
The most advanced information lookup tool on Telegram.

📊 **Statistics:**
• 👥 Total Users: {total_users}
• ✅ Active Now: {active_users}
• 🛠️ Active Tools: 9+

📅 **Current Date:** {date}
⏰ **System Time:** {time}

⚡ **Key Features:**
• Real-time Lookup APIs
• Secure User Management
• Fast Group Moderation
• Automatic Cloud Backup

Developed with ❤️ by @KissuHQ"""
            current_about = get_setting('user_about_text', default_about)
            user_data = get_user(sender.id)
            stats = get_stats()
            formatted_about = format_text(current_about, sender, stats, user_data)
            await event.edit(formatted_about, buttons=[[Button.inline('🔙 Back', b'user_back')]])
            return

        elif callback_data == 'user_back':
            bot_user = await client.get_me()
            add_to_group_url = f"https://t.me/{bot_user.username}?startgroup=true"
            buttons = [
                [Button.url('➕ Add me to group', add_to_group_url)],
                [Button.inline('👤 Profile', b'user_profile'), Button.inline('👥 Groups', b'user_groups')],
                [Button.inline('❓ Help', b'user_help'), Button.inline('ℹ️ About', b'user_about')],
            ]
            stats = get_stats()
            user_text = format_text(get_setting('user_start_text', get_default_user_text()), sender, stats, user_data)
            await event.edit(user_text, buttons=buttons)
            return

        elif callback_data == 'check_subscription':
            # Subscription check logic...
            pass 
        else:
            await safe_answer(event, "Owner only!", alert=True)
            return

    elif data == b'owner_groups':
        # Official Groups Filter: Only show official groups in lists/tools
        from database import get_official_groups
        official_groups = get_official_groups()
        if official_groups:
            groups = official_groups
        else:
            # Fallback to all groups if no official groups defined
            groups = get_all_groups()
        
        buttons = [
            [Button.inline('➕ Add', b'group_add'), Button.inline('❌ Remove', b'group_remove')],
            [Button.inline('📋 List', b'group_list_page_1'), Button.inline('🗑️ Removed Groups', b'groups_removed_1')],
            [Button.inline('👋 Welcome Msgs', b'group_welcome_text')],
            [Button.inline('🏛️ Official Group', b'official_group_setting')],
            [Button.inline('🔙 Back', b'owner_back')],
        ]
        group_text = f"GROUPS\n\nConnected: {len(groups)}\n\nWhat do you want to do?"
        await event.edit(group_text, buttons=buttons)

    elif data == b'official_group_setting':
        from database import get_official_groups
        groups = get_official_groups()
        buttons = [
            [Button.inline('➕ Add', b'official_group_add'), Button.inline('❌ Remove', b'official_group_remove')],
            [Button.inline('📋 List', b'official_group_list')],
            [Button.inline('🔙 Back', b'owner_groups')]
        ]
        await event.edit(f"🏛️ **OFFICIAL GROUPS**\n\nTotal Official Groups: {len(groups)}\n\nManage your official group list:", buttons=buttons)

    elif data == b'official_group_add':
        from database import get_official_groups
        groups = get_all_groups()
        official_ids = [g['group_id'] for g in get_official_groups()]
        available = [g for g in groups if g['group_id'] not in official_ids]
        
        if not available:
            await event.edit("⚠️ **No groups available to add!**", buttons=[[Button.inline('🔙 Back', b'official_group_setting')]])
            return

        buttons = []
        for grp in available[:10]:
            buttons.append([Button.inline(f"➕ {grp['title']}", f"make_official_{grp['group_id']}".encode())])
        
        buttons.append([Button.inline('🔙 Back', b'official_group_setting')])
        await event.edit("➕ **SELECT GROUP TO MAKE OFFICIAL**", buttons=buttons)

    elif data.startswith(b'make_official_'):
        group_id = int(data.split(b'_')[2])
        from database import add_official_group
        add_official_group(group_id)
        await safe_answer(event, "✅ Group marked as Official!", alert=True)
        # Manually trigger official_group_setting logic to avoid event loop issues with click()
        from database import get_official_groups
        groups = get_official_groups()
        buttons = [
            [Button.inline('➕ Add', b'official_group_add'), Button.inline('❌ Remove', b'official_group_remove')],
            [Button.inline('📋 List', b'official_group_list')],
            [Button.inline('🔙 Back', b'owner_groups')]
        ]
        await event.edit(f"🏛️ **OFFICIAL GROUPS**\n\nTotal Official Groups: {len(groups)}\n\nManage your official group list:", buttons=buttons)

    elif data == b'official_group_remove':
        from database import get_official_groups
        groups = get_official_groups()
        if not groups:
            await event.edit("⚠️ **No official groups to remove!**", buttons=[[Button.inline('🔙 Back', b'official_group_setting')]])
            return

        buttons = []
        for grp in groups:
            buttons.append([Button.inline(f"❌ {grp['title']}", f"unoff_grp_{grp['group_id']}".encode())])
        
        buttons.append([Button.inline('🔙 Back', b'official_group_setting')])
        await event.edit("❌ **SELECT GROUP TO REMOVE FROM OFFICIALS**", buttons=buttons)

    elif data.startswith(b'unoff_grp_'):
        group_id = int(data.split(b'_')[2])
        from database import remove_official_group
        remove_official_group(group_id)
        await safe_answer(event, "✅ Group is now Unofficial!", alert=True)
        from database import get_official_groups
        groups = get_official_groups()
        buttons = [
            [Button.inline('➕ Add', b'official_group_add'), Button.inline('❌ Remove', b'official_group_remove')],
            [Button.inline('📋 List', b'official_group_list')],
            [Button.inline('🔙 Back', b'owner_groups')]
        ]
        await event.edit(f"🏛️ **OFFICIAL GROUPS**\n\nTotal Official Groups: {len(groups)}\n\nManage your official group list:", buttons=buttons)

    elif data == b'official_group_list':
        from database import get_official_groups
        groups = get_official_groups()
        if not groups:
            await event.edit("⚠️ **No official groups yet!**", buttons=[[Button.inline('🔙 Back', b'official_group_setting')]])
            return
            
        text = "🏛️ **OFFICIAL GROUPS LIST**\n\n"
        for i, grp in enumerate(groups, 1):
            text += f"{i}. {grp['title']} (@{grp['username']})\n"
        
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'official_group_setting')]])

    elif data == b'group_welcome_text':
        buttons = [
            [Button.inline('✏️ Edit', b'group_welcome_text_add'), Button.inline('🗑️ Remove', b'group_welcome_text_remove'), Button.inline('🔄 Default', b'group_welcome_text_default')],
            [Button.inline('💬 Messages', b'group_welcome_text_msgs')],
            [Button.inline('🔙 Back', b'owner_groups')],
        ]
        current_text = get_setting('group_welcome_text', 'Welcome to group!')
        text = f"GROUP WELCOME TEXT\n\nCurrent: {current_text}\n\nManage welcome message for new members:"
        await event.edit(text, buttons=buttons)

    elif data == b'group_welcome_text_msgs':
        from database import get_official_groups
        official_groups = get_official_groups()
        if official_groups:
            groups = official_groups
        else:
            groups = get_all_groups()
        total_groups = len(groups)
        msg_text = f"Total Groups Connected: {total_groups}\n\n"
        for i, grp in enumerate(groups, 1):
            msg_text += f"{i}. {grp['title']}\n"
        buttons = [
            [Button.inline('🔙 Back', b'group_welcome_text')]
        ]
        await event.edit(msg_text, buttons=buttons)

    elif data == b'group_welcome_text_add':
        start_text_temp[sender.id] = 'group_welcome'
        buttons = [[Button.inline('❌ Cancel', b'group_welcome_text')]]
        help_text = "Type new group welcome text:\n\nPlaceholders: {greeting}, {date}, {time}, {bot_name}, {first_name}"
        await event.edit(help_text, buttons=buttons)

    elif data == b'group_welcome_text_remove':
        set_setting('group_welcome_text', '')
        await event.edit('Group welcome text removed!', buttons=[[Button.inline('🔙 Back', b'group_welcome_text')]])

    elif data == b'group_welcome_text_default':
        set_setting('group_welcome_text', '')
        await event.edit('Group welcome text reset to random default messages!', buttons=[[Button.inline('🔙 Back', b'group_welcome_text')]])

    elif data == b'group_add':
        group_action_temp[sender.id] = 'add'
        buttons = [[Button.inline('❌ Cancel', b'owner_groups')]]
        await event.edit("ADD GROUP\n\nChoose one method:\n1. Group ID (number)\n2. Group username (@username)\n3. Forward message from group", buttons=buttons)

    elif data == b'group_remove':
        from database import get_official_groups
        official_groups = get_official_groups()
        groups = official_groups if official_groups else get_all_groups()
        if not groups:
            await event.edit('No groups to remove!', buttons=[[Button.inline('🔙 Back', b'owner_groups')]])
        else:
            group_page_temp[sender.id] = 1
            total_pages = (len(groups) + 5) // 6
            start_idx = 0
            end_idx = min(6, len(groups))
            buttons = []
            for grp in groups[start_idx:end_idx]:
                buttons.append([Button.inline(f'❌ {grp["username"]}', f'remove_grp_{grp["group_id"]}')])
            if total_pages > 1:
                buttons.append([Button.inline(f'➡️ Next (1/{total_pages})', b'group_remove_next')])
            buttons.append([Button.inline('🔙 Back', b'owner_groups')])
            try:
                await event.edit('REMOVE GROUP\n\nSelect group to remove:', buttons=buttons)
            except:
                await safe_answer(event, '✅ Group removed!')

    elif data == b'group_remove_next':
        from database import get_official_groups
        official_groups = get_official_groups()
        groups = official_groups if official_groups else get_all_groups()
        page = group_page_temp.get(sender.id, 1) + 1
        total_pages = (len(groups) + 5) // 6
        if page > total_pages:
            page = 1
        group_page_temp[sender.id] = page
        start_idx = (page - 1) * 6
        end_idx = min(start_idx + 6, len(groups))
        buttons = []
        for grp in groups[start_idx:end_idx]:
            buttons.append([Button.inline(f'❌ {grp["username"]}', f'remove_grp_{grp["group_id"]}')])
        if total_pages > 1:
            buttons.append([Button.inline(f'➡️ Next ({page}/{total_pages})', b'group_remove_next')])
        buttons.append([Button.inline('🔙 Back', b'owner_groups')])
        await event.edit('REMOVE GROUP\n\nSelect group to remove:', buttons=buttons)

    elif data == b'group_list_page_1':
        from database import get_official_groups
        official_groups = get_official_groups()
        groups = official_groups if official_groups else get_all_groups()
        if not groups:
            await event.edit('No groups yet!', buttons=[[Button.inline('🔙 Back', b'owner_groups')]])
        else:
            group_page_temp[sender.id] = 1
            total_pages = (len(groups) + 5) // 6
            start_idx = 0
            end_idx = min(6, len(groups))
            buttons = []
            for grp in groups[start_idx:end_idx]:
                buttons.append([Button.inline(f'👥 {grp["title"]}', f'show_grp_{grp["group_id"]}')])
            if total_pages > 1:
                buttons.append([Button.inline(f'➡️ Next (1/{total_pages})', b'group_list_next')])
            buttons.append([Button.inline('🔙 Back', b'owner_groups')])
            await event.edit('GROUPS LIST', buttons=buttons)

    elif data == b'group_list_next':
        from database import get_official_groups
        official_groups = get_official_groups()
        groups = official_groups if official_groups else get_all_groups()
        page = group_page_temp.get(sender.id, 1) + 1
        total_pages = (len(groups) + 5) // 6
        if page > total_pages:
            page = 1
        group_page_temp[sender.id] = page
        start_idx = (page - 1) * 6
        end_idx = min(start_idx + 6, len(groups))
        buttons = []
        for grp in groups[start_idx:end_idx]:
            buttons.append([Button.inline(f'👥 {grp["title"]}', f'show_grp_{grp["group_id"]}')])
        if total_pages > 1:
            buttons.append([Button.inline(f'➡️ Next ({page}/{total_pages})', b'group_list_next')])
        buttons.append([Button.inline('🔙 Back', b'owner_groups')])
        await event.edit('GROUPS LIST', buttons=buttons)

    elif data.startswith(b'remove_grp_'):
        group_id = int(data.split(b'_')[2])
        remove_group(group_id)
        from database import get_official_groups
        official_groups = get_official_groups()
        groups = official_groups if official_groups else get_all_groups()
        if not groups:
            await event.edit('All groups removed!', buttons=[[Button.inline('🔙 Back', b'owner_groups')]])
        else:
            total_pages = (len(groups) + 5) // 6
            group_page_temp[sender.id] = 1
            start_idx = 0
            end_idx = min(6, len(groups))
            buttons = []
            for grp in groups[start_idx:end_idx]:
                buttons.append([Button.inline(f'❌ {grp["username"]}', f'remove_grp_{grp["group_id"]}')])
            if total_pages > 1:
                buttons.append([Button.inline(f'➡️ Next (1/{total_pages})', b'group_remove_next')])
            buttons.append([Button.inline('🔙 Back', b'owner_groups')])
            try:
                await event.edit('REMOVE GROUP\n\nSelect group to remove:', buttons=buttons)
            except:
                await safe_answer(event, '✅ Group removed!')

    elif data.startswith(b'show_grp_'):
        group_id = int(data.split(b'_')[2])
        from database import get_official_groups
        official_groups = get_official_groups()
        groups = official_groups if official_groups else get_all_groups()
        grp_info = next((g for g in groups if g['group_id'] == group_id), None)
        if grp_info:
            info_text = f"👥 GROUP: {grp_info['title']}\nID: {grp_info['group_id']}\nUsername: @{grp_info['username']}\nAdded: {grp_info['added_date'][:10]}"
            await event.edit(info_text, buttons=[[Button.inline('🔙 Back', b'group_list_page_1')]])

    elif data == b'setting_start_text':
        buttons = [
            [Button.inline('👑 Owner', b'start_text_owner'), Button.inline('👤 User', b'start_text_user')],
            [Button.inline('🔙 Back', b'owner_settings')],
        ]
        await event.edit('START TEXT\n\nChoose which text to customize:', buttons=buttons)

    elif data == b'start_text_owner':
        buttons = [
            [Button.inline('✏️ Edit', b'start_text_owner_edit'), Button.inline('👁️ See', b'start_text_owner_see')],
            [Button.inline('🔄 Default', b'start_text_owner_default')],
            [Button.inline('🔙 Back', b'setting_start_text')],
        ]
        await event.edit('OWNER START TEXT\n\nWhat do you want to do?', buttons=buttons)

    elif data == b'start_text_user':
        buttons = [
            [Button.inline('✏️ Edit', b'start_text_user_edit'), Button.inline('👁️ See', b'start_text_user_see')],
            [Button.inline('🔄 Default', b'start_text_user_default')],
            [Button.inline('🔙 Back', b'setting_start_text')],
        ]
        await event.edit('USER START TEXT\n\nWhat do you want to do?', buttons=buttons)

    elif data == b'start_text_owner_edit':
        start_text_temp[sender.id] = 'owner'
        buttons = [[Button.inline('❌ Cancel', b'start_text_owner')]]
        help_text = "Type new start text for Owner:\n\nPlaceholders: {greeting}, {date}, {time}, {total_users}, {active_users}, {bot_name}"
        await event.edit(help_text, buttons=buttons)

    elif data == b'start_text_user_edit':
        start_text_temp[sender.id] = 'user'
        buttons = [[Button.inline('❌ Cancel', b'start_text_user')]]
        help_text = "Type new start text for User:\n\nPlaceholders: {greeting}, {first_name}, {username}, {date}, {user_messages}, {joined_date}"
        await event.edit(help_text, buttons=buttons)

    elif data == b'start_text_owner_see':
        owner_text = get_setting('owner_start_text', get_default_owner_text())
        preview = format_text(owner_text, sender, get_stats(), None)
        see_text = f"OWNER START TEXT PREVIEW:\n\n{preview}"
        await event.edit(see_text, buttons=[[Button.inline('🔙 Back', b'start_text_owner')]])

    elif data == b'start_text_user_see':
        user_text = get_setting('user_start_text', get_default_user_text())
        user_data = get_user(sender.id)
        preview = format_text(user_text, sender, get_stats(), user_data)
        see_text = f"USER START TEXT PREVIEW:\n\n{preview}"
        await event.edit(see_text, buttons=[[Button.inline('🔙 Back', b'start_text_user')]])

    elif data == b'start_text_owner_default':
        set_setting('owner_start_text', get_default_owner_text())
        await event.edit('✅ Owner start text reset to default!\n\nOK', buttons=[[Button.inline('🔙 Back', b'start_text_owner')]])

    elif data == b'start_text_user_default':
        set_setting('user_start_text', get_default_user_text())
        await event.edit('✅ User start text reset to default!\n\nOK', buttons=[[Button.inline('🔙 Back', b'start_text_user')]])

    elif data == b'setting_sub_force':
        channels = get_all_channels()
        buttons = [
            [Button.inline('➕ Add', b'sub_force_add'), Button.inline('➖ Remove', b'sub_force_remove')],
            [Button.inline('📋 List', b'sub_force_list_page_1')],
            [Button.inline('🔙 Back', b'owner_settings')],
        ]
        sub_text = f"SUB-FORCE (Channel Subscription)\n\nActive Channels: {len(channels)}\n\nWhat do you want to do?"
        await event.edit(sub_text, buttons=buttons)

    elif data == b'sub_force_add':
        channel_action_temp[sender.id] = 'add'
        buttons = [[Button.inline('❌ Cancel', b'setting_sub_force')]]
        await event.edit("ADD CHANNEL\n\nChoose one method:\n1. Channel ID (number)\n2. Channel username (@username)\n3. Forward message from channel", buttons=buttons)

    elif data == b'sub_force_remove':
        channels = get_all_channels()
        if not channels:
            await event.edit('No channels to remove!', buttons=[[Button.inline('🔙 Back', b'setting_sub_force')]])
        else:
            channel_page_temp[sender.id] = 1
            total_pages = (len(channels) + 5) // 6
            start_idx = 0
            end_idx = min(6, len(channels))
            buttons = []
            for ch in channels[start_idx:end_idx]:
                buttons.append([Button.inline(f'❌ {ch["username"]}', f'remove_ch_{ch["channel_id"]}')])
            if total_pages > 1:
                buttons.append([Button.inline(f'➡️ Next (1/{total_pages})', b'sub_force_remove_next')])
            buttons.append([Button.inline('🔙 Back', b'setting_sub_force')])
            await event.edit('REMOVE CHANNEL\n\nSelect channel to remove:', buttons=buttons)

    elif data == b'sub_force_remove_next':
        channels = get_all_channels()
        page = channel_page_temp.get(sender.id, 1) + 1
        total_pages = (len(channels) + 5) // 6
        if page > total_pages:
            page = 1
        channel_page_temp[sender.id] = page
        start_idx = (page - 1) * 6
        end_idx = min(start_idx + 6, len(channels))
        buttons = []
        for ch in channels[start_idx:end_idx]:
            buttons.append([Button.inline(f'❌ {ch["username"]}', f'remove_ch_{ch["channel_id"]}')])
        if total_pages > 1:
            buttons.append([Button.inline(f'➡️ Next ({page}/{total_pages})', b'sub_force_remove_next')])
        buttons.append([Button.inline('🔙 Back', b'setting_sub_force')])
        await event.edit('REMOVE CHANNEL\n\nSelect channel to remove:', buttons=buttons)

    elif data.startswith(b'remove_ch_'):
        channel_id = int(data.split(b'_')[2])
        channels = get_all_channels()
        for ch in channels:
            if ch['channel_id'] == channel_id:
                remove_channel(ch['username'])
                await event.edit(f'✅ Channel {ch["username"]} removed!', buttons=[[Button.inline('🔙 Back', b'setting_sub_force')]])
                break

    elif data == b'sub_force_list_page_1' or data.startswith(b'sub_force_list_page_'):
        channels = get_all_channels()
        if not channels:
            await event.edit('No channels added yet!', buttons=[[Button.inline('🔙 Back', b'setting_sub_force')]])
        else:
            if data.startswith(b'sub_force_list_page_'):
                # sub_force_list_page_X -> split gives [sub, force, list, page, X] so index 4
                page = int(data.split(b'_')[4])
            else:
                page = 1
            total_pages = (len(channels) + 5) // 6
            start_idx = (page - 1) * 6
            end_idx = min(start_idx + 6, len(channels))

            text = f"📺 CHANNELS LIST (Page {page}/{total_pages})\n\n"
            for i, ch in enumerate(channels[start_idx:end_idx], 1):
                added = ch['added_date'][:10] if ch['added_date'] else 'Unknown'
                text += f"{i}. @{ch['username']}\n"
                text += f"   Title: {ch['title']}\n"
                text += f"   Added: {added}\n\n"

            buttons = []
            if page > 1:
                buttons.append([Button.inline(f'⬅️ Prev ({page}/{total_pages})', f'sub_force_list_page_{page-1}'.encode())])
            if page < total_pages:
                buttons.append([Button.inline(f'➡️ Next ({page}/{total_pages})', f'sub_force_list_page_{page+1}'.encode())])
            buttons.append([Button.inline('🔙 Back', b'setting_sub_force')])
            await event.edit(text, buttons=buttons)

    elif data == b'owner_groups':
        # Official Groups Filter: Only show official groups in lists/tools
        from database import get_official_groups
        official_groups = get_official_groups()
        if official_groups:
            groups = official_groups
        else:
            # Fallback to all groups if no official groups defined
            groups = get_all_groups()
        
        buttons = [
            [Button.inline('➕ Add', b'group_add'), Button.inline('❌ Remove', b'group_remove')],
            [Button.inline('📋 List', b'group_list_page_1'), Button.inline('🗑️ Removed Groups', b'groups_removed_1')],
            [Button.inline('👋 Welcome Msgs', b'group_welcome_text')],
            [Button.inline('🏛️ Official Group', b'official_group_setting')],
            [Button.inline('🔙 Back', b'owner_back')],
        ]
        group_text = f"GROUPS\n\nConnected: {len(groups)}\n\nWhat do you want to do?"
        await event.edit(group_text, buttons=buttons)

    elif data == b'official_group_setting':
        from database import get_official_groups
        groups = get_official_groups()
        buttons = [
            [Button.inline('➕ Add', b'official_group_add'), Button.inline('❌ Remove', b'official_group_remove')],
            [Button.inline('📋 List', b'official_group_list')],
            [Button.inline('🔙 Back', b'owner_groups')]
        ]
        await event.edit(f"🏛️ **OFFICIAL GROUPS**\n\nTotal Official Groups: {len(groups)}\n\nManage your official group list:", buttons=buttons)

    elif data == b'official_group_add':
        from database import get_official_groups
        groups = get_all_groups()
        official_ids = [g['group_id'] for g in get_official_groups()]
        available = [g for g in groups if g['group_id'] not in official_ids]
        
        if not available:
            await event.edit("⚠️ **No groups available to add!**", buttons=[[Button.inline('🔙 Back', b'official_group_setting')]])
            return

        buttons = []
        for grp in available[:10]:
            buttons.append([Button.inline(f"➕ {grp['title']}", f"make_official_{grp['group_id']}".encode())])
        
        buttons.append([Button.inline('🔙 Back', b'official_group_setting')])
        await event.edit("➕ **SELECT GROUP TO MAKE OFFICIAL**", buttons=buttons)

    elif data.startswith(b'make_official_'):
        group_id = int(data.split(b'_')[2])
        from database import add_official_group
        add_official_group(group_id)
        await safe_answer(event, "✅ Group marked as Official!", alert=True)
        # Manually trigger official_group_setting logic to avoid event loop issues with click()
        from database import get_official_groups
        groups = get_official_groups()
        buttons = [
            [Button.inline('➕ Add', b'official_group_add'), Button.inline('❌ Remove', b'official_group_remove')],
            [Button.inline('📋 List', b'official_group_list')],
            [Button.inline('🔙 Back', b'owner_groups')]
        ]
        await event.edit(f"🏛️ **OFFICIAL GROUPS**\n\nTotal Official Groups: {len(groups)}\n\nManage your official group list:", buttons=buttons)

    elif data == b'official_group_remove':
        from database import get_official_groups
        groups = get_official_groups()
        if not groups:
            await event.edit("⚠️ **No official groups to remove!**", buttons=[[Button.inline('🔙 Back', b'official_group_setting')]])
            return

        buttons = []
        for grp in groups:
            buttons.append([Button.inline(f"❌ {grp['title']}", f"unoff_grp_{grp['group_id']}".encode())])
        
        buttons.append([Button.inline('🔙 Back', b'official_group_setting')])
        await event.edit("❌ **SELECT GROUP TO REMOVE FROM OFFICIALS**", buttons=buttons)

    elif data.startswith(b'unoff_grp_'):
        group_id = int(data.split(b'_')[2])
        from database import remove_official_group
        remove_official_group(group_id)
        await safe_answer(event, "✅ Group is now Unofficial!", alert=True)
        from database import get_official_groups
        groups = get_official_groups()
        buttons = [
            [Button.inline('➕ Add', b'official_group_add'), Button.inline('❌ Remove', b'official_group_remove')],
            [Button.inline('📋 List', b'official_group_list')],
            [Button.inline('🔙 Back', b'owner_groups')]
        ]
        await event.edit(f"🏛️ **OFFICIAL GROUPS**\n\nTotal Official Groups: {len(groups)}\n\nManage your official group list:", buttons=buttons)

    elif data == b'official_group_list':
        from database import get_official_groups
        groups = get_official_groups()
        if not groups:
            await event.edit("⚠️ **No official groups yet!**", buttons=[[Button.inline('🔙 Back', b'official_group_setting')]])
            return
            
        text = "🏛️ **OFFICIAL GROUPS LIST**\n\n"
        for i, grp in enumerate(groups, 1):
            text += f"{i}. {grp['title']} (@{grp['username']})\n"
        
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'official_group_setting')]])

    elif data.startswith(b'groups_removed_'):
        page = int(data.split(b'_')[2])
        removed_groups = get_removed_groups()
        if not removed_groups:
            await event.edit('🚫 **Abhi tak koi removed group nahi hai!**', buttons=[[Button.inline('🔙 Back', b'owner_groups')]])
            return
        
        total_pages = (len(removed_groups) + 5) // 6
        group_page_temp[sender.id] = page
        start_idx = (page - 1) * 6
        end_idx = min(start_idx + 6, len(removed_groups))
        
        buttons = []
        for grp in removed_groups[start_idx:end_idx]:
            buttons.append([Button.inline(f'🗑️ {grp["title"]}', f'show_removed_grp_{grp["group_id"]}'.encode())])
        
        nav_buttons = []
        if page > 1:
            nav_buttons.append(Button.inline('⬅️ Previous', f'groups_removed_{page-1}'.encode()))
        if page < total_pages:
            nav_buttons.append(Button.inline('➡️ Next', f'groups_removed_{page+1}'.encode()))
        if nav_buttons:
            buttons.append(nav_buttons)
            
        buttons.append([Button.inline('🔙 Back', b'owner_groups')])
        await event.edit(f'REMOVED GROUPS (Page {page}/{total_pages})', buttons=buttons)

    elif data.startswith(b'show_removed_grp_'):
        group_id = int(data.split(b'_')[3])
        grp_info = get_group_details(group_id)
        if grp_info:
            info_text = f"🗑️ **REMOVED GROUP INFO**\n\n"
            info_text += f"👥 **Name**: {grp_info['title']}\n"
            info_text += f"🆔 **ID**: `{grp_info['group_id']}`\n"
            info_text += f"📛 **Username**: @{grp_info['username']}\n"
            info_text += f"📅 **Added On**: {grp_info['added_date'][:10]}\n"
            info_text += f"👤 **Added By**: {grp_info['added_by_username'] or 'Unknown'} (`{grp_info['added_by_id'] or 'N/A'}`)\n"
            info_text += f"🔒 **Type**: {'Private' if grp_info['is_private'] else 'Public'}\n"
            
            buttons = [
                [Button.inline('🔄 Re-add', f'readd_confirm_{group_id}'.encode())],
                [Button.inline('🔙 Back', b'groups_removed_1')]
            ]
            await event.edit(info_text, buttons=buttons)
        else:
            await safe_answer(event, "❌ Group details not found!", alert=True)

    elif data.startswith(b'readd_confirm_'):
        group_id = int(data.split(b'_')[2])
        buttons = [
            [Button.inline('✅ Yes, Re-add', f'readd_group_{group_id}'.encode()), Button.inline('❌ No', f'show_removed_grp_{group_id}'.encode())]
        ]
        await event.edit("⚠️ **Are you sure you want to re-add this group?**", buttons=buttons)

    elif data.startswith(b'readd_group_'):
        group_id = int(data.split(b'_')[2])
        grp_info = get_group_details(group_id)
        if grp_info:
            add_group(grp_info['group_id'], grp_info['username'], grp_info['title'], grp_info['invite_link'], grp_info['added_by_id'], grp_info['added_by_username'], grp_info['is_private'])
            try:
                await client.send_message(group_id, f"Hello {grp_info['title']} ke members\nI'm back")
            except Exception as e:
                print(f"[LOG] Error sending I'm back message: {e}")
            await event.edit(f"✅ Group **{grp_info['title']}** has been re-added!", buttons=[[Button.inline('🔙 Back', b'owner_groups')]])

    elif data.startswith(b'show_grp_'):
        group_id = int(data.split(b'_')[2])
        grp_info = get_group_details(group_id)
        if grp_info:
            # Check permissions
            bot_me = await client.get_me()
            perms_text = ""
            perms = None
            try:
                perms = await client.get_permissions(group_id, bot_me.id)
                perms_text += f"{'🟢' if perms.is_admin else '🔴'} Manage Group\n"
                perms_text += f"{'🟢' if perms.delete_messages else '🔴'} Delete Messages\n"
                perms_text += f"{'🟢' if perms.ban_users else '🔴'} Ban Users\n"
                perms_text += f"{'🟢' if perms.invite_users else '🔴'} Invite Users\n"
            except:
                perms_text = "Could not fetch permissions (Bot might not be in group)"

            info_text = f"👥 **GROUP DETAILS**\n\n"
            info_text += f"Name: {grp_info['title']}\n"
            info_text += f"ID: `{grp_info['group_id']}`\n"
            info_text += f"Username: @{grp_info['username']}\n"
            info_text += f"Added: {grp_info['added_date'][:10]}\n"
            info_text += f"Type: {'Private' if grp_info['is_private'] else 'Public'}\n"
            info_text += f"Added By: {grp_info['added_by_username'] or 'Unknown'}\n\n"
            info_text += f"🛡️ **Permissions:**\n{perms_text}"
            
            buttons = [
                [Button.inline('🗑️ Remove', f'remove_grp_{group_id}'), Button.inline('🔄 Revoke Link', f'revoke_link_{group_id}')],
                [Button.inline('🔑 Required Permission', f'req_perm_{group_id}')],
                [Button.inline('🔙 Back', b'group_list_page_1')]
            ]
            await event.edit(info_text, buttons=buttons)

    elif data.startswith(b'revoke_link_'):
        group_id = int(data.split(b'_')[2])
        try:
            from telethon.tl.functions.messages import ExportChatInviteRequest
            new_invite = await client(ExportChatInviteRequest(group_id))
            update_group_invite_link(group_id, new_invite.link)
            await safe_answer(event, "✅ Invite link revoked and updated!", alert=True)
            # Refresh view
            await event.click(f'show_grp_{group_id}')
        except Exception as e:
            await safe_answer(event, f"❌ Error: {str(e)}", alert=True)

    elif data.startswith(b'req_perm_'):
        group_id = int(data.split(b'_')[2])
        bot_me = await client.get_me()
        try:
            perms = await client.get_permissions(group_id, bot_me.id)
            msg = "📢 **Permission Request**\n\nMujhe ye permission chahiye please give me this permission:\n\n"
            msg += f"1. Manage group (required) {'🟢' if perms.is_admin else '🔴'}\n"
            msg += f"2. Delete msg (optional) {'🟢' if perms.delete_messages else '🔴'}\n"
            msg += f"3. Ban users (optional) {'🟢' if perms.ban_users else '🔴'}\n"
            msg += f"4. Invite users (required) {'🟢' if perms.invite_users else '🔴'}"
            
            await client.send_message(group_id, msg)
            await safe_answer(event, "✅ Permission request sent to group!", alert=True)
            
            # Logic for warning system
            if not perms.is_admin or not perms.invite_users:
                warnings = increment_permission_warning(group_id)
                if warnings >= 5:
                    await client.send_message(group_id, "🚫 Required permission na hone ki vjha se group remove hogya hai")
                    remove_group(group_id)
                    await client.kick_participant(group_id, 'me')
                    await event.edit("🚫 Group removed due to 5 permission warnings!", buttons=[[Button.inline('🔙 Back', b'owner_groups')]])
        except Exception as e:
            await safe_answer(event, f"❌ Error: {str(e)}", alert=True)

    elif data == b'owner_settings':
        buttons = [
            [Button.inline('🛠️ Tools Handler', b'setting_tools_handler')],
            [Button.inline('📺 Sub-Force', b'setting_sub_force'), Button.inline('👥 Groups', b'owner_groups')],
            [Button.inline('📝 Start Text', b'setting_start_text'), Button.inline('💾 Backup', b'setting_backup')],
            [Button.inline('❓ Help Desk', b'setting_help_desk'), Button.inline('ℹ️ About Desk', b'setting_about_desk')],
            [Button.inline('🚫 Bad Words', b'setting_bad_words')],
            [Button.inline('🔙 Back', b'owner_back')],
        ]
        settings_text = "⚙️ **BOT SETTINGS**\n\nConfigure your bot settings:"
        await event.edit(settings_text, buttons=buttons)

    elif data == b'setting_help_desk':
        buttons = [
            [Button.inline('✏️ Edit', b'help_desk_edit'), Button.inline('👁️ See', b'help_desk_see')],
            [Button.inline('🔙 Back', b'owner_settings')],
        ]
        default_help = """🛠️ **OWNER HELP DESK**

👑 Hello Boss! Here is your quick guide to manage the bot.

📢 **Broadcast Management:**
• /broadcast - Send message to everyone
• Bot Only - Direct messages to users
• Group Only - Messages to all groups

⚙️ **System Control:**
• /settings - Access bot configuration
• /tools - Manage lookup tool statuses
• /backup - Manually trigger cloud backup

👥 **User Management:**
• /ban [ID] - Restrict a user
• /unban [ID] - Lift restriction
• /stats - View detailed growth reports

🛡️ **Security:**
• Keep API keys secret
• Regularly check backup logs
• Monitor unauthorized group additions"""
        current_help = get_setting('owner_help_text', default_help)
        await event.edit(current_help, buttons=buttons)

    elif data == b'help_desk_edit':
        start_text_temp[sender.id] = 'owner_help_desk'
        buttons = [[Button.inline('❌ Cancel', b'setting_help_desk')]]
        help_text = "✏️ **EDIT OWNER HELP TEXT**\n\nSend new help message for yourself."
        await event.edit(help_text, buttons=buttons)

    elif data == b'help_desk_see':
        default_help = """🛠️ **OWNER HELP DESK**

👑 Hello Boss! Here is your quick guide to manage the bot.

📢 **Broadcast Management:**
• /broadcast - Send message to everyone
• Bot Only - Direct messages to users
• Group Only - Messages to all groups

⚙️ **System Control:**
• /settings - Access bot configuration
• /tools - Manage lookup tool statuses
• /backup - Manually trigger cloud backup

👥 **User Management:**
• /ban [ID] - Restrict a user
• /unban [ID] - Lift restriction
• /stats - View detailed growth reports

🛡️ **Security:**
• Keep API keys secret
• Regularly check backup logs
• Monitor unauthorized group additions"""
        current_help = get_setting('owner_help_text', default_help)
        user_data = get_user(sender.id)
        preview = format_text(current_help, sender, get_stats(), user_data)
        buttons = [[Button.inline('🔙 Back', b'setting_help_desk')]]
        await event.edit(f"👁️ **OWNER HELP PREVIEW:**\n\n{preview}", buttons=buttons)

    elif data == b'setting_about_desk':
        buttons = [
            [Button.inline('✏️ Edit', b'about_desk_edit'), Button.inline('👁️ See', b'about_desk_see')],
            [Button.inline('🔙 Back', b'owner_settings')],
        ]
        await event.edit('ℹ️ **ABOUT DESK**\n\nManage user about section:\n\n📝 Edit the about message shown to users\n👁️ Preview current about message', buttons=buttons)

    elif data == b'about_desk_edit':
        start_text_temp[sender.id] = 'about_desk'
        buttons = [[Button.inline('❌ Cancel', b'setting_about_desk')]]
        about_text = "✏️ **EDIT ABOUT TEXT**\n\nSend new about message.\n\n📌 **Available Placeholders:**\n{greeting} - Time-based greeting\n{first_name} - User's first name\n{username} - User's username\n{user_id} - User's ID\n{bot_name} - Bot name\n{date} - Current date\n{time} - Current time\n{total_users} - Total users\n{active_users} - Active users\n{banned_users} - Banned users\n{total_messages} - Total messages\n{user_messages} - User's message count\n{joined_date} - User join date"
        await event.edit(about_text, buttons=buttons)

    elif data == b'about_desk_see':
        default_about = """ℹ️ **ABOUT THE BOT**

🤖 **Ultimate Multi-Tool Bot**
The most advanced information lookup tool on Telegram.

📊 **Statistics:**
• 👥 Total Users: {total_users}
• ✅ Active Now: {active_users}
• 🛠️ Active Tools: 9+

📅 **Current Date:** {date}
⏰ **System Time:** {time}

⚡ **Key Features:**
• Real-time Lookup APIs
• Secure User Management
• Fast Group Moderation
• Automatic Cloud Backup

Developed with ❤️ by @KissuHQ"""
        current_about = get_setting('user_about_text', default_about)
        user_data = get_user(sender.id)
        preview = format_text(current_about, sender, get_stats(), user_data)
        buttons = [[Button.inline('🔙 Back', b'setting_about_desk')]]
        await event.edit(f"👁️ **ABOUT TEXT PREVIEW:**\n\n{preview}", buttons=buttons)

    elif data == b'setting_backup':
        backup_channel = get_backup_channel()
        if not backup_channel:
            buttons = [[Button.inline('🔙 Back', b'owner_settings')]]
            await event.edit('💾 BACKUP\n\n⚠️ Please set backup channel first!\n\nSend me one of:\n- Channel ID (number)\n- @username\n- Forward a message from the channel', buttons=buttons)
            backup_channel_temp[sender.id] = 'add'
        else:
            interval = get_backup_interval()
            buttons = [
                [Button.inline('🔄 Change Channel', b'backup_change_channel')],
                [Button.inline('⏰ Interval Time', b'backup_interval'), Button.inline('💾 Backup Now', b'backup_now')],
                [Button.inline('🔙 Back', b'owner_settings')],
            ]
            backup_text = f"💾 BACKUP SETTINGS\n\n📺 Channel: {backup_channel['title']}\n@{backup_channel['username']}\n\n⏰ Interval: {interval} minutes"
            await event.edit(backup_text, buttons=buttons)

    elif data == b'backup_change_channel':
        buttons = [[Button.inline('🔙 Back', b'setting_backup')]]
        await event.edit('🔄 CHANGE BACKUP CHANNEL\n\nSend me one of:\n- Channel ID (number)\n- @username\n- Forward a message from the channel', buttons=buttons)
        backup_channel_temp[sender.id] = 'add'

    elif data == b'backup_interval':
        buttons = [[Button.inline('🔙 Back', b'setting_backup')]]
        await event.edit('⏰ SET BACKUP INTERVAL\n\nSend interval in minutes (e.g., 1440, 720, 60):', buttons=buttons)
        backup_channel_temp[sender.id] = 'interval'

    elif data == b'backup_now':
        backup_channel_temp[sender.id] = 'restore'
        buttons = [[Button.inline('🔙 Back', b'setting_backup')]]
        await event.edit('💾 BACKUP NOW\n\n📤 Send me the database file (.db) to restore.\n\n⚠️ Warning: This will replace the current database!', buttons=buttons)

    elif data == b'setting_bad_words':
        bad_words_count = get_bad_words_count()
        bad_words_enabled = get_setting('bad_words_filter_enabled', '1') == '1'
        status_text = "✅ ON" if bad_words_enabled else "❌ OFF"
        toggle_btn = b'bad_words_toggle_off' if bad_words_enabled else b'bad_words_toggle_on'
        toggle_text = "🔴 Turn OFF" if bad_words_enabled else "🟢 Turn ON"
        
        buttons = [
            [Button.inline(toggle_text, toggle_btn)],
            [Button.inline('➕ Add', b'bad_words_add'), Button.inline('➖ Remove', b'bad_words_remove')],
            [Button.inline('📄 File', b'bad_words_file')],
            [Button.inline('🔙 Back', b'owner_settings')],
        ]
        bad_words_text = f"🚫 **BAD WORDS SETTINGS**\n\n📊 Total Keywords: {bad_words_count}\n📡 Status: {status_text}\n\n🔹 Toggle - Enable/Disable filter\n🔹 Add - Add new bad words\n🔹 Remove - Remove existing words\n🔹 File - Download bad words file"
        await event.edit(bad_words_text, buttons=buttons)
    
    elif data == b'bad_words_toggle_on':
        set_setting('bad_words_filter_enabled', '1')
        await safe_answer(event, "✅ Bad word filter is now ON", alert=True)
        # Refresh the settings panel
        bad_words_count = get_bad_words_count()
        buttons = [
            [Button.inline("🔴 Turn OFF", b'bad_words_toggle_off')],
            [Button.inline('➕ Add', b'bad_words_add'), Button.inline('➖ Remove', b'bad_words_remove')],
            [Button.inline('📄 File', b'bad_words_file')],
            [Button.inline('🔙 Back', b'owner_settings')],
        ]
        bad_words_text = f"🚫 **BAD WORDS SETTINGS**\n\n📊 Total Keywords: {bad_words_count}\n📡 Status: ✅ ON\n\n🔹 Toggle - Enable/Disable filter\n🔹 Add - Add new bad words\n🔹 Remove - Remove existing words\n🔹 File - Download bad words file"
        await event.edit(bad_words_text, buttons=buttons)
    
    elif data == b'bad_words_toggle_off':
        set_setting('bad_words_filter_enabled', '0')
        await safe_answer(event, "❌ Bad word filter is now OFF", alert=True)
        # Refresh the settings panel
        bad_words_count = get_bad_words_count()
        buttons = [
            [Button.inline("🟢 Turn ON", b'bad_words_toggle_on')],
            [Button.inline('➕ Add', b'bad_words_add'), Button.inline('➖ Remove', b'bad_words_remove')],
            [Button.inline('📄 File', b'bad_words_file')],
            [Button.inline('🔙 Back', b'owner_settings')],
        ]
        bad_words_text = f"🚫 **BAD WORDS SETTINGS**\n\n📊 Total Keywords: {bad_words_count}\n📡 Status: ❌ OFF\n\n🔹 Toggle - Enable/Disable filter\n🔹 Add - Add new bad words\n🔹 Remove - Remove existing words\n🔹 File - Download bad words file"
        await event.edit(bad_words_text, buttons=buttons)

    elif data == b'bad_words_add':
        bad_words_action_temp[sender.id] = 'add'
        buttons = [[Button.inline('❌ Cancel', b'setting_bad_words')]]
        add_text = "➕ **ADD BAD WORDS**\n\n📝 Send bad words to add:\n\n**Format:**\n• Comma separated: word1, word2, word3\n• One per line:\nword1\nword2\nword3\n\n📎 You can also send a .txt file with words"
        await event.edit(add_text, buttons=buttons)

    elif data == b'bad_words_remove':
        bad_words_action_temp[sender.id] = 'remove'
        buttons = [[Button.inline('❌ Cancel', b'setting_bad_words')]]
        remove_text = "➖ **REMOVE BAD WORDS**\n\n📝 Send words to remove:\n\n**Format:**\n• Comma separated: word1, word2, word3\n• One per line:\nword1\nword2\nword3"
        await event.edit(remove_text, buttons=buttons)

    elif data == b'bad_words_file':
        try:
            file_content = get_bad_words_file_content()
            filename = 'kick_out.txt'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(file_content)
            await client.send_file(sender.id, filename, caption="📄 **Bad Words List**\n\nThis file contains all the bad words the bot will detect.")
            os.remove(filename)
            await safe_answer(event, "📄 File sent!", alert=False)
        except Exception as e:
            await safe_answer(event, f"Error: {str(e)}", alert=True)

    elif data == b'setting_tools_handler':
        tools_map = [
            ('number_info', '📱 Number Info', b'tool_number_info'),
            ('aadhar_info', '🆔 Aadhar Info', b'tool_aadhar_info'),
            ('aadhar_family', '👨‍👩‍👧‍👦 Aadhar to Family', b'tool_aadhar_family'),
            ('vehicle_info', '🚗 Vehicle Info', b'tool_vehicle_info'),
            ('ifsc_info', '🏦 IFSC Info', b'tool_ifsc_info'),
            ('pak_num', '🇵🇰 Pak Num Info', b'tool_pak_num'),
            ('pincode_info', '📍 Pin Code Info', b'tool_pincode_info'),
            ('imei_info', '📱 IMEI Info', b'tool_imei_info'),
            ('ip_info', '🌐 IP Info', b'tool_ip_info'),
        ]

        buttons = [
            [Button.inline(tools_map[0][1], tools_map[0][2])],
            [Button.inline(tools_map[1][1], tools_map[1][2]), Button.inline(tools_map[2][1], tools_map[2][2])],
            [Button.inline(tools_map[3][1], tools_map[3][2]), Button.inline(tools_map[4][1], tools_map[4][2])],
            [Button.inline(tools_map[5][1], tools_map[5][2]), Button.inline(tools_map[6][1], tools_map[6][2])],
            [Button.inline(tools_map[7][1], tools_map[7][2]), Button.inline(tools_map[8][1], tools_map[8][2])],
            [Button.inline('🔙 Back', b'owner_settings')],
        ]

        tools_text = "🛠️ TOOLS HANDLER\n\nManage Tools (Active/Inactive):"
        await event.edit(tools_text, buttons=buttons)

    elif data == b'tool_number_info':
        status = get_tool_status('number_info')
        status_text = '✅ Active' if status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_number_add_api'), Button.inline('➖ Remove API', b'tool_number_remove_api')],
            [Button.inline('📋 All API', b'tool_number_all_api'), Button.inline('📊 Status', b'tool_number_status')],
            [Button.inline(f'{status_text}', b'tool_number_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('📱 NUMBER INFO\n\nManage Number Info APIs', buttons=buttons)

    elif data == b'tool_number_toggle':
        current_status = get_tool_status('number_info')
        set_tool_status('number_info', not current_status)
        new_status = get_tool_status('number_info')
        status_text = '✅ Active' if new_status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_number_add_api'), Button.inline('➖ Remove API', b'tool_number_remove_api')],
            [Button.inline('📋 All API', b'tool_number_all_api'), Button.inline('📊 Status', b'tool_number_status')],
            [Button.inline(f'{status_text}', b'tool_number_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('📱 NUMBER INFO\n\nManage Number Info APIs', buttons=buttons)

    elif data == b'tool_number_add_api':
        tool_api_action[sender.id] = 'number_info'
        placeholder = TOOL_CONFIG['number_info']['placeholder']
        buttons = [[Button.inline('❌ Cancel', b'tool_number_info')]]
        await event.edit(f'➕ ADD API for Number Info\n\nSend API URL with placeholder {placeholder}\n\nExample:\nhttps://api.example.com/search?number={placeholder}', buttons=buttons)

    elif data == b'tool_number_remove_api':
        apis = get_tool_apis('number_info')
        if not apis:
            await event.edit('❌ No APIs found!', buttons=[[Button.inline('🔙 Back', b'tool_number_info')]])
        else:
            buttons = []
            for api in apis:
                api_preview = api['url'][:40] + '...' if len(api['url']) > 40 else api['url']
                buttons.append([Button.inline(f'❌ {api_preview}', f'remove_number_api_{api["id"]}'.encode())])
            buttons.append([Button.inline('🔙 Back', b'tool_number_info')])
            await event.edit('➖ REMOVE API\n\nSelect API to remove:', buttons=buttons)

    elif data.startswith(b'remove_number_api_'):
        api_id = int(data.decode().split('_')[3])
        remove_tool_api('number_info', api_id)
        await event.edit('✅ API removed!', buttons=[[Button.inline('🔙 Back', b'tool_number_info')]])

    elif data == b'tool_number_all_api':
        apis = get_tool_apis('number_info')
        if not apis:
            text = '📋 ALL APIs\n\nNo APIs configured yet.'
        else:
            text = f'📋 ALL APIs ({len(apis)})\n\n'
            for i, api in enumerate(apis, 1):
                text += f'{i}. {api["url"]}\n   Added: {api["added_date"][:10]}\n\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_number_info')]])

    elif data == b'tool_number_status':
        apis = get_tool_apis('number_info')
        status = get_tool_status('number_info')
        text = f'📊 NUMBER INFO STATUS\n\n'
        text += f'Tool Status: {"✅ Active" if status else "❌ Inactive"}\n'
        text += f'APIs Configured: {len(apis)}\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_number_info')]])

    elif data == b'tool_aadhar_info':
        status = get_tool_status('aadhar_info')
        status_text = '✅ Active' if status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_aadhar_add_api'), Button.inline('➖ Remove API', b'tool_aadhar_remove_api')],
            [Button.inline('📋 All API', b'tool_aadhar_all_api'), Button.inline('📊 Status', b'tool_aadhar_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_aadhar_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('🆔 AADHAR INFO\n\nManage Aadhar Info APIs', buttons=buttons)

    elif data == b'tool_aadhar_toggle':
        current_status = get_tool_status('aadhar_info')
        set_tool_status('aadhar_info', not current_status)
        new_status = get_tool_status('aadhar_info')
        status_text = '✅ Active' if new_status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_aadhar_add_api'), Button.inline('➖ Remove API', b'tool_aadhar_remove_api')],
            [Button.inline('📋 All API', b'tool_aadhar_all_api'), Button.inline('📊 Status', b'tool_aadhar_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_aadhar_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('🆔 AADHAR INFO\n\nManage Aadhar Info APIs', buttons=buttons)

    elif data == b'tool_aadhar_add_api':
        tool_api_action[sender.id] = 'aadhar_info'
        placeholder = TOOL_CONFIG['aadhar_info']['placeholder']
        buttons = [[Button.inline('❌ Cancel', b'tool_aadhar_info')]]
        await event.edit(f'➕ ADD API for Aadhar Info\n\nSend API URL with placeholder {placeholder}\n\nExample:\nhttps://api.example.com/ aadhar?id={placeholder}', buttons=buttons)

    elif data == b'tool_aadhar_remove_api':
        apis = get_tool_apis('aadhar_info')
        if not apis:
            await event.edit('❌ No APIs found!', buttons=[[Button.inline('🔙 Back', b'tool_aadhar_info')]])
        else:
            buttons = []
            for api in apis:
                api_preview = api['url'][:40] + '...' if len(api['url']) > 40 else api['url']
                buttons.append([Button.inline(f'❌ {api_preview}', f'remove_aadhar_api_{api["id"]}'.encode())])
            buttons.append([Button.inline('🔙 Back', b'tool_aadhar_info')])
            await event.edit('➖ REMOVE API\n\nSelect API to remove:', buttons=buttons)

    elif data.startswith(b'remove_aadhar_api_'):
        api_id = int(data.decode().split('_')[3])
        remove_tool_api('aadhar_info', api_id)
        await event.edit('✅ API removed!', buttons=[[Button.inline('🔙 Back', b'tool_aadhar_info')]])

    elif data == b'tool_aadhar_all_api':
        apis = get_tool_apis('aadhar_info')
        if not apis:
            text = '📋 ALL APIs\n\nNo APIs configured yet.'
        else:
            text = f'📋 ALL APIs ({len(apis)})\n\n'
            for i, api in enumerate(apis, 1):
                text += f'{i}. {api["url"]}\n   Added: {api["added_date"][:10]}\n\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_aadhar_info')]])

    elif data == b'tool_aadhar_status':
        apis = get_tool_apis('aadhar_info')
        status = get_tool_status('aadhar_info')
        text = f'📊 AADHAR INFO STATUS\n\n'
        text += f'Tool Status: {"✅ Active" if status else "❌ Inactive"}\n'
        text += f'APIs Configured: {len(apis)}\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_aadhar_info')]])

    elif data == b'tool_aadhar_family':
        status = get_tool_status('aadhar_family')
        status_text = '✅ Active' if status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_family_add_api'), Button.inline('➖ Remove API', b'tool_family_remove_api')],
            [Button.inline('📋 All API', b'tool_family_all_api'), Button.inline('📊 Status', b'tool_family_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_family_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('👨‍👩‍👧‍👦 AADHAR TO FAMILY\n\nManage Aadhar to Family APIs', buttons=buttons)

    elif data == b'tool_family_toggle':
        current_status = get_tool_status('aadhar_family')
        set_tool_status('aadhar_family', not current_status)
        new_status = get_tool_status('aadhar_family')
        status_text = '✅ Active' if new_status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_family_add_api'), Button.inline('➖ Remove API', b'tool_family_remove_api')],
            [Button.inline('📋 All API', b'tool_family_all_api'), Button.inline('📊 Status', b'tool_family_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_family_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('👨‍👩‍👧‍👦 AADHAR TO FAMILY\n\nManage Aadhar to Family APIs', buttons=buttons)

    elif data == b'tool_family_add_api':
        tool_api_action[sender.id] = 'aadhar_family'
        placeholder = TOOL_CONFIG['aadhar_family']['placeholder']
        buttons = [[Button.inline('❌ Cancel', b'tool_aadhar_family')]]
        await event.edit(f'➕ ADD API for Aadhar Family\n\nSend API URL with placeholder {placeholder}', buttons=buttons)

    elif data == b'tool_family_remove_api':
        apis = get_tool_apis('aadhar_family')
        if not apis:
            await event.edit('❌ No APIs found!', buttons=[[Button.inline('🔙 Back', b'tool_aadhar_family')]])
        else:
            buttons = []
            for api in apis:
                api_preview = api['url'][:40] + '...' if len(api['url']) > 40 else api['url']
                buttons.append([Button.inline(f'❌ {api_preview}', f'remove_family_api_{api["id"]}'.encode())])
            buttons.append([Button.inline('🔙 Back', b'tool_aadhar_family')])
            await event.edit('➖ REMOVE API\n\nSelect API to remove:', buttons=buttons)

    elif data.startswith(b'remove_family_api_'):
        api_id = int(data.decode().split('_')[3])
        remove_tool_api('aadhar_family', api_id)
        await event.edit('✅ API removed!', buttons=[[Button.inline('🔙 Back', b'tool_aadhar_family')]])

    elif data == b'tool_family_all_api':
        apis = get_tool_apis('aadhar_family')
        if not apis:
            text = '📋 ALL APIs\n\nNo APIs configured yet.'
        else:
            text = f'📋 ALL APIs ({len(apis)})\n\n'
            for i, api in enumerate(apis, 1):
                text += f'{i}. {api["url"]}\n   Added: {api["added_date"][:10]}\n\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_aadhar_family')]])

    elif data == b'tool_family_status':
        apis = get_tool_apis('aadhar_family')
        status = get_tool_status('aadhar_family')
        text = f'📊 AADHAR FAMILY STATUS\n\n'
        text += f'Tool Status: {"✅ Active" if status else "❌ Inactive"}\n'
        text += f'APIs Configured: {len(apis)}\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_aadhar_family')]])

    elif data == b'tool_vehicle_info':
        status = get_tool_status('vehicle_info')
        status_text = '✅ Active' if status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_vehicle_add_api'), Button.inline('➖ Remove API', b'tool_vehicle_remove_api')],
            [Button.inline('📋 All API', b'tool_vehicle_all_api'), Button.inline('📊 Status', b'tool_vehicle_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_vehicle_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('🚗 VEHICLE INFO\n\nManage Vehicle Info APIs', buttons=buttons)

    elif data == b'tool_vehicle_toggle':
        current_status = get_tool_status('vehicle_info')
        set_tool_status('vehicle_info', not current_status)
        new_status = get_tool_status('vehicle_info')
        status_text = '✅ Active' if new_status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_vehicle_add_api'), Button.inline('➖ Remove API', b'tool_vehicle_remove_api')],
            [Button.inline('📋 All API', b'tool_vehicle_all_api'), Button.inline('📊 Status', b'tool_vehicle_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_vehicle_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('🚗 VEHICLE INFO\n\nManage Vehicle Info APIs', buttons=buttons)

    elif data == b'tool_ifsc_info':
        status = get_tool_status('ifsc_info')
        status_text = '✅ Active' if status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_ifsc_add_api'), Button.inline('➖ Remove API', b'tool_ifsc_remove_api')],
            [Button.inline('📋 All API', b'tool_ifsc_all_api'), Button.inline('📊 Status', b'tool_ifsc_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_ifsc_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('🏦 IFSC INFO\n\nManage IFSC Info APIs', buttons=buttons)

    elif data == b'tool_ifsc_toggle':
        current_status = get_tool_status('ifsc_info')
        set_tool_status('ifsc_info', not current_status)
        new_status = get_tool_status('ifsc_info')
        status_text = '✅ Active' if new_status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_ifsc_add_api'), Button.inline('➖ Remove API', b'tool_ifsc_remove_api')],
            [Button.inline('📋 All API', b'tool_ifsc_all_api'), Button.inline('📊 Status', b'tool_ifsc_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_ifsc_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('🏦 IFSC INFO\n\nManage IFSC Info APIs', buttons=buttons)

    elif data == b'tool_pak_num':
        status = get_tool_status('pak_num')
        status_text = '✅ Active' if status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_pak_add_api'), Button.inline('➖ Remove API', b'tool_pak_remove_api')],
            [Button.inline('📋 All API', b'tool_pak_all_api'), Button.inline('📊 Status', b'tool_pak_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_pak_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('🇵🇰 PAK NUM INFO\n\nManage Pak Number APIs', buttons=buttons)

    elif data == b'tool_pak_toggle':
        current_status = get_tool_status('pak_num')
        set_tool_status('pak_num', not current_status)
        new_status = get_tool_status('pak_num')
        status_text = '✅ Active' if new_status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_pak_add_api'), Button.inline('➖ Remove API', b'tool_pak_remove_api')],
            [Button.inline('📋 All API', b'tool_pak_all_api'), Button.inline('📊 Status', b'tool_pak_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_pak_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('🇵🇰 PAK NUM INFO\n\nManage Pak Number APIs', buttons=buttons)

    elif data == b'tool_pincode_info':
        status = get_tool_status('pincode_info')
        status_text = '✅ Active' if status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_pin_add_api'), Button.inline('➖ Remove API', b'tool_pin_remove_api')],
            [Button.inline('📋 All API', b'tool_pin_all_api'), Button.inline('📊 Status', b'tool_pin_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_pin_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('📍 PIN CODE INFO\n\nManage Pin Code APIs', buttons=buttons)

    elif data == b'tool_pin_toggle':
        current_status = get_tool_status('pincode_info')
        set_tool_status('pincode_info', not current_status)
        new_status = get_tool_status('pincode_info')
        status_text = '✅ Active' if new_status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_pin_add_api'), Button.inline('➖ Remove API', b'tool_pin_remove_api')],
            [Button.inline('📋 All API', b'tool_pin_all_api'), Button.inline('📊 Status', b'tool_pin_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_pin_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('📍 PIN CODE INFO\n\nManage Pin Code APIs', buttons=buttons)

    elif data == b'tool_imei_info':
        status = get_tool_status('imei_info')
        status_text = '✅ Active' if status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_imei_add_api'), Button.inline('➖ Remove API', b'tool_imei_remove_api')],
            [Button.inline('📋 All API', b'tool_imei_all_api'), Button.inline('📊 Status', b'tool_imei_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_imei_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('📱 IMEI INFO\n\nManage IMEI Info APIs', buttons=buttons)

    elif data == b'tool_imei_toggle':
        current_status = get_tool_status('imei_info')
        set_tool_status('imei_info', not current_status)
        new_status = get_tool_status('imei_info')
        status_text = '✅ Active' if new_status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_imei_add_api'), Button.inline('➖ Remove API', b'tool_imei_remove_api')],
            [Button.inline('📋 All API', b'tool_imei_all_api'), Button.inline('📊 Status', b'tool_imei_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_imei_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('📱 IMEI INFO\n\nManage IMEI Info APIs', buttons=buttons)

    elif data == b'tool_ip_info':
        status = get_tool_status('ip_info')
        status_text = '✅ Active' if status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_ip_add_api'), Button.inline('➖ Remove API', b'tool_ip_remove_api')],
            [Button.inline('📋 All API', b'tool_ip_all_api'), Button.inline('📊 Status', b'tool_ip_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_ip_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('🌐 IP INFO\n\nManage IP Info APIs', buttons=buttons)

    elif data == b'tool_ip_toggle':
        current_status = get_tool_status('ip_info')
        set_tool_status('ip_info', not current_status)
        new_status = get_tool_status('ip_info')
        status_text = '✅ Active' if new_status else '❌ Inactive'
        buttons = [
            [Button.inline('➕ Add API', b'tool_ip_add_api'), Button.inline('➖ Remove API', b'tool_ip_remove_api')],
            [Button.inline('📋 All API', b'tool_ip_all_api'), Button.inline('📊 Status', b'tool_ip_status')],
            [Button.inline(f'🔄 {status_text}', b'tool_ip_toggle')],
            [Button.inline('🔙 Back', b'setting_tools_handler')],
        ]
        await event.edit('🌐 IP INFO\n\nManage IP Info APIs', buttons=buttons)

    # Handle skip field mapping button
    elif data.startswith(b'skip_field_mapping_'):
        api_id = int(data.decode().split('_')[3])
        # Clear any pending field mapping session
        if sender.id in api_field_mapping_temp:
            tool_name = api_field_mapping_temp[sender.id].get('tool_name', 'number_info')
            del api_field_mapping_temp[sender.id]
            back_btn = get_tool_back_button(tool_name)
        else:
            back_btn = b'setting_tools_handler'
        update_api_response_fields(api_id, None)
        await event.edit('✅ API added!\n\n📋 Response: Full JSON (all fields)', buttons=[[Button.inline('🔙 Back', back_btn)]])

    # Vehicle Info API Management
    elif data == b'tool_vehicle_add_api':
        tool_api_action[sender.id] = 'vehicle_info'
        placeholder = TOOL_CONFIG['vehicle_info']['placeholder']
        buttons = [[Button.inline('❌ Cancel', b'tool_vehicle_info')]]
        await event.edit(f'➕ ADD API for Vehicle Info\n\nSend API URL with placeholder {placeholder}', buttons=buttons)

    elif data == b'tool_vehicle_remove_api':
        apis = get_tool_apis('vehicle_info')
        if not apis:
            await event.edit('❌ No APIs found!', buttons=[[Button.inline('🔙 Back', b'tool_vehicle_info')]])
        else:
            buttons = []
            for api in apis:
                api_preview = api['url'][:40] + '...' if len(api['url']) > 40 else api['url']
                buttons.append([Button.inline(f'❌ {api_preview}', f'remove_vehicle_api_{api["id"]}'.encode())])
            buttons.append([Button.inline('🔙 Back', b'tool_vehicle_info')])
            await event.edit('➖ REMOVE API', buttons=buttons)

    elif data.startswith(b'remove_vehicle_api_'):
        api_id = int(data.decode().split('_')[3])
        remove_tool_api('vehicle_info', api_id)
        await event.edit('✅ API removed!', buttons=[[Button.inline('🔙 Back', b'tool_vehicle_info')]])

    elif data == b'tool_vehicle_all_api':
        apis = get_tool_apis('vehicle_info')
        text = f'📋 ALL APIs ({len(apis)})\n\n' if apis else '📋 ALL APIs\n\nNo APIs configured yet.'
        for i, api in enumerate(apis, 1):
            text += f'{i}. {api["url"]}\n   Added: {api["added_date"][:10]}\n\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_vehicle_info')]])

    elif data == b'tool_vehicle_status':
        apis = get_tool_apis('vehicle_info')
        status = get_tool_status('vehicle_info')
        text = f'📊 VEHICLE INFO STATUS\n\nTool Status: {"✅ Active" if status else "❌ Inactive"}\nAPIs Configured: {len(apis)}\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_vehicle_info')]])

    # IFSC Info API Management
    elif data == b'tool_ifsc_add_api':
        tool_api_action[sender.id] = 'ifsc_info'
        placeholder = TOOL_CONFIG['ifsc_info']['placeholder']
        buttons = [[Button.inline('❌ Cancel', b'tool_ifsc_info')]]
        await event.edit(f'➕ ADD API for IFSC Info\n\nSend API URL with placeholder {placeholder}', buttons=buttons)

    elif data == b'tool_ifsc_remove_api':
        apis = get_tool_apis('ifsc_info')
        if not apis:
            await event.edit('❌ No APIs found!', buttons=[[Button.inline('🔙 Back', b'tool_ifsc_info')]])
        else:
            buttons = []
            for api in apis:
                api_preview = api['url'][:40] + '...' if len(api['url']) > 40 else api['url']
                buttons.append([Button.inline(f'❌ {api_preview}', f'remove_ifsc_api_{api["id"]}'.encode())])
            buttons.append([Button.inline('🔙 Back', b'tool_ifsc_info')])
            await event.edit('➖ REMOVE API', buttons=buttons)

    elif data.startswith(b'remove_ifsc_api_'):
        api_id = int(data.decode().split('_')[3])
        remove_tool_api('ifsc_info', api_id)
        await event.edit('✅ API removed!', buttons=[[Button.inline('🔙 Back', b'tool_ifsc_info')]])

    elif data == b'tool_ifsc_all_api':
        apis = get_tool_apis('ifsc_info')
        text = f'📋 ALL APIs ({len(apis)})\n\n' if apis else '📋 ALL APIs\n\nNo APIs configured yet.'
        for i, api in enumerate(apis, 1):
            text += f'{i}. {api["url"]}\n   Added: {api["added_date"][:10]}\n\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_ifsc_info')]])

    elif data == b'tool_ifsc_status':
        apis = get_tool_apis('ifsc_info')
        status = get_tool_status('ifsc_info')
        text = f'📊 IFSC INFO STATUS\n\nTool Status: {"✅ Active" if status else "❌ Inactive"}\nAPIs Configured: {len(apis)}\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_ifsc_info')]])

    # Pakistan Number API Management
    elif data == b'tool_pak_add_api':
        tool_api_action[sender.id] = 'pak_num'
        placeholder = TOOL_CONFIG['pak_num']['placeholder']
        buttons = [[Button.inline('❌ Cancel', b'tool_pak_num')]]
        await event.edit(f'➕ ADD API for Pak Number\n\nSend API URL with placeholder {placeholder}', buttons=buttons)

    elif data == b'tool_pak_remove_api':
        apis = get_tool_apis('pak_num')
        if not apis:
            await event.edit('❌ No APIs found!', buttons=[[Button.inline('🔙 Back', b'tool_pak_num')]])
        else:
            buttons = []
            for api in apis:
                api_preview = api['url'][:40] + '...' if len(api['url']) > 40 else api['url']
                buttons.append([Button.inline(f'❌ {api_preview}', f'remove_pak_api_{api["id"]}'.encode())])
            buttons.append([Button.inline('🔙 Back', b'tool_pak_num')])
            await event.edit('➖ REMOVE API', buttons=buttons)

    elif data.startswith(b'remove_pak_api_'):
        api_id = int(data.decode().split('_')[3])
        remove_tool_api('pak_num', api_id)
        await event.edit('✅ API removed!', buttons=[[Button.inline('🔙 Back', b'tool_pak_num')]])

    elif data == b'tool_pak_all_api':
        apis = get_tool_apis('pak_num')
        text = f'📋 ALL APIs ({len(apis)})\n\n' if apis else '📋 ALL APIs\n\nNo APIs configured yet.'
        for i, api in enumerate(apis, 1):
            text += f'{i}. {api["url"]}\n   Added: {api["added_date"][:10]}\n\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_pak_num')]])

    elif data == b'tool_pak_status':
        apis = get_tool_apis('pak_num')
        status = get_tool_status('pak_num')
        text = f'📊 PAK NUMBER STATUS\n\nTool Status: {"✅ Active" if status else "❌ Inactive"}\nAPIs Configured: {len(apis)}\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_pak_num')]])

    # Pincode API Management
    elif data == b'tool_pin_add_api':
        tool_api_action[sender.id] = 'pincode_info'
        placeholder = TOOL_CONFIG['pincode_info']['placeholder']
        buttons = [[Button.inline('❌ Cancel', b'tool_pincode_info')]]
        await event.edit(f'➕ ADD API for Pincode\n\nSend API URL with placeholder {placeholder}', buttons=buttons)

    elif data == b'tool_pin_remove_api':
        apis = get_tool_apis('pincode_info')
        if not apis:
            await event.edit('❌ No APIs found!', buttons=[[Button.inline('🔙 Back', b'tool_pincode_info')]])
        else:
            buttons = []
            for api in apis:
                api_preview = api['url'][:40] + '...' if len(api['url']) > 40 else api['url']
                buttons.append([Button.inline(f'❌ {api_preview}', f'remove_pin_api_{api["id"]}'.encode())])
            buttons.append([Button.inline('🔙 Back', b'tool_pincode_info')])
            await event.edit('➖ REMOVE API', buttons=buttons)

    elif data.startswith(b'remove_pin_api_'):
        api_id = int(data.decode().split('_')[3])
        remove_tool_api('pincode_info', api_id)
        await event.edit('✅ API removed!', buttons=[[Button.inline('🔙 Back', b'tool_pincode_info')]])

    elif data == b'tool_pin_all_api':
        apis = get_tool_apis('pincode_info')
        text = f'📋 ALL APIs ({len(apis)})\n\n' if apis else '📋 ALL APIs\n\nNo APIs configured yet.'
        for i, api in enumerate(apis, 1):
            text += f'{i}. {api["url"]}\n   Added: {api["added_date"][:10]}\n\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_pincode_info')]])

    elif data == b'tool_pin_status':
        apis = get_tool_apis('pincode_info')
        status = get_tool_status('pincode_info')
        text = f'📊 PINCODE STATUS\n\nTool Status: {"✅ Active" if status else "❌ Inactive"}\nAPIs Configured: {len(apis)}\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_pincode_info')]])

    # IMEI API Management
    elif data == b'tool_imei_add_api':
        tool_api_action[sender.id] = 'imei_info'
        placeholder = TOOL_CONFIG['imei_info']['placeholder']
        buttons = [[Button.inline('❌ Cancel', b'tool_imei_info')]]
        await event.edit(f'➕ ADD API for IMEI\n\nSend API URL with placeholder {placeholder}', buttons=buttons)

    elif data == b'tool_imei_remove_api':
        apis = get_tool_apis('imei_info')
        if not apis:
            await event.edit('❌ No APIs found!', buttons=[[Button.inline('🔙 Back', b'tool_imei_info')]])
        else:
            buttons = []
            for api in apis:
                api_preview = api['url'][:40] + '...' if len(api['url']) > 40 else api['url']
                buttons.append([Button.inline(f'❌ {api_preview}', f'remove_imei_api_{api["id"]}'.encode())])
            buttons.append([Button.inline('🔙 Back', b'tool_imei_info')])
            await event.edit('➖ REMOVE API', buttons=buttons)

    elif data.startswith(b'remove_imei_api_'):
        api_id = int(data.decode().split('_')[3])
        remove_tool_api('imei_info', api_id)
        await event.edit('✅ API removed!', buttons=[[Button.inline('🔙 Back', b'tool_imei_info')]])

    elif data == b'tool_imei_all_api':
        apis = get_tool_apis('imei_info')
        text = f'📋 ALL APIs ({len(apis)})\n\n' if apis else '📋 ALL APIs\n\nNo APIs configured yet.'
        for i, api in enumerate(apis, 1):
            text += f'{i}. {api["url"]}\n   Added: {api["added_date"][:10]}\n\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_imei_info')]])

    elif data == b'tool_imei_status':
        apis = get_tool_apis('imei_info')
        status = get_tool_status('imei_info')
        text = f'📊 IMEI STATUS\n\nTool Status: {"✅ Active" if status else "❌ Inactive"}\nAPIs Configured: {len(apis)}\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_imei_info')]])

    # IP Info API Management
    elif data == b'tool_ip_add_api':
        tool_api_action[sender.id] = 'ip_info'
        placeholder = TOOL_CONFIG['ip_info']['placeholder']
        buttons = [[Button.inline('❌ Cancel', b'tool_ip_info')]]
        await event.edit(f'➕ ADD API for IP Info\n\nSend API URL with placeholder {placeholder}', buttons=buttons)

    elif data == b'tool_ip_remove_api':
        apis = get_tool_apis('ip_info')
        if not apis:
            await event.edit('❌ No APIs found!', buttons=[[Button.inline('🔙 Back', b'tool_ip_info')]])
        else:
            buttons = []
            for api in apis:
                api_preview = api['url'][:40] + '...' if len(api['url']) > 40 else api['url']
                buttons.append([Button.inline(f'❌ {api_preview}', f'remove_ip_api_{api["id"]}'.encode())])
            buttons.append([Button.inline('🔙 Back', b'tool_ip_info')])
            await event.edit('➖ REMOVE API', buttons=buttons)

    elif data.startswith(b'remove_ip_api_'):
        api_id = int(data.decode().split('_')[3])
        remove_tool_api('ip_info', api_id)
        await event.edit('✅ API removed!', buttons=[[Button.inline('🔙 Back', b'tool_ip_info')]])

    elif data == b'tool_ip_all_api':
        apis = get_tool_apis('ip_info')
        text = f'📋 ALL APIs ({len(apis)})\n\n' if apis else '📋 ALL APIs\n\nNo APIs configured yet.'
        for i, api in enumerate(apis, 1):
            text += f'{i}. {api["url"]}\n   Added: {api["added_date"][:10]}\n\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_ip_info')]])

    elif data == b'tool_ip_status':
        apis = get_tool_apis('ip_info')
        status = get_tool_status('ip_info')
        text = f'📊 IP INFO STATUS\n\nTool Status: {"✅ Active" if status else "❌ Inactive"}\nAPIs Configured: {len(apis)}\n'
        await event.edit(text, buttons=[[Button.inline('🔙 Back', b'tool_ip_info')]])

    elif data == b'setting_groups':
        # Official Groups Filter: Only show official groups in lists/tools
        from database import get_official_groups
        official_groups = get_official_groups()
        if official_groups:
            groups = official_groups
        else:
            # Fallback to all groups if no official groups defined
            groups = get_all_groups()
        buttons = [
            [Button.inline('➕ Add', b'group_add'), Button.inline('➖ Remove', b'group_remove')],
            [Button.inline('📋 List', b'group_list_page_1'), Button.inline('👋 Welcome', b'group_welcome_text')],
            [Button.inline('⚙️ Settings', b'group_setting')],
            [Button.inline('🔙 Back', b'owner_settings')],
        ]
        group_text = f"GROUPS\n\nConnected: {len(groups)}\n\nWhat do you want to do?"
        await event.edit(group_text, buttons=buttons)

    elif data == b'group_setting':
        await event.edit('⚙️ Group Settings: Coming soon...', buttons=[[Button.inline('🔙 Back', b'setting_groups')]])

    elif data == b'check_subscription':
        access_check = await check_user_access(sender.id)
        if not access_check['allowed']:
            if access_check['reason'] == 'not_subscribed':
                msg = '❌ You still need to join these channels:\n\n'
                buttons = []
                for ch in access_check['channels']:
                    ch_username = ch['username']
                    
                    # Generate join URL based on channel type
                    if ch_username.startswith('https://t.me/'):
                        # Full URL already provided
                        join_url = ch_username
                        if '+' in ch_username or 'joinchat' in ch_username:
                            display_name = f"{ch['title']} (Private)"
                        else:
                            display_name = ch['title']
                    elif ch_username.startswith('+'):
                        # Private invite link: +abc123 -> https://t.me/+abc123
                        join_url = f"https://t.me/{ch_username}"
                        display_name = f"{ch['title']} (Private)"
                    elif ch_username.startswith('joinchat/'):
                        # Legacy format: joinchat/abc123 -> https://t.me/joinchat/abc123
                        join_url = f"https://t.me/{ch_username}"
                        display_name = f"{ch['title']} (Private)"
                    else:
                        # Public channel: username -> https://t.me/username
                        clean_username = ch_username.lstrip('@')
                        join_url = f"https://t.me/{clean_username}"
                        display_name = f"@{clean_username}"
                    
                    msg += f"📺 {display_name}\n"
                    buttons.append([Button.url(f"Join {ch['title']}", join_url)])
                
                buttons.append([Button.inline('✅ Check Again', b'check_subscription')])
                try:
                    await event.edit(msg, buttons=buttons)
                except Exception as e:
                    if 'MessageNotModified' in str(type(e).__name__) or 'not modified' in str(e).lower():
                        await safe_answer(event, '⏳ Please join the channels first, then try again!', alert=True)
                    else:
                        print(f"[LOG] ❌ Error in check_subscription: {e}")
            else:
                await safe_answer(event, '🚫 Access Denied!', alert=True)
        else:
            # User has joined all channels, show normal menu
            stats = get_stats()
            user_data = get_user(sender.id)
            buttons = [
                [Button.inline('🛠️ Tools', b'user_tools')],
                [Button.inline('👤 Profile', b'user_profile'), Button.inline('❓ Help', b'user_help')],
                [Button.inline('ℹ️ About', b'user_about')],
            ]
            custom_text = get_setting('user_start_text', get_default_user_text())
            user_text = format_text(custom_text, sender, stats, user_data)
            try:
                await event.edit(user_text, buttons=buttons)
            except:
                await safe_answer(event, '✅ Verified! Use /start to continue.', alert=True)

    elif data == b'owner_back':
        buttons = [
            [Button.inline('🛠️ Tools', b'owner_tools')],
            [Button.inline('👥 Users', b'owner_users'), Button.inline('✉️ Send Messages', b'owner_broadcast')],
            [Button.inline('📊 Status', b'owner_status'), Button.inline('⚙️ Settings', b'owner_settings')],
        ]
        stats = get_stats()
        custom_text = get_setting('owner_start_text', get_default_owner_text())
        owner_text = format_text(custom_text, sender, stats, None)
        await event.edit(owner_text, buttons=buttons)

    elif data == b'owner_users':
        buttons = [
            [Button.inline('🚫 Ban', b'user_ban'), Button.inline('✅ Unban', b'user_unban')],
            [Button.inline('ℹ️ Info', b'user_info')],
            [Button.inline('🔙 Back', b'owner_back')],
        ]
        await event.edit('👥 USERS PANEL\n\nChoose an action:', buttons=buttons)

    elif data == b'user_ban':
        user_action_type[sender.id] = 'ban'
        buttons = [[Button.inline('❌ Cancel', b'owner_users')]]
        await event.edit('🚫 BAN USER\n\nEnter user ID or username (@username):', buttons=buttons)

    elif data == b'user_unban':
        user_action_type[sender.id] = 'unban'
        buttons = [[Button.inline('❌ Cancel', b'owner_users')]]
        await event.edit('✅ UNBAN USER\n\nEnter user ID or username (@username):', buttons=buttons)

    elif data == b'user_info':
        user_action_type[sender.id] = 'info'
        buttons = [[Button.inline('❌ Cancel', b'owner_users')]]
        await event.edit('ℹ️ USER INFO\n\nEnter user ID or username (@username):', buttons=buttons)

    elif data == b'owner_broadcast':
        buttons = [
            [Button.inline('🤖 Bot Only', b'msg_bot_only'), Button.inline('👥 Group Only', b'msg_group_only')],
            [Button.inline('👤 Personally', b'msg_personally'), Button.inline('📢 Broadcast', b'msg_broadcast')],
            [Button.inline('📡 Ping', b'msg_ping')],
            [Button.inline('👈 Back', b'owner_back')]
        ]
        await event.edit('✉️ **SEND MESSAGES**\n\nChoose where you want to send the message:', buttons=buttons)

    elif data == b'owner_status':
        stats = get_stats()

        # Get current date and time
        current_date = datetime.now().strftime("%d-%m-%Y")
        current_time = datetime.now().strftime("%H:%M:%S")

        # Get active tools count
        active_tools = get_all_active_tools()
        tools_count = len(active_tools)

        # Get channels and groups count
        channels = get_all_channels()
        # Official Groups Filter: Only show official groups in lists/tools
        from database import get_official_groups
        official_groups = get_official_groups()
        if official_groups:
            groups = official_groups
        else:
            # Fallback to all groups if no official groups defined
            groups = get_all_groups()

        # Get backup info
        backup_channel = get_backup_channel()
        backup_interval = get_backup_interval()
        last_backup = get_last_backup_time()

        if last_backup:
            try:
                last_backup_dt = datetime.fromisoformat(last_backup)
                last_backup_str = last_backup_dt.strftime("%d-%m-%Y %H:%M:%S")
            except:
                last_backup_str = "Never"
        else:
            last_backup_str = "Never"

        # Build status text
        status_text = f"📊 **BOT STATUS DASHBOARD**\n"
        status_text += f"{'='*35}\n\n"

        status_text += f"👥 **Users Statistics:**\n"
        status_text += f"├ Total Users: {stats['total_users']}\n"
        status_text += f"├ Active Users: {stats['active_users']}\n"
        status_text += f"└ Banned Users: {stats['banned_users']}\n\n"

        status_text += f"💬 **Messages:**\n"
        status_text += f"└ Total Messages: {stats['total_messages']}\n\n"

        status_text += f"🛠️ **Tools:**\n"
        status_text += f"└ Active Tools: {tools_count}/9\n\n"

        status_text += f"📺 **Channels & Groups:**\n"
        status_text += f"├ Sub-Force Channels: {len(channels)}\n"
        status_text += f"└ Connected Groups: {len(groups)}\n\n"

        status_text += f"💾 **Backup Info:**\n"
        if backup_channel:
            status_text += f"├ Channel: @{backup_channel['username']}\n"
            status_text += f"├ Interval: {backup_interval} minutes\n"
            status_text += f"└ Last Backup: {last_backup_str}\n\n"
        else:
            status_text += f"└ No backup configured\n\n"

        status_text += f"⏰ **System Time:**\n"
        status_text += f"├ Date: {current_date}\n"
        status_text += f"└ Time: {current_time}\n\n"

        status_text += f"{'='*35}\n"
        status_text += f"✅ **Status:** Online & Running"

        buttons = [[Button.inline('🔄 Refresh', b'owner_status'), Button.inline('🔙 Back', b'owner_back')]]
        await event.edit(status_text, buttons=buttons)

    elif data == b'owner_tools':
        tools_map = [
            ('number_info', '📱 Number Info', b'use_number_info'),
            ('aadhar_info', '🆔 Aadhar Info', b'use_aadhar_info'),
            ('aadhar_family', '👨‍👩‍👧‍👦 Aadhar to Family', b'use_aadhar_family'),
            ('vehicle_info', '🚗 Vehicle Info', b'use_vehicle_info'),
            ('ifsc_info', '🏦 IFSC Info', b'use_ifsc_info'),
            ('pak_num', '🇵🇰 Pak Num Info', b'use_pak_num'),
            ('pincode_info', '📍 Pin Code Info', b'use_pincode_info'),
            ('imei_info', '📱 IMEI Info', b'use_imei_info'),
            ('ip_info', '🌐 IP Info', b'use_ip_info'),
        ]

        active_tools = []
        for tool_key, tool_name, callback in tools_map:
            if get_tool_status(tool_key):
                active_tools.append((tool_name, callback))

        buttons = []
        for i in range(0, len(active_tools), 2):
            if i + 1 < len(active_tools):
                buttons.append([Button.inline(active_tools[i][0], active_tools[i][1]), Button.inline(active_tools[i+1][0], active_tools[i+1][1])])
            else:
                buttons.append([Button.inline(active_tools[i][0], active_tools[i][1])])

        buttons.append([Button.inline('🔙 Back', b'owner_back')])
        await event.edit('🛠️ TOOLS\n\nSelect a tool to use:', buttons=buttons)

    elif data == b'user_tools':
        # Official Groups Filter: Only show official groups in lists/tools
        from database import get_official_groups
        official_groups = get_official_groups()
        if official_groups:
            groups = official_groups
        else:
            # Fallback to all groups if no official groups defined
            groups = get_all_groups()
        if not groups:
            msg = '❌ No groups connected to this bot yet.\n\nTools can only be used in connected groups.'
            buttons = [[Button.inline('🔙 Back', b'user_back')]]
            await event.edit(msg, buttons=buttons)
            return
        
        msg = '🛠️ **Connected Groups**\n\nYou can use tools in these groups. Click to join:'
        buttons = []
        for grp in groups:
            if grp.get('invite_link'):
                grp_url = grp['invite_link']
            elif grp['username'] and not str(grp['username']).startswith('-') and not str(grp['username']).isdigit():
                grp_url = f"https://t.me/{grp['username']}"
            else:
                gid = str(grp['group_id'])
                channel_id = gid[4:] if gid.startswith('-100') else gid.lstrip('-')
                grp_url = f"https://t.me/c/{channel_id}"
            buttons.append([Button.url(grp['title'], grp_url)])
        buttons.append([Button.inline('🔙 Back', b'user_back')])
        await event.edit(msg, buttons=buttons)

    elif data == b'user_profile':
        user = get_user(sender.id)
        if user:
            joined_date = user['joined'][:10] if user['joined'] else 'Unknown'
            joined_time = user['joined'][11:19] if len(user['joined']) > 11 else ''
            status_emoji = '✅' if not user['banned'] else '🚫'
            status_text = 'ACTIVE' if not user['banned'] else 'BANNED'
            
            profile_text = f"👤 **YOUR PROFILE**\n"
            profile_text += f"{'='*30}\n\n"
            profile_text += f"📝 **Name:** {user['first_name']}\n"
            profile_text += f"🔖 **Username:** @{user['username']}\n"
            profile_text += f"🆔 **User ID:** {user['user_id']}\n\n"
            profile_text += f"💬 **Messages Sent:** {user['messages']}\n"
            profile_text += f"📅 **Joined Date:** {joined_date}\n"
            if joined_time:
                profile_text += f"⏰ **Joined Time:** {joined_time}\n"
            profile_text += f"\n{status_emoji} **Status:** {status_text}\n"
            profile_text += f"📊 **Account Type:** {user['status'].upper()}\n\n"
            profile_text += f"{'='*30}\n"
            profile_text += f"✨ Thank you for using this bot!"
        else:
            profile_text = "❌ Profile not found!\n\nPlease use /start to register."
        await event.edit(profile_text, buttons=[[Button.inline('🔙 Back', b'user_back')]])

    elif data == b'user_help':
        current_help = get_setting('user_help_text', '❓ **HELP DESK**\n\n🤖 **Bot Commands:**\n/start - Start the bot\n/hello - Get a greeting\n/time - Get current time\n\n🛠️ **Available Tools:**\n/num - Phone number lookup\n/adhar - Aadhar info\n/family - Aadhar family lookup\n/vhe - Vehicle information\n/ifsc - IFSC code details\n/pak - Pakistan number info\n/pin - PIN code lookup\n/imei - IMEI information\n/ip - IP address details\n\n📌 **Usage:**\nSelect a tool from the menu or use commands directly.\n\n💡 **Tip:**\nAll tools provide instant results in JSON format.')
        user_data = get_user(sender.id)
        formatted_help = format_text(current_help, sender, get_stats(), user_data)
        await event.edit(formatted_help, buttons=[[Button.inline('🔙 Back', b'user_back')]])

    elif data == b'user_about':
        # Use customizable about text from settings
        current_about = get_setting('user_about_text', 'ℹ️ **ABOUT BOT**\n\n🤖 **Multi-Tool Information Bot**\n\n📊 **Version:** 2.0\n🐍 **Framework:** Telethon\n💾 **Database:** SQLite\n🌐 **Web Dashboard:** Flask\n\n👥 **Total Users:** {total_users}\n✅ **Active Users:** {active_users}\n\n📅 **Date:** {date}\n⏰ **Time:** {time}\n\n⚡ **Features:**\n• 9 Information Tools\n• Group Management\n• Broadcasting System\n• Web Dashboard\n• Auto Backup\n\n💡 **Powered by Telethon MTProto**')
        
        user_data = get_user(sender.id)
        stats = get_stats()
        
        # Format about text with placeholders
        formatted_about = format_text(current_about, sender, stats, user_data)
        
        # Add powered by link at the end if not already in custom text
        if 'KissuHQ' not in formatted_about and 'Kissu' not in formatted_about:
            formatted_about += f"\n\n**💡 Powered by [༄ᶦᶰᵈ᭄ℓєgєи∂✧kìຮຮu࿐™](t.me/KissuHQ)**"
        
        await event.edit(formatted_about, buttons=[[Button.inline('🔙 Back', b'user_back')]])

    elif data == b'user_back':
        # Create user panel layout as requested:
        # Row 1: Add me to group (URL button)
        # Row 2: Profile, Groups (Callback buttons)
        # Row 3: Help, About (Callback buttons)
        bot_user = await client.get_me()
        add_to_group_url = f"https://t.me/{bot_user.username}?startgroup=true"
        
        buttons = [
            [Button.url('➕ Add me to group', add_to_group_url)],
            [Button.inline('👤 Profile', b'user_profile'), Button.inline('👥 Groups', b'user_groups')],
            [Button.inline('❓ Help', b'user_help'), Button.inline('ℹ️ About', b'user_about')],
        ]
        stats = get_stats()
        user_data = get_user(sender.id)
        custom_text = get_setting('user_start_text', get_default_user_text())
        user_text = format_text(custom_text, sender, stats, user_data)
        await event.edit(user_text, buttons=buttons)

    elif data == b'user_groups':
        # Under development message with back button
        msg = "🚧 **GROUPS FEATURE**\n\nThis feature is currently under development. Please check back later!"
        buttons = [[Button.inline('👈 Back', b'user_back')]]
        await event.edit(msg, buttons=buttons)

    elif data == b'msg_bot_only':
        broadcast_temp[sender.id] = 'bot'
        broadcast_start_times[sender.id] = datetime.now()
        await event.edit('🤖 **BOT ONLY BROADCAST**\n\nSend the message (Text/Photo/Video/File) you want to send to all bot users:\n\n⏳ **Note:** You have 60 seconds to send the message.', buttons=[[Button.inline('❌ Cancel', b'owner_broadcast')]])

    elif data == b'msg_group_only':
        broadcast_temp[sender.id] = 'group'
        broadcast_start_times[sender.id] = datetime.now()
        await event.edit('👥 **GROUP ONLY BROADCAST**\n\nSend the message (Text/Photo/Video/File) you want to send to all connected groups:\n\n⏳ **Note:** You have 60 seconds to send the message.', buttons=[[Button.inline('❌ Cancel', b'owner_broadcast')]])

    elif data == b'msg_broadcast':
        broadcast_temp[sender.id] = 'all'
        broadcast_start_times[sender.id] = datetime.now()
        await event.edit('📢 **FULL BROADCAST**\n\nSend the message (Text/Photo/Video/File) you want to send to all users and groups:\n\n⏳ **Note:** You have 60 seconds to send the message.', buttons=[[Button.inline('❌ Cancel', b'owner_broadcast')]])

    elif data == b'msg_personally':
        user_action_type[sender.id] = 'personal_msg_user'
        # No timeout here yet, timeout starts after user is found
        await event.edit('👤 **PERSONAL MESSAGE**\n\nEnter User ID or Username of the target user:', buttons=[[Button.inline('❌ Cancel', b'owner_broadcast')]])

    elif data == b'msg_ping':
        await event.answer('📡 Starting Ping...', alert=False)
        asyncio.create_task(run_ping_broadcast(sender.id))

    elif data == b'broadcast_detail':
        stats = broadcast_stats.get(sender.id)
        if stats:
            # Create the detail text file content
            file_content = "📋 BROADCAST REPORT\n"
            file_content += f"{'='*50}\n\n"
            file_content += f"✅ SUCCESSFULLY SENT: {stats['sent_count']}\n"
            file_content += f"{'-'*50}\n"

            if stats['sent']:
                for user_info in stats['sent']:
                    file_content += f"{user_info}\n"
            else:
                file_content += "No users\n"

            file_content += f"\n\n❌ FAILED TO SEND: {stats['failed_count']}\n"
            file_content += f"{'-'*50}\n"

            if stats['failed']:
                for user_info in stats['failed']:
                    file_content += f"{user_info}\n"
            else:
                file_content += "No failures\n"

            file_content += f"\n\n{'='*50}\n"
            file_content += f"Total Users: {stats['sent_count'] + stats['failed_count']}\n"

            # Write to file
            filename = f"broadcast_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(file_content)

            # Send file
            try:
                await client.send_file(sender.id, filename)
                await safe_answer(event, "📄 Report sent!", alert=False)
            except Exception as e:
                await safe_answer(event, f"Error sending file: {str(e)}", alert=True)
                print(f"[LOG] ❌ Error sending broadcast report: {e}")

@client.on(events.NewMessage(incoming=True))
async def message_handler(event):
    sender = await event.get_sender()
    if not sender:
        return

    # Handle database file restore (only for owner)
    if sender.id == owner_id and event.file and event.file.name and event.file.name.endswith('.db'):
        try:
            db_file = get_db_file()

            # Download the new database file
            temp_file = "temp_restore.db"
            await event.download_media(file=temp_file)

            # Delete old database
            if os.path.exists(db_file):
                os.remove(db_file)
                print(f"[LOG] 🗑️ Old database deleted")

            # Replace with new database
            os.rename(temp_file, db_file)
            print(f"[LOG] ✅ Database restored from file")

            await event.respond('✅ Database restored successfully!\n\n🔄 Bot restarting...')

            # Restart bot to reload database
            import sys
            os.execv(sys.executable, ['python'] + sys.argv)

        except Exception as e:
            await event.respond(f'❌ Database restore failed: {str(e)}')
            print(f"[LOG] ❌ Database restore error: {e}")

        raise events.StopPropagation

    # Handle official group link input
    if sender.id in start_text_temp and start_text_temp[sender.id] == 'official_link':
        new_link = event.text.strip()
        if not new_link.startswith('https://t.me/'):
            await event.respond("❌ Invalid link! Must start with https://t.me/")
            return
        set_setting('official_group_link', new_link)
        del start_text_temp[sender.id]
        await event.respond(f"✅ Official Group link updated to:\n{new_link}", buttons=[[Button.inline('🔙 Back', b'official_group_setting')]])
        raise events.StopPropagation

    # Handle bad words add/remove (text or file)
    if sender.id in bad_words_action_temp:
        action = bad_words_action_temp[sender.id]
        words_text = ""
        
        # Check if it's a file
        if event.file and event.file.name and event.file.name.endswith('.txt'):
            try:
                temp_file = "temp_bad_words.txt"
                await event.download_media(file=temp_file)
                with open(temp_file, 'r', encoding='utf-8') as f:
                    words_text = f.read()
                os.remove(temp_file)
            except Exception as e:
                await event.respond(f'❌ Error reading file: {str(e)}', buttons=[[Button.inline('🔙 Back', b'setting_bad_words')]])
                raise events.StopPropagation
        elif event.text:
            words_text = event.text.strip()
        
        if words_text:
            words = parse_bad_words_input(words_text)
            if words:
                if action == 'add':
                    added = add_bad_words(words)
                    bad_words_action_temp[sender.id] = None
                    if added:
                        await event.respond(f'✅ Added {len(added)} new words!\n\n📝 Words: {", ".join(added[:10])}{"..." if len(added) > 10 else ""}', buttons=[[Button.inline('🔙 Back', b'setting_bad_words')]])
                    else:
                        await event.respond('⚠️ All words already exist!', buttons=[[Button.inline('🔙 Back', b'setting_bad_words')]])
                elif action == 'remove':
                    removed = remove_bad_words(words)
                    bad_words_action_temp[sender.id] = None
                    if removed:
                        await event.respond(f'✅ Removed {len(removed)} words!\n\n📝 Words: {", ".join(removed[:10])}{"..." if len(removed) > 10 else ""}', buttons=[[Button.inline('🔙 Back', b'setting_bad_words')]])
                    else:
                        await event.respond('⚠️ No matching words found to remove!', buttons=[[Button.inline('🔙 Back', b'setting_bad_words')]])
            else:
                await event.respond('❌ No valid words found!', buttons=[[Button.inline('🔙 Back', b'setting_bad_words')]])
        raise events.StopPropagation

    # Handle API field mapping input (Step 2 of API add)
    if sender.id in api_field_mapping_temp:
        mapping_info = api_field_mapping_temp[sender.id]
        api_id = mapping_info['api_id']
        tool_name = mapping_info['tool_name']
        fields_text = event.text.strip()
        
        # Parse fields (comma or newline separated)
        if fields_text.lower() in ['skip', 'all', 'full', 'pura']:
            # User wants full JSON response
            update_api_response_fields(api_id, None)
            del api_field_mapping_temp[sender.id]
            back_btn = get_tool_back_button(tool_name)
            await event.respond('✅ API added!\n\n📋 Response: Full JSON (all fields)', buttons=[[Button.inline('🔙 Back', back_btn)]])
        else:
            # Parse field names
            fields = [f.strip() for f in re.split(r'[,\n]+', fields_text) if f.strip()]
            if fields:
                fields_json = json.dumps(fields)
                update_api_response_fields(api_id, fields_json)
                del api_field_mapping_temp[sender.id]
                back_btn = get_tool_back_button(tool_name)
                await event.respond(f'✅ API added!\n\n📋 Response fields: {", ".join(fields)}', buttons=[[Button.inline('🔙 Back', back_btn)]])
            else:
                await event.respond('❌ Invalid fields!\n\nSend field names separated by comma or type "skip" for full JSON.')
        raise events.StopPropagation

    # Handle API URL input (Step 1 of API add)
    if sender.id in tool_api_action:
        tool_name = tool_api_action[sender.id]
        api_url = event.text.strip()

        # Validate that URL contains the placeholder
        placeholder = TOOL_CONFIG[tool_name]['placeholder']
        if placeholder not in api_url:
            await event.respond(f'❌ Invalid API URL!\n\nURL must contain placeholder: {placeholder}', buttons=[[Button.inline('🔙 Back', f'tool_{tool_name.split("_")[0]}_info'.encode())]])
            raise events.StopPropagation

        # Add API to database and get ID
        api_id = add_tool_api(tool_name, api_url)
        del tool_api_action[sender.id]
        
        # Store for field mapping step
        api_field_mapping_temp[sender.id] = {
            'api_id': api_id,
            'tool_name': tool_name
        }

        # Ask for field mapping
        field_example = '''📝 **STEP 2: Select Response Fields**

API URL saved! Now choose which fields to show.

**Available Fields in API Response:**
name, mobile, address, father_name, alt_mobile, circle, id_number, email, id, source, etc.

**How to send:**
✅ Simple format:
   `name, mobile, address`

✅ Nested format:
   `data.0.name, data.0.mobile`

**Examples:**
   `name, mobile, address, father_name`
   `data.0.name, data.0.mobile, data.0.id`

Or type **"skip"** to show full response.'''
        
        back_btn = get_tool_back_button(tool_name)
        await event.respond(field_example, buttons=[[Button.inline('⏭️ Skip (Full JSON)', f'skip_field_mapping_{api_id}'.encode())], [Button.inline('❌ Cancel', back_btn)]])
        raise events.StopPropagation

    if sender.id in tool_session:
        tool_key = tool_session[sender.id]
        validator = VALIDATORS.get(tool_key)
        if validator:
            validated = validator(event.text)
            if validated:
                back_btn = b'owner_tools' if sender.id == owner_id else b'user_tools'
                processing_msg = await event.respond('⏳ Processing...')

                data, error = await call_tool_api(tool_key, validated)

                if data:
                    response = format_json_as_text(data, query=validated)
                    if len(response) > 4000:
                        response = response[:3997] + "..."
                    await processing_msg.edit(response)
                    asyncio.create_task(send_back_button_delayed(client, sender.id, processing_msg.id, back_btn, 2))
                else:
                    msg = f"🔍 **Your Query**: `{validated}`\n❌ Error: {error}\n\n━━━━━━━━━━━━━━━━━━━━━\nOwner: @Cyber_as\nDeveloped by: @KissuHQ"
                    await processing_msg.edit(msg, buttons=[[Button.inline('👈 Back', back_btn)]])

                del tool_session[sender.id]
            else:
                back_btn = b'owner_tools' if sender.id == owner_id else b'user_tools'
                await event.respond(f"❌ Invalid input!\n\n{TOOL_CONFIG[tool_key]['prompt']}", buttons=[[Button.inline('❌ Cancel', back_btn)]])
        raise events.StopPropagation

    if backup_channel_temp.get(sender.id) == 'interval':
        try:
            interval = int(event.text.strip())
            if interval <= 0:
                await event.respond('❌ Invalid interval! Must be a positive number.', buttons=[[Button.inline('🔙 Back', b'setting_backup')]])
            else:
                set_backup_interval(interval)
                backup_channel_temp[sender.id] = None
                backup_channel = get_backup_channel()
                buttons = [
                    [Button.inline('🔄 Change Channel', b'backup_change_channel')],
                    [Button.inline('⏰ Interval Time', b'backup_interval'), Button.inline('💾 Backup Now', b'backup_now')],
                    [Button.inline('🔙 Back', b'owner_settings')],
                ]
                backup_text = f"💾 BACKUP SETTINGS\n\n📺 Channel: {backup_channel['title']}\n@{backup_channel['username']}\n\n⏰ Interval: {interval} minutes\n\n✅ Interval updated successfully!"
                await event.respond(backup_text, buttons=buttons)
        except ValueError:
            await event.respond('❌ Invalid number! Send interval in minutes.', buttons=[[Button.inline('🔙 Back', b'setting_backup')]])
        raise events.StopPropagation

    if backup_channel_temp.get(sender.id) == 'restore':
        if event.file and event.file.name and event.file.name.endswith('.db'):
            try:
                db_file = get_db_file()

                # Download the new database file
                temp_file = "temp_restore.db"
                await event.download_media(file=temp_file)

                # Delete old database
                if os.path.exists(db_file):
                    os.remove(db_file)
                    print(f"[LOG] 🗑️ Old database deleted")

                # Replace with new database
                os.rename(temp_file, db_file)
                print(f"[LOG] ✅ Database restored from backup")

                backup_channel_temp[sender.id] = None

                await event.respond('✅ Database restored successfully!\n\n🔄 Bot restarting...')

                # Restart bot to reload database
                import sys
                os.execv(sys.executable, ['python'] + sys.argv)

            except Exception as e:
                await event.respond(f'❌ Database restore failed: {str(e)}')
                print(f"[LOG] ❌ Database restore error: {e}")
                backup_channel_temp[sender.id] = None
        else:
            await event.respond('❌ Please send a valid .db database file!', buttons=[[Button.inline('🔙 Back', b'setting_backup')]])
        raise events.StopPropagation

    if sender.id == owner_id and backup_channel_temp.get(sender.id) == 'add':
        ch_id = None
        ch_name = None
        ch_title = None

        if event.forward and event.forward.chat:
            try:
                channel_entity = await client.get_entity(event.forward.chat)
                ch_id = channel_entity.id
                ch_name = channel_entity.username or str(channel_entity.id)
                ch_title = channel_entity.title
            except Exception as e:
                await event.respond(f'❌ Error extracting channel: {str(e)}')
                return
        elif event.text:
            ch_input = event.text.strip()
            if ch_input.lstrip('-').isdigit():
                ch_id = int(ch_input)
                ch_name = ch_input
                ch_title = ch_input
            elif ch_input.startswith('@'):
                try:
                    channel_entity = await client.get_entity(ch_input)
                    ch_id = channel_entity.id
                    ch_name = channel_entity.username or str(channel_entity.id)
                    ch_title = channel_entity.title
                except Exception as e:
                    await event.respond(f'❌ Error finding channel: {str(e)}')
                    return
            else:
                await event.respond('❌ Invalid format. Use: ID number, @username, or forward message.', buttons=[[Button.inline('🔙 Back', b'setting_backup')]])
                raise events.StopPropagation

        if not ch_id or not ch_name:
            await event.respond('❌ Send one of: ID, @username, or forward a message.', buttons=[[Button.inline('🔙 Back', b'setting_backup')]])
            raise events.StopPropagation

        set_backup_channel(ch_id, ch_name, ch_title)
        backup_channel_temp[sender.id] = None
        interval = get_backup_interval()
        buttons = [
            [Button.inline('🔄 Change Channel', b'backup_change_channel')],
            [Button.inline('⏰ Interval Time', b'backup_interval'), Button.inline('💾 Backup Now', b'backup_now')],
            [Button.inline('🔙 Back', b'owner_settings')],
        ]
        backup_text = f"💾 BACKUP SETTINGS\n\n📺 Channel: {ch_title}\n@{ch_name}\n\n⏰ Interval: {interval} minutes\n\n✅ Backup channel set successfully!"
        await event.respond(backup_text, buttons=buttons)
        raise events.StopPropagation

    if channel_action_temp.get(sender.id) == 'add':
        ch_id = None
        ch_name = None
        ch_title = None
        ch_invite_link = None

        if event.forward and event.forward.chat:
            try:
                channel_entity = await client.get_entity(event.forward.chat)
                ch_id = channel_entity.id
                ch_title = channel_entity.title or 'Private Channel'
                
                # Try to get username, if not available it's a private channel
                if hasattr(channel_entity, 'username') and channel_entity.username:
                    ch_name = channel_entity.username
                else:
                    # Private channel - get invite link
                    try:
                        from telethon.tl.functions.messages import ExportChatInviteRequest
                        invite = await client(ExportChatInviteRequest(channel_entity))
                        ch_invite_link = invite.link
                        ch_name = ch_invite_link  # Store full link as username
                        print(f"[LOG] 📎 Private channel invite link: {ch_invite_link}")
                    except Exception as invite_err:
                        await event.respond(f'❌ Could not get invite link: {str(invite_err)}\n\nMake sure bot is admin in the channel!')
                        return
                        
            except Exception as e:
                await event.respond(f'❌ Error extracting channel: {str(e)}')
                return
                
        elif event.text:
            ch_input = event.text.strip()
            
            # Handle full invite link (https://t.me/+abc or https://t.me/joinchat/abc)
            if ch_input.startswith('https://t.me/+') or ch_input.startswith('https://t.me/joinchat/'):
                ch_name = ch_input
                ch_invite_link = ch_input
                ch_title = 'Private Channel'
                try:
                    # Try to get channel entity to get ID and title
                    channel_entity = await client.get_entity(ch_input)
                    ch_id = channel_entity.id
                    ch_title = channel_entity.title or 'Private Channel'
                except Exception as e:
                    # Can't get entity, use hash as ID
                    ch_id = abs(hash(ch_input)) % 1000000000
                    print(f"[LOG] ⚠️ Could not get channel entity from link: {e}")
                    
            # Handle numeric channel ID
            elif ch_input.lstrip('-').isdigit():
                try:
                    ch_id = int(ch_input)
                    channel_entity = await client.get_entity(ch_id)
                    ch_title = channel_entity.title or 'Channel'
                    
                    if hasattr(channel_entity, 'username') and channel_entity.username:
                        ch_name = channel_entity.username
                    else:
                        # Private channel - get invite link
                        try:
                            from telethon.tl.functions.messages import ExportChatInviteRequest
                            invite = await client(ExportChatInviteRequest(channel_entity))
                            ch_invite_link = invite.link
                            ch_name = ch_invite_link
                            print(f"[LOG] 📎 Private channel invite link: {ch_invite_link}")
                        except Exception as invite_err:
                            await event.respond(f'❌ Could not get invite link: {str(invite_err)}\n\nMake sure bot is admin!')
                            return
                except Exception as e:
                    await event.respond(f'❌ Error getting channel by ID: {str(e)}\n\nMake sure bot is admin in the channel!')
                    return
                    
            # Handle @username
            elif ch_input.startswith('@'):
                try:
                    channel_entity = await client.get_entity(ch_input)
                    ch_id = channel_entity.id
                    ch_name = channel_entity.username
                    ch_title = channel_entity.title or ch_input
                except Exception as e:
                    await event.respond(f'❌ Error getting channel: {str(e)}\n\nMake sure bot is admin in the channel!')
                    return
            else:
                await event.respond('❌ Invalid format. Use:\n- Channel ID (number)\n- @username\n- https://t.me/+xxx invite link\n- Forward message from channel')
                raise events.StopPropagation

        if not ch_id or not ch_name:
            await event.respond('❌ Send one of: ID, @username, invite link, or forward a message.')
            raise events.StopPropagation

        if channel_exists(ch_name):
            buttons = [[Button.inline('🔙 Back', b'setting_sub_force')]]
            await event.respond(f'⚠️ Channel already added!', buttons=buttons)
        else:
            # Store the invite link if available
            final_ch_name = ch_name
            if ch_invite_link:
                final_ch_name = ch_invite_link
            
            add_channel(final_ch_name, ch_title, ch_id)
            channel_action_temp[sender.id] = None
            buttons = [[Button.inline('🔙 Back', b'setting_sub_force')]]
            
            if ch_invite_link:
                await event.respond(f'✅ Private Channel added!\n\n📺 {ch_title}\nID: {ch_id}\n🔗 Link: {ch_invite_link}', buttons=buttons)
            else:
                await event.respond(f'✅ Channel added!\n\n📺 {ch_title}\nID: {ch_id}\n@{ch_name}', buttons=buttons)
        raise events.StopPropagation

    if group_action_temp.get(sender.id) == 'add':
        grp_id = None
        grp_name = None
        grp_title = None

        if event.forward and event.forward.chat:
            try:
                group_entity = await client.get_entity(event.forward.chat)
                grp_id = group_entity.id
                grp_name = group_entity.username or str(group_entity.id)
                grp_title = group_entity.title
            except Exception as e:
                await event.respond(f'Error extracting group: {str(e)}')
                return
        elif event.text:
            grp_input = event.text.strip()
            if grp_input.isdigit():
                grp_id = int(grp_input)
                grp_name = grp_input
                grp_title = grp_input
            elif grp_input.startswith('@'):
                grp_name = grp_input[1:]
                grp_id = hash(grp_name) % 1000000
                grp_title = grp_input[1:]
            else:
                await event.respond('Invalid format. Use: ID number, @username, or forward message.')
                raise events.StopPropagation

        if not grp_id or not grp_name:
            await event.respond('Send one of: ID, @username, or forward a message.')
            raise events.StopPropagation

        if group_exists(grp_id):
            buttons = [[Button.inline('Back', b'owner_groups')]]
            await event.respond(f'Group {grp_name} already added!', buttons=buttons)
        else:
            # Try to generate invite link for the group
            grp_invite_link = None
            try:
                if grp_name and not grp_name.lstrip('-').isdigit():
                    # Public group with username
                    grp_invite_link = f"https://t.me/{grp_name.lstrip('@')}"
                else:
                    # Private group - try to create invite link
                    try:
                        from telethon.tl.functions.messages import ExportChatInviteRequest
                        group_entity = await client.get_entity(grp_id)
                        invite = await client(ExportChatInviteRequest(group_entity))
                        grp_invite_link = invite.link
                        print(f"[LOG] ✅ Generated invite link for group {grp_name}: {grp_invite_link}")
                    except Exception as invite_err:
                        print(f"[LOG] ⚠️ Could not generate invite link for group {grp_name}: {invite_err}")
            except:
                pass
            
            add_group(grp_id, grp_name, grp_title, grp_invite_link)
            group_action_temp[sender.id] = None
            buttons = [[Button.inline('Back', b'owner_groups')]]
            if grp_invite_link:
                await event.respond(f'✅ Group added successfully!\n\n👥 {grp_title}\nID: {grp_id}\n🔗 Link: {grp_invite_link}', buttons=buttons)
            else:
                await event.respond(f'✅ Group added successfully!\n\n👥 {grp_title}\nID: {grp_id}\n@{grp_name}', buttons=buttons)
        raise events.StopPropagation

    # Handle broadcast/personal message content
    if broadcast_temp.get(sender.id):
        mode = broadcast_temp[sender.id]
        
        # Check if user took too long to send the message (60s timeout)
        start_time = broadcast_start_times.get(sender.id)
        if start_time:
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > 60:
                broadcast_temp[sender.id] = False
                if sender.id in broadcast_start_times:
                    del broadcast_start_times[sender.id]
                await event.respond("⏳ **Time Out!** 60 seconds limit reached. Aapne 1 minute ke andar message nahi bheja. Please dobara koshish karein.")
                raise events.StopPropagation
        
        broadcast_temp[sender.id] = False
        if sender.id in broadcast_start_times:
            del broadcast_start_times[sender.id]
            
        target_user_id = None
        
        if mode == 'personally':
            target_user_id = user_action_temp.get(sender.id)
            user_action_temp[sender.id] = None
        
        asyncio.create_task(smart_broadcast_logic(sender.id, event, mode, target_user_id))
        raise events.StopPropagation

    # Handle personal message user lookup
    if user_action_type.get(sender.id) == 'personal_msg_user':
        user_input = event.text.strip()
        target_user = None
        if user_input.isdigit():
            target_user = get_user(int(user_input))
        elif user_input.startswith('@'):
            username = user_input[1:].lower()
            all_users = get_all_users()
            for u in all_users.values():
                if u.get('username', '').lower() == username:
                    target_user = u
                    break
        
        if not target_user:
            await event.respond('❌ User not found in database!', buttons=[[Button.inline('🔙 Back', b'owner_broadcast')]])
        else:
            user_action_temp[sender.id] = target_user['user_id']
            broadcast_temp[sender.id] = 'personally'
            broadcast_start_times[sender.id] = datetime.now()
            details = f"👤 **Target User Found**\n\nName: {target_user['first_name']}\nID: {target_user['user_id']}\nUsername: @{target_user.get('username', 'N/A')}\n\nNow send the message (Text/Photo/Video/File) to send to this user:\n\n⏳ **Note:** You have 60 seconds to send the message."
            await event.respond(details, buttons=[[Button.inline('❌ Cancel', b'owner_broadcast')]])
        
        user_action_type[sender.id] = None
        raise events.StopPropagation

    # Original user action handler
    if user_action_type.get(sender.id):
        action = user_action_type[sender.id]
        user_input = event.text.strip()
        target_user = None

        if user_input.isdigit():
            target_user = get_user(int(user_input))
        elif user_input.startswith('@'):
            username = user_input[1:]
            all_users = get_all_users()
            for uid_str, user in all_users.items():
                if user.get('username') == username:
                    target_user = user
                    break
        else:
            await event.respond('Invalid format. Use: user ID or @username', buttons=[[Button.inline('🔙 Back', b'owner_users')]])
            raise events.StopPropagation

        if not target_user:
            await event.respond('❌ User not found!', buttons=[[Button.inline('🔙 Back', b'owner_users')]])
            user_action_type[sender.id] = None
            raise events.StopPropagation

        if action == 'ban':
            if target_user.get('banned'):
                await event.respond('❌ This user is already banned!', buttons=[[Button.inline('🔙 Back', b'owner_users')]])
            else:
                ban_user(target_user['user_id'])
                user_action_type[sender.id] = None
                result_text = f"✅ User Banned!\n\nUser ID: {target_user['user_id']}\nUsername: @{target_user['username']}\nName: {target_user['first_name']}"
                buttons = [[Button.inline('🔙 Back', b'owner_users')]]
                await event.respond(result_text, buttons=buttons)
                try:
                    await client.send_message(target_user['user_id'], '🚫 You have been BANNED from this bot. You cannot use any commands or features.')
                except Exception:
                    pass

        elif action == 'unban':
            if not target_user.get('banned'):
                await event.respond('❌ This user is not banned!', buttons=[[Button.inline('🔙 Back', b'owner_users')]])
            else:
                unban_user(target_user['user_id'])
                user_action_type[sender.id] = None
                result_text = f"✅ User Unbanned!\n\nUser ID: {target_user['user_id']}\nUsername: @{target_user['username']}\nName: {target_user['first_name']}"
                buttons = [[Button.inline('🔙 Back', b'owner_users')]]
                await event.respond(result_text, buttons=buttons)
                try:
                    await client.send_message(target_user['user_id'], '✅ You have been UNBANNED! You can now use the bot again.')
                except Exception:
                    pass

        elif action == 'info':
            user_action_type[sender.id] = None
            info_text = f"ℹ️ USER DETAILS\n\n"
            info_text += f"👤 ID: {target_user['user_id']}\n"
            info_text += f"👤 Username: @{target_user['username']}\n"
            info_text += f"📝 Name: {target_user['first_name']}\n"
            info_text += f"💬 Messages: {target_user['messages']}\n"
            info_text += f"📅 Joined: {target_user['joined'][:10]}\n"
            info_text += f"⏰ Full Join Date: {target_user['joined']}\n"
            info_text += f"🔄 Status: {'🚫 BANNED' if target_user['banned'] else '✅ ACTIVE'}\n"
            if target_user['banned'] and target_user.get('ban_reason'):
                info_text += f"📋 Ban Reason: {target_user['ban_reason']}\n"
                if target_user.get('ban_date'):
                    info_text += f"📅 Ban Date: {target_user['ban_date'][:10]}\n"
            info_text += f"📊 User Status: {target_user['status']}\n"
            buttons = [[Button.inline('🔙 Back', b'owner_users')]]
            await event.respond(info_text, buttons=buttons)

        raise events.StopPropagation

    if start_text_temp.get(sender.id):
        text_type = start_text_temp[sender.id]
        message = event.text

        if text_type == 'owner':
            set_setting('owner_start_text', message)
            start_text_temp[sender.id] = None
            preview = format_text(message, sender, get_stats())
            buttons = [[Button.inline('Back', b'start_text_owner')]]
            await event.respond(f"Owner start text saved!\n\nPreview:\n{preview}", buttons=buttons)
        elif text_type == 'user':
            set_setting('user_start_text', message)
            start_text_temp[sender.id] = None
            preview = format_text(message, sender, get_stats())
            buttons = [[Button.inline('Back', b'start_text_user')]]
            await event.respond(f"User start text saved!\n\nPreview:\n{preview}", buttons=buttons)
        elif text_type == 'group_welcome':
            set_setting('group_welcome_text', message)
            start_text_temp[sender.id] = None
            preview = format_text(message, sender, get_stats())
            buttons = [[Button.inline('Back', b'group_welcome_text')]]
            await event.respond(f"Group welcome text saved!\n\nPreview:\n{preview}", buttons=buttons)
        elif text_type == 'help_desk':
            set_setting('user_help_text', message)
            start_text_temp[sender.id] = None
            user_data = get_user(sender.id)
            preview = format_text(message, sender, get_stats(), user_data)
            buttons = [[Button.inline('🔙 Back', b'setting_help_desk')]]
            await event.respond(f"✅ **Help text saved!**\n\n**Preview:**\n{preview}", buttons=buttons)
        elif text_type == 'about_desk':
            set_setting('user_about_text', message)
            start_text_temp[sender.id] = None
            user_data = get_user(sender.id)
            preview = format_text(message, sender, get_stats(), user_data)
            buttons = [[Button.inline('🔙 Back', b'setting_about_desk')]]
            await event.respond(f"✅ **About text saved!**\n\n**Preview:**\n{preview}", buttons=buttons)

        raise events.StopPropagation

    if broadcast_temp.get(sender.id):
        message = event.text
        all_users = get_all_users()
        stats = get_stats()

        print(f"[LOG] 📢 Starting broadcast to {len(all_users)} users")
        sent_count = 0
        failed_count = 0
        sent_users = []
        failed_users = []

        for user_id_str, user in all_users.items():
            if user.get('banned'):
                continue

            try:
                # Create a temporary user object for formatting
                class UserObj:
                    def __init__(self, user_data):
                        self.first_name = user_data.get('first_name', 'User')
                        self.username = user_data.get('username', 'user')
                        self.id = user_data.get('user_id', 0)

                user_obj = UserObj(user)
                # Format message with placeholders for each user
                formatted_message = format_text(message, user_obj, stats, user)
                await client.send_message(int(user_id_str), formatted_message)
                sent_count += 1
                sent_users.append(f"ID: {user['user_id']} | @{user['username']} | {user['first_name']}")
                await asyncio.sleep(0.3)  # Delay to avoid FloodWait
            except Exception as e:
                failed_count += 1
                failed_users.append(f"ID: {user['user_id']} | @{user['username']} | {user['first_name']} | Error: {str(e)}")
                print(f"[LOG] ❌ Broadcast failed to user {user_id_str}: {e}")

        # Store stats for detail view
        broadcast_stats[sender.id] = {
            'sent': sent_users,
            'failed': failed_users,
            'sent_count': sent_count,
            'failed_count': failed_count
        }

        print(f"[LOG] ✅ Broadcast complete: {sent_count} sent, {failed_count} failed")
        broadcast_temp[sender.id] = False
        result_text = f"✅ Broadcast Complete!\n\n✅ Sent: {sent_count}\n❌ Failed: {failed_count}"
        buttons = [
            [Button.inline('📋 Detail', b'broadcast_detail'), Button.inline('🔙 Back', b'owner_back')]
        ]
        await event.respond(result_text, buttons=buttons)
        raise events.StopPropagation

# Track processed join events to avoid duplicates
processed_joins = {}

@client.on(events.ChatAction)
async def member_joined_handler(event):
    """Handle new members joining the group"""
    try:
        # Only process if there's an action message (user joined/added)
        if not event.action_message:
            return

        # Check if BOT itself was added to a group
        if event.user_added:
            user = await event.get_user()
            if user and user.id == (await client.get_me()).id:
                # Bot was added to a new group
                chat = await event.get_chat()
                if not chat:
                    return
                
                grp_id = chat.id
                grp_name = chat.username or str(chat.id)
                grp_title = chat.title or 'Unknown Group'
                invite_link = None
                is_private = 1 if not chat.username else 0
                added_by_id = sender.id
                added_by_username = sender.username or sender.first_name or "Unknown"
                
                # Try to get invite link for private groups
                if not chat.username:
                    try:
                        from telethon.tl.functions.messages import ExportChatInviteRequest
                        invite = await client(ExportChatInviteRequest(chat))
                        invite_link = invite.link
                        print(f"[LOG] 📎 Got invite link for private group '{grp_title}': {invite_link}")
                    except Exception as invite_err:
                        print(f"[LOG] ⚠️ Could not get invite link for '{grp_title}': {invite_err}")
                
                # Auto-add group when bot is directly added
                was_new = False
                if not group_exists(grp_id):
                    add_group(grp_id, grp_name, grp_title, invite_link, added_by_id, added_by_username, is_private)
                    print(f"[LOG] 🤖 Bot added to new group '{grp_title}' - Auto-added to database")
                    was_new = True
                else:
                    # Group exists but might be inactive - reactivate it
                    add_group(grp_id, grp_name, grp_title, invite_link, added_by_id, added_by_username, is_private)
                    print(f"[LOG] 🤖 Bot re-added to group '{grp_title}' - Reactivated in database")
                
                # Send thank you message and auto-delete after 10 seconds
                try:
                    if was_new:
                        thank_msg = f"🎉 **Thank you for adding me to {grp_title}!**\n\n"
                        thank_msg += f"✨ I'm now ready to serve this group!\n\n"
                        thank_msg += f"📋 **Available Commands:**\n"
                        thank_msg += f"• /help - View all commands\n"
                        thank_msg += f"• /ban - Ban a user (Admins only)\n"
                        thank_msg += f"• /unban - Unban a user (Admins only)\n"
                        thank_msg += f"• /info - Get user info (Admins only)\n\n"
                        thank_msg += f"🛠️ **Tools:** Use /help to see all available tools\n\n"
                        thank_msg += f"💡 **Tip:** Make me admin for best performance!"
                    else:
                        thank_msg = f"🎉 **Thank you for re-adding me to {grp_title}!**\n\n"
                        thank_msg += f"✨ I'm back and ready to serve!\n\n"
                        thank_msg += f"Use /help to see all available commands and tools."
                    
                    # Send message and get message object
                    sent_msg = await client.send_message(chat, thank_msg)
                    print(f"[LOG] ✅ Thank you message sent to group '{grp_title}'")
                    
                    # Schedule auto-deletion after 10 seconds
                    async def delete_thank_you_msg():
                        await asyncio.sleep(10)
                        try:
                            await sent_msg.delete()
                            print(f"[LOG] 🗑️ Thank you message auto-deleted in group '{grp_title}'")
                        except Exception as del_err:
                            print(f"[LOG] ❌ Could not delete thank you message: {del_err}")
                    
                    # Run deletion in background
                    asyncio.create_task(delete_thank_you_msg())
                    
                except Exception as send_err:
                    print(f"[LOG] ❌ Could not send thank you message: {send_err}")
                
                return

        if event.user_joined or event.user_added:
            chat = await event.get_chat()
            if not chat:
                print(f"[LOG] ⚠️ Could not get chat info in member_joined_handler")
                return

            grp_id = chat.id
            grp_name = chat.username or str(chat.id)
            grp_title = chat.title or 'Unknown Group'

            # Check if group is active - if not, skip welcome message
            if not is_group_active(grp_id):
                print(f"[LOG] ⏭️ Group '{grp_title}' is removed - skipping welcome message")
                return

            # Get the user who joined
            user = await event.get_user()
            if not user:
                print(f"[LOG] ⚠️ Could not get user info for join event in {grp_title}")
                return

            # CHECK IF USER IS BANNED - if yes, ban them immediately with EditBannedRequest
            banned_user = get_user(user.id)
            if banned_user and banned_user.get('banned'):
                try:
                    banned_rights = ChatBannedRights(
                        until_date=None,
                        view_messages=True,
                        send_messages=True,
                        send_media=True,
                        send_stickers=True,
                        send_gifs=True,
                        send_games=True,
                        send_inline=True,
                        embed_links=True
                    )
                    await client(EditBannedRequest(chat, user.id, banned_rights))
                    print(f"[LOG] 🚫 Banned user {user.first_name} tried to rejoin {grp_title} - BANNED!")
                    kick_msg = await client.send_message(chat, f"🚫 @{user.username or user.first_name} is banned! Auto-banned!")
                    await schedule_message_delete(kick_msg, 30)
                except Exception as kick_err:
                    print(f"[LOG] ❌ Could not ban user: {kick_err}")
                return

            # Create unique key based on message ID to prevent duplicate processing
            if hasattr(event.action_message, 'id'):
                join_key = f"{grp_id}_{user.id}_{event.action_message.id}"
            else:
                join_key = f"{grp_id}_{user.id}_{int(datetime.now().timestamp())}"

            # Check if we already processed this exact join event
            if join_key in processed_joins:
                print(f"[LOG] ⏭️ Skipping duplicate join event for {user.first_name} in {grp_title}")
                return

            # Mark as processed
            processed_joins[join_key] = datetime.now().timestamp()

            print(f"[LOG] 👤 New member joined: {user.first_name} (@{user.username or 'no_username'}) ID: {user.id}")
            print(f"[LOG] 📍 Group: {grp_title} (ID: {grp_id})")

            # Add user to database
            add_user(user.id, user.username or 'unknown', user.first_name or 'User')
            print(f"[LOG] ✅ User '{user.first_name}' added/updated in database")

            # Get random welcome message (includes both default and custom messages)
            user_username = user.username or user.first_name or "user"
            msg_text = get_random_welcome_message(user_username, grp_title)
            print(f"[LOG] 🎲 Random welcome message selected: {msg_text[:50]}...")

            try:
                # Send welcome message
                welcome_message = await client.send_message(chat, msg_text)
                print(f"[LOG] ✅ Welcome message sent to {user.first_name} in {grp_title}")

                # Schedule deletion after 600 seconds (10 minutes)
                async def delete_after_delay():
                    await asyncio.sleep(600)
                    try:
                        await welcome_message.delete()
                        print(f"[LOG] 🗑️ Welcome message auto-deleted for {user.first_name} in {grp_title}")
                    except Exception as del_err:
                        print(f"[LOG] ❌ Could not delete welcome message: {del_err}")

                # Run deletion in background
                asyncio.create_task(delete_after_delay())
            except Exception as send_err:
                print(f"[LOG] ❌ Error sending welcome message: {send_err}")

    except Exception as e:
        print(f"[LOG] ❌ Error in member_joined_handler: {e}")

@client.on(events.NewMessage(incoming=True))
async def group_message_handler(event):
    try:
        if not event.is_group:
            return
            
        chat = await event.get_chat()
        grp_id = chat.id
        sender = await event.get_sender()

        if not sender or not chat:
            return
        
        # Check if group is active - if not, don't track messages
        if not is_group_active(grp_id):
            print(f"[LOG] ⏭️ Group '{chat.title}' is removed - ignoring message")
            return

        # Track messages only in active groups
        add_user(sender.id, sender.username or 'unknown', sender.first_name or 'User')
        increment_messages(sender.id)
        
        # Skip if message is forwarded or has no text (to avoid wrongful detection)
        if event.forward or not event.text:
            return
            
        # Check for bad words in message (skip for admins and only sender-authored text)
        # Also check if bad word filter is enabled
        bad_words_filter_enabled = get_setting('bad_words_filter_enabled', '1') == '1'
        is_admin = await check_admin_permission(event, sender.id)
        has_bad_word, found_words = False, []
        if bad_words_filter_enabled and not is_admin:
            has_bad_word, found_words = check_message_for_bad_words(event.text)
        if has_bad_word:
            user_name = sender.first_name or sender.username or "User"
            warning_count = add_warning(grp_id, sender.id, 0, "Bad language")
            
            if warning_count >= 3:
                try:
                    # Check if bot has kick permissions
                    bot_perms = await client.get_permissions(chat, 'me')
                    if bot_perms.ban_users:
                        await client.kick_participant(chat, sender.id)
                        warn_msg = await event.reply(f"🚫 **{user_name}** has been kicked from the group!\n\n⚠️ Reason: 3 warnings for bad language\n📋 Detected: {', '.join(found_words[:3])}")
                        await schedule_message_delete(warn_msg, 60)
                    else:
                        warn_msg = await event.reply(f"⚠️ **{user_name}** should be kicked but bot has no ban permissions!")
                        await schedule_message_delete(warn_msg, 30)
                except Exception as kick_err:
                    print(f"[LOG] ❌ Could not kick user: {kick_err}")
            else:
                warn_msg = await event.reply(f"⚠️ **Warning {warning_count}/3** - {user_name}\n\n🚫 Bad language detected!\n📋 Word: ||{found_words[0]}||\n\n⛔ 3 warnings = Kick from group")
                await schedule_message_delete(warn_msg, 30)
            return
        
        # Check for greetings and respond (only for short messages likely to be greetings)
        if len(event.text) < 50:
            greeting_type = detect_greeting_type(event.text)
            if greeting_type:
                user_name = sender.first_name or sender.username or "Friend"
                response = get_response_for_greeting(greeting_type, user_name)
                if response:
                    greeting_msg = await event.reply(response)
                    await schedule_message_delete(greeting_msg, 120)
                    
    except Exception as e:
        print(f"[LOG] ❌ Error in group_message_handler: {e}")

async def check_admin_permission(event, sender_id=None):
    """Check if user has admin permission (bot owner, group owner, or group admin)"""
    from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator, PeerChannel, PeerUser

    # Bot owner has permission everywhere
    if sender_id and sender_id == owner_id:
        return True

    # In private chat, only bot owner allowed
    if event.is_private:
        return sender_id == owner_id

    # In group, check if user is group owner or admin
    if event.is_group:
        try:
            chat = await event.get_chat()

            # Check for anonymous admin
            if hasattr(event, 'from_id') and isinstance(event.from_id, PeerChannel):
                print(f"Anonymous admin detected in group {chat.title}")
                return True

            if event.message and hasattr(event.message, 'from_id'):
                if isinstance(event.message.from_id, PeerChannel):
                    print(f"Anonymous admin detected via message.from_id in group {chat.title}")
                    return True

            # Check regular user using get_permissions
            if sender_id:
                try:
                    permissions = await client.get_permissions(chat, sender_id)
                    if permissions.is_admin:
                        print(f"User {sender_id} is admin/creator in {chat.title}")
                        return True
                except Exception as perm_err:
                    print(f"[LOG] Admin check failed for {sender_id}: {perm_err}")
                    pass

        except Exception as e:
            print(f"[LOG] Error in check_admin_permission: {e}")
            pass

    return False

@client.on(events.NewMessage(pattern=r'/ping'))
async def manual_ping_handler(event):
    """Manual trigger for daily report and ping system (Owner only)"""
    if event.sender_id != owner_id:
        return
        
    status_msg = await event.respond("🔄 **Processing status check and ping system...**")
    success, result = await run_daily_report_and_ping()
    
    if success:
        await status_msg.edit("✅ **Status check and ping system completed successfully!**\n\nReport has been sent to your private chat.")
    else:
        await status_msg.edit(f"❌ **Error running status check:**\n`{result}`")

@client.on(events.NewMessage(pattern=r'/ban(?:\s+(.+))?'))
async def ban_handler(event):
    # Ignore commands from removed groups
    if event.is_group:
        chat = await event.get_chat()
        if not is_group_active(chat.id):
            raise events.StopPropagation

    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    sender_id = sender.id if sender else None

    # Check admin permission (allows anonymous admins too)
    has_permission = await check_admin_permission(event, sender_id)
    if not has_permission:
        await send_error_message(event, '🔐 You do not have permission! ❌\n\n👑 Only the bot owner or group admins can use this!')
        raise events.StopPropagation

    # Get target user and reason
    target_user_id = None
    target_user = None
    reason = None
    match = event.pattern_match
    args = match.group(1).strip() if match.group(1) else ''

    if event.reply_to_msg_id:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.from_id:
            target_user_id = reply_msg.from_id.user_id
            target_user = get_user(target_user_id)
            reason = args if args else None
    elif args:
        parts = args.split(None, 1)
        user_input = parts[0]
        reason = parts[1] if len(parts) > 1 else None
        
        if user_input.isdigit():
            target_user_id = int(user_input)
            target_user = get_user(target_user_id)
        elif user_input.startswith('@'):
            username = user_input[1:]
            all_users = get_all_users()
            for uid_str, user in all_users.items():
                if user.get('username') == username:
                    target_user = user
                    target_user_id = user['user_id']
                    break
            if not target_user_id:
                try:
                    entity = await client.get_entity(user_input)
                    target_user_id = entity.id
                    target_user = get_user(target_user_id)
                except:
                    pass
        else:
            await send_error_message(event, '❌ Invalid format!\n\n📌 Correct format: `/ban <user_id> reason` or `/ban @username reason` or reply to a message with `/ban reason`')
            raise events.StopPropagation
    else:
        await send_error_message(event, '❌ No user specified!\n\n📌 Use: `/ban <user_id> reason` or `/ban @username reason` or reply to a message with `/ban reason`')
        raise events.StopPropagation

    # In group, verify target user is in the same group
    if event.is_group:
        try:
            chat = await event.get_chat()
            target_in_group = await client.get_permissions(chat, target_user_id)
            if not target_in_group:
                await send_error_message(event, '❌ This user is not in this group!')
                raise events.StopPropagation
        except Exception as e:
            await send_error_message(event, '❌ This user is not in this group!')
            raise events.StopPropagation

    if not target_user:
        await send_error_message(event, '❌ This user is not in the bot database!')
        raise events.StopPropagation

    if target_user.get('banned'):
        await send_error_message(event, '⚠️ This user is already banned!')
    else:
        # Ban user in bot database
        ban_user(target_user['user_id'], reason)

        # If in group, properly ban user using EditBannedRequest
        if event.is_group:
            try:
                chat = await event.get_chat()
                # Use EditBannedRequest with ChatBannedRights for proper permanent ban
                banned_rights = ChatBannedRights(
                    until_date=None,
                    view_messages=True,
                    send_messages=True,
                    send_media=True,
                    send_stickers=True,
                    send_gifs=True,
                    send_games=True,
                    send_inline=True,
                    embed_links=True
                )
                await client(EditBannedRequest(chat, target_user_id, banned_rights))
                group_name = f" in {chat.title}"
                print(f"[LOG] ✅ User {target_user_id} properly banned from group {chat.title}")
            except Exception as ban_err:
                print(f"Could not ban user from group: {ban_err}")
                # Fallback to edit_permissions if EditBannedRequest fails
                try:
                    await client.edit_permissions(chat, target_user_id, view_messages=False, send_messages=False)
                    group_name = f" in {chat.title}"
                except:
                    group_name = " in bot"
        else:
            group_name = " in bot"

        result_text = f"🔨 **User BANNED{group_name}!** ✅\n\n👤 User ID: `{target_user['user_id']}`\n📛 Username: @{target_user['username']}\n📝 Name: {target_user['first_name']}"
        if reason:
            result_text += f"\n📋 Reason: {reason}"
        response_msg = await event.respond(result_text)
        await schedule_message_delete(response_msg, 300)
        try:
            await event.delete()
        except:
            pass
        try:
            ban_msg = f'🚫 You have been BANNED{group_name}! ❌'
            if reason:
                ban_msg += f'\n📋 Reason: {reason}'
            await client.send_message(target_user['user_id'], ban_msg)
        except Exception:
            pass

    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/unban(?:\s+(.+))?'))
async def unban_handler(event):
    # Ignore commands from removed groups
    if event.is_group:
        chat = await event.get_chat()
        if not is_group_active(chat.id):
            raise events.StopPropagation

    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    sender_id = sender.id if sender else None

    # Check admin permission (allows anonymous admins too)
    has_permission = await check_admin_permission(event, sender_id)
    if not has_permission:
        await event.respond('🔐 You do not have permission! ❌\n\n👑 Only the bot owner or group admins can use this!')
        raise events.StopPropagation

    # Get target user
    target_user_id = None
    target_user = None
    match = event.pattern_match

    if event.reply_to_msg_id:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.from_id:
            target_user_id = reply_msg.from_id.user_id
            target_user = get_user(target_user_id)
    elif match.group(1):
        user_input = match.group(1).strip()
        if user_input.isdigit():
            target_user_id = int(user_input)
            target_user = get_user(target_user_id)
        elif user_input.startswith('@'):
            username = user_input[1:]
            all_users = get_all_users()
            for uid_str, user in all_users.items():
                if user.get('username') == username:
                    target_user = user
                    target_user_id = user['user_id']
                    break
        else:
            await event.respond('❌ Invalid format!\n\n📌 Correct format: `/unban <user_id>` or `/unban @username` or reply to a message with `/unban`')
            raise events.StopPropagation
    else:
        await event.respond('❌ No user specified!\n\n📌 Use: `/unban <user_id>` or `/unban @username` or reply to a message with `/unban`')
        raise events.StopPropagation

    # In group, verify target user is in the same group
    if event.is_group:
        try:
            chat = await event.get_chat()
            target_in_group = await client.get_permissions(chat, target_user_id)
            if not target_in_group:
                await event.respond('❌ This user is not in this group!')
                raise events.StopPropagation
        except Exception as e:
            await event.respond('❌ This user is not in this group!')
            raise events.StopPropagation

    if not target_user:
        await event.respond('❌ This user is not in the bot database!')
        raise events.StopPropagation

    if not target_user.get('banned'):
        await event.respond('⚠️ This user is not even banned!')
    else:
        # Unban user in bot database
        unban_user(target_user['user_id'])

        # If in group, also restore permissions
        if event.is_group:
            try:
                chat = await event.get_chat()
                # Restore full permissions (no restrictions)
                await client.edit_permissions(chat, target_user_id, view_messages=True, send_messages=True)
                group_name = f" in {chat.title}"
            except Exception as restore_err:
                print(f"Could not restore user in group: {restore_err}")
                group_name = " in bot"
        else:
            group_name = " in bot"

        result_text = f"🔓 **User UNBANNED{group_name}!** ✅\n\n👤 User ID: `{target_user['user_id']}`\n📛 Username: @{target_user['username']}\n📝 Name: {target_user['first_name']}"
        response_msg = await event.respond(result_text)
        await schedule_message_delete(response_msg, 300)
        try:
            await event.delete()
        except:
            pass
        try:
            await client.send_message(target_user['user_id'], f'✅ Your ban has been lifted{group_name}! 🎉\n\nYou can use the bot again!')
        except Exception:
            pass

    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/gban(?:\s+(.+))?'))
async def gban_handler(event):
    # Ignore commands from removed groups
    if event.is_group:
        chat = await event.get_chat()
        if not is_group_active(chat.id):
            raise events.StopPropagation

    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    sender_id = sender.id if sender else None

    # Check admin permission (allows anonymous admins too)
    has_permission = await check_admin_permission(event, sender_id)
    if not has_permission:
        await event.respond('🔐 You do not have permission! ❌\n\n👑 Only the bot owner or group admins can use this!')
        raise events.StopPropagation

    # Get target user and reason
    target_user_id = None
    target_user = None
    reason = None
    match = event.pattern_match
    args = match.group(1).strip() if match.group(1) else ''

    if event.reply_to_msg_id:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.from_id:
            target_user_id = reply_msg.from_id.user_id
            target_user = get_user(target_user_id)
            reason = args if args else None
    elif args:
        parts = args.split(None, 1)
        user_input = parts[0]
        reason = parts[1] if len(parts) > 1 else None
        
        if user_input.isdigit():
            target_user_id = int(user_input)
            target_user = get_user(target_user_id)
        elif user_input.startswith('@'):
            username = user_input[1:]
            all_users = get_all_users()
            for uid_str, user in all_users.items():
                if user.get('username') == username:
                    target_user = user
                    target_user_id = user['user_id']
                    break
            if not target_user_id:
                try:
                    entity = await client.get_entity(user_input)
                    target_user_id = entity.id
                    target_user = get_user(target_user_id)
                except:
                    pass
        else:
            await event.respond('❌ Invalid format!\n\n📌 Correct format: `/gban <user_id> reason` or `/gban @username reason` or reply to a message with `/gban reason`')
            raise events.StopPropagation
    else:
        await event.respond('❌ No user specified!\n\n📌 Use: `/gban <user_id> reason` or `/gban @username reason` or reply to a message with `/gban reason`')
        raise events.StopPropagation

    # In group, verify target user is in the same group
    if event.is_group:
        try:
            chat = await event.get_chat()
            target_in_group = await client.get_permissions(chat, target_user_id)
            if not target_in_group:
                await event.respond('❌ This user is not in this group!')
                raise events.StopPropagation
        except Exception as e:
            await event.respond('❌ This user is not in this group!')
            raise events.StopPropagation
    else:
        await event.respond('❌ /gban can only be used in groups!')
        raise events.StopPropagation

    if not target_user:
        await event.respond('❌ This user is not in the bot database!')
        raise events.StopPropagation

    if target_user.get('banned'):
        await event.respond('⚠️ This user is already banned!')
    else:
        # Ban user in bot database
        ban_user(target_user['user_id'], reason)

        # Kick from group
        try:
            chat = await event.get_chat()
            await client.kick_participant(chat, target_user_id)
            group_name = f" in {chat.title} aur bot se"
        except Exception as kick_err:
            print(f"Could not kick user from group: {kick_err}")
            group_name = " from bot"

        result_text = f"🔨 **User GLOBAL BAN (GBAN) SUCCESSFUL!** ✅\n\n👤 User ID: `{target_user['user_id']}`\n📛 Username: @{target_user['username']}\n📝 Name: {target_user['first_name']}\n🌍 Ban Location: {group_name}"
        if reason:
            result_text += f"\n📋 Reason: {reason}"
        response_msg = await event.respond(result_text)
        await schedule_message_delete(response_msg, 300)
        try:
            await event.delete()
        except:
            pass
        try:
            ban_msg = f'🚫 You have been GLOBAL BANNED! ❌\n\nYou are now banned from this group and the bot.'
            if reason:
                ban_msg += f'\n📋 Reason: {reason}'
            await client.send_message(target_user['user_id'], ban_msg)
        except Exception:
            pass

    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/info(?:\s+(.+))?'))
async def info_handler(event):
    # Ignore commands from removed groups
    if event.is_group:
        chat = await event.get_chat()
        if not is_group_active(chat.id):
            raise events.StopPropagation

    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    sender_id = sender.id if sender else None

    # Check admin permission (allows anonymous admins too)
    has_permission = await check_admin_permission(event, sender_id)
    if not has_permission:
        await event.respond('🔐 You do not have permission! ❌\n\n👑 Only the bot owner or group admins can use this!')
        raise events.StopPropagation

    # Get target user
    target_user_id = None
    target_user = None
    match = event.pattern_match

    if event.reply_to_msg_id:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.from_id:
            target_user_id = reply_msg.from_id.user_id
            target_user = get_user(target_user_id)
    elif match.group(1):
        user_input = match.group(1).strip()
        if user_input.isdigit():
            target_user_id = int(user_input)
            target_user = get_user(target_user_id)
        elif user_input.startswith('@'):
            username = user_input[1:]
            all_users = get_all_users()
            for uid_str, user in all_users.items():
                if user.get('username') == username:
                    target_user = user
                    target_user_id = user['user_id']
                    break
        else:
            await event.respond('❌ Invalid format!\n\n📌 Correct format: `/info <user_id>` or `/info @username` or reply to a message with `/info`')
            raise events.StopPropagation
    else:
        await event.respond('❌ No user specified!\n\n📌 Use: `/info <user_id>` or `/info @username` or reply to a message with `/info`')
        raise events.StopPropagation

    # In group, verify target user is in the same group
    if event.is_group:
        try:
            chat = await event.get_chat()
            target_in_group = await client.get_permissions(chat, target_user_id)
            if not target_in_group:
                await event.respond('❌ This user is not in this group!')
                raise events.StopPropagation
        except Exception as e:
            await event.respond('❌ This user is not in this group!')
            raise events.StopPropagation

    if not target_user:
        await event.respond('❌ This user is not in the bot database!')
        raise events.StopPropagation

    info_text = f"📋 **USER DETAILS** 👤\n\n"
    info_text += f"🆔 ID: `{target_user['user_id']}`\n"
    info_text += f"📛 Username: @{target_user['username']}\n"
    info_text += f"📝 Name: {target_user['first_name']}\n"
    info_text += f"💬 Total Messages: {target_user['messages']}\n"
    info_text += f"📅 Join Date: {target_user['joined'][:10]}\n"
    info_text += f"⏰ Full Date: {target_user['joined']}\n"
    info_text += f"🔄 Status: {'🚫 BANNED' if target_user['banned'] else '✅ ACTIVE'}\n"
    if target_user['banned'] and target_user.get('ban_reason'):
        info_text += f"📋 Ban Reason: {target_user['ban_reason']}\n"
        if target_user.get('ban_date'):
            info_text += f"📅 Ban Date: {target_user['ban_date'][:10]}\n"
    info_text += f"📊 User Level: {target_user['status']}\n"

    if event.is_group:
        chat = await event.get_chat()
        info_text += f"\n📍 Group: {chat.title}"

    await event.respond(info_text)

    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/warn(?:\s+(.+))?'))
async def warn_handler(event):
    """Warn a user in group. 3 warnings = auto-ban"""
    if not event.is_group:
        await event.respond('⚠️ This command only works in groups!')
        raise events.StopPropagation
    
    chat = await event.get_chat()
    if not is_group_active(chat.id):
        raise events.StopPropagation
    
    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    sender_id = sender.id if sender else None
    
    has_permission = await check_admin_permission(event, sender_id)
    if not has_permission:
        await event.respond('🔐 No permission! Only admins can warn!')
        raise events.StopPropagation
    
    target_user_id = None
    reason = None
    match = event.pattern_match
    args = match.group(1).strip() if match.group(1) else ''
    
    if event.reply_to_msg_id:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.from_id:
            target_user_id = reply_msg.from_id.user_id
            reason = args if args else None
    elif args:
        parts = args.split(None, 1)
        user_input = parts[0]
        reason = parts[1] if len(parts) > 1 else None
        
        if user_input.isdigit():
            target_user_id = int(user_input)
        elif user_input.startswith('@'):
            try:
                entity = await client.get_entity(user_input)
                target_user_id = entity.id
            except:
                await event.respond('❌ User not found!')
                raise events.StopPropagation
    else:
        await event.respond('❌ No user specified!\n\n📌 Use: `/warn @username reason` or reply to a message with `/warn reason`')
        raise events.StopPropagation
    
    if not target_user_id:
        await event.respond('❌ User not found!')
        raise events.StopPropagation
    
    try:
        target_perms = await client.get_permissions(chat, target_user_id)
        if target_perms.is_admin or target_perms.is_creator:
            await event.respond('❌ Cannot warn admins!')
            raise events.StopPropagation
    except:
        pass
    
    new_count = add_warning(chat.id, target_user_id, sender_id, reason)
    
    try:
        target_entity = await client.get_entity(target_user_id)
        target_name = target_entity.first_name or 'User'
        target_username = f"@{target_entity.username}" if target_entity.username else f"ID: {target_user_id}"
    except:
        target_name = 'User'
        target_username = f"ID: {target_user_id}"
    
    if new_count >= 3:
        try:
            await client.edit_permissions(chat, target_user_id, view_messages=False)
            clear_warnings(chat.id, target_user_id)
            warn_text = f"🚨 **AUTO BAN!** 🚨\n\n👤 {target_name} ({target_username})\n⚠️ 3 warnings complete!\n🔨 Banned from group!"
            if reason:
                warn_text += f"\n📝 Last Reason: {reason}"
        except Exception as e:
            warn_text = f"⚠️ **WARNING {new_count}/3** ⚠️\n\n👤 {target_name} ({target_username})\n❌ Auto-ban failed: {str(e)[:50]}"
    else:
        warn_text = f"⚠️ **WARNING {new_count}/3** ⚠️\n\n👤 {target_name} ({target_username})"
        if reason:
            warn_text += f"\n📝 Reason: {reason}"
        if new_count == 2:
            warn_text += "\n\n⚠️ One more warning and you will be BANNED!"
    
    # Send response and schedule auto-delete after 5 min
    response_msg = await event.respond(warn_text)
    await schedule_message_delete(response_msg, 300)
    try:
        await event.delete()  # Delete command message
    except:
        pass
    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/delwarn(?:\s+(.+))?'))
async def delwarn_handler(event):
    """Delete message and warn the user"""
    if not event.is_group:
        await event.respond('⚠️ This command only works in groups!')
        raise events.StopPropagation
    
    chat = await event.get_chat()
    if not is_group_active(chat.id):
        raise events.StopPropagation
    
    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    sender_id = sender.id if sender else None
    
    has_permission = await check_admin_permission(event, sender_id)
    if not has_permission:
        await event.respond('🔐 No permission!')
        raise events.StopPropagation
    
    if not event.reply_to_msg_id:
        await event.respond('❌ Use this by replying to a message!')
        raise events.StopPropagation
    
    reply_msg = await event.get_reply_message()
    if not reply_msg or not reply_msg.from_id:
        await event.respond('❌ User message not found!')
        raise events.StopPropagation
    
    target_user_id = reply_msg.from_id.user_id
    match = event.pattern_match
    reason = match.group(1).strip() if match.group(1) else "Message delete + warn"
    
    try:
        target_perms = await client.get_permissions(chat, target_user_id)
        if target_perms.is_admin or target_perms.is_creator:
            await event.respond('❌ Cannot warn admins!')
            raise events.StopPropagation
    except:
        pass
    
    msg_deleted = False
    try:
        await reply_msg.delete()
        msg_deleted = True
    except Exception as e:
        # Message delete failed but warning still added
        pass
    
    new_count = add_warning(chat.id, target_user_id, sender_id, reason)
    
    try:
        target_entity = await client.get_entity(target_user_id)
        target_name = target_entity.first_name or 'User'
        target_username = f"@{target_entity.username}" if target_entity.username else f"ID: {target_user_id}"
    except:
        target_name = 'User'
        target_username = f"ID: {target_user_id}"
    
    delete_status = "🗑️ Message deleted" if msg_deleted else "⚠️ Message not deleted"
    
    if new_count >= 3:
        try:
            await client.edit_permissions(chat, target_user_id, view_messages=False)
            clear_warnings(chat.id, target_user_id)
            warn_text = f"{delete_status} + 🚨 **AUTO BAN!**\n\n👤 {target_name} ({target_username})\n⚠️ 3 warnings complete!\n🔨 Banned from group!"
            if reason:
                warn_text += f"\n📝 Reason: {reason}"
        except:
            warn_text = f"{delete_status} + ⚠️ **WARNING {new_count}/3**\n\n👤 {target_name}"
    else:
        warn_text = f"{delete_status} + ⚠️ **WARNING {new_count}/3**\n\n👤 {target_name} ({target_username})"
        if reason:
            warn_text += f"\n📝 Reason: {reason}"
    
    # Send response and schedule auto-delete after 5 min
    response_msg = await event.respond(warn_text)
    await schedule_message_delete(response_msg, 300)
    try:
        await event.delete()  # Delete command message
    except:
        pass
    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/unwarn(?:\s+(.+))?'))
async def unwarn_handler(event):
    """Remove one warning from user"""
    if not event.is_group:
        await event.respond('⚠️ This command only works in groups!')
        raise events.StopPropagation
    
    chat = await event.get_chat()
    if not is_group_active(chat.id):
        raise events.StopPropagation
    
    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    sender_id = sender.id if sender else None
    
    has_permission = await check_admin_permission(event, sender_id)
    if not has_permission:
        await event.respond('🔐 No permission!')
        raise events.StopPropagation
    
    target_user_id = None
    match = event.pattern_match
    args = match.group(1).strip() if match.group(1) else ''
    
    if event.reply_to_msg_id:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.from_id:
            target_user_id = reply_msg.from_id.user_id
    elif args:
        user_input = args.split()[0]
        if user_input.isdigit():
            target_user_id = int(user_input)
        elif user_input.startswith('@'):
            try:
                entity = await client.get_entity(user_input)
                target_user_id = entity.id
            except:
                await event.respond('❌ User not found!')
                raise events.StopPropagation
    else:
        await event.respond('❌ No user specified!\n\n📌 Use: `/unwarn @username` or reply to a message with `/unwarn`')
        raise events.StopPropagation
    
    if not target_user_id:
        await event.respond('❌ User not found!')
        raise events.StopPropagation
    
    current = get_user_warnings(chat.id, target_user_id)
    if current['warnings'] == 0:
        await event.respond('ℹ️ This user has no warnings!')
        raise events.StopPropagation
    
    new_count = remove_warning(chat.id, target_user_id)
    
    try:
        target_entity = await client.get_entity(target_user_id)
        target_name = target_entity.first_name or 'User'
        target_username = f"@{target_entity.username}" if target_entity.username else f"ID: {target_user_id}"
    except:
        target_name = 'User'
        target_username = f"ID: {target_user_id}"
    
    response_msg = await event.respond(f"✅ Warning removed!\n\n👤 {target_name} ({target_username})\n⚠️ Current warnings: {new_count}/3")
    await schedule_message_delete(response_msg, 300)
    try:
        await event.delete()
    except:
        pass
    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/mute(?:\s+(.+))?'))
async def mute_handler(event):
    """Mute a user in group"""
    if not event.is_group:
        await event.respond('⚠️ This command only works in groups!')
        raise events.StopPropagation
    
    chat = await event.get_chat()
    if not is_group_active(chat.id):
        raise events.StopPropagation
    
    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    sender_id = sender.id if sender else None
    
    has_permission = await check_admin_permission(event, sender_id)
    if not has_permission:
        await event.respond('🔐 No permission!')
        raise events.StopPropagation
    
    target_user_id = None
    reason = None
    match = event.pattern_match
    args = match.group(1).strip() if match.group(1) else ''
    
    if event.reply_to_msg_id:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.from_id:
            target_user_id = reply_msg.from_id.user_id
            reason = args if args else None
    elif args:
        parts = args.split(None, 1)
        user_input = parts[0]
        reason = parts[1] if len(parts) > 1 else None
        
        if user_input.isdigit():
            target_user_id = int(user_input)
        elif user_input.startswith('@'):
            try:
                entity = await client.get_entity(user_input)
                target_user_id = entity.id
            except:
                await event.respond('❌ User not found!')
                raise events.StopPropagation
    else:
        await event.respond('❌ No user specified!\n\n📌 Use: `/mute @username reason` or reply to a message with `/mute reason`')
        raise events.StopPropagation
    
    if not target_user_id:
        await event.respond('❌ User not found!')
        raise events.StopPropagation
    
    try:
        target_perms = await client.get_permissions(chat, target_user_id)
        if target_perms.is_admin or target_perms.is_creator:
            await event.respond('❌ Cannot mute admins!')
            raise events.StopPropagation
    except:
        pass
    
    try:
        # Mute user - restrict send_messages permission
        await client.edit_permissions(chat, target_user_id, send_messages=False)
        
        try:
            target_entity = await client.get_entity(target_user_id)
            target_name = target_entity.first_name or 'User'
            target_username = f"@{target_entity.username}" if target_entity.username else f"ID: {target_user_id}"
        except:
            target_name = 'User'
            target_username = f"ID: {target_user_id}"
        
        mute_text = f"🔇 **USER MUTED!**\n\n👤 {target_name} ({target_username})"
        if reason:
            mute_text += f"\n📝 Reason: {reason}"
        response_msg = await event.respond(mute_text)
        await schedule_message_delete(response_msg, 300)
        try:
            await event.delete()
        except:
            pass
    except Exception as e:
        await event.respond(f'❌ Could not mute user: {str(e)[:100]}')
    
    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/unmute(?:\s+(.+))?'))
async def unmute_handler(event):
    """Unmute a user in group"""
    if not event.is_group:
        await event.respond('⚠️ This command only works in groups!')
        raise events.StopPropagation
    
    chat = await event.get_chat()
    if not is_group_active(chat.id):
        raise events.StopPropagation
    
    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    sender_id = sender.id if sender else None
    
    has_permission = await check_admin_permission(event, sender_id)
    if not has_permission:
        await event.respond('🔐 No permission!')
        raise events.StopPropagation
    
    target_user_id = None
    match = event.pattern_match
    args = match.group(1).strip() if match.group(1) else ''
    
    if event.reply_to_msg_id:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.from_id:
            target_user_id = reply_msg.from_id.user_id
    elif args:
        user_input = args.split()[0]
        if user_input.isdigit():
            target_user_id = int(user_input)
        elif user_input.startswith('@'):
            try:
                entity = await client.get_entity(user_input)
                target_user_id = entity.id
            except:
                await event.respond('❌ User not found!')
                raise events.StopPropagation
    else:
        await event.respond('❌ No user specified!\n\n📌 Use: `/unmute @username` or reply to a message with `/unmute`')
        raise events.StopPropagation
    
    if not target_user_id:
        await event.respond('❌ User not found!')
        raise events.StopPropagation
    
    try:
        # Unmute user - restore send_messages permission
        await client.edit_permissions(chat, target_user_id, send_messages=True)
        
        try:
            target_entity = await client.get_entity(target_user_id)
            target_name = target_entity.first_name or 'User'
            target_username = f"@{target_entity.username}" if target_entity.username else f"ID: {target_user_id}"
        except:
            target_name = 'User'
            target_username = f"ID: {target_user_id}"
        
        response_msg = await event.respond(f"🔊 **USER UNMUTED!**\n\n👤 {target_name} ({target_username})")
        await schedule_message_delete(response_msg, 300)
        try:
            await event.delete()
        except:
            pass
    except Exception as e:
        await event.respond(f'❌ Could not unmute user: {str(e)[:100]}')
    
    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/num(?:\s+(.+))?'))
async def num_handler(event):
    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    if not sender:
        return

    allowed, response = await check_tool_group_access(event)
    if not allowed:
        if isinstance(response, tuple):
            msg, buttons = response
            await event.respond(msg, buttons=buttons)
        else:
            await event.respond(response)
        raise events.StopPropagation

    # Check if tool is active
    if not get_tool_status('number_info'):
        await event.respond('🚫 This tool is currently disabled! ❌')
        raise events.StopPropagation

    match = event.pattern_match
    if not match.group(1):
        await event.respond('📱 **Number Info Tool**\n\n🔹 Usage: `/num <mobile_number>`\n📝 Example: `/num 7999520665`')
        raise events.StopPropagation

    number = match.group(1).strip()
    validated = validate_phone_number(number)

    if not validated:
        await event.respond('❌ Invalid number!\n\n📌 Format: Must be 10 digits\n📝 Example: 7999520665')
        raise events.StopPropagation

    processing_msg = await event.respond('⏳ Processing, please wait...')
    data, error = await call_tool_api('number_info', validated)

    if data:
        response = format_json_as_text(data, query=validated)
        if len(response) > 4000:
            response = response[:3997] + "..."
        await processing_msg.edit(response)
    else:
        msg = f"🔍 **Your Query**: `{validated}`\n❌ Error: {error}\n\n━━━━━━━━━━━━━━━━━━━━━\nOwner: @Cyber_as\nDeveloped by: @KissuHQ"
        await processing_msg.edit(msg)
    
    # Auto-delete response after 5 minutes
    await schedule_message_delete(processing_msg, 300)

    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/adhar(?:\s+(.+))?'))
async def adhar_handler(event):
    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    if not sender:
        return

    allowed, response = await check_tool_group_access(event)
    if not allowed:
        if isinstance(response, tuple):
            msg, buttons = response
            await event.respond(msg, buttons=buttons)
        else:
            await event.respond(response)
        raise events.StopPropagation

    if not get_tool_status('aadhar_info'):
        await event.respond('🚫 This tool is currently disabled! ❌')
        raise events.StopPropagation

    match = event.pattern_match
    if not match.group(1):
        await event.respond('🆔 **Aadhar Info Tool**\n\n🔹 Usage: `/adhar <aadhar_number>`\n📝 Example: `/adhar 123456789012`')
        raise events.StopPropagation

    aadhar = match.group(1).strip()
    validated = validate_aadhar(aadhar)

    if not validated:
        await event.respond('❌ Invalid Aadhar number!\n\n📌 Format: Must be 12 digits')
        raise events.StopPropagation

    processing_msg = await event.respond('⏳ Fetching data, please wait...')
    data, error = await call_tool_api('aadhar_info', validated)

    if data:
        response = format_json_as_text(data, query=validated)
        if len(response) > 4000:
            response = response[:3997] + "..."
        await processing_msg.edit(response)
    else:
        msg = f"🔍 **Your Query**: `{validated}`\n❌ Error: {error}\n\n━━━━━━━━━━━━━━━━━━━━━\nOwner: @Cyber_as\nDeveloped by: @KissuHQ"
        await processing_msg.edit(msg)
    
    # Auto-delete response after 5 minutes
    await schedule_message_delete(processing_msg, 300)

    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/family(?:\s+(.+))?'))
async def family_handler(event):
    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    if not sender:
        return

    allowed, response = await check_tool_group_access(event)
    if not allowed:
        if isinstance(response, tuple):
            msg, buttons = response
            await event.respond(msg, buttons=buttons)
        else:
            await event.respond(response)
        raise events.StopPropagation

    if not get_tool_status('aadhar_family'):
        await event.respond('🚫 This tool is currently disabled! ❌')
        raise events.StopPropagation

    match = event.pattern_match
    if not match.group(1):
        await event.respond('👨‍👩‍👧‍👦 **Family Info Tool**\n\n🔹 Usage: `/family <aadhar_number>`\n📝 Example: `/family 123456789012`')
        raise events.StopPropagation

    aadhar = match.group(1).strip()
    validated = validate_aadhar(aadhar)

    if not validated:
        await event.respond('❌ Invalid Aadhar number!\n\n📌 Format: Must be 12 digits')
        raise events.StopPropagation

    processing_msg = await event.respond('⏳ Fetching family data, please wait...')
    data, error = await call_tool_api('aadhar_family', validated)

    if data:
        response = format_json_as_text(data, query=validated)
        if len(response) > 4000:
            response = response[:3997] + "..."
        await processing_msg.edit(response)
    else:
        msg = f"🔍 **Your Query**: `{validated}`\n❌ Error: {error}\n\n━━━━━━━━━━━━━━━━━━━━━\nOwner: @Cyber_as\nDeveloped by: @KissuHQ"
        await processing_msg.edit(msg)
    
    # Auto-delete response after 5 minutes
    await schedule_message_delete(processing_msg, 300)

    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/vhe(?:\s+(.+))?'))
async def vhe_handler(event):
    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    if not sender:
        return

    allowed, response = await check_tool_group_access(event)
    if not allowed:
        if isinstance(response, tuple):
            msg, buttons = response
            await event.respond(msg, buttons=buttons)
        else:
            await event.respond(response)
        raise events.StopPropagation

    if not get_tool_status('vehicle_info'):
        await event.respond('🚫 This tool is currently disabled! ❌')
        raise events.StopPropagation

    match = event.pattern_match
    if not match.group(1):
        await event.respond('🚗 **Vehicle Info Tool**\n\n🔹 Usage: `/vhe <vehicle_number>`\n📝 Example: `/vhe MH12AB1234`')
        raise events.StopPropagation

    vehicle = match.group(1).strip()
    validated = validate_vehicle(vehicle)

    if not validated:
        await event.respond('❌ Invalid vehicle number!\n\n📌 Format: Indian Vehicle Number\n📝 Example: MH12AB1234')
        raise events.StopPropagation

    processing_msg = await event.respond('⏳ Fetching vehicle data, please wait...')
    data, error = await call_tool_api('vehicle_info', validated)

    if data:
        response = format_json_as_text(data, query=validated)
        if len(response) > 4000:
            response = response[:3997] + "..."
        await processing_msg.edit(response)
    else:
        msg = f"🔍 **Your Query**: `{validated}`\n❌ Error: {error}\n\n━━━━━━━━━━━━━━━━━━━━━\nOwner: @Cyber_as\nDeveloped by: @KissuHQ"
        await processing_msg.edit(msg)
    
    # Auto-delete response after 5 minutes
    await schedule_message_delete(processing_msg, 300)

    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/ifsc(?:\s+(.+))?'))
async def ifsc_handler(event):
    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    if not sender:
        return

    allowed, response = await check_tool_group_access(event)
    if not allowed:
        if isinstance(response, tuple):
            msg, buttons = response
            await event.respond(msg, buttons=buttons)
        else:
            await event.respond(response)
        raise events.StopPropagation

    if not get_tool_status('ifsc_info'):
        await event.respond('🚫 This tool is currently disabled! ❌')
        raise events.StopPropagation

    match = event.pattern_match
    if not match.group(1):
        await event.respond('🏦 **IFSC Code Tool**\n\n🔹 Usage: `/ifsc <ifsc_code>`\n📝 Example: `/ifsc SBIN0001234`')
        raise events.StopPropagation

    ifsc = match.group(1).strip()
    validated = validate_ifsc(ifsc)

    if not validated:
        await event.respond('❌ Invalid IFSC code!\n\n📌 Format: Must be 11 characters\n📝 Example: SBIN0001234')
        raise events.StopPropagation

    processing_msg = await event.respond('⏳ Fetching bank details, please wait...')
    data, error = await call_tool_api('ifsc_info', validated)

    if data:
        response = format_json_as_text(data, query=validated)
        if len(response) > 4000:
            response = response[:3997] + "..."
        await processing_msg.edit(response)
    else:
        msg = f"🔍 **Your Query**: `{validated}`\n❌ Error: {error}\n\n━━━━━━━━━━━━━━━━━━━━━\nOwner: @Cyber_as\nDeveloped by: @KissuHQ"
        await processing_msg.edit(msg)
    
    # Auto-delete response after 5 minutes
    await schedule_message_delete(processing_msg, 300)

    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/pak(?:\s+(.+))?'))
async def pak_handler(event):
    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    if not sender:
        return

    allowed, response = await check_tool_group_access(event)
    if not allowed:
        if isinstance(response, tuple):
            msg, buttons = response
            await event.respond(msg, buttons=buttons)
        else:
            await event.respond(response)
        raise events.StopPropagation

    if not get_tool_status('pak_num'):
        await event.respond('🚫 This tool is currently disabled! ❌')
        raise events.StopPropagation

    match = event.pattern_match
    if not match.group(1):
        await event.respond('🇵🇰 **Pakistan Number Tool**\n\n🔹 Usage: `/pak <pakistan_number>`\n📝 Example: `/pak 03001234567`')
        raise events.StopPropagation

    pak_num = match.group(1).strip()
    validated = validate_pak_number(pak_num)

    if not validated:
        await event.respond('❌ Invalid Pakistan number!\n\n📌 Format: Must be 10-11 digits\n📝 Example: 03001234567')
        raise events.StopPropagation

    processing_msg = await event.respond('⏳ Fetching data, please wait...')
    data, error = await call_tool_api('pak_num', validated)

    if data:
        response = format_json_as_text(data, query=validated)
        if len(response) > 4000:
            response = response[:3997] + "..."
        await processing_msg.edit(response)
    else:
        msg = f"🔍 **Your Query**: `{validated}`\n❌ Error: {error}\n\n━━━━━━━━━━━━━━━━━━━━━\nOwner: @Cyber_as\nDeveloped by: @KissuHQ"
        await processing_msg.edit(msg)
    
    # Auto-delete response after 5 minutes
    await schedule_message_delete(processing_msg, 300)

    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/pin(?:\s+(.+))?'))
async def pin_handler(event):
    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    if not sender:
        return

    allowed, response = await check_tool_group_access(event)
    if not allowed:
        if isinstance(response, tuple):
            msg, buttons = response
            await event.respond(msg, buttons=buttons)
        else:
            await event.respond(response)
        raise events.StopPropagation

    if not get_tool_status('pincode_info'):
        await event.respond('🚫 This tool is currently disabled! ❌')
        raise events.StopPropagation

    match = event.pattern_match
    if not match.group(1):
        await event.respond('📍 **PIN Code Tool**\n\n🔹 Usage: `/pin <pincode>`\n📝 Example: `/pin 400001`')
        raise events.StopPropagation

    pincode = match.group(1).strip()
    validated = validate_pincode(pincode)

    if not validated:
        await event.respond('❌ Invalid PIN code!\n\n📌 Format: Must be 6 digits\n📝 Example: 400001')
        raise events.StopPropagation

    processing_msg = await event.respond('⏳ Fetching location info, please wait...')
    data, error = await call_tool_api('pincode_info', validated)

    if data:
        response = format_json_as_text(data, query=validated)
        if len(response) > 4000:
            response = response[:3997] + "..."
        await processing_msg.edit(response)
    else:
        msg = f"🔍 **Your Query**: `{validated}`\n❌ Error: {error}\n\n━━━━━━━━━━━━━━━━━━━━━\nOwner: @Cyber_as\nDeveloped by: @KissuHQ"
        await processing_msg.edit(msg)
    
    # Auto-delete response after 5 minutes
    await schedule_message_delete(processing_msg, 300)

    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/imei(?:\s+(.+))?'))
async def imei_handler(event):
    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    if not sender:
        return

    allowed, response = await check_tool_group_access(event)
    if not allowed:
        if isinstance(response, tuple):
            msg, buttons = response
            await event.respond(msg, buttons=buttons)
        else:
            await event.respond(response)
        raise events.StopPropagation

    if not get_tool_status('imei_info'):
        await event.respond('🚫 This tool is currently disabled! ❌')
        raise events.StopPropagation

    match = event.pattern_match
    if not match.group(1):
        await event.respond('📱 **IMEI Info Tool**\n\n🔹 Usage: `/imei <imei_number>`\n📝 Example: `/imei 123456789012345`')
        raise events.StopPropagation

    imei = match.group(1).strip()
    validated = validate_imei(imei)

    if not validated:
        await event.respond('❌ Invalid IMEI number!\n\n📌 Format: Must be 15 digits\n📝 Example: 123456789012345')
        raise events.StopPropagation

    processing_msg = await event.respond('⏳ Fetching device info, please wait...')
    data, error = await call_tool_api('imei_info', validated)

    if data:
        response = format_json_as_text(data, query=validated)
        if len(response) > 4000:
            response = response[:3997] + "..."
        await processing_msg.edit(response)
    else:
        msg = f"🔍 **Your Query**: `{validated}`\n❌ Error: {error}\n\n━━━━━━━━━━━━━━━━━━━━━\nOwner: @Cyber_as\nDeveloped by: @KissuHQ"
        await processing_msg.edit(msg)
    
    # Auto-delete response after 5 minutes
    await schedule_message_delete(processing_msg, 300)

    raise events.StopPropagation

@client.on(events.NewMessage(pattern=r'/ip(?:\s+(.+))?'))
async def ip_handler(event):
    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()
    if not sender:
        return

    allowed, response = await check_tool_group_access(event)
    if not allowed:
        if isinstance(response, tuple):
            msg, buttons = response
            await event.respond(msg, buttons=buttons)
        else:
            await event.respond(response)
        raise events.StopPropagation

    if not get_tool_status('ip_info'):
        await event.respond('🚫 This tool is currently disabled! ❌')
        raise events.StopPropagation

    match = event.pattern_match
    if not match.group(1):
        await event.respond('🌐 **IP Info Tool**\n\n🔹 Usage: `/ip <ip_address>`\n📝 Example: `/ip 8.8.8.8`')
        raise events.StopPropagation

    ip = match.group(1).strip()
    validated = validate_ip(ip)

    if not validated:
        await event.respond('❌ Invalid IP address!\n\n📌 Format: Must be IPv4 or IPv6\n📝 Example: 8.8.8.8')
        raise events.StopPropagation

    processing_msg = await event.respond('⏳ Fetching IP details, please wait...')
    data, error = await call_tool_api('ip_info', validated)

    if data:
        response = format_json_as_text(data, query=validated)
        if len(response) > 4000:
            response = response[:3997] + "..."
        await processing_msg.edit(response)
    else:
        msg = f"🔍 **Your Query**: `{validated}`\n❌ Error: {error}\n\n━━━━━━━━━━━━━━━━━━━━━\nOwner: @Cyber_as\nDeveloped by: @KissuHQ"
        await processing_msg.edit(msg)
    
    # Auto-delete response after 5 minutes
    await schedule_message_delete(processing_msg, 300)

    raise events.StopPropagation

@client.on(events.NewMessage(pattern='/help'))
async def help_handler(event):
    # Check if in removed group
    if event.is_group:
        chat = await event.get_chat()
        if not is_group_active(chat.id):
            raise events.StopPropagation

    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()

    # Check access
    if sender.id != owner_id:
        access_check = await check_user_access(sender.id)
        if not access_check['allowed']:
            if access_check['reason'] == 'banned':
                await event.respond('🚫 You are BANNED from this bot! ❌')
            elif access_check['reason'] == 'not_subscribed':
                msg = '⚠️ Please join these channels first!'
                buttons = []
                for ch in access_check['channels']:
                    ch_username = ch['username']
                    if not ch_username.startswith('@'):
                        ch_username = '@' + ch_username
                    buttons.append([Button.url(f"Join {ch['title']}", f"https://t.me/{ch['username']}")])
                await event.respond(msg, buttons=buttons)
            raise events.StopPropagation

    # Owner gets full command list
    if sender.id == owner_id:
        help_text = "**👑 OWNER COMMANDS**\n\n"
        help_text += "**👥 User Management:**\n"
        help_text += "├ `/ban <user_id/@username>` - Ban user\n"
        help_text += "├ `/unban <user_id/@username>` - Unban user\n"
        help_text += "└ `/info <user_id/@username>` - Get user info\n\n"
        
        help_text += "**🛠️ Tool Commands:**\n"
        help_text += "├ `/num <number>` - Phone number info\n"
        help_text += "├ `/adhar <number>` - Aadhar info\n"
        help_text += "├ `/family <aadhar>` - Aadhar family lookup\n"
        help_text += "├ `/vhe <vehicle>` - Vehicle info\n"
        help_text += "├ `/ifsc <code>` - IFSC code info\n"
        help_text += "├ `/pak <number>` - Pakistan number info\n"
        help_text += "├ `/pin <pincode>` - PIN code info\n"
        help_text += "├ `/imei <number>` - IMEI info\n"
        help_text += "└ `/ip <address>` - IP address info\n\n"
        
        help_text += "**🤖 General Commands:**\n"
        help_text += "├ `/start` - Start the bot\n"
        help_text += "├ `/help` - Show this help\n"
        help_text += "├ `/hello` - Get greeting\n"
        help_text += "└ `/time` - Get current time\n\n"
        
        help_text += "**💡 Tips:**\n"
        help_text += "• Use bot menu for broadcast & settings\n"
        help_text += "• Reply to message + command for quick actions\n"
        help_text += "• All tools support direct commands"
        
        await event.respond(help_text)
    else:
        # Regular user gets help section from settings
        current_help = get_setting('user_help_text', '❓ **HELP DESK**\n\n🤖 **Bot Commands:**\n/start - Start the bot\n/hello - Get a greeting\n/time - Get current time\n\n🛠️ **Available Tools:**\n/num - Phone number lookup\n/adhar - Aadhar info\n/family - Aadhar family lookup\n/vhe - Vehicle information\n/ifsc - IFSC code details\n/pak - Pakistan number info\n/pin - PIN code lookup\n/imei - IMEI information\n/ip - IP address details\n\n📌 **Usage:**\nSelect a tool from the menu or use commands directly.\n\n💡 **Tip:**\nAll tools provide instant results in JSON format.')
        user_data = get_user(sender.id)
        formatted_help = format_text(current_help, sender, get_stats(), user_data)
        await event.respond(formatted_help)
    
    raise events.StopPropagation

@client.on(events.NewMessage(pattern='/hello'))
async def hello_handler(event):
    # Check if in removed group
    if event.is_group:
        chat = await event.get_chat()
        if not is_group_active(chat.id):
            raise events.StopPropagation

    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()

    # Check access
    if sender.id != owner_id:
        access_check = await check_user_access(sender.id)
        if not access_check['allowed']:
            if access_check['reason'] == 'banned':
                await event.respond('🚫 You are BANNED from this bot! ❌')
            elif access_check['reason'] == 'not_subscribed':
                msg = '⚠️ Please join these channels first!'
                buttons = []
                for ch in access_check['channels']:
                    ch_username = ch['username']
                    if not ch_username.startswith('@'):
                        ch_username = '@' + ch_username
                    buttons.append([Button.url(f"Join {ch['title']}", f"https://t.me/{ch['username']}")])
                await event.respond(msg, buttons=buttons)
            raise events.StopPropagation

    hello_msg = get_random_hello_message(sender.first_name or 'Friend')
    await event.respond(hello_msg)
    raise events.StopPropagation

@client.on(events.NewMessage(pattern='/time'))
async def time_handler(event):
    # Check if in removed group
    if event.is_group:
        chat = await event.get_chat()
        if not is_group_active(chat.id):
            raise events.StopPropagation

    # Isolate group/private chats: Each (chat_id, user_id) has its own state
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check 1-minute timeout
    if not await check_message_timeout(event):
        return

    sender = await event.get_sender()

    # Check access
    if sender.id != owner_id:
        access_check = await check_user_access(sender.id)
        if not access_check['allowed']:
            if access_check['reason'] == 'banned':
                await event.respond('🚫 You are BANNED from this bot! ❌')
            elif access_check['reason'] == 'not_subscribed':
                msg = '⚠️ Please join these channels first!'
                buttons = []
                for ch in access_check['channels']:
                    ch_username = ch['username']
                    if not ch_username.startswith('@'):
                        ch_username = '@' + ch_username
                    buttons.append([Button.url(f"Join {ch['title']}", f"https://t.me/{ch['username']}")])
                await event.respond(msg, buttons=buttons)
            raise events.StopPropagation

    current_time = datetime.now().strftime("%H:%M:%S")
    await event.respond(f'🕐 Abhi ka time: **{current_time}**')
    raise events.StopPropagation

@app.route('/')
def index():
    stats = get_stats()
    status = "Online" if bot_status["running"] else "Offline"
    
    active_tools = get_all_active_tools()
    # Official Groups Filter: Only show official groups in lists/tools
    from database import get_official_groups
    official_groups = get_official_groups()
    if official_groups:
        groups = official_groups
    else:
        # Fallback to all groups if no official groups defined
        groups = get_all_groups()
    channels = get_all_channels()
    
    uptime = "N/A"
    if bot_status["start_time"]:
        delta = datetime.now() - bot_status["start_time"]
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime = f"{hours}h {minutes}m {seconds}s"
    
    return render_template('index.html',
        status=status,
        total_users=stats['total_users'],
        active_users=stats['active_users'],
        banned_users=stats['banned_users'],
        total_messages=stats['total_messages'],
        active_tools=len(active_tools),
        total_tools=len(TOOL_CONFIG),
        total_groups=len(groups),
        total_channels=len(channels),
        uptime=uptime,
        owner_id=owner_id,
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

@app.route('/api/status')
def api_status():
    stats = get_stats()
    return {
        "status": "online" if bot_status["running"] else "offline",
        "total_users": stats['total_users'],
        "active_users": stats['active_users'],
        "banned_users": stats['banned_users'],
        "total_messages": stats['total_messages'],
        "uptime": str(datetime.now() - bot_status["start_time"]) if bot_status["start_time"] else "N/A"
    }

def run_flask():
    from werkzeug.serving import make_server
    import socket
    
    # Create server with SO_REUSEADDR
    # Replit needs host check bypass for the webview to work
    app.config['SERVER_NAME'] = None
    server = make_server('0.0.0.0', 5000, app, threaded=True)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.serve_forever()

async def auto_backup_loop():
    """Background task to automatically send database backup to channel"""
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            
            backup_channel = get_backup_channel()
            if not backup_channel:
                continue
            
            backup_interval = get_backup_interval()
            last_backup = get_last_backup_time()
            
            should_backup = False
            if not last_backup:
                should_backup = True
            else:
                try:
                    last_backup_dt = datetime.fromisoformat(last_backup)
                    time_diff = (datetime.now() - last_backup_dt).total_seconds() / 60
                    if time_diff >= backup_interval:
                        should_backup = True
                except:
                    should_backup = True
            
            if should_backup:
                try:
                    db_file = get_db_file()
                    if os.path.exists(db_file) and backup_channel:
                        try:
                            channel_id = backup_channel['channel_id']
                            if channel_id and channel_id > 0:  # Validate channel ID
                                backup_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                caption = f"💾 Auto Backup\n📅 {backup_time}\n📊 Database: {db_file}"
                                
                                try:
                                    await client.send_file(channel_id, db_file, caption=caption)
                                    set_last_backup_time(datetime.now().isoformat())
                                    print(f"[LOG] ✅ Auto backup sent to channel {backup_channel['username']}")
                                except Exception as send_err:
                                    # Channel might be invalid or inaccessible
                                    print(f"[LOG] ⚠️ Could not send to channel {channel_id}: {str(send_err)[:80]}")
                            else:
                                print(f"[LOG] ⚠️ Invalid backup channel ID: {channel_id}")
                        except Exception as e:
                            print(f"[LOG] ⚠️ Backup channel error: {e}")
                except Exception as e:
                    print(f"[LOG] ❌ Auto backup failed: {e}")
        except Exception as e:
            print(f"[LOG] ❌ Backup loop error: {e}")
            await asyncio.sleep(60)

def run_bot():
    bot_status["running"] = True
    bot_status["start_time"] = datetime.now()
    print("Bot started!")
    
    # Start auto backup background task
    asyncio.get_event_loop().create_task(auto_backup_loop())
    print("[LOG] 🔄 Auto backup loop started")
    
    client.run_until_disconnected()

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("Flask server started on port 5000")
    run_bot()

