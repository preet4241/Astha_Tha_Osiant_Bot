# 📖 Complete Command & Feature Reference

## Owner Commands

### Ban Management

#### `/ban <user_id>` 
Ban a user globally with optional reason
```
/ban 123456789
/ban 123456789 Spam and abuse
/ban @username Violating rules
```

**Response includes**:
- User ID and name
- Ban timestamp
- Ban reason (if provided)
- Confirmation of global ban

#### `/unban <user_id>`
Unban a previously banned user
```
/unban 123456789
/unban @username
```

**Note**: Clears ban reason and date

### User Information

#### `/info <user_id>`
Get detailed user information
```
/info 123456789
/info @username
```

**Shows**:
- User ID, username, name
- Total messages
- Join date and full timestamp
- Ban status (BANNED/ACTIVE)
- **Ban reason** (if banned)
- **Ban date** (if banned)
- User level/status

#### `/info` (reply)
Get info about user who sent the message
```
[Reply to a message]
/info
```

### Warning System

#### `/warn <user_id>`
Warn a user (group-specific, 3 warnings = auto-kick)
```
/warn 123456789
/warn @username
/warn 123456789 Spamming messages
```

**Behavior**:
- Warning 1: Alert sent
- Warning 2: Alert sent
- Warning 3: User auto-kicked from group
- Admin exemption: Admins can't be warned

### Group Commands

#### `/help`
View all available commands (in group or private)
```
/help
```

Shows bot capabilities and command list

## Menu Navigation

### Start Menu
Displayed when user starts bot:
- **Owner** - Access owner panel
- **User** - Access user panel
- **Help** - View help text

### Owner Panel
Top-level admin interface:

```
📊 Status     → Dashboard with stats
⚙️  Settings  → Detailed configuration
👥 Users      → User management
🛠️  Tools     → Tool management
🔔 Broadcast  → Send messages to all
```

### Owner Settings Sub-Menus

#### Bad Words Filter
```
🚫 BAD WORDS SETTINGS

📊 Total Keywords: 42
📡 Status: ✅ ON

[🔴 Turn OFF]
[➕ Add] [➖ Remove]
[📄 File]
[🔙 Back]
```

**Features**:
- Toggle ON/OFF filter
- Add new bad words
- Remove existing words
- Download current list

**Detection Method**:
1. Regex matching (word boundaries)
2. Fuzzy matching (80% confidence)
3. Admin exemption

#### Tools Management
```
🛠️ TOOLS

Select tool to configure:
- 📱 Number Info
- 🆔 Aadhar Info
- 👨‍👩‍👧‍♦️ Aadhar to Family
- 🚗 Vehicle Info
- 🏦 IFSC Info
- 🇵🇰 Pak Num Info
- 📍 Pin Code Info
- 📱 IMEI Info
- 🌐 IP Info
```

Each tool allows:
- Enable/Disable
- Add custom API
- Configure response fields
- Test with sample data

#### Broadcast Settings
```
📢 BROADCAST

Send message to all users:
- Custom placeholders
- View delivery stats
- Export report
```

**Available Placeholders**:
- `{greeting}` - Good Morning/Afternoon/Evening/Night
- `{first_name}` - User's first name
- `{username}` - User's username
- `{user_id}` - User's ID
- `{total_users}` - Total users count
- `{active_users}` - Active users count
- `{date}` - Today's date (DD-MM-YYYY)
- `{time}` - Current time (HH:MM:SS)
- `{datetime}` - Full date and time
- `{bot_name}` - Bot name

#### Backup Settings
```
💾 BACKUP SETTINGS

[🔄 Change Channel] [⏰ Set Interval] [💾 Backup Now] [🔙 Restore]
```

**Options**:
- Set backup channel (forward message from channel)
- Set backup interval in minutes
- Backup database now
- Restore from previously backed up file

#### Channel Force-Subscribe
```
📺 FORCE SUBSCRIBE

[➕ Add Channel] [➖ Remove Channel] [📄 List]
```

**Features**:
- Add required channels
- Set join limits
- Set expiry dates
- Track join counts

### User Panel
Regular user interface:

```
👤 User Panel

[🛠️  Tools]  → Use available tools
[👤 Profile]  → User information
[📋 Help]     → Help text
```

## Bad Words Filter Details

### Detection Algorithm

**Step 1: Regex Matching** (Highest Precision)
- Uses word boundaries: `\bword\b`
- Prevents false positives
- Example: "good" won't match "goodbye"

**Step 2: Fuzzy Matching** (High Recall)
- Activates for typos/variations
- Token set ratio matching
- 80% confidence threshold required
- Example: "chotyya" → "chutiya"

### When Filter Activates

**Filter is OFF**: No detection
**Filter is ON**:
1. **Admins**: Skip filter (can use any language)
2. **Regular Users**: Full detection and warnings

### Warning System
- 1st warning: Alert message (30s auto-delete)
- 2nd warning: Alert message (30s auto-delete)
- 3rd warning: User auto-kicked from group (60s message deletion)

### Logging

Bad word detections appear in logs:
```
[GREETING] Regex match: 'hello' matched in text (type: hello)
[GREETING] Fuzzy match: 'hii' matched in 'hi' with 90% confidence
```

## Greeting Detection Details

### Detection Algorithm

**Step 1: Regex Matching** (Highest Precision)
- Word boundaries
- Exact phrase matching
- Fast and reliable

**Step 2: Fuzzy Matching** (High Recall)
- Token set ratio matching
- 75% confidence threshold
- Handles typos/variations

### Supported Greetings

**Basic**:
- hello, hellow, helo (variants)
- hi, hii, hiii (variants)
- hey, heyy, hay (variants)

**Time-based**:
- good morning, gm, suprabhat
- good night, gn, shubh ratri
- good afternoon, ga, dopahar
- good evening, ge, shubh sandhya

**Question**:
- how are you, kaise ho, howdy
- how r u, hru, sup

**Social**:
- thank you, thanks, shukriya, dhanyawad
- bye, goodbye, alvida, chal phir
- (haha, lol, xd) - Laugh
- (sad, udas, stressed) - Sadness

## User Information Display

### Ban Details in Info

When user is banned:
```
🔄 Status: 🚫 BANNED
📋 Ban Reason: Spam and harassment
📅 Ban Date: 2024-12-19
```

When user is active:
```
🔄 Status: ✅ ACTIVE
```

### Info Sources

Ban reasons and dates stored from:
1. `/ban @username reason` command
2. Auto-ban (3 warnings for bad words)
3. `/info` command shows historical data

## Permissions

### Command Restrictions

| Command | Owner | Group Admin | Regular User |
|---------|-------|-------------|--------------|
| /ban | ✅ | ✅ | ❌ |
| /unban | ✅ | ❌ | ❌ |
| /info | ✅ | ✅ | ❌ |
| /warn | ✅ | ✅ | ❌ |
| /help | ✅ | ✅ | ✅ |

### Settings Access

- **Owner only**: Most settings
- **Group admin**: Limited group settings
- **Anonymous admin**: Special handling

## Error Messages

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Permission nahi hai" | Not admin | Need admin/owner status |
| "User not in database" | New user | Use `/info` to add to DB |
| "User not in group" | Not member | User must be in group |
| "Invalid format" | Wrong syntax | Check command format |
| "Database is locked" | Concurrent access | Wait and retry |

## Rate Limiting

### FloodWait Protection

- Broadcast messages: 0.3s delay between each
- Message sending: Automatic retry
- API calls: Built-in throttling

## Database Schema (Advanced)

### Users Table
```sql
user_id INTEGER PRIMARY KEY
username TEXT
first_name TEXT
joined DATETIME
messages INTEGER
banned BOOLEAN
ban_reason TEXT        -- Stores reason for ban
ban_date DATETIME      -- When ban was issued
status TEXT            -- user/admin/etc
```

### Example Ban Tracking
```
Ban issued: /ban 123456789 Spam and harassment
Stored:
  banned = 1
  ban_reason = "Spam and harassment"
  ban_date = "2024-12-19T10:30:45.123456"

When checking /info:
  Shows ban_reason and ban_date
```

## FAQ

**Q: How are bad words detected?**
A: Regex matching first (precise), then fuzzy matching (typos) at 80% confidence.

**Q: Can admins be warned?**
A: No, admins are exempt from bad word filter and warnings.

**Q: Are ban reasons saved?**
A: Yes! Use `/ban user reason` and reason is saved with timestamp.

**Q: How do I see ban reasons?**
A: Use `/info @username` or via Settings → Users → Info button.

**Q: What happens after 3 warnings?**
A: User is automatically kicked from group.

**Q: Is there a way to disable bad word filter?**
A: Yes, go to Settings → Bad Words → Turn OFF.

---

**Last Updated**: December 2024  
**Version**: 2.0
