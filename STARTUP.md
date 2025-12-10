
# 🚀 Bot Startup & Deployment Guide

Complete guide to host and deploy this Telegram Multi-Tool Bot on different platforms.

---

## 📋 Prerequisites

Before deploying, you need:

1. **Telegram API Credentials:**
   - API ID
   - API Hash
   - Bot Token
   - Owner ID

2. **How to Get Credentials:**
   - Visit https://my.telegram.org
   - Login with your phone number
   - Go to "API Development Tools"
   - Create a new application
   - Copy your `API_ID` and `API_HASH`
   - Get Bot Token from [@BotFather](https://t.me/BotFather)
   - Get your Owner ID from [@userinfobot](https://t.me/userinfobot)

---

## 🌐 Platform 1: Replit (Recommended - Easiest)

Replit is the **easiest and fastest** way to deploy this bot with **zero configuration**.

### Step 1: Fork/Import Project
1. Go to [Replit](https://replit.com)
2. Click **"+ Create Repl"**
3. Select **"Import from GitHub"**
4. Enter this repository URL or fork it directly

### Step 2: Set Environment Variables
1. Click **"Secrets"** (🔒 icon) in the left sidebar
2. Add these secrets:
   ```
   Key: API_ID
   Value: your_api_id_here

   Key: API_HASH
   Value: your_api_hash_here

   Key: BOT_TOKEN
   Value: your_bot_token_here

   Key: OWNER_ID
   Value: your_telegram_user_id
   ```

### Step 3: Run the Bot
1. Click the **"Run"** button at the top
2. Bot will automatically install dependencies
3. Both bot and web dashboard will start on port 5000

### Step 4: Deploy to Production (Optional)
1. Click **"Release"** at the top right
2. Select **"Deploy"**
3. Choose your deployment tier (Reserved VM, Autoscale, or Static)
4. Set build command: `pip install -r requirements.txt`
5. Set run command: `python main.py`
6. Click **"Deploy your project"**
7. Your bot will be live 24/7 with a public URL!

**✅ Advantages:**
- No server setup required
- Free tier available
- Automatic package installation
- Built-in web hosting
- Easy to manage
- 24/7 uptime with Deployments

---

## 🐙 GitHub Repository Setup

Before deploying on any platform, setup your GitHub repository properly:

### Required Files for GitHub

Your repository should have these essential files:

1. **main.py** - Main bot file (already exists)
2. **database.py** - Database module (already exists)
3. **requirements.txt** - Python dependencies (already exists)
4. **Procfile** - Tells Heroku/Railway how to run the bot
5. **runtime.txt** - Specifies Python version
6. **.github/workflows/deploy.yml** - GitHub Actions for CI/CD
7. **.gitignore** - Files to ignore in Git (already exists)
8. **README.md** - Project documentation (already exists)

### Creating GitHub Repository

```bash
# Initialize git repository (if not already)
git init

# Add all files
git add .

# Create first commit
git commit -m "Initial commit: Telegram Multi-Tool Bot"

# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push to GitHub
git push -u origin main
```

### Essential File Contents

**Procfile:**
```
web: python main.py
```

**runtime.txt:**
```
python-3.11.0
```

**.github/workflows/deploy.yml:**
```yaml
name: Deploy Bot

on:
  push:
    branches:
      - main
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
```

### GitHub Secrets Setup

For secure deployment, add these secrets in GitHub repository settings:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add these secrets:
   - `API_ID` - Your Telegram API ID
   - `API_HASH` - Your Telegram API Hash
   - `BOT_TOKEN` - Your bot token
   - `OWNER_ID` - Your Telegram user ID

### .gitignore Important Entries

Make sure these are in your `.gitignore`:
```
# Bot session files
*.session
*.session-journal

# Database
*.db

# Environment variables
.env

# Python cache
__pycache__/
*.pyc
```

---

## 💻 Platform 2: VPS (Ubuntu/Debian)

Deploy on any VPS like DigitalOcean, Linode, AWS EC2, or Google Cloud.

### Step 1: Connect to VPS
```bash
ssh root@your_vps_ip
```

### Step 2: Install Python & Git
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3 python3-pip git -y

# Verify installation
python3 --version
```

### Step 3: Clone Repository
```bash
# Clone the bot
git clone https://github.com/your-username/your-bot-repo.git

# Navigate to directory
cd your-bot-repo
```

### Step 4: Install Dependencies
```bash
# Install required packages
pip3 install -r requirements.txt
```

### Step 5: Set Environment Variables
```bash
# Create .env file
nano .env
```

Add these lines:
```
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
OWNER_ID=your_telegram_user_id
```

Save and exit (Ctrl+X, then Y, then Enter)

### Step 6: Load Environment Variables
```bash
# Load variables
export $(cat .env | xargs)
```

### Step 7: Run Bot
```bash
# Start the bot
python3 main.py
```

### Step 8: Keep Bot Running 24/7 (Using Screen)
```bash
# Install screen
sudo apt install screen -y

# Create new screen session
screen -S telegram_bot

# Run bot inside screen
python3 main.py

# Detach from screen (Ctrl+A, then D)
# To reattach: screen -r telegram_bot
```

**Alternative: Using systemd service**
```bash
# Create service file
sudo nano /etc/systemd/system/telegram-bot.service
```

Add this content:
```ini
[Unit]
Description=Telegram Multi-Tool Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/your-bot-repo
Environment="API_ID=your_api_id"
Environment="API_HASH=your_api_hash"
Environment="BOT_TOKEN=your_bot_token"
Environment="OWNER_ID=your_owner_id"
ExecStart=/usr/bin/python3 /root/your-bot-repo/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot

# Check status
sudo systemctl status telegram-bot
```

**✅ Advantages:**
- Full control over server
- Better performance
- Can run multiple bots
- Custom configurations

---

## ☁️ Platform 3: Heroku (GitHub Integration)

Deploy directly from GitHub repository with automatic deployments.

### Prerequisites
- GitHub repository with all required files (Procfile, runtime.txt, etc.)
- Heroku account (free tier available)

### Method 1: Deploy via Heroku Dashboard (Recommended)

1. **Login to Heroku Dashboard**
   - Go to https://dashboard.heroku.com
   - Login with your account

2. **Create New App**
   - Click **"New"** → **"Create new app"**
   - Enter app name (e.g., `my-telegram-bot`)
   - Choose region (US or Europe)
   - Click **"Create app"**

3. **Connect GitHub Repository**
   - Go to **"Deploy"** tab
   - Select **"GitHub"** as deployment method
   - Click **"Connect to GitHub"**
   - Search for your repository name
   - Click **"Connect"**

4. **Set Environment Variables**
   - Go to **"Settings"** tab
   - Click **"Reveal Config Vars"**
   - Add these variables:
     ```
     API_ID = your_api_id
     API_HASH = your_api_hash
     BOT_TOKEN = your_bot_token
     OWNER_ID = your_owner_id
     ```

5. **Enable Automatic Deploys**
   - Go to **"Deploy"** tab
   - Scroll to **"Automatic deploys"**
   - Select branch: `main`
   - Click **"Enable Automatic Deploys"**

6. **Manual Deploy First Time**
   - Scroll to **"Manual deploy"**
   - Select branch: `main`
   - Click **"Deploy Branch"**
   - Wait for build to complete

7. **View Logs**
   - Click **"More"** → **"View logs"** to see bot running

### Method 2: Deploy via Heroku CLI

### Step 1: Install Heroku CLI
```bash
# Download and install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login to Heroku
heroku login
```

### Step 2: Create Heroku App
```bash
# Navigate to your bot directory
cd your-bot-repo

# Create Heroku app
heroku create your-bot-name

# Set Python buildpack
heroku buildpacks:set heroku/python
```

### Step 3: Set Environment Variables
```bash
heroku config:set API_ID=your_api_id
heroku config:set API_HASH=your_api_hash
heroku config:set BOT_TOKEN=your_bot_token
heroku config:set OWNER_ID=your_owner_id
```

### Step 4: Create Procfile
```bash
echo "web: python main.py" > Procfile
```

### Step 5: Deploy
```bash
# Initialize git (if not already)
git init
git add .
git commit -m "Initial commit"

# Deploy to Heroku
git push heroku main

# Check logs
heroku logs --tail
```

**✅ Advantages:**
- Free tier available (550 hours/month)
- Easy deployment
- GitHub integration
- Auto-scaling
- Automatic SSL

**⚠️ Limitations:**
- App sleeps after 30 minutes of inactivity (free tier)
- Need to ping every 30 minutes to keep alive

---

## 🚂 Platform 4: Railway (GitHub Integration)

Modern platform with excellent GitHub integration and free tier.

### Step 1: Create Railway Account
1. Go to https://railway.app
2. Sign up with GitHub account
3. Authorize Railway

### Step 2: Create New Project
1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose your repository
4. Railway will auto-detect Python

### Step 3: Configure Environment Variables
1. Click on your project
2. Go to **"Variables"** tab
3. Add these variables:
   ```
   API_ID = your_api_id
   API_HASH = your_api_hash
   BOT_TOKEN = your_bot_token
   OWNER_ID = your_owner_id
   ```

### Step 4: Configure Build Settings
1. Go to **"Settings"** tab
2. Set these values:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Watch Paths:** Leave empty for all files

### Step 5: Deploy
1. Railway will automatically deploy
2. Click **"Deployments"** to see logs
3. Your bot is now live!

### Enable GitHub Auto-Deploy
- Railway automatically deploys on every push to `main` branch
- No additional configuration needed

**✅ Advantages:**
- $5 free credit monthly
- GitHub auto-deploy
- Easy to use
- No sleep time (unlike Heroku)
- Instant deployments

---

## 🐍 Platform 5: PythonAnywhere

Great for Python applications with free hosting.

### Step 1: Create Account
1. Go to [PythonAnywhere](https://www.pythonanywhere.com)
2. Sign up for free account
3. Verify your email

### Step 2: Open Bash Console
1. Go to **"Consoles"** tab
2. Start a new **"Bash"** console

### Step 3: Clone Repository
```bash
# Clone your bot
git clone https://github.com/your-username/your-bot-repo.git

# Navigate to directory
cd your-bot-repo
```

### Step 4: Install Dependencies
```bash
# Install packages
pip3 install --user -r requirements.txt
```

### Step 5: Set Environment Variables
```bash
# Edit .bashrc
nano ~/.bashrc
```

Add these lines at the end:
```bash
export API_ID="your_api_id"
export API_HASH="your_api_hash"
export BOT_TOKEN="your_bot_token"
export OWNER_ID="your_owner_id"
```

Save and reload:
```bash
source ~/.bashrc
```

### Step 6: Create Always-On Task
1. Go to **"Tasks"** tab
2. Click **"Create a new scheduled task"**
3. Set command: `/home/yourusername/your-bot-repo/main.py`
4. Set frequency: **Daily**
5. Click **"Create"**

**Alternative: Keep bot running in console**
```bash
# Run in background
nohup python3 main.py &

# Check if running
ps aux | grep main.py
```

**✅ Advantages:**
- Free tier with always-on tasks
- Easy Python setup
- No credit card required
- Good for small bots

---

## 🔧 Post-Deployment Setup

After deploying on any platform:

### 1. Test Bot
- Send `/start` to your bot on Telegram
- Check if it responds correctly
- Test all tools

### 2. Access Web Dashboard
- Visit your deployment URL (e.g., `https://your-app.replit.app`)
- Check bot statistics
- Verify auto-refresh works

### 3. Configure Bot Settings
- Add force-subscribe channels
- Connect Telegram groups
- Set up automatic backups
- Customize welcome messages
- Add API endpoints for tools

### 4. Monitor Bot
- Check web dashboard regularly
- Monitor logs for errors
- Track user statistics

---

## 🛠️ Common Issues & Solutions

### Issue 1: Bot not responding
**Solution:**
- Check if bot is running
- Verify environment variables are set correctly
- Check Telegram API credentials
- Review logs for errors

### Issue 2: Web dashboard not loading
**Solution:**
- Ensure port 5000 is accessible
- Check if Flask server started
- Verify deployment URL is correct

### Issue 3: Database errors
**Solution:**
- Check if `bot_database.db` file exists
- Verify write permissions
- Delete and let bot recreate database

### Issue 4: API errors
**Solution:**
- Add multiple API endpoints per tool
- Check API URLs are correct
- Verify API placeholder format

---

## 📊 Monitoring & Maintenance

### Check Bot Status
```bash
# View running processes
ps aux | grep main.py

# Check logs (systemd)
sudo journalctl -u telegram-bot -f

# Check logs (screen)
screen -r telegram_bot
```

### Update Bot
```bash
# Pull latest changes
git pull origin main

# Restart bot
sudo systemctl restart telegram-bot
# OR
screen -r telegram_bot
# Ctrl+C to stop, then python3 main.py
```

### Backup Database
- Use built-in backup feature in bot settings
- Or manually copy `bot_database.db` file
- Schedule automatic backups to Telegram channel

---

## 🎯 Recommended Platform Comparison

| Feature | Replit | VPS | Heroku | Railway | PythonAnywhere |
|---------|--------|-----|--------|---------|----------------|
| **Setup Time** | 5 minutes | 30 minutes | 15 minutes | 10 minutes | 20 minutes |
| **Difficulty** | ⭐ Easy | ⭐⭐⭐ Medium | ⭐⭐ Easy | ⭐ Easy | ⭐⭐ Easy |
| **Free Tier** | ✅ Yes | ❌ No | ✅ Limited | ✅ Yes | ✅ Yes |
| **24/7 Uptime** | ✅ Paid | ✅ Yes | ⭐ Sleeps | ✅ Yes | ⭐ Limited |
| **GitHub Deploy** | ✅ Yes | ❌ Manual | ✅ Yes | ✅ Yes | ❌ Manual |
| **Auto Deploy** | ✅ Yes | ❌ Manual | ✅ Yes | ✅ Yes | ❌ Manual |
| **Web Dashboard** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Best For** | Beginners | Advanced | Startups | Developers | Python Apps |

---

## 💡 Pro Tips

1. **Use Replit for quick testing** - Deploy in 5 minutes
2. **Use VPS for production** - Best performance and control
3. **Set up monitoring** - Track bot uptime and errors
4. **Enable auto-backups** - Never lose your data
5. **Add multiple API endpoints** - Ensure high availability
6. **Monitor web dashboard** - Track user activity

---

## 🆘 Support

Having issues? Check:
1. Environment variables are set correctly
2. Bot token is valid
3. Python version is 3.11+
4. All dependencies installed
5. Ports are accessible (5000)

**Contact:** [t.me/KissuHQ](https://t.me/KissuHQ)

---

**Powered by ༄ᶦᶰᵈ᭄ℓєgєи∂✧kìຮຮu࿐™**

Start your bot empire today! 🚀
