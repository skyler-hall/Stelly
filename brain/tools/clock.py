"""
Stelly's sense of time.

One tool that hands the brain the current local date and time whenever a
conversation needs it. This is the foundation for everything time shaped
coming later: calendar creation, time blocking, event crafting, and
knowing whether it is day or night. Keeping it as a tool (instead of
stamping the time into every system prompt) means Stelly only reaches
for the clock when the conversation actually calls for it, and always
gets a fresh reading instead of a stale one from the start of a long
chat.
"""

from datetime import datetime

from config.timekeeping import is_daytime

GET_TIME_TOOL = {
    "name": "get_current_time",
    "description": (
        "Look at the clock. Returns the current local date, time, day of "
        "the week, and whether it is currently daytime or nighttime. Use "
        "this whenever the conversation involves the current time or date, "
        "scheduling, how long something has been, or greetings that depend "
        "on the time of day."
    ),
    "input_schema": {"type": "object", "properties": {}},
}

def get_current_time():
    """Current local time, formatted for the model to read naturally."""
    now = datetime.now()
    period = "daytime" if is_daytime(now) else "nighttime"
    return (
        f"It is {now.strftime('%A, %B %d, %Y')} at {now.strftime('%I:%M %p').lstrip('0')}. "
        f"It is currently {period}."
    )
