# -*- coding: utf-8 -*-
"""
Islamic Prayer Times Telegram Bot - Notification Service Module
=========================================================
Handle azan notifications and message sending.

Version: 2.0.0 (Production Ready)
Author: Islamic Prayer Bot Team
License: MIT
"""
import telebot
from telebot.apihelper import ApiTelegramException

import config
from logger_config import logger


# =====================================================
# AZAN NOTIFICATION
# =====================================================

def send_azan_notification(bot: telebot.TeleBot, chat_id: int,
                          prayer_name: str, prayer_time: str) -> bool:
    """
    Send azan notification to a group with smart error handling.

    Args:
        bot: TeleBot instance
        chat_id: Target group chat ID
        prayer_name: Prayer name (Fajr, Dhuhr, Asr, Maghrib, Isha)
        prayer_time: Prayer time string

    Returns:
        bool: True if sent successfully
    """
    try:
        prayer_arabic = config.PRAYER_NAMES_ARABIC.get(prayer_name, prayer_name)

        message = f"""
🕌 <b>الأذان - {prayer_arabic}</b> 🕌

حان الآن وقت صلاة {prayer_arabic} - {prayer_time}

حَيَّ عَلَى الصَّلاَةِ، حَيَّ عَلَى الْفَلاَحِ

🤲 اللَّهُمَّ اجْعَلْنَا مِنَ الْمُحْتَفِظِينَ بِالصَّلَوَاتِ 🤲
        """

        # Create inline keyboard for prayer logging
        keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
        btn_prayed = telebot.types.InlineKeyboardButton(
            f'✅ صليت {prayer_arabic}',
            callback_data=f'prayed_{prayer_name.lower()}'
        )
        keyboard.add(btn_prayed)

        # Send message
        bot.send_message(chat_id, message, parse_mode='HTML', reply_markup=keyboard)
        logger.info(f"✅ Sent azan notification for {prayer_name} to group {chat_id}")
        return True

    except ApiTelegramException as e:
        # Smart handling of Telegram errors
        error_code = e.result_json.get('error_code')
        description = e.result_json.get('description', '')

        if error_code == 403 or 'kicked' in description or 'blocked' in description:
            logger.warning(f"🚫 Bot was kicked/blocked from group {chat_id}. Deleting data now...")
            # Delete group from database to prevent repeated errors
            from database import reset_group_data
            reset_group_data(chat_id)
        else:
            logger.error(f"⚠️ Telegram API Error for {chat_id}: {e}")

        return False

    except Exception as e:
        logger.error(f"❌ General Error sending azan notification: {e}", exc_info=True)
        return False


def send_test_azan(bot: telebot.TeleBot, chat_id: int) -> bool:
    """
    Send a test azan notification for testing purposes.

    Args:
        bot: TeleBot instance
        chat_id: Target group chat ID

    Returns:
        bool: True if sent successfully
    """
    try:
        # Send test azan for Dhuhr prayer
        return send_azan_notification(bot, chat_id, 'Dhuhr', '12:00 (تجربة)')
    except Exception as e:
        logger.error(f"Error in send_test_azan: {e}", exc_info=True)
        return False


# =====================================================
# GENERAL NOTIFICATIONS
# =====================================================

def send_success_message(bot: telebot.TeleBot, chat_id: int, message: str) -> bool:
    """
    Send a success message.

    Args:
        bot: TeleBot instance
        chat_id: Target chat ID
        message: Message text

    Returns:
        bool: True if sent successfully
    """
    from utils import send_message_safe
    return send_message_safe(bot, chat_id, message, parse_mode='HTML')


def send_error_message(bot: telebot.TeleBot, chat_id: int,
                     error_text: str = "حدث خطأ! ❌") -> bool:
    """
    Send an error message.

    Args:
        bot: TeleBot instance
        chat_id: Target chat ID
        error_text: Error message text

    Returns:
        bool: True if sent successfully
    """
    from utils import send_message_safe
    return send_message_safe(bot, chat_id, error_text, parse_mode='HTML')
