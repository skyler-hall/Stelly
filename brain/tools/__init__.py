"""
Tool registry. This is the one place ai_handler.py looks to find out what
Stelly is capable of doing. Adding a new tool means writing the function
and its description elsewhere in this package, then registering both
here, ai_handler.py itself never needs to change.
"""

from brain.tools.clock import GET_TIME_TOOL, get_current_time
from brain.tools.email import CHECK_EMAIL_TOOL, check_email
from brain.tools.music import PLAY_MUSIC_TOOL, play_music

TOOL_DEFINITIONS = [
    PLAY_MUSIC_TOOL,
    CHECK_EMAIL_TOOL,
    GET_TIME_TOOL,
]

TOOL_FUNCTIONS = {
    "play_music": play_music,
    "check_email": check_email,
    "get_current_time": get_current_time,
}
