# 🕌 Islamic Prayer Times Telegram Bot

<div align="center">

![Version](https://img.shields.io/badge/version-2.0.0-brightgreen)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-production--ready-success)

**Smart Multi-Group Telegram Bot for Prayer Times • Azan Notifications • Hadiths**

[Features](#-features) • [Architecture](#-architecture) • [Installation](#-installation) • [Usage](#-usage) • [Contributing](#-contributing)

</div>

---

## 📞 Quick Links

- 📊 **[📋 Changelog](CHANGELOG_EN.md)** - All changes from v1.0.2 → v2.0.0
- 🏗️ **[📐 Architecture](ARCHITECTURE_EN.md)** - Complete architecture details
- 🤝 **[🚀 Contributing](CONTRIBUTING_EN.md)** - Comprehensive contributing guide
- 📋 **[📅 Future Roadmap](TO-DO_EN.md)** - What's coming in v2.1.0+
- 📦 **[🏷️ Version Info](VERSION_EN.md)** - v2.0.0 Production Ready
- 📂 **[🔗 All Documentation](README_LINKS.md)** - Links hub for all files
- 🌐 **[🌍 Arabic Docs](README.md)** - Documentation in Arabic

---



A comprehensive Islamic Telegram bot for groups providing:

- 🕐 **Accurate Prayer Times** for 18+ global cities
- 🔔 **Automatic Azan Notifications** at exact times
- 📚 **Smart Hadith System** with 493 diverse categories
- 🏆 **Prayer Tracking & Points System** with leaderboards
- ⚙️ **Customizable Settings** with multiple calculation methods
- 🌍 **Local Timezone Support** for each group
- 🔄 **High Performance** with multi-threaded processing

---

## ✨ Key Features

### 🕐 Accurate Prayer Times
- Fetch prayer times from [Aladhan API](https://aladhan.com)
- Support for 8 different calculation methods (ISNA, Muslim World League, Umm Al-Qura, etc.)
- 18 pre-configured cities (Riyadh, Makkah, Cairo, London, New York, etc.)
- Automatic Hijri date display

### 🔔 Smart Azan Notifications
- Timely notifications for each prayer (Fajr, Dhuhr, Asr, Maghrib, Isha)
- **"I Prayed" button** for tracking prayers and earning points
- Automatic duplicate prevention per day
- Intelligent error handling (if bot is kicked from group)

### 📚 Smart Hadith System v2.0.0
- **493 hadith categories** from [HadeethEnc.com](https://hadeethenc.com) API
- Time-based category selection (morning, midday, afternoon, evening, night)
- **Cooldown system** to prevent spam
- **Daily limit** (maximum 5 hadiths per day)
- Smart database caching
- Local fallback (offline support when API fails)

### 🏆 Engagement & Points System
- Prayer tracking with points (+10 per prayer)
- Leaderboards (`/top`)
- User activity tracking

### ⚙️ Group Management
- Admin-only commands
- `/setup` - First-time group setup
- `/setgroupcity` - Change city
- `/setcalculationmethod` - Change calculation method
- `/groupstatus` - View current settings and prayer times

### 🛡️ Security & Reliability
- **Thread-safe database** with connection pooling
- **WAL mode** for concurrent read/write operations
- **Context managers** ensuring connection cleanup
- **Automatic log rotation** preventing disk overflow
- **Exponential backoff** for retry mechanisms
- **Graceful shutdown** on bot termination

---

## 🏗️ Architecture

### Main Components

```
📦 Islamic Prayer Times Bot v2.0.0
├── 🤖 bot.py                      # Main entry point
├── 🎮 bot_handlers.py              # Telegram command handlers
├── ⚙️ config.py                   # Centralized configuration
├── 🗄️ database.py                 # Database operations
├── 📖 hadith_system.py            # Hadith system
├── 🧠 smart_hadith_engine.py      # Smart hadith selection engine
├── ⏰ scheduler_service.py         # Notification scheduling (APScheduler)
├── 🕌 prayer_api.py               # Aladhan API integration
├── 📢 notification_service.py      # Notification sending
├── 🔧 utils.py                    # Utility functions
├── 📝 logger_config.py            # Logging system
├── 🗂️ database_schema.sql          # Database schema
├── 📋 categories_list.txt          # 493 hadith categories
├── 📥 init_categories.py           # Initialize categories
├── 🔄 update_database.py           # Migration scripts
├── 🔒 fix_columns.py              # Fix database columns
├── 📐 fix_tables.py               # Fix database tables
└── 💾 prefetch_service.py         # Prefetch service (currently disabled)
```

### Data Flow

```
┌─────────────────┐
│   User Input   │
│  (Telegram)   │
└───────┬───────┘
        │
        ▼
┌─────────────────┐
│  Bot Handlers  │◄───┐
└───────┬───────┘    │
        │             │
        ▼             │
┌─────────────────┐    │
│   Database     │    │
│  (SQLite WAL)  │    │
└───────┬───────┘    │
        │             │
        ▼             │
┌─────────────────┐    │
│   Scheduler    │    │
│  (APScheduler) │────┘
└───────┬───────┘
        │
        ▼
┌─────────────────┐
│  External APIs │
│  (Aladhan/    │
│   HadeethEnc) │
└───────────────┘
```

---

## 🗄️ Database

### Main Tables

| Table | Purpose |
|-------|---------|
| `users` | User information and points |
| `groups` | Group settings |
| `prayer_times_per_group` | Daily prayer times |
| `azan_sent_log` | Azan notifications sent (duplicate prevention) |
| `content_sent_log` | Content sent tracking |
| `prayer_logs` | User prayer records |
| `settings` | System settings |
| `categories_index` | 493 hadith category index |
| `hadith_cache` | Hadith caching system |
| `hadith_send_log` | Hadith send tracking (cooldown) |

---

## 🤖 How to Use the Bot (No Self-Hosting Required)

This bot is already hosted on a private server, you can use it directly in your groups and channels!

### 🔗 Bot Links

- 🤖 **Bot Link**: [@Uislamic_bot](https://t.me/Uislamic_bot)
- 💬 **Developer Contact**: [@A245F](https://t.me/A245F)
- 📂 **Official Repository**: [GitHub Repository](https://github.com/muslim-kh09/Islamic-Prayer-Times-Bot)

### 📋 Adding Bot to a Group or Channel

#### For Groups:

1. Open the Telegram group you want to add the bot to
2. Go to Group Settings
3. Select "Administrators"
4. Click "Add Administrator"
5. Search for **@Uislamic_bot** and select it
6. Grant the bot the following admin permissions:
   - ✅ Send Messages
   - ✅ Send Media
   - ✅ Invite Users
7. Click "Done" or "Save"
8. After adding the bot, type `/setup` in the group
9. Select city and calculation method from the lists

#### For Channels:

1. Open the channel you want to add the bot to
2. Go to Channel Settings
3. Select "Administrators"
4. Click "Add Administrator"
5. Search for **@Uislamic_bot** and select it
6. Grant the bot the following admin permissions:
   - ✅ Send Messages
   - ✅ Edit Messages of Channel
7. Click "Done" or "Save"

### 📌 Important Notes

- ✅ The bot **must be an admin** in the group/channel to work properly
- ✅ If the bot is kicked from a group, it will automatically stop sending notifications to that group
- ✅ You can use the bot in unlimited groups and channels
- ✅ Notifications are sent automatically at prayer times for each group
- ✅ Each group has independent settings (city, calculation method, etc.)

---

## 📞 Support & Contact

- 💬 **Developer Telegram**: [@A245F](https://t.me/A245F)
- 🤖 **Bot Link**: [@Uislamic_bot](https://t.me/Uislamic_bot)
- 📂 **Official Repository**: [GitHub Repository](https://github.com/muslim-kh09/Islamic-Prayer-Times-Bot)
- 🐛 **Report issues**: [GitHub Issues](https://github.com/muslim-kh09/Islamic-Prayer-Times-Bot/issues)

---

## 👨‍💻 For Developers (Self-Hosting)

If you want to host your own instance of the bot, you can follow the installation instructions below.

---

### Requirements

```bash
Python 3.8 or higher
Telegram Bot Token (from @BotFather)
```

### 1️⃣ Clone the Project

```bash
git clone https://github.com/muslim-kh09/Islamic-Prayer-Times-Bot.git
cd Islamic-Prayer-Times-Bot
```

### 2️⃣ Create Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt:**

```txt
pyTelegramBotAPI==4.14.0
requests==2.31.0
apscheduler==3.10.4
pytz==2023.3
```

### 4️⃣ Create Environment File

```bash
cp .env.example .env
```

**Example .env:**

```bash
BOT_TOKEN=your_bot_token_here
DATABASE_PATH=prayer_bot.db
ENV=development  # or production
```

### 5️⃣ Initialize Database

```bash
python -c "from database import initialize_database; initialize_database()"
```

### 6️⃣ Load Categories (493 categories)

```bash
python init_categories.py
```

### 7️⃣ Run the Bot

```bash
python bot.py
```

---

## 📖 Usage

### General User Commands

| Command | Description |
|---------|-------------|
| `/start` | Start using the bot |
| `/help` | Show help message |
| `/hadith` | Random hadith |
| `/rules` | Bot rules |

### Admin Commands (Groups Only)

| Command | Description |
|---------|-------------|
| `/setup` | First-time group setup |
| `/setgroupcity` | Change city |
| `/setcalculationmethod` | Change prayer calculation method |
| `/groupstatus` | View current settings |
| `/status` | System status |

### Tracking Commands

| Command | Description |
|---------|-------------|
| `/prayed` | Log current prayer |
| `/top` | Leaderboard |

### Example: Setting Up a New Group

```
1. Add bot to group
2. Type /setup
3. Select city from list (Riyadh, Makkah, Cairo, etc.)
4. Select calculation method (ISNA is default)
5. Done! 🎉
```

---

## ⚙️ Configuration

### Available Prayer Calculation Methods

| ID | Method | Description |
|----|---------|-------------|
| 0 | Ithna Ashari | Jafari / Shia Ithna Ashari |
| 1 | University of Islamic Sciences, Karachi | University of Islamic Sciences, Karachi |
| 2 | ISNA | **Default** |
| 3 | Muslim World League | Muslim World League |
| 4 | Umm Al-Qura University, Makkah | Umm Al-Qura University, Makkah |
| 5 | Egyptian General Authority of Survey | Egyptian General Authority of Survey |
| 7 | Institute of Geophysics, University of Tehran | Institute of Geophysics, University of Tehran |
| 8 | Gulf Region | Gulf Region |
| 9 | Kuwait | Kuwait |
| 10 | Qatar | Qatar |
| 11 | Majlis Ugama Islam Singapura, Singapore | Majlis Ugama Islam Singapura, Singapore |
| 12 | Union Organization islamic de France | Union Organization islamic de France |
| 13 | Diyanet İşleri Başkanlığı, Turkey | Diyanet İşleri Başkanlığı, Turkey |
| 14 | Spiritual Administration of Muslims of Russia | Spiritual Administration of Muslims of Russia |

### Supported Cities

- 🇸🇦 **Saudi Arabia**: Riyadh, Makkah, Madinah
- 🇪🇬 **Egypt**: Cairo
- 🇩🇿 **Algeria**: Algiers
- 🇲🇦 **Morocco**: Rabat
- 🇹🇳 **Tunisia**: Tunis
- 🇯🇴 **Jordan**: Amman
- 🇱🇧 **Lebanon**: Beirut
- 🇸🇾 **Syria**: Damascus
- 🇮🇶 **Iraq**: Baghdad
- 🇰🇼 **Kuwait**: Kuwait City
- 🇶🇦 **Qatar**: Doha
- 🇦🇪 **UAE**: Abu Dhabi, Dubai
- 🇷🇺 **Russia**: Moscow
- 🇬🇧 **UK**: London
- 🇺🇸 **USA**: New York

### Logging Configuration

**Development Mode:**
```bash
ENV=development
```
- Everything logged to `bot_debug.log`
- Console shows INFO and above

**Production Mode:**
```bash
ENV=production
```
- Only WARNING and ERROR logged to file
- Console shows ERROR only
- Reduced I/O consumption

---

## 🐛 Troubleshooting

### Problem: Bot Not Sending Azan Notifications

**Solutions:**
1. Check if notifications are enabled: `/groupstatus`
2. Verify group is set up: `/setup`
3. Verify bot permissions (must be admin)
4. Check `bot_debug.log` for errors

### Problem: Database Errors

**Solutions:**
```bash
# Fix columns
python fix_columns.py

# Fix tables
python fix_tables.py

# Update database
python update_database.py
```

### Problem: Hadiths Not Being Sent

**Solutions:**
1. Verify HadeethEnc API connectivity
2. Check categories are loaded: `python init_categories.py`
3. Check `bot_debug.log` for errors

### Problem: Incorrect Prayer Times

**Solutions:**
1. Verify correct city
2. Verify appropriate calculation method for your region
3. Verify timezone settings

---

## 📈 Performance Tips

### 1️⃣ Reduce Memory Usage

The system uses:
- **Thread-local connection pooling** (one connection per thread)
- **WAL mode** for concurrent read/write
- **In-memory hadith cache** limited to 2 per category

### 2️⃣ Improve API Response Time

The system uses:
- **Exponential backoff** for retries
- **Cache TTL** (24 hours for prayers, 24 hours for hadiths)
- **Cooldown tracking** to prevent duplicate requests

### 3️⃣ Reduce I/O Consumption

The system uses:
- **Automatic log rotation** (10MB files)
- **Production logging mode** (WARNING+ only)
- **Context managers** ensuring connection cleanup

---

## 🔄 Upgrading from v1.0.2 to v2.0.0

### Steps:

1. **Clone new version**
```bash
git pull origin v2.0.0
```

2. **Run migration scripts**
```bash
python update_database.py
python fix_columns.py
python fix_tables.py
```

3. **Load new categories**
```bash
python init_categories.py
```

4. **Update requirements**
```bash
pip install -r requirements.txt
```

5. **Restart bot**
```bash
python bot.py
```

> **Note:** Old database will work seamlessly. New tables will be added automatically.

---

## 🤝 Contributing

We welcome all contributions! Please follow these steps:

1. **Fork** the repository
2. **Create branch** for your feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** your changes (`git commit -m 'Add some AmazingFeature'`)
4. **Push** to the branch (`git push origin feature/AmazingFeature`)
5. **Open a Pull Request**

---

## 📝 License

This project is licensed under the [MIT License](LICENSE).

---

## 👨‍💻 Author

**Khaled Hani Al-Shashtawi**

- 💬 Telegram: [@A245F](https://t.me/A245F)
- 📂 GitHub: [muslim-kh09](https://github.com/muslim-kh09)

---

## 🙏 Acknowledgments

- [Aladhan API](https://aladhan.com) for prayer times
- [HadeethEnc API](https://hadeethenc.com) for hadiths
- [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) for Telegram library
- [APScheduler](https://github.com/agronholm/apscheduler) for scheduling

---

<div align="center">

**Built with ❤️ for the Islamic Community**

![Star](https://img.shields.io/github/stars/muslim-kh09/Islamic-Prayer-Times-Bot?style=social)
![Forks](https://img.shields.io/github/forks/muslim-kh09/Islamic-Prayer-Times-Bot?style=social)

**Developer: Khaled Hani Al-Shashtawi**
