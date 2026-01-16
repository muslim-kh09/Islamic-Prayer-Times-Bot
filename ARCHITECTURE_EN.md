# 🏗️ Architecture

Islamic Prayer Times Telegram Bot - v2.0.0

---

## 📋 Overview

A multi-group Islamic Telegram bot built on Python 3.8+ using:
- **SQLite** with WAL mode for database
- **APScheduler** for event-driven scheduling
- **pyTelegramBotAPI** for Telegram integration
- **Requests** for external API calls

---

## 🏷️ Modular Design

The project is divided into 16 separate files, each with clear responsibilities:

```
📦 islamic-prayer-bot/
│
├── 🤖 bot.py                      # Main entry point
├── 🎮 bot_handlers.py              # Telegram command handlers
├── ⚙️ config.py                   # Centralized configuration
├── 🗄️ database.py                 # Database operations
├── 📖 hadith_system.py            # Hadith system
├── 🧠 smart_hadith_engine.py      # Smart hadith selection engine
├── ⏰ scheduler_service.py         # Notification scheduling
├── 🕌 prayer_api.py               # Aladhan API integration
├── 📢 notification_service.py      # Notification sending
├── 🔧 utils.py                    # Utility functions
├── 📝 logger_config.py            # Logging system
├── 🗂️ database_schema.sql          # Database schema
├── 📋 categories_list.txt          # 493 hadith categories
├── 📥 init_categories.py           # Initialize categories
├── 🔄 update_database.py           # Migration scripts
├── 🔒 fix_columns.py              # Fix columns
├── 📐 fix_tables.py               # Fix tables
└── 💾 prefetch_service.py         # Prefetch service (disabled)
```

---

## 🔄 Data Flow

### 1️⃣ User Command Processing

```
User (Telegram)
    ↓
Bot Handler (bot_handlers.py)
    ↓
Database (database.py)
    ↓
Response (Telegram)
```

**Example Commands:**
- `/start` - Register new user
- `/setup` - Setup group
- `/hadith` - Random hadith
- `/top` - Leaderboard

### 2️⃣ Azan Scheduling

```
APScheduler (scheduler_service.py)
    ↓
Prayer Times Check (prayer_api.py)
    ↓
Database Query (database.py)
    ↓
Notification (notification_service.py)
    ↓
Telegram API
```

**Steps:**
1. APScheduler schedules a job for each prayer
2. When time arrives, calls `send_prayer_notification()`
3. Checks database (was it sent today?)
4. Sends azan notification
5. Logs send in `azan_sent_log`

### 3️⃣ Hadith Scheduling

```
APScheduler (scheduler_service.py)
    ↓
Smart Hadith Engine (smart_hadith_engine.py)
    ↓
Hadith Cache Check (database.py)
    ↓
API Call (hadith_system.py)
    ↓
Notification (notification_service.py)
    ↓
Telegram API
```

**Steps:**
1. APScheduler schedules jobs in 4 time windows
2. Smart Hadith Engine selects category based on time
3. Check cache in database
4. If empty, call HadeethEnc API
5. Store in `hadith_cache`
6. Check cooldown in `hadith_send_log`
7. Send hadith
8. Log send in `hadith_send_log`

---

## 🗄️ Database Schema

### Main Tables

#### 1️⃣ `users` - User Information
```sql
- id (PK)
- telegram_id (UNIQUE)
- username
- first_name
- last_name
- score
- prayer_count
- created_at
- last_active
```

#### 2️⃣ `groups` - Group Settings
```sql
- id (PK)
- chat_id (UNIQUE)
- group_name
- city
- country
- timezone
- calculation_method
- is_active
- notification_enabled
- created_at
- updated_at
```

#### 3️⃣ `prayer_times_per_group` - Daily Prayer Times
```sql
- id (PK)
- group_chat_id (FK)
- date
- fajr_time
- dhuhr_time
- asr_time
- maghrib_time
- isha_time
- hijri_date
- fetched_at
UNIQUE(group_chat_id, date)
```

#### 4️⃣ `azan_sent_log` - Azan Notification Log
```sql
- id (PK)
- group_chat_id (FK)
- prayer_name
- prayer_date
- sent_at
UNIQUE(group_chat_id, prayer_name, prayer_date)
```

#### 5️⃣ `hadith_cache` - Hadith Caching
```sql
- id (PK)
- hadith_id (UNIQUE)
- category_id
- hadith_text
- attribution
- grade
- explanation
- source_url
- created_at
- last_used_at
- usage_count
```

#### 6️⃣ `hadith_send_log` - Hadith Send Tracking (CRITICAL FIX!)
```sql
- id (PK)
- group_id
- category_id
- sent_at
- window_name
PRIMARY KEY(group_id, sent_at)
```

### Indexes

```sql
- idx_content_sent_log_group_date
- idx_prayer_times_group_date
- idx_azan_sent_log_group_date
- idx_prayer_logs_user_date
- idx_users_score
- idx_hadith_cache_category
- idx_hadith_cache_usage
- idx_hadith_send_log_group_time
- idx_categories_index_active
```

---

## ⏰ Scheduling

### APScheduler Configuration

```python
BackgroundScheduler(
    jobstores={'default': MemoryJobStore()},
    executors={'default': ThreadPoolExecutor(max_workers=10)},
    timezone='UTC',
    job_defaults={
        'coalesce': True,
        'max_instances': 1,
        'misfire_grace_time': 300
    }
)
```

### Job Types

1. **Prayer Jobs** (DateTrigger)
   - Scheduled once per prayer
   - Job ID: `prayer_{chat_id}_{prayer_name}`
   - Time: Exact prayer time

2. **Hadith Jobs** (DateTrigger)
   - Scheduled 4 times per day
   - Job ID: `hadith_{chat_id}_{window_name}`
   - Time: Random within time window

3. **Daily Reschedule Job** (CronTrigger)
   - Scheduled daily at midnight UTC
   - Job ID: `daily_reschedule`
   - Function: Rebuild all schedules

---

## 🔐 Database Security

### Thread-Safety

```python
# Thread-local connection pooling
_local = threading.local()

def _get_thread_connection():
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(DATABASE_PATH)
        _local.conn.row_factory = sqlite3.Row
        # Enable WAL mode
        _local.conn.execute('PRAGMA journal_mode=WAL')
    return _local.conn
```

### Context Managers

```python
@contextmanager
def get_db_connection():
    conn = _get_thread_connection()
    try:
        conn.execute('BEGIN')
        yield conn
        conn.commit()  # Auto-commit
    except Exception as e:
        conn.rollback()  # Auto-rollback
        raise e
```

### WAL Mode

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=-5000;
PRAGMA temp_store=MEMORY;
PRAGMA mmap_size=268435456;
```

---

## 📚 Hadith System

### Main Components

1. **Smart Hadith Engine** (`smart_hadith_engine.py`)
   - Time-based category selection
   - Time windows: morning, midday, afternoon, evening, night
   - Keyword matching for Arabic and English
   - Track recent categories to avoid repetition

2. **Hadith Cache** (`database.py`)
   - `hadith_cache` table for caching
   - 2 hadiths per category (reduced memory)
   - Update `usage_count` and `last_used_at`

3. **Hadith Send Log** (`database.py`)
   - `hadith_send_log` table for send tracking
   - Check cooldown before sending
   - Check daily limit

### Hadith Selection Flow

```
Current Time
    ↓
Determine Time Window
    ↓
Select Category (Smart Engine)
    ↓
Check Database Cache
    ↓
Empty? → Fetch from API
    ↓
Save to Cache
    ↓
Check Cooldown (Database)
    ↓
Check Daily Limit (Database)
    ↓
Send Hadith
    ↓
Log to Database
```

---

## 📢 Notification System

### Notification Types

1. **Azan Notification**
   - Notify when prayer time arrives
   - "I Prayed" button for logging
   - Handle 403 errors (bot kicked)

2. **Hadith Notification**
   - Send hadith in time windows
   - HTML formatting with links
   - Handle API errors

3. **Success/Error Messages**
   - Confirmation messages for users
   - Detailed error messages
   - Retry mechanism

---

## 📝 Logging System

### Levels

```python
DEBUG:   Detailed information (development only)
INFO:    General information
WARNING:  Warnings (production mode default)
ERROR:    Errors (production mode default)
CRITICAL: Critical errors
```

### Handlers

1. **RotatingFileHandler**
   - 10MB files
   - 5 backup files
   - All levels (DEBUG+)

2. **ConsoleHandler (with Filter)**
   - Development: INFO and above
   - Production: ERROR and above
   - Reduced terminal noise

### ConsoleFilter

```python
class ConsoleFilter(logging.Filter):
    def filter(self, record):
        if self.production_mode:
            return record.levelno >= logging.ERROR
        return record.levelno >= logging.INFO
```

---

## 🔧 Configuration

### Configuration Files

1. **config.py** - Centralized configuration
2. **.env** - Environment variables (secrets)
3. **database_schema.sql** - Database schema

### Key Settings

```python
BOT_TOKEN           # From @BotFather
DATABASE_PATH       # Database file path
ALADHAN_API_BASE   # API URL
HADEETHENC_API_BASE # API URL
ENV                 # development | production
LOG_FILE           # Log file path
```

---

## 🚀 Performance & Reliability

### Performance Optimizations

1. **Thread-local Connection Pooling**
   - One connection per thread
   - No connection leaks
   - WAL mode for concurrency

2. **Event-Driven Scheduling**
   - APScheduler instead of polling
   - Reduced CPU usage
   - Precise scheduling

3. **Smart Caching**
   - Database cache instead of in-memory
   - TTL (24 hours)
   - Lazy loading

4. **Log Rotation**
   - Prevent disk overflow
   - 10MB files
   - 5 backup files

### Reliability

1. **Retry Logic**
   - Exponential backoff
   - 3 retry attempts
   - Network error handling

2. **Error Handling**
   - Graceful shutdown
   - Context managers
   - Auto-rollback

3. **Validation**
   - Settings validated on startup
   - Input validation
   - Type hints

---

## 🔄 Upgrade & Maintenance

### Migration Scripts

```bash
python update_database.py   # Update database
python fix_columns.py        # Fix columns
python fix_tables.py         # Fix tables
python init_categories.py    # Load categories
```

### Routine Maintenance

1. Review `bot_debug.log` for errors
2. Check database size
3. Update categories (493)
4. Review logs for health

---

## 📞 Support & Resources

For more information, see:
- [README.md](README.md) - Usage guide
- [CHANGELOG.md](CHANGELOG.md) - Changelog
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
- [VERSION.md](VERSION.md) - Version info

---

<div align="center">

**Architecture v2.0.0 | Production Ready**

</div>
