# -*- coding: utf-8 -*-
"""
Islamic Prayer Times Telegram Bot - Prefetch Service (DISABLED)
==============================================================
This module is DISABLED in the optimized version.

The system now uses lazy on-demand caching instead of aggressive prefetch.
See hadith_system.py for the new lazy caching implementation.

This file is kept for compatibility but does nothing.
"""

# Prefetch service has been disabled in favor of lazy caching.
# The hadith_system.py now handles on-demand fetching when cache is empty.


def initialize_prefetch_service(shutdown_event):
    """
    Placeholder function for compatibility.
    Does nothing in the optimized version.
    """
    pass


def stop_prefetch_service():
    """
    Placeholder function for compatibility.
    Does nothing in the optimized version.
    """
    pass


def get_prefetch_service():
    """
    Placeholder function for compatibility.
    Returns None in the optimized version.
    """
    return None
