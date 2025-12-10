
# Telegram Multi-Tool Bot - Complete Feature Reference

## Overview
A powerful, feature-rich Telegram bot designed for information retrieval and user management. Built with modern Python technologies for maximum performance and reliability.

---

## Key Selling Points

### 1. Multi-Tool Information System (9 Tools)
| Tool | Command | Description |
|------|---------|-------------|
| Phone Number Info | `/num <number>` | Get detailed information about Indian mobile numbers |
| Aadhar Info | `/adhar <number>` | Look up Aadhar card details |
| Aadhar to Family | `/family <aadhar>` | Find family members linked to Aadhar |
| Vehicle Info | `/vhe <vehicle>` | Indian vehicle registration lookup |
| IFSC Info | `/ifsc <code>` | Bank IFSC code information |
| Pakistan Number Info | `/pak <number>` | Pakistani phone number lookup |
| Pin Code Info | `/pin <pincode>` | Indian postal code details |
| IMEI Info | `/imei <number>` | Mobile IMEI number lookup |
| IP Info | `/ip <address>` | IP address geolocation and details |

**All tools provide instant results in JSON format!**

### 2. Complete Command System

#### User Commands (Available to Everyone)
| Command | Description |
|---------|-------------|
| `/start` | Start the bot and access main menu |
| `/help` | View comprehensive help with all commands |
| `/hello` | Get a personalized greeting |
| `/time` | Check current time |
| `/num` | Phone number lookup tool |
| `/adhar` | Aadhar information tool |
| `/family` | Aadhar family lookup tool |
| `/vhe` | Vehicle information tool |
| `/ifsc` | IFSC code details tool |
| `/pak` | Pakistan number info tool |
| `/pin` | PIN code lookup tool |
| `/imei` | IMEI information tool |
| `/ip` | IP address details tool |

#### Owner Commands (Bot Owner Only)
| Command | Usage | Description |
|---------|-------|-------------|
| `/ban` | `/ban <user_id/@username>` or reply with `/ban` | Ban user from using the bot |
| `/unban` | `/unban <user_id/@username>` or reply with `/unban` | Unban previously banned user |
| `/info` | `/info <user_id/@username>` or reply with `/info` | Get detailed user information |
| `/help` | `/help` | View all owner commands and features |

**Owner commands work in both private chat and groups!**

### 3. Advanced API Management
- Support for **multiple APIs per tool**
- Automatic **failover** - if one API fails, tries next
- **Load balancing** - randomly distributes requests across APIs
- Easy add/remove APIs through bot interface
- **No coding required** to manage APIs
- Real-time API status monitoring

### 4. Complete User Management
- Track all users with join date and time
- View user statistics (messages, activity, status)
- **Ban/Unban users** with commands or menu
- **Search users** by ID or username
- Paginated user list for large databases
- Reply to user message + `/ban`, `/unban`, or `/info` for quick actions
- Works in groups with permission checks

### 5. Force Subscribe System
- Add **unlimited channels** for force-join
- Users must join all channels to use bot
- Automatic subscription verification with "Check Again" button
- Easy channel management interface
- Add channels via: ID, @username, or forward message
- Remove channels with pagination support
- View all channels with details (title, added date)

### 6. Group Management
- Connect bot to **unlimited groups**
- **Custom welcome messages** for new members
- **10+ default welcome message templates**
- Random welcome message rotation (includes custom messages)
- **Auto-delete** welcome messages after 15 seconds
- Enable/Disable groups easily
- Add groups via: ID, @username, or forward message
- Paginated group list and removal
- Track messages per group
- **Anonymous admin support** - works with hidden admins

### 7. Broadcast System
- Send messages to **all active users** at once
- Real-time broadcast progress tracking
- **Detailed statistics**:
  - ✅ Successfully sent count
  - ❌ Failed delivery count
  - 📋 Detailed report with user info
- **Placeholder support** in broadcasts:
  - Each user receives personalized message
  - Use {first_name}, {username}, {greeting}, etc.
- Export detailed report as text file
- Cancel broadcast anytime

### 8. Web Status Dashboard
- **Real-time bot status** monitoring (Online/Offline)
- Beautiful **animated interface** with floating particles
- **Comprehensive statistics**:
  - Total Users, Active Users, Banned Users
  - Total Messages sent to bot
  - Active Tools count (X/9)
  - Connected Groups count
  - Force Channels count
  - Bot Uptime tracking
- **Auto-refresh** every 30 seconds
- **Mobile responsive** design
- JSON API endpoint (`/api/status`)
- Last updated timestamp

### 9. Database Backup System
- **Automatic scheduled backups** to Telegram channel
- **Manual backup** option (backup now)
- **Database restore** from .db file
- **Configurable intervals** (set in minutes)
- Backup to any Telegram channel
- Easy channel configuration
- Track last backup time
- **Auto-restart** after restore

### 10. Customization Options

#### Customizable Messages
- **Owner Start Text** - Greeting shown to bot owner
- **User Start Text** - Greeting shown to regular users
- **Help Desk** - Help message with commands and usage
- **About Desk** - About message with bot info
- **Group Welcome** - Welcome message for new group members

#### Available Placeholders (Use in ALL custom messages)
| Placeholder | Description |
|-------------|-------------|
| `{greeting}` | Time-based greeting (Good Morning/Afternoon/Evening/Night) |
| `{first_name}` | User's first name |
| `{username}` | User's username |
| `{user_id}` | User's Telegram ID |
| `{total_users}` | Total registered users |
| `{active_users}` | Active (non-banned) users |
| `{banned_users}` | Total banned users |
| `{total_messages}` | All messages sent to bot |
| `{user_messages}` | Messages sent by specific user |
| `{joined_date}` | User's join date (DD-MM-YYYY) |
| `{date}` | Current date (DD-MM-YYYY) |
| `{time}` | Current time (HH:MM:SS) |
| `{datetime}` | Full date and time |
| `{bot_name}` | Bot name (MultiBot) |

### 11. Tools Handler Features
Each tool can be:
- ✅ **Enabled** or ❌ **Disabled** with one click
- Configured with **multiple API endpoints**
- Managed through clean interface:
  - ➕ Add API
  - ➖ Remove API
  - 📋 View All APIs
  - 📊 Check Status

**No coding required - all through bot menus!**

---

## Technical Specifications

| Feature | Specification |
|---------|---------------|
| Language | Python 3.11+ |
| Framework | Telethon (MTProto Protocol) |
| Database | SQLite (Lightweight, No Setup Required) |
| Web Server | Flask (Port 5000) |
| API Calls | aiohttp (Async HTTP Client) |
| Architecture | Async/Await for High Performance |
| Threading | Multithreaded (Bot + Web Server) |
| Error Handling | Comprehensive logging and recovery |

---

## Database Schema

### 1. users
- `user_id` (Primary Key)
- `username`
- `first_name`
- `joined` (Timestamp)
- `messages` (Counter)
- `banned` (Boolean)
- `status` (Text)

### 2. channels
- `channel_id` (Primary Key)
- `username`
- `title`
- `added_date` (Timestamp)

### 3. groups
- `group_id` (Primary Key)
- `username`
- `title`
- `added_date` (Timestamp)
- `active` (Boolean)

### 4. settings
- `key` (Primary Key)
- `value` (JSON Text)

### 5. tools
- `tool_name` (Primary Key)
- `active` (Boolean)

### 6. tool_apis
- `id` (Auto Increment)
- `tool_name`
- `url`
- `added_date` (Timestamp)

---

## Bot Menu Structure

### Owner Dashboard (`/start` as owner)
```
🛠️ Tools
├── Enable/Disable Tools
├── Add/Remove APIs
├── View API Status
└── Tool Statistics

👥 Users
├── Ban User
├── Unban User
└── User Info

📢 Broadcast
└── Send to All Users

📊 Status
├── User Statistics
├── Tool Statistics
├── Connection Statistics
└── Uptime & System Info

⚙️ Settings
├── 🛠️ Tools Handler
├── 📺 Sub-Force
├── 👥 Groups
├── 📝 Start Text
├── 💾 Backup
├── ❓ Help Desk
└── ℹ️ About Desk
```

### User Dashboard (`/start` as user)
```
🛠️ Tools
└── Access Enabled Tools

👤 Profile
├── User ID
├── Username
├── Messages Sent
├── Join Date
└── Account Status

❓ Help
└── Commands & Usage

ℹ️ About
├── Bot Information
├── User Statistics
├── Available Tools
└── Credits
```

---

## Security Features

| Feature | Description |
|---------|-------------|
| Owner-Only Admin | Only bot owner can access admin controls |
| User Ban System | Ban/unban users from using bot |
| Force Subscribe | Ensure users join channels before access |
| Environment Variables | Secure credential storage |
| Permission Checks | Verify permissions in groups |
| Anonymous Admin Support | Works with hidden admin posts |
| Group Permission Check | Admin commands work only for admins in groups |

---

## Easy Setup (4 Steps)

1. **Set Environment Variables:**
   ```bash
   API_ID="your_api_id"
   API_HASH="your_api_hash"
   BOT_TOKEN="your_bot_token"
   OWNER_ID="your_telegram_user_id"
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Bot:**
   ```bash
   python main.py
   ```

4. **Access Dashboard:**
   - Bot: Send `/start` to your bot on Telegram
   - Web: Open `http://localhost:5000` in browser

---

## File Structure

```
Project/
├── main.py              # Main bot logic + Flask server
├── database.py          # SQLite database operations
├── templates/
│   └── index.html       # Web dashboard (animated UI)
├── requirements.txt     # Python dependencies
├── bot_database.db      # SQLite database (auto-created)
├── README.md            # Setup documentation
└── BOT_FEATURES.md      # This feature reference
```

---

## Advanced Features

### 1. Multi-API Failover System
```
User Request → Try API 1 → Success ✅
                ↓ Fail
              Try API 2 → Success ✅
                ↓ Fail
              Try API 3 → Success ✅
                ↓ All Failed
              Return Error ❌
```

### 2. Smart Message Tracking
- Tracks messages **per user**
- Tracks messages **per group**
- Only counts messages from **active groups**
- Increments counter in database

### 3. Welcome Message System
```
New Member Joins → Check if group active
                    ↓ Yes
                  Select random welcome message
                    ↓
                  Send welcome (personalized)
                    ↓
                  Auto-delete after 15 seconds
```

### 4. Subscription Verification Flow
```
User uses bot → Check if banned
                 ↓ Not banned
               Check if joined required channels
                 ↓ Not joined
               Show channels + "Check Again" button
                 ↓ Joined all
               Allow bot access
```

---

## Why Choose This Bot?

| Benefit | Description |
|---------|-------------|
| ✅ **All-in-One Solution** | 9 tools + management in single bot |
| ✅ **No Coding Required** | Manage everything via bot interface |
| ✅ **100% Reliable** | Multiple API failover ensures uptime |
| ✅ **Modern UI** | Beautiful web dashboard with animations |
| ✅ **Scalable** | SQLite handles thousands of users efficiently |
| ✅ **Easy Deployment** | Works on Replit, VPS, or any Python hosting |
| ✅ **Active Monitoring** | Real-time status dashboard |
| ✅ **Backup System** | Automatic backups - never lose data |
| ✅ **Fully Customizable** | Change all texts and messages |
| ✅ **Group Compatible** | Works in groups with admin checks |
| ✅ **Command Support** | Direct commands for all tools |
| ✅ **Anonymous Admin** | Supports hidden admin posts |

---

## Perfect For:

- 📱 **Information Service Providers**
- 💼 **Telegram Bot Resellers**
- 👥 **Private Group/Channel Owners**
- 🔍 **Data Lookup Services**
- 🏢 **Business Telegram Bots**
- 🎓 **Educational Projects**
- 🌐 **API Service Integrators**

---

## Credits

**Powered by ༄ᶦᶰᵈ᭄ℓєgєи∂✧kìຮຮu࿐™**

📱 Telegram: [t.me/KissuHQ](https://t.me/KissuHQ)

---

## Support & Updates

- ✅ Clean, well-documented code
- ✅ Easy to customize and extend
- ✅ Modular architecture
- ✅ Production-ready
- ✅ Active development
- ✅ Regular updates

---

**Start building your information empire today! 🚀**
