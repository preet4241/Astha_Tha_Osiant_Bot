# -*- coding: utf-8 -*-
from telethon import TelegramClient, events, Button
import os
from datetime import datetime, timedelta
from database import (
    add_user, get_user, ban_user, unban_user, 
    get_all_users, get_stats, increment_messages,
    set_setting, get_setting, add_channel, remove_channel,
    get_all_channels, channel_exists, add_group, remove_group,
    get_all_groups, group_exists
)

api_id = int(os.getenv('API_ID', '22880380'))
api_hash = os.getenv('API_HASH', '08dae0d98b2dc8f8dc4e6a9ff97a071b')
bot_token = os.getenv('BOT_TOKEN', '8028312869:AAErsD7WmHHw11c2lL2Jdoj_DBU4bqRv_kQ')
owner_id = int(os.getenv('OWNER_ID', '0'))

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

broadcast_temp = {}
start_text_temp = {}
channel_action_temp = {}
channel_page_temp = {}
group_action_temp = {}
group_page_temp = {}

def get_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good Morning"
    elif 12 <= hour < 17:
        return "Good Afternoon"
    elif 17 <= hour < 21:
        return "Good Evening"
    else:
        return "Good Night"

def get_default_owner_text():
    return "{greeting} Boss\n\nBOT Status: Online\nUsers: {total_users} | Active: {active_users}\n\nControl Desk:"

def get_default_user_text():
    return "{greeting} {first_name}!\n\nWhat would you like to do?"

def format_text(text, sender, stats, user=None):
    current_date = datetime.now().strftime("%d-%m-%Y")
    current_time = datetime.now().strftime("%H:%M:%S")
    current_datetime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    
    user_messages = 0
    joined_date = "Unknown"
    if user:
        user_messages = user.get('messages', 0)
        joined_date = user.get('joined', 'Unknown')[:10]
    
    return text.format(
        greeting=get_greeting(),
        first_name=sender.first_name or 'User',
        username=sender.username or 'user',
        user_id=sender.id,
        total_users=stats['total_users'],
        active_users=stats['active_users'],
        banned_users=stats['banned_users'],
        total_messages=stats['total_messages'],
        date=current_date,
        time=current_time,
        datetime=current_datetime,
        user_messages=user_messages,
        joined_date=joined_date,
        bot_name='MultiBot'
    )

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    sender = await event.get_sender()
    add_user(sender.id, sender.username or 'unknown', sender.first_name or 'User')
    
    stats = get_stats()
    
    if sender.id == owner_id:
        buttons = [
            [Button.inline('Tools', b'owner_tools')],
            [Button.inline('Users', b'owner_users'), Button.inline('Broadcast', b'owner_broadcast')],
            [Button.inline('Status', b'owner_status'), Button.inline('Settings', b'owner_settings')],
            [Button.inline('Groups', b'owner_groups')],
        ]
        custom_text = get_setting('owner_start_text', get_default_owner_text())
        owner_text = format_text(custom_text, sender, stats, None)
        await event.respond(owner_text, buttons=buttons)
    else:
        buttons = [
            [Button.inline('Tools', b'user_tools')],
            [Button.inline('Profile', b'user_profile'), Button.inline('Help', b'user_help')],
            [Button.inline('About', b'user_about')],
        ]
        user_data = get_user(sender.id)
        custom_text = get_setting('user_start_text', get_default_user_text())
        user_text = format_text(custom_text, sender, stats, user_data)
        await event.respond(user_text, buttons=buttons)
    
    raise events.StopPropagation

@client.on(events.CallbackQuery)
async def callback_handler(event):
    sender = await event.get_sender()
    data = event.data
    
    if sender.id != owner_id and not data.startswith(b'user_'):
        await event.answer("Owner only!", alert=True)
        return
    
    if data == b'owner_groups':
        groups = get_all_groups()
        buttons = [
            [Button.inline('Add', b'group_add'), Button.inline('Remove', b'group_remove')],
            [Button.inline('List', b'group_list_page_1'), Button.inline('Start Text', b'group_start_text')],
            [Button.inline('Back', b'owner_back')],
        ]
        group_text = f"GROUPS\n\nConnected: {len(groups)}\n\nWhat do you want to do?"
        await event.edit(group_text, buttons=buttons)
    
    elif data == b'group_start_text':
        buttons = [
            [Button.inline('Add', b'group_start_text_add'), Button.inline('Remove', b'group_start_text_remove'), Button.inline('Default', b'group_start_text_default')],
            [Button.inline('Msgs', b'group_start_text_msgs'), Button.inline('Setting', b'group_start_text_setting')],
            [Button.inline('Back', b'owner_groups')],
        ]
        await event.edit('GROUP START TEXT\n\nManage group welcome message:', buttons=buttons)
    
    elif data == b'group_start_text_add':
        start_text_temp[sender.id] = 'group'
        buttons = [[Button.inline('Cancel', b'group_start_text')]]
        help_text = "Type new group start text:\n\nPlaceholders: {greeting}, {date}, {time}, {bot_name}"
        await event.edit(help_text, buttons=buttons)
    
    elif data == b'group_start_text_remove':
        set_setting('group_start_text', '')
        await event.edit('Group start text removed!', buttons=[[Button.inline('Back', b'group_start_text')]])
    
    elif data == b'group_start_text_default':
        set_setting('group_start_text', 'Bot added to group!')
        await event.edit('Group start text reset to default!', buttons=[[Button.inline('Back', b'group_start_text')]])
    
    elif data == b'group_start_text_msgs':
        await event.edit('Messages: Coming soon...', buttons=[[Button.inline('Back', b'group_start_text')]])
    
    elif data == b'group_start_text_setting':
        await event.edit('Settings: Coming soon...', buttons=[[Button.inline('Back', b'group_start_text')]])
    
    elif data == b'group_add':
        group_action_temp[sender.id] = 'add'
        buttons = [[Button.inline('Cancel', b'owner_groups')]]
        await event.edit("ADD GROUP\n\nChoose one method:\n1. Group ID (number)\n2. Group username (@username)\n3. Forward message from group", buttons=buttons)
    
    elif data == b'group_remove':
        groups = get_all_groups()
        if not groups:
            await event.edit('No groups to remove!', buttons=[[Button.inline('Back', b'owner_groups')]])
        else:
            group_page_temp[sender.id] = 1
            total_pages = (len(groups) + 5) // 6
            start_idx = 0
            end_idx = min(6, len(groups))
            buttons = []
            for grp in groups[start_idx:end_idx]:
                buttons.append([Button.inline(f'X {grp["username"]}', f'remove_grp_{grp["group_id"]}')]) 
            if total_pages > 1:
                buttons.append([Button.inline(f'Next (1/{total_pages})', b'group_remove_next')])
            buttons.append([Button.inline('Back', b'owner_groups')])
            await event.edit('REMOVE GROUP\n\nSelect group to remove:', buttons=buttons)
    
    elif data == b'group_remove_next':
        groups = get_all_groups()
        page = group_page_temp.get(sender.id, 1) + 1
        total_pages = (len(groups) + 5) // 6
        if page > total_pages:
            page = 1
        group_page_temp[sender.id] = page
        start_idx = (page - 1) * 6
        end_idx = min(start_idx + 6, len(groups))
        buttons = []
        for grp in groups[start_idx:end_idx]:
            buttons.append([Button.inline(f'X {grp["username"]}', f'remove_grp_{grp["group_id"]}')]) 
        if total_pages > 1:
            buttons.append([Button.inline(f'Next ({page}/{total_pages})', b'group_remove_next')])
        buttons.append([Button.inline('Back', b'owner_groups')])
        await event.edit('REMOVE GROUP\n\nSelect group to remove:', buttons=buttons)
    
    elif data == b'group_list_page_1':
        groups = get_all_groups()
        if not groups:
            await event.edit('No groups yet!', buttons=[[Button.inline('Back', b'owner_groups')]])
        else:
            group_page_temp[sender.id] = 1
            total_pages = (len(groups) + 5) // 6
            start_idx = 0
            end_idx = min(6, len(groups))
            buttons = []
            for grp in groups[start_idx:end_idx]:
                buttons.append([Button.inline(grp["title"], f'show_grp_{grp["group_id"]}')])
            if total_pages > 1:
                buttons.append([Button.inline(f'Next (1/{total_pages})', b'group_list_next')])
            buttons.append([Button.inline('Back', b'owner_groups')])
            await event.edit('GROUPS LIST', buttons=buttons)
    
    elif data == b'group_list_next':
        groups = get_all_groups()
        page = group_page_temp.get(sender.id, 1) + 1
        total_pages = (len(groups) + 5) // 6
        if page > total_pages:
            page = 1
        group_page_temp[sender.id] = page
        start_idx = (page - 1) * 6
        end_idx = min(start_idx + 6, len(groups))
        buttons = []
        for grp in groups[start_idx:end_idx]:
            buttons.append([Button.inline(grp["title"], f'show_grp_{grp["group_id"]}')])
        if total_pages > 1:
            buttons.append([Button.inline(f'Next ({page}/{total_pages})', b'group_list_next')])
        buttons.append([Button.inline('Back', b'owner_groups')])
        await event.edit('GROUPS LIST', buttons=buttons)
    
    elif data.startswith(b'remove_grp_'):
        group_id = int(data.split(b'_')[2])
        remove_group(group_id)
        groups = get_all_groups()
        if not groups:
            await event.edit('All groups removed!', buttons=[[Button.inline('Back', b'owner_groups')]])
        else:
            total_pages = (len(groups) + 5) // 6
            group_page_temp[sender.id] = 1
            start_idx = 0
            end_idx = min(6, len(groups))
            buttons = []
            for grp in groups[start_idx:end_idx]:
                buttons.append([Button.inline(f'X {grp["username"]}', f'remove_grp_{grp["group_id"]}')]) 
            if total_pages > 1:
                buttons.append([Button.inline(f'Next (1/{total_pages})', b'group_remove_next')])
            buttons.append([Button.inline('Back', b'owner_groups')])
            await event.edit('REMOVE GROUP\n\nSelect group to remove:', buttons=buttons)
    
    elif data.startswith(b'show_grp_'):
        group_id = int(data.split(b'_')[2])
        groups = get_all_groups()
        grp_info = next((g for g in groups if g['group_id'] == group_id), None)
        if grp_info:
            info_text = f"GROUP: {grp_info['title']}\nID: {grp_info['group_id']}\nUsername: @{grp_info['username']}\nAdded: {grp_info['added_date'][:10]}"
            await event.edit(info_text, buttons=[[Button.inline('Back', b'group_list_page_1')]])
    
    elif data == b'setting_start_text':
        buttons = [
            [Button.inline('Owner', b'start_text_owner'), Button.inline('User', b'start_text_user')],
            [Button.inline('Back', b'owner_settings')],
        ]
        await event.edit('START TEXT\n\nChoose which text to customize:', buttons=buttons)
    
    elif data == b'start_text_owner':
        buttons = [
            [Button.inline('Edit', b'start_text_owner_edit'), Button.inline('See', b'start_text_owner_see')],
            [Button.inline('Default', b'start_text_owner_default')],
            [Button.inline('Back', b'setting_start_text')],
        ]
        await event.edit('OWNER START TEXT\n\nWhat do you want to do?', buttons=buttons)
    
    elif data == b'start_text_user':
        buttons = [
            [Button.inline('Edit', b'start_text_user_edit'), Button.inline('See', b'start_text_user_see')],
            [Button.inline('Default', b'start_text_user_default')],
            [Button.inline('Back', b'setting_start_text')],
        ]
        await event.edit('USER START TEXT\n\nWhat do you want to do?', buttons=buttons)
    
    elif data == b'start_text_owner_edit':
        start_text_temp[sender.id] = 'owner'
        buttons = [[Button.inline('Cancel', b'start_text_owner')]]
        help_text = "Type new start text for Owner:\n\nPlaceholders: {greeting}, {date}, {time}, {total_users}, {active_users}, {bot_name}"
        await event.edit(help_text, buttons=buttons)
    
    elif data == b'start_text_user_edit':
        start_text_temp[sender.id] = 'user'
        buttons = [[Button.inline('Cancel', b'start_text_user')]]
        help_text = "Type new start text for User:\n\nPlaceholders: {greeting}, {first_name}, {username}, {date}, {user_messages}, {joined_date}"
        await event.edit(help_text, buttons=buttons)
    
    elif data == b'start_text_owner_see':
        owner_text = get_setting('owner_start_text', get_default_owner_text())
        preview = format_text(owner_text, sender, get_stats(), None)
        see_text = f"OWNER START TEXT PREVIEW:\n\n{preview}"
        await event.edit(see_text, buttons=[[Button.inline('Back', b'start_text_owner')]])
    
    elif data == b'start_text_user_see':
        user_text = get_setting('user_start_text', get_default_user_text())
        user_data = get_user(sender.id)
        preview = format_text(user_text, sender, get_stats(), user_data)
        see_text = f"USER START TEXT PREVIEW:\n\n{preview}"
        await event.edit(see_text, buttons=[[Button.inline('Back', b'start_text_user')]])
    
    elif data == b'start_text_owner_default':
        set_setting('owner_start_text', get_default_owner_text())
        await event.edit('Owner start text reset to default!\n\nOK', buttons=[[Button.inline('Back', b'start_text_owner')]])
    
    elif data == b'start_text_user_default':
        set_setting('user_start_text', get_default_user_text())
        await event.edit('User start text reset to default!\n\nOK', buttons=[[Button.inline('Back', b'start_text_user')]])
    
    elif data == b'setting_sub_force':
        channels = get_all_channels()
        buttons = [
            [Button.inline('Add', b'sub_force_add'), Button.inline('Remove', b'sub_force_remove')],
            [Button.inline('List', b'sub_force_list_page_1')],
            [Button.inline('Back', b'owner_settings')],
        ]
        sub_text = f"SUB-FORCE (Channel Subscription)\n\nActive Channels: {len(channels)}\n\nWhat do you want to do?"
        await event.edit(sub_text, buttons=buttons)
    
    elif data == b'sub_force_add':
        channel_action_temp[sender.id] = 'add'
        buttons = [[Button.inline('Cancel', b'setting_sub_force')]]
        await event.edit("ADD CHANNEL\n\nChoose one method:\n1. Channel ID (number)\n2. Channel username (@username)\n3. Forward message from channel", buttons=buttons)
    
    elif data == b'sub_force_remove':
        channels = get_all_channels()
        if not channels:
            await event.edit('No channels to remove!', buttons=[[Button.inline('Back', b'setting_sub_force')]])
        else:
            channel_page_temp[sender.id] = 1
            total_pages = (len(channels) + 5) // 6
            start_idx = 0
            end_idx = min(6, len(channels))
            buttons = []
            for ch in channels[start_idx:end_idx]:
                buttons.append([Button.inline(f'X {ch["username"]}', f'remove_ch_{ch["channel_id"]}')]) 
            if total_pages > 1:
                buttons.append([Button.inline(f'Next (1/{total_pages})', b'sub_force_remove_next')])
            buttons.append([Button.inline('Back', b'setting_sub_force')])
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
            buttons.append([Button.inline(f'X {ch["username"]}', f'remove_ch_{ch["channel_id"]}')])
        if total_pages > 1:
            buttons.append([Button.inline(f'Next ({page}/{total_pages})', b'sub_force_remove_next')])
        buttons.append([Button.inline('Back', b'setting_sub_force')])
        await event.edit('REMOVE CHANNEL\n\nSelect channel to remove:', buttons=buttons)
    
    elif data.startswith(b'remove_ch_'):
        channel_id = int(data.split(b'_')[2])
        channels = get_all_channels()
        for ch in channels:
            if ch['channel_id'] == channel_id:
                remove_channel(ch['username'])
                await event.edit(f'Channel {ch["username"]} removed!', buttons=[[Button.inline('Back', b'setting_sub_force')]])
                break
    
    elif data == b'sub_force_list_page_1' or data.startswith(b'sub_force_list_page_'):
        channels = get_all_channels()
        if not channels:
            await event.edit('No channels added yet!', buttons=[[Button.inline('Back', b'setting_sub_force')]])
        else:
            if data.startswith(b'sub_force_list_page_'):
                page = int(data.split(b'_')[3])
            else:
                page = 1
            total_pages = (len(channels) + 5) // 6
            start_idx = (page - 1) * 6
            end_idx = min(start_idx + 6, len(channels))
            
            text = f"CHANNELS LIST (Page {page}/{total_pages})\n\n"
            for i, ch in enumerate(channels[start_idx:end_idx], 1):
                added = ch['added_date'][:10] if ch['added_date'] else 'Unknown'
                text += f"{i}. @{ch['username']}\n"
                text += f"   Title: {ch['title']}\n"
                text += f"   Added: {added}\n\n"
            
            buttons = []
            if page > 1:
                buttons.append([Button.inline(f'Prev ({page}/{total_pages})', f'sub_force_list_page_{page-1}'.encode())])
            if page < total_pages:
                buttons.append([Button.inline(f'Next ({page}/{total_pages})', f'sub_force_list_page_{page+1}'.encode())])
            buttons.append([Button.inline('Back', b'setting_sub_force')])
            await event.edit(text, buttons=buttons)
    
    elif data == b'owner_settings':
        buttons = [
            [Button.inline('Start Text', b'setting_start_text')],
            [Button.inline('Sub-Force', b'setting_sub_force'), Button.inline('Groups', b'setting_groups')],
            [Button.inline('Back', b'owner_back')],
        ]
        settings_text = "BOT SETTINGS\n\nConfigure your bot:"
        await event.edit(settings_text, buttons=buttons)
    
    elif data == b'setting_groups':
        await event.edit('Group Handling: Coming soon...', buttons=[[Button.inline('Back', b'owner_settings')]])
    
    elif data == b'owner_back':
        buttons = [
            [Button.inline('Tools', b'owner_tools')],
            [Button.inline('Users', b'owner_users'), Button.inline('Broadcast', b'owner_broadcast')],
            [Button.inline('Status', b'owner_status'), Button.inline('Settings', b'owner_settings')],
        ]
        greeting = get_greeting()
        stats = get_stats()
        owner_text = f"{greeting} Boss\n\nStatus: Online\nUsers: {stats['total_users']} | Active: {stats['active_users']}\n\nControl Desk:"
        await event.edit(owner_text, buttons=buttons)
    
    elif data == b'owner_users':
        await event.edit('Users Panel (coming soon...)', buttons=[[Button.inline('Back', b'owner_back')]])
    
    elif data == b'owner_broadcast':
        buttons = [
            [Button.inline('Send', b'broadcast_send')],
            [Button.inline('Back', b'owner_back')],
        ]
        await event.edit('BROADCAST\n\nSend message to all users', buttons=buttons)
    
    elif data == b'owner_status':
        stats = get_stats()
        current_time = datetime.now().strftime("%H:%M:%S")
        status_text = f"BOT STATUS\n\nUsers: {stats['total_users']}\nActive: {stats['active_users']}\nMessages: {stats['total_messages']}\nTime: {current_time}"
        buttons = [[Button.inline('Back', b'owner_back')]]
        await event.edit(status_text, buttons=buttons)
    
    elif data == b'owner_tools':
        await event.edit('Tools (coming soon...)', buttons=[[Button.inline('Back', b'owner_back')]])
    
    elif data == b'user_tools':
        await event.edit('User Tools (coming soon...)', buttons=[[Button.inline('Back', b'user_back')]])
    
    elif data == b'user_profile':
        user = get_user(sender.id)
        if user:
            profile_text = f"Profile\n\nName: {user['first_name']}\nUsername: @{user['username']}\nMessages: {user['messages']}\nJoined: {user['joined'][:10]}"
        else:
            profile_text = "Profile not found"
        await event.edit(profile_text, buttons=[[Button.inline('Back', b'user_back')]])
    
    elif data == b'user_help':
        await event.edit('Help: Coming soon...', buttons=[[Button.inline('Back', b'user_back')]])
    
    elif data == b'user_about':
        await event.edit('About: Bot v1.0 by MultiBot', buttons=[[Button.inline('Back', b'user_back')]])
    
    elif data == b'user_back':
        buttons = [
            [Button.inline('Tools', b'user_tools')],
            [Button.inline('Profile', b'user_profile'), Button.inline('Help', b'user_help')],
            [Button.inline('About', b'user_about')],
        ]
        greeting = get_greeting()
        user_text = f"{greeting} {sender.first_name}!\n\nWhat would you like to do?"
        await event.edit(user_text, buttons=buttons)
    
    elif data == b'broadcast_send':
        broadcast_temp[sender.id] = True
        buttons = [[Button.inline('Cancel', b'owner_back')]]
        await event.edit('Type your broadcast message:', buttons=buttons)

@client.on(events.NewMessage)
async def message_handler(event):
    sender = await event.get_sender()
    
    if channel_action_temp.get(sender.id) == 'add':
        ch_name = None
        ch_title = None
        
        if event.forward and event.forward.chat:
            try:
                channel_entity = await client.get_entity(event.forward.chat)
                ch_name = channel_entity.username or str(channel_entity.id)
                ch_title = channel_entity.title
            except Exception as e:
                await event.respond(f'Error extracting channel: {str(e)}')
                return
        elif event.text:
            ch_input = event.text.strip()
            if ch_input.isdigit():
                ch_name = ch_input
                ch_title = ch_input
            elif ch_input.startswith('@'):
                ch_name = ch_input[1:]
                ch_title = ch_input[1:]
            else:
                await event.respond('Invalid format. Use: ID number, @username, or forward message.')
                return
        
        if not ch_name:
            await event.respond('Send one of: ID, @username, or forward a message.')
            return
        
        if channel_exists(ch_name):
            buttons = [[Button.inline('Back', b'setting_sub_force')]]
            await event.respond(f'Channel {ch_name} already added!', buttons=buttons)
        else:
            add_channel(ch_name, ch_title)
            channel_action_temp[sender.id] = None
            buttons = [[Button.inline('Back', b'setting_sub_force')]]
            await event.respond(f'Channel {ch_name} added successfully!', buttons=buttons)
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
                return
        
        if not grp_id or not grp_name:
            await event.respond('Send one of: ID, @username, or forward a message.')
            return
        
        if group_exists(grp_id):
            buttons = [[Button.inline('Back', b'owner_groups')]]
            await event.respond(f'Group {grp_name} already added!', buttons=buttons)
        else:
            add_group(grp_id, grp_name, grp_title)
            group_action_temp[sender.id] = None
            buttons = [[Button.inline('Back', b'owner_groups')]]
            await event.respond(f'Group {grp_name} added successfully!', buttons=buttons)
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
        elif text_type == 'group':
            set_setting('group_start_text', message)
            start_text_temp[sender.id] = None
            preview = format_text(message, sender, get_stats())
            buttons = [[Button.inline('Back', b'group_start_text')]]
            await event.respond(f"Group start text saved!\n\nPreview:\n{preview}", buttons=buttons)
        
        raise events.StopPropagation
    
    if broadcast_temp.get(sender.id):
        message = event.text
        all_users = get_all_users()
        stats = get_stats()
        
        sent_count = 0
        failed_count = 0
        
        for user_id_str, user in all_users.items():
            if user.get('banned'):
                continue
            
            try:
                await client.send_message(int(user_id_str), message)
                sent_count += 1
            except Exception:
                failed_count += 1
        
        broadcast_temp[sender.id] = False
        result_text = f"Broadcast Complete!\n\nSent: {sent_count}\nFailed: {failed_count}"
        buttons = [[Button.inline('Back', b'owner_back')]]
        await event.respond(result_text, buttons=buttons)
        raise events.StopPropagation

@client.on(events.ChatAction())
async def chat_action_handler(event):
    if event.user_joined or event.user_added:
        chat = await event.get_chat()
        try:
            if hasattr(chat, 'id') and event.action_user == (await client.get_me()).id:
                grp_id = chat.id
                grp_name = chat.username or str(chat.id)
                grp_title = chat.title or 'Unknown'
                
                if not group_exists(grp_id):
                    add_group(grp_id, grp_name, grp_title)
                    msg_text = get_setting('group_start_text', 'Bot added to group!')
                    msg_text = format_text(msg_text, await event.get_sender(), get_stats())
                    buttons = [[Button.inline('Add to List', f'quick_add_group_{grp_id}'.encode())]]
                    await event.respond(msg_text, buttons=buttons)
        except Exception as e:
            print(f"Error in auto-detect group: {e}")
    raise events.StopPropagation

@client.on(events.NewMessage(pattern='/hello'))
async def hello_handler(event):
    sender = await event.get_sender()
    await event.respond(f'Hello {sender.first_name}!')
    raise events.StopPropagation

@client.on(events.NewMessage(pattern='/time'))
async def time_handler(event):
    current_time = datetime.now().strftime("%H:%M:%S")
    await event.respond(f'Current time: {current_time}')
    raise events.StopPropagation

print("Bot started!")
client.run_until_disconnected()
