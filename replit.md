# Telegram Multi-Tool Bot

## Overview
A Telegram bot with multiple information lookup tools and a Flask-based web dashboard. The bot provides various lookup services (phone numbers, Aadhar info, vehicle info, etc.) and features user management, channel subscriptions, and group tools.

## Architecture
- **Language**: Python 3.11
- **Telegram Library**: Telethon
- **Web Framework**: Flask
- **Database**: SQLite (local file `bot_database.db`)
- **Port**: 5000 (Flask dashboard)

## Project Structure
- `main.py` - Main bot application with Telegram handlers and Flask routes
- `database.py` - SQLite database operations for users, channels, groups, settings
- `messages.py` - Message templates and greeting functions
- `kick_out.py` - Bad words filtering and moderation
- `bad_words.json` - List of filtered words
- `templates/index.html` - Web dashboard template

## Required Environment Variables
- `API_ID` - Telegram API ID (from my.telegram.org)
- `API_HASH` - Telegram API Hash (from my.telegram.org)
- `BOT_TOKEN` - Bot token from @BotFather
- `OWNER_ID` - Telegram user ID of the bot owner

## Running
The bot runs both the Telegram client and Flask server:
- Flask serves on `0.0.0.0:5000` for the status dashboard
- Telegram bot runs in the main thread

## Features
- Multiple information lookup tools (configurable via API)
- User ban/unban management
- Force subscribe to channels
- Group tools with admin controls
- Auto database backup to channel
- Web dashboard showing bot status and statistics

## Recent Changes
- 2025-12-25: Initial Replit setup with Python 3.11 and dependencies
