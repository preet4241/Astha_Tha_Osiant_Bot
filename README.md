# Telegram Bot (Telethon)

## Overview
Ye ek advanced Telegram bot hai jo Telethon library use karta hai with Owner/User panel feature.

## Features
### User Features
- `/start` - User panel dekho
- `/hello` - Bot hello bolega
- `/time` - Current date aur time
- `/help` - User commands
- Echo feature - Private messages ko repeat karta hai

### Owner Features
- `/start` - Owner admin panel
- `/broadcast` - Sab users ko message bhejo
- `/stats` - Bot statistics
- `/users` - Active users list
- Owner panel se buttons use karke options access karo

## Admin Panel
Bot mein 2 panels hain:
1. **Owner Panel** - Admin features ke liye (Owner ID match karne par)
2. **User Panel** - Regular users ke liye

## Configuration
Bot chalane ke liye environment variables set karo:
- `OWNER_ID` - Owner ka Telegram User ID (jaisa /start karoge to user ID dekh jao)
- `API_ID` - my.telegram.org se
- `API_HASH` - my.telegram.org se
- `BOT_TOKEN` - @BotFather se

## How to Find Owner ID
Bot ko message karo aur code main:
```python
print(sender.id)
```
Aapka ID console mein dikhega.

## File Structure
- `bot.py` - Main bot code with owner/user panels

## Recent Changes
- 2025-12-02: Owner/User panel feature added with inline buttons
- 2025-12-02: Initial bot created with basic commands
