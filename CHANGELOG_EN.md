# 📝 Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-01-16

### 🎉 Major Release - Complete Architectural Refactor

This release represents a major transformation of the project architecture, converting it from a monolithic single file to a modular architecture with significant performance and reliability improvements.

---

### ✨ Added (New Features)

#### 🏗️ Complete Modular Architecture
- Converted project from single file (~1700 lines) to 16 separate modules
- Separated concerns: database, API, handlers, scheduling, logging, etc.
- Improved maintainability and future development

#### ⏰ Advanced Scheduling System (APScheduler)
- Replaced polling loops with APScheduler Event-Driven
- Precise to-the-second scheduling instead of minutes
- CronTrigger for daily operations
- DateTrigger for scheduled tasks
- Significantly reduced CPU usage (from polling every 30s to event-driven)

#### 🧠 Smart Hadith Engine (v2)
- Time-based hadith category selection (morning, midday, afternoon, evening, night)
- 493 hadith categories from API instead of local JSON
- Advanced keyword matching for categorization
- Cooldown system to prevent spam
- Daily limit (max 5 hadiths)
- Smart database caching

#### 📚 Enhanced Hadith Database System
- `categories_index` table for storing 493 categories
- `hadith_cache` table for caching
- `hadith_send_log` table for send tracking (instead of log file reading!)
- Performance indexes

#### 🛡️ Security & Reliability Improvements
- **Thread-local connection pooling** (one connection per thread)
- **WAL mode** for concurrent read/write operations
- **Context managers** ensuring connection cleanup
- **Automatic transaction handling** (auto-commit/rollback)

#### 📖 Professional Logging System
- Separate `logger_config.py` module
- **RotatingFileHandler** (10MB files, 5 backups)
- Custom Console filter (INFO+ in dev, ERROR+ in prod)
- Detailed format in file, simple in console
- Support for multiple environments (development/production)

#### ⚙️ Centralized Configuration
- Separate `config.py` module
- Configuration validation functions (`validate_config()`)
- Updated API constants (Aladhan, HadeethEnc)
- Retry settings (exponential backoff)
- 18 pre-configured cities in separate configuration
- 15 prayer calculation methods with descriptions

#### 🕌 Improved API Integration
- Separate `prayer_api.py` module
- **Retry logic with exponential backoff**
- Advanced network error handling
- **get_current_prayer** with edge case handling (midnight boundary)
- Timezone-aware "today" calculation per group

#### 📢 Separate Notification Service
- Separate `notification_service.py` module
- Intelligent Telegram error handling (403 = bot kicked)
- Automatic group data cleanup when bot is kicked
- Retry mechanism for message sending

#### 🔧 Enhanced Utilities
- Separate `utils.py` module
- `send_message_safe` with retry mechanism
- `is_user_admin` for permission verification
- `parse_time` for time parsing
- `time_within_window` for time window checking

#### 📥 Migration Scripts
- `update_database.py` for database updates
- `init_categories.py` for loading 493 categories
- `fix_columns.py` for column fixes
- `fix_tables.py` for table fixes

---

### 🔄 Changed

#### Database
- ✅ Added new tables:
  - `categories_index` (493 categories)
  - `category_stats` (prefetch statistics)
  - `hadith_cache` (hadith caching)
  - `hadith_send_log` (send tracking - CRITICAL FIX!)
  - `content_sent_log` (content sent tracking)
- ✅ Enabled WAL mode (`PRAGMA journal_mode=WAL`)
- ✅ Reduced cache size from 10MB to 5MB
- ✅ Added performance indexes:
  - `idx_hadith_cache_category`
  - `idx_hadith_cache_usage`
  - `idx_hadith_send_log_group_time`
  - `idx_categories_index_active`
  - `idx_category_stats_prefetch`

#### Hadith System
- ✅ Replaced log file reading with database queries (CRITICAL SECURITY FIX!)
- ✅ Reduced in-memory cache from 5 to 2 per category
- ✅ Added local `fallback` when API fails
- ✅ Updated hadith_cache (usage_count, last_used_at)
- ✅ Added hadith_send_log for send tracking

#### Scheduling
- ✅ Replaced polling loops with APScheduler
- ✅ Removed prefetch_service (replaced with lazy caching)
- ✅ Added daily reschedule job (midnight UTC)
- ✅ Added `reschedule_group` for immediate updates on setting changes

#### Configuration
- ✅ Added `API_MAX_RETRIES`, `API_RETRY_DELAY`, `API_RETRY_BACKOFF`
- ✅ Added `HADITH_COOLDOWN_MINUTES`, `MAX_HADITH_PER_DAY`
- ✅ Added `HADITH_WINDOWS` (4 time windows)
- ✅ Added `DB_CACHE_SIZE`, `DB_SYNCHRONOUS`

#### Logging
- ✅ Added `LOG_FILE`, `LOG_MAX_BYTES`, `LOG_BACKUP_COUNT`
- ✅ Added `LOG_FORMAT_DETAILED`, `LOG_FORMAT_SIMPLE`
- ✅ Added `ConsoleFilter` class for noise reduction
- ✅ Added `ENV` variable (development/production)

---

### 🐛 Fixed (Critical Fixes)

#### CRITICAL FIX: Log File Reading for Hadith Tracking
- ❌ **Problem in v1.0.2:**
  - System was reading log file `hadith_brain_v2.log` to track sent hadiths
  - File reading is unsafe in multi-threaded environment
  - Potential data corruption and lost data
  - High I/O consumption

- ✅ **Solution in v2.0.0:**
  - Added `hadith_send_log` table in database
  - Store every sent hadith with timestamp
  - Use database queries instead of file reading
  - Safe and reliable in multi-threaded environment
  - Much better performance

#### Fixed: Database Connection Leaks
- ❌ **Problem in v1.0.2:**
  - Connections were opened and closed manually
  - Potential for forgetting to close connections
  - Connection leaks over time

- ✅ **Solution in v2.0.0:**
  - Thread-local connection pooling
  - Context managers (`with get_db_connection() as conn:`)
  - Auto-commit on success
  - Auto-rollback on failure
  - No connection leaks ever

#### Fixed: CPU Usage in Polling Loops
- ❌ **Problem in v1.0.2:**
  - `azan_scheduler_loop` ran every 30 seconds
  - `content_scheduler_loop` ran every 30 seconds
  - Continuous CPU usage even with no activity

- ✅ **Solution in v2.0.0:**
  - APScheduler event-driven
  - Jobs scheduled once per day
  - Significantly reduced CPU usage
  - Lower power consumption

#### Fixed: Timezone Handling
- ❌ **Problem in v1.0.2:**
  - "Today" was calculated once for all groups
  - Potential date errors for groups with different timezones

- ✅ **Solution in v2.0.0:**
  - Calculate "today" per group based on their timezone
  - Use `datetime.now(group_tz)` for accurate timing
  - Reduced date errors

#### Fixed: Telegram API Error Handling
- ❌ **Problem in v1.0.2:**
  - No handling for 403 (bot kicked)
  - Continued sending attempts to groups that kicked the bot

- ✅ **Solution in v2.0.0:**
  - Intelligent Telegram API error handling
  - Automatic group data cleanup when kicked
  - Reduced errors in logs

---

### ⚡ Performance Improvements

#### Database Optimizations
- ✅ WAL mode for concurrent read/write
- ✅ Thread-local connection pooling
- ✅ Reduced cache size from 10MB to 5MB
- ✅ Optimized indexes for all critical queries

#### Memory Optimizations
- ✅ Reduced in-memory hadith cache from 5 to 2 per category
- ✅ Removed prefetch_service (wasn't being used)
- ✅ Database cache instead of in-memory

#### I/O Optimizations
- ✅ Automatic log rotation (10MB files)
- ✅ Production logging mode (WARNING+ only)
- ✅ Reduced logging in loops

#### Network Optimizations
- ✅ Exponential backoff for retries
- ✅ Cache TTL (24 hours)
- ✅ Cooldown tracking (prevent duplicate requests)

---

### ⚠️ Removed

#### Prefetch Service
- ❌ Removed `prefetch_service` (replaced with lazy caching)
- Reason: Not effectively used, unnecessary resource consumption

#### Polling Loops
- ❌ Removed `azan_scheduler_loop` (replaced with APScheduler)
- ❌ Removed `content_scheduler_loop` (replaced with APScheduler)
- Reason: Continuous CPU usage, less accurate

#### Local JSON Content
- ❌ Removed dependency on `content.json`
- Reason: Replaced with API with 493 categories

---

### 🔒 Security Improvements

#### Database Thread Safety
- ✅ Thread-local connection pooling
- ✅ Context managers for transactions
- ✅ WAL mode for concurrent read/write

#### Input Validation
- ✅ `validate_config()` for configuration verification
- ✅ Check BOT_TOKEN length
- ✅ Validate API URLs (HTTPS only)

---

### 📚 Documentation

#### README.md
- ✅ Complete rewrite
- ✅ "Why This Bot?" section
- ✅ Architecture Diagram
- ✅ Data Flow Diagram
- ✅ Detailed Installation Guide
- ✅ Usage Examples
- ✅ Troubleshooting Section
- ✅ Performance Tips
- ✅ Migration Guide (v1.0.2 → v2.0.0)

#### Changelog
- ✅ Created comprehensive CHANGELOG.md
- ✅ Documented all changes from v1.0.2 → v2.0.0
- ✅ Keep a Changelog format

---

### 🧪 Testing

#### Migration Scripts
- ✅ Tested `update_database.py` on v1.0.2 database
- ✅ Tested `init_categories.py` with 493 categories
- ✅ Tested `fix_columns.py` and `fix_tables.py`

#### Core Functionality
- ✅ Tested APScheduler instead of polling
- ✅ Tested hadith tracking in database
- ✅ Tested WAL mode with multi-threading

---

## [1.0.2] - 2026-01-14

### ✨ Added
- Enhanced logging system
- Added ConsoleFilter to reduce terminal noise
- Added RotatingFileHandler to prevent disk overflow

### 🐛 Fixed
- Fixed logging configuration
- Fixed timezone handling for groups
- Fixed prayer time parsing

---

## [1.0.1] - 2026-01-12

### ✨ Added
- Added basic prayer times
- Added azan notifications
- Added prayer logging system

---

## [1.0.0] - 2023-XX-XX

### ✨ Initial Release
- Basic prayer times bot
- Support for major Arabic cities
- Basic group setup

---

## 📋 Future Roadmap

### [2.1.0] - Planned
- [ ] Multi-language support (English, Urdu, Turkish)
- [ ] Web dashboard for statistics
- [ ] Backup/Restore automation
- [ ] Metrics & Analytics integration

### [2.2.0] - Planned
- [ ] Machine Learning for hadith selection
- [ ] User preferences system
- [ ] Custom prayer reminders
- [ ] Advanced analytics dashboard

### [3.0.0] - Planned
- [ ] Microservices architecture
- [ ] Redis cache layer
- [ ] PostgreSQL support
- [ ] REST API for external integrations

---

## 📞 Support

If you encounter any issues:
- 🐛 GitHub Issues: [Report a bug](https://github.com/muslim-kh09/Islamic-Prayer-Times-Bot/issues)

---

<div align="center">

**Developed with ❤️ for the Islamic Community**

</div>
