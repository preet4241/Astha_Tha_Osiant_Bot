# 🤖 Telegram Bot - Complete Guide

A feature-rich Telegram bot with advanced user management, tools integration, broadcasting, and group management capabilities.

## 🎯 Key Features

### 👥 User Management
- **Ban System**: Global ban (GBAN) with reasons and timestamps
- **User Tracking**: Track all users with message counts and join dates
- **Ban Reasons**: Every ban is logged with reason and date
- **Quick Info**: View detailed user information anytime

### 🛠️ Tools Integration
- **9 Tools Available**:
  - 📱 Number Info - Get number details
  - 🆔 Aadhar Info - Aadhar number verification
  - 👨‍👩‍👧‍👦 Aadhar to Family - Get family details from Aadhar
  - 🚗 Vehicle Info - Vehicle registration details
  - 🏦 IFSC Info - Bank IFSC code lookup
  - 🇵🇰 Pak Num Info - Pakistani number info
  - 📍 Pin Code Info - Postal code details
  - 📱 IMEI Info - IMEI number lookup
  - 🌐 IP Info - IP address information

### 📢 Broadcasting
- Send messages to all users at once
- Custom placeholders support
- FloodWait protection (0.3s delays)
- Detailed delivery statistics

### 🚫 Content Moderation
- **Bad Word Filter** with ON/OFF toggle
- **Dual Detection**: Regex + Fuzzywuzzy matching
- Automatic warning system (3 warnings = kick)
- Admin exemption from filter
- 80% fuzzy confidence threshold for typo detection

### 💬 Smart Responses
- **Greeting Detection**: Regex + Fuzzy matching
- Responds to: Hello, Hi, Hey, Good Morning/Night/Evening/Afternoon
- Automatic welcome messages for new members
- "How are you", "Thank you", "Bye", emotional responses

### 💾 Data Management
- Auto-backup to Telegram channel
- Database restore capability
- Scheduled backups (configurable interval)
- Full database export

### 👥 Group Management
- Auto-group tracking
- Member welcome messages
- Warning system per group
- Ban management per group
- Admin permission verification

## 📊 User Info Display

When checking user information, you'll see:
```
📋 USER KI DETAILS 👤

🆔 ID: 123456789
📛 Username: @username
📝 Naam: John Doe
💬 Total Messages: 145
📅 Join Date: 2024-01-15
⏰ Full Date: 2024-01-15T10:30:45.123456
🔄 Status: 🚫 BANNED
📋 Ban Reason: Spam and abuse
📅 Ban Date: 2024-12-19
📊 User Level: user
```

## 🔧 Admin Commands

### Ban Commands
- `/ban <user_id>` - Global ban a user
- `/ban @username` - Ban by username
- `/ban <user_id> reason here` - Ban with reason

### User Management
- `/unban <user_id>` - Unban a user
- `/info <user_id>` - Get user details
- `/info @username` - Get info by username
- `/info` (reply to message) - Get info about message sender

### Group Commands
- `/warn <user_id>` - Warn user (3 warnings = auto-kick)
- `/warn @username` - Warn by username
- `/help` - View all commands

## 🎛️ Settings Panel

Access via bot start menu:

### Bad Words Filter
- **Toggle ON/OFF**: Stop/Start bad word detection
- **Add Words**: Add new bad words to filter
- **Remove Words**: Delete words from filter
- **Download List**: Export current bad words list

### Tools Management
- Enable/Disable each of 9 tools
- Configure custom APIs
- Set response field mappings

### Broadcasting
- Send messages to all users
- Use placeholders for personalization
- View delivery statistics

### Backup Settings
- Set backup channel
- Configure backup interval
- Manual backup/restore
- View last backup time

## 📝 Ban Reason System

The bot automatically saves:
- **Ban Reason**: Why the user was banned
- **Ban Date**: When the ban occurred
- **Ban Status**: Active/Inactive

This information is visible in:
1. **User Info Command**: `/info @username`
2. **User Info Button**: Settings → Users → Info
3. **Database**: Stored in `bot_database.db`

## 🔐 Admin Requirements

Most commands require:
- Bot owner (via config)
- Group owner/admin status
- Anonymous admin detection

## 🌍 Supported Languages

- English
- Hindi/Hinglish
- Multilingual user support

## 📦 Dependencies

```
telethon>=1.34.0
aiohttp>=3.9.0
flask>=3.0.0
fuzzywuzzy>=0.18.0
python-Levenshtein>=0.21.0
```

## 🚀 Performance Features

- Database connection pooling (thread-safe)
- Async message handling
- Automatic message cleanup
- FloodWait protection
- Efficient caching

## 📧 Support

For issues or feature requests, contact the bot owner.

---

**Bot Version**: 2.0  
**Last Updated**: December 2024
