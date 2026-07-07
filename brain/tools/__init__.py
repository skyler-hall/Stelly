"""
Tool registry. This is the one place ai_handler.py looks to find out what
Stelly is capable of doing. Adding a new tool means writing the function
and its description elsewhere in this package, then registering both
here, ai_handler.py itself never needs to change.
"""

from brain.tools.clock import GET_TIME_TOOL, get_current_time
from brain.tools.email import CHECK_EMAIL_TOOL, check_email
from brain.tools.leetcode import (
    GET_DAILY_CHALLENGE_TOOL,
    GET_LEETCODE_PROGRESS_TOOL,
    get_leetcode_daily,
    get_leetcode_progress,
)
from brain.tools.memory import (
    FORGET_TOOL,
    LIST_MEMORIES_TOOL,
    REMEMBER_TOOL,
    forget_memory,
    list_memories,
    remember_this,
)
from brain.tools.music import PLAY_MUSIC_TOOL, play_music
from brain.tools.preferences import (
    GET_NOTIFICATION_PREFERENCES_TOOL,
    SET_NOTIFICATION_PREFERENCE_TOOL,
    get_notification_preferences,
    set_notification_preference,
)

TOOL_DEFINITIONS = [
    PLAY_MUSIC_TOOL,
    CHECK_EMAIL_TOOL,
    GET_TIME_TOOL,
    GET_LEETCODE_PROGRESS_TOOL,
    GET_DAILY_CHALLENGE_TOOL,
    REMEMBER_TOOL,
    LIST_MEMORIES_TOOL,
    FORGET_TOOL,
    SET_NOTIFICATION_PREFERENCE_TOOL,
    GET_NOTIFICATION_PREFERENCES_TOOL,
]

TOOL_FUNCTIONS = {
    "play_music": play_music,
    "check_email": check_email,
    "get_current_time": get_current_time,
    "get_leetcode_progress": get_leetcode_progress,
    "get_leetcode_daily": get_leetcode_daily,
    "remember_this": remember_this,
    "list_memories": list_memories,
    "forget_memory": forget_memory,
    "set_notification_preference": set_notification_preference,
    "get_notification_preferences": get_notification_preferences,
}
