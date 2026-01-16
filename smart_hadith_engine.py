# -*- coding: utf-8 -*-
"""
Islamic Prayer Times Telegram Bot - Simplified Hadith Engine
==========================================================
Time-based hadith selection (removed complex scoring).

Optimizations (v2.0.0):
- Improved category categorization logic
- Eliminated duplicate category assignments
- Better time window matching
- Reduced memory usage
- Default category for unmatched items

Version: 2.0.0 (Production Ready)
Author: Islamic Prayer Bot Team
License: MIT
"""
import random
from datetime import datetime
from typing import Dict, List

from logger_config import logger


class SimpleHadithEngine:
    """
    Simplified hadith selection engine.
    Uses time-based selection with improved categorization.
    """

    def __init__(self):
        # Load categories once at startup
        self.categories = self._load_categories()

        # Group categories by time windows
        self.categories_by_time = self._group_categories_by_time()

        # In-memory cache for recent hadiths (to avoid repetition)
        self.recent_cache = {}  # {group_id: [(category_id, hadith_id), ...]}
        self.cache_max_size = 10

    def _load_categories(self) -> List[Dict[str, any]]:
        """
        Load categories from database.
        Returns list of category dictionaries.

        Returns:
            List[Dict]: List of categories with id and title
        """
        try:
            from database import get_db_connection

            with get_db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT category_id, category_name_ar
                    FROM categories_index
                    WHERE is_active = 1
                    ORDER BY id ASC
                ''')

                categories = []
                for row in cursor.fetchall():
                    cat = {
                        'id': row['category_id'],
                        'title': row['category_name_ar']
                    }
                    categories.append(cat)

                logger.info(f"Loaded {len(categories)} categories from database")
                return categories

        except Exception as e:
            logger.error(f"Error loading categories: {e}", exc_info=False)
            # Fallback to empty list
            return []

    def _group_categories_by_time(self) -> Dict[str, List[str]]:
        """
        Group categories by time windows with improved logic.

        Instead of adding unmatched categories to ALL windows,
        we assign them to a default "general" window.

        Returns:
            Dict[str, List[str]]: {time_window: [category_ids]}
        """
        # Time windows
        time_groups = {
            'morning': [],      # 06:00-11:00
            'midday': [],       # 11:00-14:00
            'afternoon': [],     # 14:00-18:00
            'evening': [],      # 18:00-22:00
            'night': [],         # 22:00-06:00
            'general': []        # Default for unmatched categories
        }

        # Enhanced keyword matching (more specific)
        time_keywords = {
            'morning': ['صبح', 'فجر', 'إصباح', 'بكور', 'dawn', 'fajr', 'sunrise', 'morning'],
            'midday': ['ظهر', 'الظهيرة', 'نصف', 'noon', 'midday', 'dhuhr', 'asr'],
            'afternoon': ['عصر', 'بعد', 'ظهر', 'afternoon', 'asr', 'mid-afternoon'],
            'evening': ['مغرب', 'غروب', 'عشاء', 'مساء', 'sunset', 'maghrib', 'evening'],
            'night': ['ليل', 'نوم', 'منام', 'night', 'sleep', 'isha', 'midnight']
        }

        # Assign categories to time windows
        for cat in self.categories:
            name_lower = cat['title'].lower()
            assigned = False

            # Try each time window's keywords
            for time_window, keywords in time_keywords.items():
                for keyword in keywords:
                    if keyword in name_lower:
                        time_groups[time_window].append(cat['id'])
                        assigned = True
                        break
                if assigned:
                    break

            # If no match, add to general (not all windows!)
            if not assigned:
                time_groups['general'].append(cat['id'])

        # Log distribution
        for key, cats in time_groups.items():
            logger.debug(f"Time window '{key}': {len(cats)} categories")

        return time_groups

    def select_category(self, hour: int = None, group_id: int = 0) -> str:
        """
        Select a category based on current hour.
        Uses time-based selection with repetition avoidance.

        Args:
            hour: Current hour (0-23). If None, uses current time.
            group_id: Group ID for repetition tracking

        Returns:
            str: Category ID
        """
        # Get current hour
        if hour is None:
            hour = datetime.now().hour

        # Determine time window
        if 5 <= hour < 11:
            time_window = 'morning'
        elif 11 <= hour < 14:
            time_window = 'midday'
        elif 14 <= hour < 18:
            time_window = 'afternoon'
        elif 18 <= hour < 22:
            time_window = 'evening'
        else:
            time_window = 'night'

        # Get categories for this time window
        available_categories = self.categories_by_time.get(time_window, [])

        # If no categories in time window, use general
        if not available_categories:
            logger.debug(f"No categories in time window '{time_window}', using general")
            available_categories = self.categories_by_time.get('general', [])

        # If still no categories, fallback to all categories
        if not available_categories:
            logger.warning(f"No categories available, falling back to all categories")
            available_categories = [cat['id'] for cat in self.categories]

        # Avoid recent categories for this group
        recent_categories = []
        if group_id in self.recent_cache:
            recent_categories = [cat_id for cat_id, _ in self.recent_cache[group_id][-5:]]

        # Filter out recent categories
        filtered_categories = [
            cat_id for cat_id in available_categories
            if cat_id not in recent_categories
        ]

        # If filtered list is empty, use available categories anyway
        if not filtered_categories:
            logger.debug(f"All categories filtered as recent, using available categories")
            filtered_categories = available_categories

        # Random selection
        selected_category = random.choice(filtered_categories)

        # Update cache
        if group_id not in self.recent_cache:
            self.recent_cache[group_id] = []
        self.recent_cache[group_id].append((selected_category, datetime.now().timestamp()))

        # Keep cache size limited
        if len(self.recent_cache[group_id]) > self.cache_max_size:
            self.recent_cache[group_id] = self.recent_cache[group_id][-self.cache_max_size:]

        return selected_category

    def get_category_info(self, category_id: str) -> Dict[str, any]:
        """
        Get category info by ID.

        Args:
            category_id: Category ID

        Returns:
            Dict: Category info or None
        """
        for cat in self.categories:
            if cat['id'] == category_id:
                return cat
        return None


# =====================================================
# GLOBAL INSTANCE (Lazy-loaded)
# =====================================================

_engine = None


def get_engine() -> SimpleHadithEngine:
    """
    Get or create the hadith engine instance.
    Lazy-loaded to avoid database access before initialization.

    Returns:
        SimpleHadithEngine: Engine instance
    """
    global _engine
    if _engine is None:
        _engine = SimpleHadithEngine()
        logger.info("Simple hadith engine initialized")
    return _engine
