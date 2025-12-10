
# Telegram Multi-Tool Bot

A feature-rich Telegram bot built with Telethon for information retrieval and user management, with an integrated web status dashboard.

## Features

### Web Status Dashboard
- Real-time bot status display (Online/Offline)
- User statistics (Total, Active, Banned)
- Message count tracking
- Tool and connection statistics
- Beautiful animated interface with floating particles
- Auto-refresh every 30 seconds
- API endpoint for status data
- Mobile responsive design

### Information Tools (9 Total)
- **Number Info** - Get details about Indian mobile numbers
- **Aadhar Info** - Look up Aadhar card information
- **Aadhar to Family** - Find family details linked to Aadhar
- **Vehicle Info** - Get Indian vehicle registration details
- **IFSC Info** - Bank IFSC code lookup
- **Pakistan Number Info** - Pakistani phone number lookup
- **Pin Code Info** - Indian postal code information
- **IMEI Info** - Mobile IMEI number lookup
- **IP Info** - IP address geolocation and details

### User Commands
All users can use these commands:
- `/start` - Start the bot and access main menu
- `/help` - View help section with all available commands
- `/hello` - Get a personalized greeting
- `/time` - Check current time

### Tool Commands (Direct Access)
Users can directly access tools via commands:
- `/num <number>` - Phone number lookup
- `/adhar <number>` - Aadhar information
- `/family <aadhar>` - Aadhar family lookup
- `/vhe <vehicle>` - Vehicle information
- `/ifsc <code>` - IFSC code details
- `/pak <number>` - Pakistan number info
- `/pin <pincode>` - PIN code lookup
- `/imei <number>` - IMEI information
- `/ip <address>` - IP address details

### Owner Commands
Bot owner has access to:
- `/ban <user_id/@username>` - Ban a user from using the bot
- `/unban <user_id/@username>` - Unban a previously banned user
- `/info <user_id/@username>` - Get detailed user information
- All user commands plus full bot management via menu

### Bot Management
- **User Management** - Ban/unban users, view user statistics, search users
- **Channel Management** - Force-subscribe channels with automatic join verification
- **Group Management** - Connect and manage Telegram groups with customizable welcome messages
- **Broadcast System** - Send messages to all users with detailed delivery stats
- **Status Dashboard** - Comprehensive bot statistics and active tools overview
- **Database Backup** - Automatic and manual database backups to Telegram channel
- **Tools Handler** - Enable/disable tools, manage multiple API endpoints per tool

### Advanced Features
- **Multi-API Support** - Each tool supports multiple API endpoints with automatic failover
- **Load Balancing** - Distributes API requests across multiple endpoints
- **Customizable Messages** - Personalize start messages, help text, about text, and welcome messages
- **Placeholder System** - Dynamic content with variables like {first_name}, {greeting}, {date}, etc.
- **Anonymous Admin Support** - Works with Telegram anonymous admin posts in groups
- **Auto-Welcome** - Sends random welcome messages to new group members (auto-deletes after 15 seconds)
- **Subscription Verification** - Ensures users join required channels before using the bot

## Requirements

- Python 3.11+
- Telegram API credentials (API ID, API Hash, Bot Token)

## Installation

1. Clone the repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables:
```bash
export API_ID="your_api_id"
export API_HASH="your_api_hash"
export BOT_TOKEN="your_bot_token"
export OWNER_ID="your_telegram_user_id"
```

4. Run the bot and web server:
```bash
python main.py
```

This will start both the Telegram bot and Flask web server on port 5000.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_ID` | Telegram API ID from my.telegram.org |
| `API_HASH` | Telegram API Hash from my.telegram.org |
| `BOT_TOKEN` | Bot token from @BotFather |
| `OWNER_ID` | Your Telegram user ID (owner permissions) |

## Project Structure

```
.
├── main.py              # Main bot logic, handlers, and Flask server
├── database.py          # SQLite database operations
├── templates/
│   └── index.html       # Web dashboard template
├── requirements.txt     # Python dependencies
├── bot_database.db      # SQLite database (created automatically)
├── README.md            # This file
└── BOT_FEATURES.md      # Detailed feature documentation
```

## Web Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Web dashboard with animated status display |
| `/api/status` | JSON API returning bot status and statistics |

## Database Tables

- **users** - User information, join dates, message counts, and ban status
- **channels** - Force-subscribe channels with titles and usernames
- **groups** - Connected Telegram groups
- **settings** - Bot configuration settings (start texts, help/about messages)
- **tools** - Tool enable/disable status
- **tool_apis** - API endpoints for each tool with automatic failover support

## Usage

### For Users
1. Send `/start` to the bot
2. Join required channels if prompted
3. Use the menu buttons or direct commands to access tools
4. Use `/help` to see all available commands
5. Check your profile with the Profile button

### For Bot Owner
1. Access owner dashboard via `/start`
2. Manage tools, users, and settings through the menu
3. Configure force-subscribe channels
4. Set up automatic database backups
5. Customize all bot messages and welcome texts
6. Add multiple API endpoints for each tool
7. Broadcast messages to all users
8. Use admin commands in groups for quick user management

### Customization Options
- **Owner Start Text** - Customize greeting shown to bot owner
- **User Start Text** - Customize greeting shown to regular users
- **Help Desk** - Edit help message with available placeholders
- **About Desk** - Edit about message with bot information
- **Group Welcome** - Set custom welcome messages for new group members

### Available Placeholders
Use these in your custom messages:
- `{greeting}` - Time-based greeting (Good Morning/Afternoon/Evening/Night)
- `{first_name}` - User's first name
- `{username}` - User's username
- `{user_id}` - User's Telegram ID
- `{total_users}` - Total registered users
- `{active_users}` - Active (non-banned) users
- `{banned_users}` - Total banned users
- `{total_messages}` - All messages sent to bot
- `{user_messages}` - Messages sent by specific user
- `{joined_date}` - User's join date
- `{date}` - Current date (DD-MM-YYYY)
- `{time}` - Current time (HH:MM:SS)
- `{datetime}` - Full date and time
- `{bot_name}` - Bot name

## Technical Features

- **Asynchronous Architecture** - Built with async/await for high performance
- **MTProto Protocol** - Uses Telethon for efficient Telegram API communication
- **SQLite Database** - Lightweight, serverless database (no setup required)
- **Flask Web Server** - Integrated status dashboard
- **aiohttp** - Async HTTP client for API calls
- **Automatic Failover** - Multiple API support with smart fallback
- **Error Handling** - Comprehensive error handling and logging
- **Group Compatibility** - Works in private chats and groups
- **Admin Detection** - Supports anonymous admin posts

## Security

- Owner-only admin controls
- User ban/unban system
- Force subscription verification
- Environment variable configuration
- No hardcoded credentials
- Group-based permission checks

## Deployment on Replit

This bot is optimized for Replit deployment:
1. Fork this Repl
2. Set environment variables in Secrets
3. Click Run button
4. Bot + Web Dashboard starts automatically on port 5000

## Credits

**Powered by ༄ᶦᶰᵈ᭄ℓєgєи∂✧kìຮຮu࿐™**
Telegram: [t.me/KissuHQ](https://t.me/KissuHQ)

## License

This project is for educational purposes.
