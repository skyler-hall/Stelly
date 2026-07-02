"""
One shared definition of day and night.

Both the face (auto light and dark theme) and the brain (the
get_current_time tool) need to know whether it is daytime. Keeping the
boundary hours and the helpers here, in config where nothing heavy gets
imported, means the two can never disagree and the display never has to
import brain code just to read a clock.

Fixed hours for now, like the "scheduled" mode on phones. Sunset math
based on location could replace is_daytime later without touching any
caller.
"""

from datetime import datetime, timedelta

DAY_STARTS_HOUR = 7     # 7am, face goes light
NIGHT_STARTS_HOUR = 19  # 7pm, face goes dark


def is_daytime(moment=None):
    moment = moment or datetime.now()
    return DAY_STARTS_HOUR <= moment.hour < NIGHT_STARTS_HOUR


def next_transition(moment=None):
    """The next moment the theme should flip, as a datetime.

    Used by the display's manual override: pressing D forces a theme
    until the next natural sunrise or sunset boundary, then automatic
    switching resumes, the same behavior phones use.
    """
    moment = moment or datetime.now()
    today = moment.replace(minute=0, second=0, microsecond=0)
    candidates = [
        today.replace(hour=DAY_STARTS_HOUR),
        today.replace(hour=NIGHT_STARTS_HOUR),
        today.replace(hour=DAY_STARTS_HOUR) + timedelta(days=1),
    ]
    return min(c for c in candidates if c > moment)
