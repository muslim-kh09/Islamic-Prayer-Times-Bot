#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Islamic Prayer Times Telegram Bot
==================================
A multi-group Telegram bot for tracking prayer times, sending azan notifications,
and managing religious content (athkar, hadiths).

This is the main entry point for the application.

Version: 2.0.0 (Modular Refactor - Production Ready)

Author: Islamic Prayer Bot Team
License: MIT
"""
import sys
import signal
import threading
import requests

import config
import telebot
from logger_config import logger
from database import initialize_database
from scheduler_service import start_schedulers, stop_schedulers, shutdown_event
from bot_handlers import register_handlers


# =====================================================
# BOT INSTANCE
# =====================================================

bot = telebot.TeleBot(config.BOT_TOKEN)


# =====================================================
# SIGNAL HANDLER
# =====================================================

def signal_handler(signum, frame):
    """
    Handle system signals for graceful shutdown.
    SIGINT: Ctrl+C, SIGTERM: systemd/systemd stop
    """
    logger.info(f"Received signal {signum}, shutting down...")

    # Signal all threads to stop
    shutdown_event.set()

    # Wait for threads to finish (with timeout)
    logger.info("Waiting for threads to finish...")
    import time
    time.sleep(1)

    logger.info("Graceful shutdown complete")
    sys.exit(0)


# =====================================================
# CONFIGURATION VALIDATION
# =====================================================

def validate_configuration() -> bool:
    """
    Validate all configuration before starting.

    Returns:
        bool: True if configuration is valid
    """
    errors = config.validate_config()

    if errors:
        logger.error("❌ Configuration validation failed:")
        for error in errors:
            logger.error(f"  {error}")
        print("\n❌ Configuration validation failed. Check bot_debug.log for details.")
        print("\n🔧 Fix following issues:")
        for error in errors:
            print(f"  {error}")
        return False

    return True


def check_api_connectivity() -> bool:
    """
    Check if external APIs are accessible.

    Returns:
        bool: True if APIs are accessible
    """
    try:
        # Check Aladhan API
        response = requests.get(
            config.ALADHAN_API_BASE,
            params={'city': 'Riyadh', 'country': 'Saudi Arabia', 'method': '2'},
            timeout=5
        )
        if response.status_code == 200:
            logger.info("✅ Aladhan API is accessible")
        else:
            logger.warning(f"⚠️ Aladhan API returned status code: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Aladhan API: {e}")
        return False

    return True


# =====================================================
# MAIN ENTRY POINT
# =====================================================

def main():
    """
    Main entry point for bot.
    Validates configuration, initializes database, handles graceful shutdown,
    manages daemon threads.
    """
    # Validate configuration before starting
    if not validate_configuration():
        sys.exit(1)

    # Check API connectivity
    if not check_api_connectivity():
        logger.warning("⚠️ API connectivity issues detected. Bot may have limited functionality.")

    logger.info("=" * 60)
    logger.info("Islamic Prayer Times Telegram Bot Starting...")
    logger.info("=" * 60)

    # Initialize database
    initialize_database()

    # Register all bot handlers
    register_handlers(bot)
    logger.info("✅ All bot handlers registered successfully")
    
    # Set bot instance for scheduler
    from scheduler_service import set_bot_instance
    set_bot_instance(bot)
    logger.info("✅ Bot instance set for scheduler")

    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start schedulers in separate threads
    start_schedulers()
    logger.info("✅ All schedulers started successfully")

    # Start bot polling
    logger.info("Starting bot polling...")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=120)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, initiating shutdown...")
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        logger.error(f"Bot polling error: {e}", exc_info=True)
        # Attempt graceful shutdown
        stop_schedulers()


# =====================================================
# ENTRY POINT
# =====================================================

if __name__ == '__main__':
    main()
