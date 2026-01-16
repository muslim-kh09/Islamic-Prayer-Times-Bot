# 🏗️ البنية المعمارية (Architecture)

Islamic Prayer Times Telegram Bot - v2.0.0

---

## 📋 نظرة عامة (Overview)

بوت تيليجر إسلامي متعدد المجموعات مبني على Python 3.8+ باستخدام:
- **SQLite** مع WAL mode لقاعدة البيانات
- **APScheduler** للجدولة Event-Driven
- **pyTelegramBotAPI** للتكامل مع تيليجر
- **Requests** لاستدعاء الـ APIs الخارجية

---

## 🏷️ التصميم المعياري (Modular Design)

المشروع مقسم إلى 16 ملف منفصل، كل منها بمسؤولية واضحة:

```
📦 islamic-prayer-bot/
│
├── 🤖 bot.py                      # نقطة الدخول الرئيسية
├── 🎮 bot_handlers.py              # معالجات أوامر التيليجر
├── ⚙️ config.py                   # الإعدادات المركزية
├── 🗄️ database.py                 # عمليات قاعدة البيانات
├── 📖 hadith_system.py            # نظام الأحاديث
├── 🧠 smart_hadith_engine.py      # محرك اختيار الفئات
├── ⏰ scheduler_service.py         # جدولة الإشعارات
├── 🕌 prayer_api.py               # تكامل Aladhan API
├── 📢 notification_service.py      # إرسال الإشعارات
├── 🔧 utils.py                    # دوال مساعدة
├── 📝 logger_config.py            # نظام التسجيل
├── 🗂️ database_schema.sql          # مخطط قاعدة البيانات
├── 📋 categories_list.txt          # 493 تصنيف حديث
├── 📥 init_categories.py           # تحميل التصنيفات
├── 🔄 update_database.py           # migration scripts
├── 🔒 fix_columns.py              # إصلاح الأعمدة
├── 📐 fix_tables.py               # إصلاح الجداول
└── 💾 prefetch_service.py         # خدمة التحميل المسبق (معطلة)
```

---

## 🔄 تدفق البيانات (Data Flow)

### 1️⃣ معالجة أوامر المستخدم (User Commands)

```
User (Telegram)
    ↓
Bot Handler (bot_handlers.py)
    ↓
Database (database.py)
    ↓
Response (Telegram)
```

**أمثلة الأوامر:**
- `/start` - تسجيل مستخدم جديد
- `/setup` - إعداد مجموعة
- `/hadith` - حديث عشوائي
- `/top` - لوحة المتصدرين

### 2️⃣ جدولة الأذان (Azan Scheduling)

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

**الخطوات:**
1. APScheduler يُجدول job لكل صلاة
2. عند حلول الوقت، يُستدعى `send_prayer_notification()`
3. التحقق من قاعدة البيانات (هل تم الإرسال اليوم؟)
4. إرسال إشعار الأذان
5. تسجيل الإرسال في `azan_sent_log`

### 3️⃣ جدولة الأحاديث (Hadith Scheduling)

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

**الخطوات:**
1. APScheduler يُجدول jobs في 4 نوافذ زمنية
2. Smart Hadith Engine يختار الفئة حسب الوقت
3. التحقق من الـ cache في قاعدة البيانات
4. إذا فارغ، استدعاء HadeethEnc API
5. تخزين في `hadith_cache`
6. التحقق من cooldown في `hadith_send_log`
7. إرسال الحديث
8. تسجيل الإرسال في `hadith_send_log`

---

## 🗄️ قاعدة البيانات (Database Schema)

### الجداول الرئيسية

#### 1️⃣ `users` - معلومات المستخدمين
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

#### 2️⃣ `groups` - إعدادات المجموعات
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

#### 3️⃣ `prayer_times_per_group` - أوقات الصلاة
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

#### 4️⃣ `azan_sent_log` - سجل إشعارات الأذان
```sql
- id (PK)
- group_chat_id (FK)
- prayer_name
- prayer_date
- sent_at
UNIQUE(group_chat_id, prayer_name, prayer_date)
```

#### 5️⃣ `hadith_cache` - التخزين المؤقت للأحاديث
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

#### 6️⃣ `hadith_send_log` - سجل الأحاديث المرسلة (إصلاح حرج!)
```sql
- id (PK)
- group_id
- category_id
- sent_at
- window_name
PRIMARY KEY(group_id, sent_at)
```

### الفهارس (Indexes)

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

## ⏰ الجدولة (Scheduling)

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

### أنواع الـ Jobs

1. **Prayer Jobs** (DateTrigger)
   - تُجدول مرة واحدة لكل صلاة
   - Job ID: `prayer_{chat_id}_{prayer_name}`
   - التوقيت: وقت الصلاة الدقيق

2. **Hadith Jobs** (DateTrigger)
   - تُجدول 4 مرات في اليوم
   - Job ID: `hadith_{chat_id}_{window_name}`
   - التوقيت: عشوائي داخل النافذة الزمنية

3. **Daily Reschedule Job** (CronTrigger)
   - تُجدول يومياً في منتصف الليل UTC
   - Job ID: `daily_reschedule`
   - الوظيفة: إعادة بناء جميع الجداول

---

## 🔐 أمان قاعدة البيانات (Database Security)

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

## 📚 نظام الأحاديث (Hadith System)

### المكونات الرئيسية

1. **Smart Hadith Engine** (`smart_hadith_engine.py`)
   - اختيار الفئة حسب الوقت
   - نوافذ زمنية: morning, midday, afternoon, evening, night
   - مطابقة كلمات مفتاحية للعربية والإنجليزية
   - تتبع الفئات الأخيرة لتجنب التكرار

2. **Hadith Cache** (`database.py`)
   - جدول `hadith_cache` للتخزين المؤقت
   - 2 أحاديث لكل تصنيف (تقليل الذاكرة)
   - تحديث `usage_count` و `last_used_at`

3. **Hadith Send Log** (`database.py`)
   - جدول `hadith_send_log` لتتبع الإرسال
   - التحقق من cooldown قبل الإرسال
   - التحقق من daily limit

### تدفق اختيار الحديث

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

## 📢 نظام الإشعارات (Notification System)

### أنواع الإشعارات

1. **Azan Notification**
   - إشعار عند حلول وقت الصلاة
   - زر "صليت" لتسجيل الصلاة
   - معالجة أخطاء 403 (bot kicked)

2. **Hadith Notification**
   - إرسال حديث في النوافذ الزمنية
   - HTML formatting مع روابط
   - معالجة أخطاء الـ API

3. **Success/Error Messages**
   - رسائل تأكيد للمستخدم
   - رسائل خطأ مفصلة
   - Retry mechanism لإعادة المحاولة

---

## 📝 نظام التسجيل (Logging System)

### المستويات (Levels)

```python
DEBUG:   معلومات تفصيلية (development only)
INFO:    معلومات عامة
WARNING: تحذيرات (production mode default)
ERROR:    أخطاء (production mode default)
CRITICAL: أخطاء حرجة
```

### الـ Handlers

1. **RotatingFileHandler**
   - 10MB ملف
   - 5 نسخ احتياطية
   - جميع المستويات (DEBUG+)

2. **ConsoleHandler (with Filter)**
   - Development: INFO و أعلى
   - Production: ERROR و أعلى
   - تقليل الضوضاء في التيرمنل

### ConsoleFilter

```python
class ConsoleFilter(logging.Filter):
    def filter(self, record):
        if self.production_mode:
            return record.levelno >= logging.ERROR
        return record.levelno >= logging.INFO
```

---

## 🔧 التكوين (Configuration)

### ملفات الإعدادات

1. **config.py** - الإعدادات المركزية
2. **.env** - متغيرات البيئة (secrets)
3. **database_schema.sql** - مخطط قاعدة البيانات

### الإعدادات الرئيسية

```python
BOT_TOKEN           # من @BotFather
DATABASE_PATH       # مسار قاعدة البيانات
ALADHAN_API_BASE   # URL للـ API
HADEETHENC_API_BASE # URL للـ API
ENV                 # development | production
LOG_FILE           # مسار ملف السجل
```

---

## 🚀 الأداء والموثوقية (Performance & Reliability)

### تحسينات الأداء

1. **Thread-local Connection Pooling**
   - اتصال واحد لكل خيط
   - لا connection leaks
   - WAL mode للتزامن

2. **Event-Driven Scheduling**
   - APScheduler بدلاً من polling
   - تقليل استهلاك CPU
   - جدولة دقيقة

3. **Smart Caching**
   - Database cache بدلاً من in-memory
   - TTL (24 ساعة)
   - Lazy loading

4. **Log Rotation**
   - منع امتلاء القرص
   - 10MB ملف
   - 5 نسخ احتياطية

### الموثوقية

1. **Retry Logic**
   - Exponential backoff
   - 3 محاولات
   - معالجة أخطاء الشبكة

2. **Error Handling**
   - Graceful shutdown
   - Context managers
   - Auto-rollback

3. **Validation**
   - إعدادات مُتحقق منها
   - Input validation
   - Type hints

---

## 🔄 الترقية والصيانة (Upgrade & Maintenance)

### Migration Scripts

```bash
python update_database.py   # تحديث قاعدة البيانات
python fix_columns.py        # إصلاح الأعمدة
python fix_tables.py         # إصلاح الجداول
python init_categories.py    # تحميل التصنيفات
```

### الصيانة الروتينية

1. مراجعة `bot_debug.log` للأخطاء
2. فحص حجم قاعدة البيانات
3. تحديث التصنيفات (493)
4. مراجعة الـ logs للتأكد من الصحة

---

## 📞 التواصل والدعم (Support)

للمزيد من المعلومات، راجع:
- [README.md](README.md) - دليل الاستخدام
- [CHANGELOG.md](CHANGELOG.md) - سجل التغييرات
- [CONTRIBUTING.md](CONTRIBUTING.md) - كيفية المساهمة
- [VERSION.md](VERSION.md) - معلومات الإصدار

---

<div align="center">

**Architecture v2.0.0 | Production Ready**

</div>
