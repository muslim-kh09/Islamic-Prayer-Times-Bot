# -*- coding: utf-8 -*-
"""
Islamic Prayer Times Telegram Bot - Utility Functions
=================================================
Helper functions used across the application.

Version: 2.0.0 (Production Ready)
Author: Islamic Prayer Bot Team
License: MIT
"""
from typing import Optional
import logging

logger = logging.getLogger('IslamicPrayerBot')


# =====================================================
# TIME UTILITIES
# =====================================================

def parse_time(time_str: str) -> tuple:
    """
    Parse time string in HH:MM format.

    Args:
        time_str: Time string (e.g., "12:30")

    Returns:
        tuple: (hour, minute) or (0, 0) if parsing fails
    """
    try:
        parts = time_str.split(':')
        return int(parts[0]), int(parts[1])
    except Exception:
        logger.error(f"Error parsing time string: {time_str}")
        return 0, 0


def time_within_window(current_time: tuple, prayer_time: tuple,
                       window_minutes: int = 1) -> bool:
    """
    Check if current time is within the specified window of prayer time.

    Args:
        current_time: Tuple (hour, minute) of current time
        prayer_time: Tuple (hour, minute) of prayer time
        window_minutes: Window in minutes (default: 1)

    Returns:
        bool: True if current time is within window
    """
    try:
        current_minutes = current_time[0] * 60 + current_time[1]
        prayer_minutes = prayer_time[0] * 60 + prayer_time[1]

        return abs(current_minutes - prayer_minutes) <= window_minutes

    except Exception as e:
        logger.error(f"Error in time_within_window: {e}", exc_info=True)
        return False


# =====================================================
# MESSAGE SENDING UTILITIES
# =====================================================

def send_message_safe(bot, chat_id: int, text: str, parse_mode: str = 'HTML',
                   disable_web_page_preview: bool = False) -> bool:
    """
    Send a message with retry mechanism for better resilience.

    Args:
        bot: TeleBot instance
        chat_id: Target chat ID
        text: Message text
        parse_mode: Parse mode (HTML or Markdown)
        disable_web_page_preview: Disable web link preview

    Returns:
        bool: True if message sent successfully
    """
    from config import MAX_RETRIES, RETRY_DELAY
    from telebot.apihelper import ApiTelegramException

    for attempt in range(MAX_RETRIES):
        try:
            bot.send_message(
                chat_id,
                text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview
            )
            logger.debug(f"Message sent to {chat_id} on attempt {attempt + 1}")
            return True

        except Exception as e:
            error_type = type(e).__name__
            logger.warning(f"Send attempt {attempt + 1} failed: {error_type} - {e}")

            # If it's the last attempt, return False
            if attempt == MAX_RETRIES - 1:
                logger.error(f"All {MAX_RETRIES} attempts failed for chat {chat_id}: {e}")

                # Check if it's a connection error
                if 'Connection' in error_type or 'RemoteDisconnected' in error_type:
                    return False  # Don't show error to user
                else:
                    try:
                        bot.send_message(
                            chat_id,
                            "عذراً، حدث خطأ في إرسال الرسالة. يرجى المحاولة لاحقاً ❌"
                        )
                    except Exception:
                        pass
                return False

            # Wait before retry
            import time
            time.sleep(RETRY_DELAY)

    return False


# =====================================================
# ADMIN CHECK UTILITIES
# =====================================================

def is_user_admin(bot, chat_id: int, user_id: int) -> bool:
    """
    Check if a user is an admin in the specified chat.

    Args:
        bot: TeleBot instance
        chat_id: The chat/group ID
        user_id: The user's Telegram ID

    Returns:
        bool: True if user is admin, False otherwise
    """
    try:
        # Get list of administrators
        admins = bot.get_chat_administrators(chat_id)

        # Check if user is in admin list
        for admin in admins:
            if admin.user.id == user_id:
                return True

        return False

    except Exception as e:
        logger.error(f"Error checking admin status for user {user_id}: {e}", exc_info=True)
        return False
