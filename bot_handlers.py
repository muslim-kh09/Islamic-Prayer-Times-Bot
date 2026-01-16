# -*- coding: utf-8 -*-
"""
Islamic Prayer Times Telegram Bot - Bot Handlers Module
===================================================
All Telegram bot command handlers and callback handlers.

Version: 2.0.0 (Production Ready)
Author: Islamic Prayer Bot Team
License: MIT
"""
import telebot
from datetime import datetime

import config
from logger_config import logger
from database import (
    get_or_create_user,
    get_group,
    create_group,
    update_group,
    update_group_calculation_method,
    get_top_users,
    record_user_prayer,
    get_system_status,
    reset_group_data
)
from prayer_api import get_current_prayer, fetch_and_save_prayer_times
from hadith_system import fetch_smart_hadith
from utils import is_user_admin, send_message_safe
from notification_service import send_test_azan


# =====================================================
# HANDLERS REGISTRATION
# =====================================================

def register_handlers(bot: telebot.TeleBot):
    """
    Register all bot handlers with the bot instance.
    """
    # Message handlers
    @bot.message_handler(commands=['start'])
    def handle_start(message):
        """Handle /start command."""
        try:
            user = message.from_user
            chat_id = message.chat.id

            # Register user in database
            user_id = get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )

            welcome_message = f"""
🌸 <b>مرحباً بك في بوت أوقات الصلاة</b> 🌸

أهلاً {user.first_name}! 👋

🕌 هذا البوت يساعدك في:
• معرفة أوقات الصلاة في مدينتك
• استقبال إشعارات الأذان
• تسجيل صلواتك
• الاستفادة من الأحاديث الذكية

<b>الأوامر المتاحة:</b>

/setup - إعداد إعدادات المجموعة
/setgroupcity - تغيير المدينة
/setcalculationmethod - تغيير طريقة حساب الصلاة
/groupstatus - عرض إعدادات المجموعة
/top - لوحة المتصدرين
/prayed - تسجيل صلاة
/rules - القوانين
/help - المساعدة
/status - حالة النظام
/hadith - حديث عشوائي

استخدم الأوامر للاستفادة من البوت! 🚀
            """

            bot.send_message(chat_id, welcome_message, parse_mode='HTML')
            logger.info(f"User {user.id} started the bot")

        except Exception as e:
            logger.error(f"Error in handle_start: {e}", exc_info=True)


    @bot.message_handler(commands=['setup'])
    def handle_setup(message):
        """Handle /setup command."""
        try:
            chat_id = message.chat.id
            chat_type = message.chat.type

            if chat_type not in ['group', 'supergroup']:
                bot.reply_to(message, "هذا الأمر يعمل فقط في المجموعات! 👥")
                return

            # Check if group already exists
            existing_group = get_group(chat_id)

            if existing_group:
                bot.reply_to(message, "المجموعة مهيأة بالفعل! ✅")
                return

            # Create new group entry
            create_group(
                chat_id=chat_id,
                group_name=message.chat.title,
                city='Riyadh',
                country='Saudi Arabia',
                timezone='Asia/Riyadh'
            )

            setup_message = """
✅ <b>تم إعداد المجموعة بنجاح!</b>

الإعدادات الافتراضية:
📍 المدينة: الرياض
🇸🇦 الدولة: السعودية
🕐 التوقيت: السعودية
🕌 طريقة الحساب: ISNA (الافتراضية)

استخدم /setgroupcity لتغيير المدينة
استخدم /setcalculationmethod لتغيير طريقة الحساب
استخدم /groupstatus لعرض الإعدادات الحالية
            """

            bot.send_message(chat_id, setup_message, parse_mode='HTML')
            logger.info(f"Group {chat_id} setup completed")

        except Exception as e:
            logger.error(f"Error in handle_setup: {e}", exc_info=True)
            bot.reply_to(message, "حدث خطأ أثناء إعداد المجموعة! ❌")


    @bot.message_handler(commands=['setgroupcity'])
    def handle_setgroupcity(message):
        """
        Handle /setgroupcity command.
        RESTRICTED TO ADMINS ONLY.
        Show inline keyboard with city options.
        """
        try:
            chat_id = message.chat.id
            user_id = message.from_user.id
            chat_type = message.chat.type

            # Check if it's a group
            if chat_type not in ['group', 'supergroup']:
                bot.reply_to(message, "هذا الأمر يعمل فقط في المجموعات! 👥")
                return

            # Verify admin permissions
            if not is_user_admin(bot, chat_id, user_id):
                bot.reply_to(message, "⛔ هذا الأمر متاح فقط للمشرفين!")
                return

            # Check if group exists
            group = get_group(chat_id)
            if not group:
                bot.reply_to(message, "المجموعة غير مهيأة! استخدم /setup أولاً")
                return

            # Create inline keyboard with cities
            keyboard = telebot.types.InlineKeyboardMarkup(row_width=3)

            for city_data in config.CITIES_CONFIG:
                arabic_name = city_data['arabic']
                city = city_data['english']
                country = city_data['country']
                tz = city_data['timezone']

                callback_data = f"city_{city}|{country}|{tz}"
                btn = telebot.types.InlineKeyboardButton(arabic_name, callback_data=callback_data)
                keyboard.add(btn)

            bot.send_message(
                chat_id,
                "📍 <b>إعدادات المدينة (للمشرفين فقط)</b>\nاختر مدينتك لضبط مواقيت الصلاة:",
                parse_mode='HTML',
                reply_markup=keyboard
            )

            logger.info(f"City selection menu sent to group {chat_id} by admin {user_id}")

        except Exception as e:
            logger.error(f"Error in handle_setgroupcity: {e}", exc_info=True)
            bot.reply_to(message, "حدث خطأ! ❌")


    @bot.callback_query_handler(func=lambda call: call.data.startswith('city_'))
    def handle_city_selection(call):
        """Handle city selection from inline keyboard."""
        try:
            chat_id = call.message.chat.id

            # Parse callback data
            data = call.data[5:]  # Remove 'city_' prefix
            city, country, tz = data.split('|')

            # Get current group settings
            current_group = get_group(chat_id)

            # Check if city is the same as current
            if current_group and current_group['city'] == city:
                bot.answer_callback_query(
                    call.id,
                    f"المدينة الحالية هي بالفعل {city}! ✅",
                    show_alert=True
                )
                logger.info(f"Group {chat_id} already set to city {city}")
                return

            # Update group settings
            update_group(chat_id, city, country, tz)
            
            # Reschedule group jobs (new scheduler integration)
            from scheduler_service import reschedule_group
            reschedule_group(chat_id)
            
            # Send confirmation
            confirmation_message = f"""
✅ <b>تم تحديث المدينة بنجاح!</b>

📍 المدينة الجديدة: {city}
🇸🇦 الدولة: {country}
🕐 التوقيت: {tz}

سيتم إرسال إشعارات الأذان حسب التوقيت الجديد!

استخدم /groupstatus لعرض الإعدادات والأوقات
            """

            bot.edit_message_text(confirmation_message, chat_id, call.message.message_id, parse_mode='HTML')
            bot.answer_callback_query(call.id, "تم تحديث المدينة بنجاح! ✅")
            logger.info(f"Group {chat_id} updated to city {city}, {country}")

        except Exception as e:
            logger.error(f"Error in handle_city_selection: {e}", exc_info=True)


    @bot.message_handler(commands=['setcalculationmethod'])
    def handle_setcalculationmethod(message):
        """
        Handle /setcalculationmethod command.
        RESTRICTED TO ADMINS ONLY.
        Show inline keyboard with calculation method options.
        """
        try:
            chat_id = message.chat.id
            user_id = message.from_user.id
            chat_type = message.chat.type

            # Check if it's a group
            if chat_type not in ['group', 'supergroup']:
                bot.reply_to(message, "هذا الأمر يعمل فقط في المجموعات! 👥")
                return

            # Verify admin permissions
            if not is_user_admin(bot, chat_id, user_id):
                bot.reply_to(message, "⛔ هذا الأمر متاح فقط للمشرفين!")
                return

            # Check if group exists
            group = get_group(chat_id)
            if not group:
                bot.reply_to(message, "المجموعة غير مهيأة! استخدم /setup أولاً")
                return

            # Get current calculation method
            current_method = group.get('calculation_method', 2)

            # Create inline keyboard with calculation methods
            keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)

            # Add all calculation methods
            for method_data in config.CALCULATION_METHODS:
                method_id = method_data['id']
                arabic_name = method_data['arabic']
                description = method_data['description']

                # Mark current method with ✓
                prefix = "✓ " if method_id == current_method else ""
                callback_data = f"calc_method_{method_id}"

                btn = telebot.types.InlineKeyboardButton(
                    f"{prefix}{arabic_name}\n({method_id}) {description}",
                    callback_data=callback_data
                )
                keyboard.add(btn)

            bot.send_message(
                chat_id,
                f"🕌 <b>إعدادات طريقة حساب أوقات الصلاة</b>\n\n"
                f"الطريقة الحالية: {current_method} (الافتراضية: ISNA)\n\n"
                f"اختر طريقة الحساب المناسبة:",
                parse_mode='HTML',
                reply_markup=keyboard
            )

            logger.info(f"Calculation method selection menu sent to group {chat_id} by admin {user_id}")

        except Exception as e:
            logger.error(f"Error in handle_setcalculationmethod: {e}", exc_info=True)
            bot.reply_to(message, "حدث خطأ! ❌")


    @bot.callback_query_handler(func=lambda call: call.data.startswith('calc_method_'))
    def handle_calculation_method_selection(call):
        """Handle calculation method selection from inline keyboard."""
        try:
            chat_id = call.message.chat.id

            # Parse callback data
            data = call.data[12:]  # Remove 'calc_method_' prefix
            method_id = int(data)

            # Get current group settings
            current_group = get_group(chat_id)

            # Check if method is the same as current
            if current_group and current_group.get('calculation_method', 2) == method_id:
                bot.answer_callback_query(
                    call.id,
                    f"طريقة الحساب الحالية هي بالفعل {method_id}! ✅",
                    show_alert=True
                )
                logger.info(f"Group {chat_id} already using calculation method {method_id}")
                return

            # Update group calculation method
            update_group_calculation_method(chat_id, method_id)
            
            # Reschedule group jobs (new scheduler integration)
            from scheduler_service import reschedule_group
            reschedule_group(chat_id)
            
            # Get method details for confirmation
            method_details = next(
                (m for m in config.CALCULATION_METHODS if m['id'] == method_id),
                {'arabic': 'غير معروف', 'description': ''}
            )

            # Send confirmation
            confirmation_message = f"""
✅ <b>تم تحديث طريقة حساب أوقات الصلاة بنجاح!</b>

🕌 الطريقة الجديدة: {method_details['arabic']}
📝 الوصف: {method_details['description']}

سيتم إرسال إشعارات الأذان حسب الطريقة الجديدة!

استخدم /groupstatus لعرض الإعدادات والأوقات
            """

            bot.edit_message_text(confirmation_message, chat_id, call.message.message_id, parse_mode='HTML')
            bot.answer_callback_query(call.id, "تم تحديث طريقة الحساب بنجاح! ✅")
            logger.info(f"Group {chat_id} updated to calculation method {method_id}")

        except Exception as e:
            logger.error(f"Error in handle_calculation_method_selection: {e}", exc_info=True)


    @bot.message_handler(commands=['groupstatus'])
    def handle_groupstatus(message):
        """
        Handle /groupstatus command.
        RESTRICTED TO ADMINS ONLY.
        """
        try:
            chat_id = message.chat.id
            user_id = message.from_user.id
            chat_type = message.chat.type

            # Check if it's a group
            if chat_type not in ['group', 'supergroup']:
                bot.reply_to(message, "هذا الأمر يعمل فقط في المجموعات! 👥")
                return

            # Verify admin permissions
            if not is_user_admin(bot, chat_id, user_id):
                bot.reply_to(message, "⛔ هذا الأمر متاح فقط للمشرفين!")
                return

            # Get group settings
            group = get_group(chat_id)
            if not group:
                bot.reply_to(message, "المجموعة غير مهيأة! استخدم /setup أولاً")
                return

            # Get calculation method details
            calc_method_id = group.get('calculation_method', 2)
            calc_method = next(
                (m for m in config.CALCULATION_METHODS if m['id'] == calc_method_id),
                {'arabic': 'غير معروف', 'description': ''}
            )

            # Get today's prayer times
            today = datetime.now().strftime('%Y-%m-%d')
            from database import get_group_prayer_times
            prayer_times = get_group_prayer_times(chat_id, today)

            # Build status message
            status_message = f"""
📊 <b>إعدادات المجموعة</b> 📊

📍 المدينة: {group['city']}
🇸🇦 الدولة: {group['country']}
🕐 التوقيت: {group['timezone']}
🕌 طريقة الحساب: {calc_method['arabic']}
✨ حالة الإشعارات: {'مفعّلة' if group['notification_enabled'] else 'معطّلة'}

"""

            if prayer_times:
                status_message += f"""
<b>أوقات الصلاة اليوم</b> 🕌

🌅 الفجر: {prayer_times['fajr_time']}
☀️ الظهر: {prayer_times['dhuhr_time']}
🌤️ العصر: {prayer_times['asr_time']}
🌅 المغرب: {prayer_times['maghrib_time']}
🌙 العشاء: {prayer_times['isha_time']}

"""
                if prayer_times['hijri_date']:
                    status_message += f"📆 التاريخ الهجري: {prayer_times['hijri_date']}\n"
            else:
                status_message += "\n⏳ جاري جلب أوقات الصلاة...\n"

            bot.send_message(chat_id, status_message, parse_mode='HTML')
            logger.info(f"Group status displayed for {chat_id}")

        except Exception as e:
            logger.error(f"Error in handle_groupstatus: {e}", exc_info=True)
            bot.reply_to(message, "حدث خطأ! ❌")


    @bot.message_handler(commands=['prayed'])
    def handle_prayed(message):
        """
        Handle /prayed command.
        Shows only the current prayer for logging.
        """
        try:
            chat_id = message.chat.id

            # Get current prayer
            current_prayer = get_current_prayer(chat_id)

            if not current_prayer:
                # No prayer times or no current prayer
                group = get_group(chat_id)
                if not group:
                    bot.send_message(
                        chat_id,
                        "⚠️ لم يتم إعداد المجموعة بعد!\n\n"
                        "الرجاء استخدام /setup لإعداد المجموعة أولاً."
                    )
                else:
                    bot.send_message(
                        chat_id,
                        "⏰ لم يحن وقت أي صلاة بعد.\n\n"
                        "يمكنك استخدام هذا الأمر بعد دخول وقت الصلاة."
                    )
                return

            # Display only the current prayer
            keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)

            btn = telebot.types.InlineKeyboardButton(
                f'✅ صليت {current_prayer["name_arabic"]}',
                callback_data=f'manual_prayed_{current_prayer["name"].lower()}'
            )
            keyboard.add(btn)

            bot.send_message(
                chat_id,
                f"⏰ الصلاة الحالية: <b>{current_prayer['name_arabic']}</b>\n"
                f"📅 الوقت: {current_prayer['time']}\n\n"
                "اضغط على الزر لتسجيل الصلاة:",
                parse_mode='HTML',
                reply_markup=keyboard
            )

        except Exception as e:
            logger.error(f"Error in handle_prayed: {e}", exc_info=True)
            bot.reply_to(message, "حدث خطأ! ❌")


    @bot.message_handler(commands=['top'])
    def handle_top(message):
        """Handle /top command."""
        try:
            top_users = get_top_users(10)

            if not top_users:
                bot.reply_to(message, "لا يوجد مستخدمين في السجل بعد! 📊")
                return

            leaderboard_message = "🏆 <b>لوحة المتصدرين</b> 🏆\n\n"

            for idx, user in enumerate(top_users, start=1):
                medal = ['🥇', '🥈', '🥉'][idx - 1] if idx <= 3 else f"{idx}."
                name = user['first_name'] or user['username'] or 'مستخدم'
                leaderboard_message += f"{medal} {name}\n"
                leaderboard_message += f"   📊 عدد الصلوات: {user['prayer_count']}\n"
                leaderboard_message += f"   ⭐ النقاط: {user['score']}\n\n"

            bot.send_message(message.chat.id, leaderboard_message, parse_mode='HTML')
            logger.info("Leaderboard displayed")

        except Exception as e:
            logger.error(f"Error in handle_top: {e}", exc_info=True)
            bot.reply_to(message, "حدث خطأ! ❌")


    @bot.message_handler(commands=['rules'])
    def handle_rules(message):
        """Handle /rules command."""
        try:
            rules_message = """
📜 <b>قوانين البوت</b> 📜

<b>الاستخدام الصحيح للبوت:</b>

1️⃣ يجب أن يكون البوت مشرفاً في المجموعة
2️⃣ استخدم /setup لإعداد المجموعة لأول مرة
3️⃣ استخدم /setgroupcity لتحديد مدينتك
4️⃣ استخدم /setcalculationmethod لاختيار طريقة الحساب
5️⃣ استخدم /groupstatus لعرض الإعدادات والأوقات

<b>تسجيل الصلوات:</b>

• يمكنك تسجيل صلواتك عبر زر الأذان
• أو استخدم /prayed لتسجيل يدوياً
• كل صلاة = +10 نقاط

<b>الإشعارات:</b>

• البوت يرسل إشعار الأذان قبل أو عند وقت الصلاة
• الإشعارات تعتمد على توقيت مدينتك وطريقة الحساب
• يمكنك تغيير المدينة وطريقة الحساب في أي وقت

<b>الأحاديث الذكية:</b>

• الأحاديث تُرسل بشكل ذكي خلال اليوم
• النظام يختار أحاديث متنوعة ومتوازنة
• استخدم /hadith لحديث عشوائي في أي وقت

🤲 نسأل الله أن ينفع بنا وبكم 🤲
            """

            send_message_safe(bot, message.chat.id, rules_message)
            logger.info("Rules displayed")

        except Exception as e:
            logger.error(f"Error in handle_rules: {e}", exc_info=True)


    @bot.message_handler(commands=['help'])
    def handle_help(message):
        """Handle /help command."""
        try:
            help_message = """
🆘 <b>دليل المساعدة</b> 🆘

<b>الأوامر الأساسية:</b>

/start - بدء البوت والتسجيل
/setup - إعداد المجموعة
/setgroupcity - تغيير المدينة
/setcalculationmethod - تغيير طريقة حساب الصلاة
/groupstatus - عرض الإعدادات والأوقات
/prayed - تسجيل صلاة
/top - لوحة المتصدرين
/rules - عرض القوانين
/help - عرض هذه الرسالة

<b>أوامر الأحاديث:</b>

/hadith - حديث عشوائي

<b>الأزرار التفاعلية:</b>

📋 زر تسجيل الصلاة (يظهر مع كل أذان)
📍 اختيار المدينة (من قائمة المدن المتاحة)
🕌 اختيار طريقة الحساب (من الطرق المتاحة)

<b>معلومات إضافية:</b>

• البوت يدعم عدد غير محدود من المجموعات
• كل مجموعة لها إعداداتها الخاصة
• الإشعارات تعمل حسب توقيت كل مجموعة
• الأحاديث تُرسل تلقائياً بشكل ذكي

للدعم والتواصل، تواصل مع مشرف البوت
            """

            bot.send_message(message.chat.id, help_message, parse_mode='HTML')
            logger.info("Help displayed")

        except Exception as e:
            logger.error(f"Error in handle_help: {e}", exc_info=True)
            bot.reply_to(message, "حدث خطأ! ❌")


    @bot.message_handler(commands=['hadith'])
    def handle_hadith_command(message):
        """جلب حديث ذكي عند الطلب"""
        bot.send_chat_action(message.chat.id, 'typing')

        hadith_text = fetch_smart_hadith()

        if hadith_text:
            bot.reply_to(message, hadith_text, parse_mode='HTML')
        else:
            bot.reply_to(message, "عذراً، لا يمكن جلب الحديث حالياً. حاول لاحقاً.")


    @bot.message_handler(commands=['test_azan'])
    def handle_test_azan(message):
        """
        أمر تجريبي للمشرفين: إرسال أذان وهمي الآن للتأكد من عمل البوت
        """
        chat_id = message.chat.id
        user_id = message.from_user.id

        try:
            if message.chat.type in ['group', 'supergroup']:
                # Verify user is admin
                if not is_user_admin(bot, chat_id, user_id):
                    bot.reply_to(message, "⛔ هذا الأمر متاح فقط للمشرفين!")
                    return

                # Send test for Dhuhr prayer
                bot.reply_to(message, "⏳ جاري تجربة إرسال الأذان...")
                success = send_test_azan(bot, chat_id)

                if not success:
                    bot.send_message(chat_id, "❌ فشلت التجربة. تأكد من صلاحيات البوت في الإرسال.")
            else:
                 bot.reply_to(message, "هذا الأمر للمجموعات فقط.")
        except Exception as e:
            bot.reply_to(message, f"حدث خطأ: {e}")


    @bot.message_handler(commands=['status'])
    def handle_status(message):
        """
        Handle /status command - Show detailed system status.
        RESTRICTED TO ADMINS ONLY.
        """
        try:
            chat_id = message.chat.id
            user_id = message.from_user.id

            # Verify admin permissions
            if message.chat.type in ['group', 'supergroup']:
                if not is_user_admin(bot, chat_id, user_id):
                    bot.reply_to(message, "⛔ هذا الأمر متاح فقط للمشرفين!")
                    return

            # Get system status
            status = get_system_status(chat_id)

            if not status:
                bot.reply_to(message, "❌ حدث خطأ في جلب حالة النظام!")
                return

            # Build status message
            status_text = "📊 <b>حالة النظام التفصيلية</b>\n\n"

            # --- Overall Statistics ---
            status_text += "📈 <b>الإحصائيات العامة:</b>\n"
            status_text += f"├─ المستخدمون: {status['total_users']}\n"
            status_text += f"├─ المجموعات النشطة: {status['total_groups']}\n"
            status_text += f"├─ إجمالي الصلوات: {status['total_prayers']}\n"
            status_text += f"└─ أول تسجيل: {status['first_registration'] or 'غير متوفر'}\n\n"

            # --- Group Information ---
            status_text += "👥 <b>معلومات المجموعة الحالية:</b>\n"
            if status['group_info']:
                group = status['group_info']
                status_text += f"├─ الاسم: {group['group_name'] or 'غير محدد'}\n"
                status_text += f"├─ المدينة: {group['city']}\n"
                status_text += f"├─ البلد: {group['country']}\n"
                status_text += f"├─ التوقيت: {group['timezone']}\n"
                status_text += f"├─ طريقة الحساب: {group['calculation_method']}\n"
                status_text += f"├─ حالة الإشعارات: {'مفعلة ✓' if group['notification_enabled'] else 'معطلة ✗'}\n"
                status_text += f"└─ حالة النشاط: {'نشطة ✓' if group['is_active'] else 'غير نشطة ✗'}\n"
            else:
                status_text += "└─ ⚠️ المجموعة غير موجودة في قاعدة البيانات!\n"
            status_text += "\n"

            # --- Prayer Times ---
            status_text += "⏰ <b>أوقات الصلاة اليوم:</b>\n"
            if status['prayer_times']:
                pt = status['prayer_times']
                status_text += f"├─ الفجر: {pt['fajr_time']}\n"
                status_text += f"├─ الظهر: {pt['dhuhr_time']}\n"
                status_text += f"├─ العصر: {pt['asr_time']}\n"
                status_text += f"├─ المغرب: {pt['maghrib_time']}\n"
                status_text += f"├─ العشاء: {pt['isha_time']}\n"
                status_text += f"└─ التاريخ الهجري: {pt['hijri_date'] or 'غير متوفر'}\n"
            else:
                status_text += "└─ ⚠️ لم يتم جلب أوقات الصلاة بعد\n"
            status_text += "\n"

            # --- Group Stats ---
            status_text += "📊 <b>إحصائيات المجموعة:</b>\n"
            status_text += f"├─ المستخدمون النشطون: {status['group_active_users']}\n"
            status_text += f"└─ الأذان المرسل: {status['azan_sent_count']}\n"

            if status['prayer_stats']:
                status_text += "\n🕌 <b>الصلوات المسجلة:</b>\n"
                prayer_names_ar = {
                    'fajr': 'الفجر',
                    'dhuhr': 'الظهر',
                    'asr': 'العصر',
                    'maghrib': 'المغرب',
                    'isha': 'العشاء'
                }
                for prayer, count in status['prayer_stats'].items():
                    prayer_ar = prayer_names_ar.get(prayer, prayer)
                    status_text += f"├─ {prayer_ar}: {count}\n"
            status_text += "\n"

            # --- Top Users ---
            status_text += "🏆 <b>أفضل المستخدمين:</b>\n"
            if status['top_users']:
                for idx, user in enumerate(status['top_users'], 1):
                    medals = ['🥇', '🥈', '🥉']
                    medal = medals[idx - 1] if idx <= 3 else f'{idx}.'
                    username_display = f"@{user['username']}" if user['username'] else user['first_name'] or 'مستخدم'
                    status_text += f"{medal} {username_display} - {user['score']} نقطة\n"
            else:
                status_text += "└─ لا يوجد مستخدمين بعد\n"
            status_text += "\n"

            # --- System Health ---
            import os
            status_text += "✅ <b>صحة النظام:</b>\n"
            status_text += f"├─ قاعدة البيانات: {'متاحة ✓' if os.path.exists(config.DATABASE_PATH) else 'غير متاحة ✗'}\n"
            status_text += f"├─ API: متاح ✓\n"
            status_text += f"└─ نظام الأحاديث الذكية: {'نشط ✓' if os.path.exists('categories_list.txt') else 'غير نشط ✗'}\n"

            # Send message
            bot.send_message(chat_id, status_text, parse_mode='HTML', disable_web_page_preview=True)
            logger.info(f"Status viewed by ADMIN {message.from_user.id} in group {chat_id}")

        except Exception as e:
            logger.error(f"Error in handle_status: {e}", exc_info=True)
            bot.reply_to(message, "❌ حدث خطأ! ❌")


    @bot.message_handler(commands=['reset_all'])
    def handle_reset_all(message):
        """
        Handle /reset_all command - Admin only.
        Shows confirmation dialog before resetting.
        """
        try:
            chat_id = message.chat.id
            user_id = message.from_user.id

            # Check if user is admin
            if not is_user_admin(bot, chat_id, user_id):
                bot.reply_to(message, "⛔ هذا الأمر متاح فقط للمشرفين!")
                return

            # Check if chat is a group
            if message.chat.type not in ['group', 'supergroup']:
                bot.reply_to(message, "⛔ هذا الأمر متاح فقط في المجموعات!")
                return

            # Send confirmation message
            warning_text = f"""
⚠️ <b>تحذير هام!</b> ⚠️

أنت على وشك حذف <b>كل البيانات</b> لهذه المجموعة:

❌ جميع سجلات الصلاة
❌ جميع سجلات الأذان
❌ جميع سجلات المحتوى
❌ إعدادات المجموعة (المدينة، التوقيت، إلخ)
❌ أوقات الصلاة المحفوظة

<b>هذا الإجراء لا يمكن التراجع عنه!</b>

هل أنت متأكد من المتابعة؟
            """

            keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
            btn_confirm = telebot.types.InlineKeyboardButton(
                '🗑️ نعم، احذف كل شيء',
                callback_data=f'reset_confirm_{chat_id}_{user_id}'
            )
            btn_cancel = telebot.types.InlineKeyboardButton(
                '❌ إلغاء',
                callback_data=f'reset_cancel_{chat_id}'
            )
            keyboard.add(btn_confirm, btn_cancel)

            bot.send_message(chat_id, warning_text, parse_mode='HTML', reply_markup=keyboard)
            logger.info(f"Reset confirmation requested by user {user_id} in group {chat_id}")

        except Exception as e:
            logger.error(f"Error in handle_reset_all: {e}", exc_info=True)
            bot.reply_to(message, "حدث خطأ! ❌")


    # =====================================================
    # CALLBACK HANDLERS
    # =====================================================

    @bot.callback_query_handler(func=lambda call: call.data.startswith('prayed_'))
    def handle_prayed_callback(call):
        """Handle prayed button callback."""
        try:
            user = call.from_user
            chat_id = call.message.chat.id
            prayer_name = call.data[7:]  # Remove 'prayed_' prefix

            # Get or create user
            user_id = get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )

            # Get today's date
            today = datetime.now().strftime('%Y-%m-%d')

            # Record prayer
            if record_user_prayer(user_id, chat_id, prayer_name, today):
                prayer_names_arabic = {
                    'fajr': 'الفجر',
                    'dhuhr': 'الظهر',
                    'asr': 'العصر',
                    'maghrib': 'المغرب',
                    'isha': 'العشاء'
                }

                prayer_arabic = prayer_names_arabic.get(prayer_name, prayer_name)
                success_message = f"""
✅ <b>تم تسجيل صلاتك!</b>

شكراً لتسجيل صلاة {prayer_arabic} 🤲
+10 نقاط! 🌟
                """
            else:
                success_message = "تم تسجيل هذه الصلاة مسبقاً اليوم! ✅"

            bot.answer_callback_query(call.id, success_message, show_alert=True)

        except Exception as e:
            logger.error(f"Error in handle_prayed_callback: {e}", exc_info=True)


    @bot.callback_query_handler(func=lambda call: call.data.startswith('manual_prayed_'))
    def handle_manual_prayed_callback(call):
        """Handle manual prayer recording callback."""
        try:
            from database import get_or_create_user
            user = call.from_user
            chat_id = call.message.chat.id
            prayer_name = call.data[14:]  # Remove 'manual_prayed_' prefix

            # Get or create user
            user_id = get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )

            # Use the same logic as handle_prayed_callback
            today = datetime.now().strftime('%Y-%m-%d')

            # Record prayer
            if record_user_prayer(user_id, chat_id, prayer_name, today):
                prayer_names_arabic = {
                    'fajr': 'الفجر',
                    'dhuhr': 'الظهر',
                    'asr': 'العصر',
                    'maghrib': 'المغرب',
                    'isha': 'العشاء'
                }

                prayer_arabic = prayer_names_arabic.get(prayer_name, prayer_name)
                success_message = f"""
✅ <b>تم تسجيل صلاتك!</b>

شكراً لتسجيل صلاة {prayer_arabic} 🤲
+10 نقاط! 🌟
                """
            else:
                success_message = "تم تسجيل هذه الصلاة مسبقاً اليوم! ✅"

            bot.answer_callback_query(call.id, success_message, show_alert=True)

        except Exception as e:
            logger.error(f"Error in handle_manual_prayed_callback: {e}", exc_info=True)


    @bot.callback_query_handler(func=lambda call: call.data.startswith('reset_confirm_'))
    def handle_reset_confirm(call):
        """Handle reset confirmation callback."""
        try:
            # Parse callback data
            parts = call.data.split('_')
            chat_id = int(parts[2])
            requesting_user_id = int(parts[3])
            current_user_id = call.from_user.id

            # Verify it's same user who requested reset
            if requesting_user_id != current_user_id:
                bot.answer_callback_query(call.id, "⛔ هذا الإجراء غير مصرح لك!")
                return

            # Verify admin status again
            if not is_user_admin(bot, chat_id, current_user_id):
                bot.answer_callback_query(call.id, "⛔ هذا الأمر متاح فقط للمشرفين!")
                return

            # Perform reset
            bot.answer_callback_query(call.id, "جاري حذف البيانات...")

            success = reset_group_data(chat_id)

            if success:
                success_message = """
✅ <b>تم إعادة التعيين بنجاح!</b>

تم حذف جميع البيانات لهذه المجموعة. للبدء من جديد:

/start - لإعداد المجموعة مرة أخرى

⚠️ تأكد من إعداد المجموعة بشكل صحيح لتعمل جميع الميزات.
                """
                bot.send_message(chat_id, success_message, parse_mode='HTML')
                logger.info(f"Group {chat_id} reset successfully by admin {current_user_id}")
            else:
                bot.send_message(chat_id, "❌ حدث خطأ أثناء إعادة التعيين. يرجى المحاولة لاحقاً.")
                logger.error(f"Failed to reset group {chat_id}")

        except Exception as e:
            logger.error(f"Error in handle_reset_confirm: {e}", exc_info=True)
            try:
                bot.send_message(call.message.chat.id, "❌ حدث خطأ! ❌")
            except Exception:
                pass


    @bot.callback_query_handler(func=lambda call: call.data.startswith('reset_cancel_'))
    def handle_reset_cancel(call):
        """Handle reset cancellation callback."""
        try:
            bot.answer_callback_query(call.id, "تم إلغاء العملية")
            bot.edit_message_text(
                "✅ تم إلغاء عملية إعادة التعيين.",
                call.message.chat.id,
                call.message.message_id
            )
            logger.info(f"Reset cancelled by user {call.from_user.id}")
        except Exception as e:
            logger.error(f"Error in handle_reset_cancel: {e}", exc_info=True)

