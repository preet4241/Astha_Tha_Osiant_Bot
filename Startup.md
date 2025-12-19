# 🚀 Bot Startup & Setup Guide

## Initial Setup

### 1. Configure Credentials

Create a `config.py` file with:

```python
# Telegram API Credentials
API_ID = "your_api_id"
API_HASH = "your_api_hash"
BOT_TOKEN = "your_bot_token"

# Owner ID
OWNER_ID = your_user_id  # Get from /info in any Telegram chat
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Requirements include:
- `telethon` - Telegram client library
- `aiohttp` - Async HTTP client
- `flask` - Web framework
- `fuzzywuzzy` - Fuzzy string matching
- `python-Levenshtein` - Levenshtein distance

### 3. Start the Bot

```bash
python main.py
```

You should see:
```
Flask server started on port 5000
Bot started!
[LOG] 🔄 Auto backup loop started
```

## First-Time Configuration

After starting, do the following:

### Step 1: Set Bad Words Filter
- Open bot in Telegram
- Go to Menu → Settings → Bad Words
- Add common bad words or use defaults
- Toggle ON/OFF as needed

### Step 2: Configure Tools (Optional)
- Menu → Owner Panel → Tools
- Select which tools to enable
- Add custom API endpoints if needed

### Step 3: Set Backup Channel (Optional)
- Menu → Settings → Backup
- Forward a message from your backup channel
- Set backup interval (recommend 1440 minutes = 24 hours)

### Step 4: Add Groups
- Add bot to your Telegram groups
- Bot auto-registers groups in database
- Configure group settings as needed

## Database Structure

The bot creates `bot_database.db` with tables:

### Users Table
```
user_id (PRIMARY KEY)
username
first_name
joined (timestamp)
messages (count)
banned (0/1)
status (user level)
ban_reason (TEXT - why they were banned)
ban_date (TEXT - when they were banned)
```

### Groups Table
```
group_id (PRIMARY KEY)
group_username
group_title
added_date
is_active (0/1)
invite_link
```

### Other Tables
- `channels` - Force-subscribe channels
- `tools` - Tool enable/disable status
- `tool_apis` - Custom API configurations
- `settings` - Bot settings (backup, messages, etc.)
- `group_warnings` - User warnings per group

## Automatic Features

### Auto-Backup Loop
- Runs every N minutes (configured in settings)
- Exports database to backup channel
- Timestamp tracking for all backups

### Database Migration
- Auto-adds missing columns on startup
- Maintains backward compatibility
- No data loss during updates

### Thread Safety
- All database connections use `check_same_thread=False`
- Safe for concurrent message handling
- No database locks

## Environment Variables

Optional - can be set in deployment:

```bash
# For production deployment
DATABASE_URL=sqlite:///bot_database.db
BOT_TOKEN=your_token
```

## Restart & Recovery

### Safe Restart
```bash
# Stop current process (Ctrl+C)
# Start again
python main.py
```

Database state is preserved automatically.

### Full Database Reset
If needed, backup then delete `bot_database.db`:
```bash
# Bot will recreate with defaults
rm bot_database.db
python main.py
```

### Restore from Backup
1. Menu → Settings → Backup
2. Click "Backup Now"
3. Upload previously saved `.db` file
4. Bot will restart with restored data

## Troubleshooting

### Bot doesn't start
- Check `config.py` credentials
- Verify Python 3.8+
- Check internet connection
- Review logs for errors

### Database is locked
- Wait 30 seconds
- Check no other instances running
- Restart bot

### Messages not sending
- Verify bot permissions in group
- Check rate limiting (FloodWait)
- Ensure sufficient privileges

### Bad words not detecting
- Check filter is ON (Settings → Bad Words)
- Verify words added to list
- Check logs for detection logs

## Performance Tuning

### For Large Groups
1. Disable unnecessary tools
2. Set reasonable backup intervals
3. Monitor database size
4. Archive old backups

### For Multiple Groups
1. Use efficient queries
2. Enable caching where possible
3. Monitor memory usage
4. Regular database maintenance

## Security Best Practices

1. **Never share config.py** - Contains sensitive tokens
2. **Backup regularly** - Keep backup channel active
3. **Monitor permissions** - Review admin access
4. **Update dependencies** - Keep libraries current
5. **Rotate tokens** - If compromised, create new token

## Useful Logs

Check console output for important events:

```
[LOG] 🤖 Bot added to new group 'Group Name' - Auto-added to database
[LOG] 🚫 Database is locked
[LOG] ✅ Broadcast complete: 150 sent, 5 failed
[GREETING] Regex match: 'hello' matched in 'hello' (type: hello)
```

## Next Steps

1. Read `Reference.md` for command details
2. Configure your first tool API
3. Set up backup channel
4. Test commands in a private group
5. Monitor logs regularly

---

**For Help**: Check `/help` command in bot or review Reference.md
