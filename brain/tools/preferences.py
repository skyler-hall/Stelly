"""
Tools that let Stelly flip Skyler's notification preferences by voice.

"Stelly, stop sending me leetcode reminders" should just work, so these
give the model a switch it can flip. Preferences persist in the memory
database and are read by reminders/checks.py before anything sends.
"""

from brain.memory_manager import get_manager

_FEATURES = {
    "leetcode_reminders": "pref_leetcode_reminders",
    "job_alerts": "pref_job_alerts",
    "job_listings": "pref_job_listing_alerts",
}

SET_NOTIFICATION_PREFERENCE_TOOL = {
    "name": "set_notification_preference",
    "description": (
        "Turn Skyler's text message notifications on or off. Use when he "
        "asks to start or stop LeetCode reminders, job application "
        "alerts, or new job listing alerts. The change persists until he "
        "asks to flip it back."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "feature": {
                "type": "string",
                "enum": ["leetcode_reminders", "job_alerts", "job_listings"],
            },
            "enabled": {"type": "boolean"},
        },
        "required": ["feature", "enabled"],
    },
}

GET_NOTIFICATION_PREFERENCES_TOOL = {
    "name": "get_notification_preferences",
    "description": (
        "Check which of Skyler's text notifications are currently on: "
        "LeetCode reminders, job application alerts, and new job listing "
        "alerts."
    ),
    "input_schema": {"type": "object", "properties": {}},
}


def set_notification_preference(feature, enabled):
    key = _FEATURES.get(feature)
    if key is None:
        return f"Unknown feature: {feature}"
    get_manager().set_state(key, "on" if enabled else "off")
    state = "on" if enabled else "off"
    pretty = feature.replace("_", " ")
    return f"Okay, {pretty} are now {state}."


def get_notification_preferences():
    manager = get_manager()
    lines = []
    for feature, key in _FEATURES.items():
        state = manager.get_state(key, "on")
        lines.append(f"{feature.replace('_', ' ')}: {state}")
    return "\n".join(lines)
