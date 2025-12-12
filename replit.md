# Telegram Multi-Tool Bot

## Overview

A Telegram bot built with Telethon (Python) that provides information lookup tools for various data types (phone numbers, Aadhar cards, vehicles, IFSC codes, etc.) along with user management features. The bot includes a Flask-based web dashboard for real-time status monitoring.

The bot serves as a multi-tool information retrieval system with 9 different lookup tools, user banning/unbanning capabilities, and broadcast messaging features for the bot owner.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Framework
- **Technology**: Telethon (async Telegram client library)
- **Rationale**: Telethon provides low-level access to Telegram's MTProto API, enabling more features than the standard Bot API
- **Pattern**: Event-driven architecture using decorators for command/callback handling

### Web Dashboard
- **Technology**: Flask web framework
- **Purpose**: Real-time status monitoring with auto-refresh
- **Features**: User statistics, bot status, animated UI with particle effects
- **Runs alongside**: The bot runs concurrently with Flask using threading

### Database Layer
- **Technology**: SQLite with direct sqlite3 module
- **Schema Tables**:
  - `users`: Stores user data (user_id, username, first_name, joined date, message count, ban status)
  - `channels`: Tracks connected Telegram channels
  - `groups`: Manages group associations with invite_link support for private groups
- **Pattern**: Function-based database operations (add_user, get_user, ban_user, etc.)

### Private Group Support
- **Invite Links**: Bot automatically fetches and stores invite links for private groups when added
- **URL Generation**: Smart URL generation that uses invite_link for private groups, public URL for public groups
- **Group ID Handling**: Proper handling of Telegram's -100 prefix for supergroup IDs

### Tool System
- **Architecture**: Configurable tool registry (TOOL_CONFIG dictionary)
- **API Integration**: External APIs called via aiohttp for async HTTP requests
- **Pattern**: Each tool has enable/disable status and configurable API endpoints

### Session Management
- **Temporary State**: In-memory dictionaries for user sessions (broadcast_temp, tool_session, etc.)
- **Bot Session**: Telethon session file stored as 'bot' in the project root

## External Dependencies

### Telegram API
- **Credentials Required**: API_ID, API_HASH, BOT_TOKEN, OWNER_ID
- **Source**: https://my.telegram.org for API credentials, @BotFather for bot token
- **Environment Variables**: All credentials stored as environment secrets

### External Lookup APIs
- Phone number info (Indian mobile numbers)
- Aadhar card information
- Vehicle registration lookup
- IFSC bank code lookup
- Pakistan phone number lookup
- PIN code information
- IMEI number lookup
- IP address geolocation

### Python Packages
- `telethon>=1.34.0`: Telegram client library
- `aiohttp>=3.9.0`: Async HTTP client for API calls
- `flask>=3.0.0`: Web dashboard framework