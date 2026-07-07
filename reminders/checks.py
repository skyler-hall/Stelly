"""
The checks behind Stelly's text message reminders.

Two checks live here. The LeetCode reminder fires in the evening if no
accepted submission happened today, and includes today's daily challenge
as a concrete suggestion. The job application alert runs the tracker
pipeline against Gmail and texts whatever new application activity it
found (the seen set guarantees nothing is ever texted twice).

Both are toggleable by talking to Stelly ("stop the leetcode reminders"),
the preferences persist in his memory database, and both are safe to
call as often as you like: they dedupe themselves, skip quietly when
turned off or unconfigured, and never raise.
"""

from datetime import datetime

from brain.memory_manager import get_manager
from notify import notify

REMINDER_HOUR = 18          # leetcode nag opens for business at 6pm local
PREF_LEETCODE = "pref_leetcode_reminders"
PREF_JOBS = "pref_job_alerts"
LAST_SENT_KEY = "leetcode_reminder_sent"

FETCH_LIMIT = 15


def pref_enabled(key, manager=None):
    """Preferences default to on. Stelly's tools write 'off' to disable."""
    manager = manager or get_manager()
    return manager.get_state(key, "on") != "off"


def solved_leetcode_today(now=None):
    """True if any accepted submission happened today (local time).
    None when the API is unreachable, so callers can skip rather than
    nag someone who might have actually done the work."""
    from brain.tools import leetcode
    from config import settings

    if not settings.LEETCODE_USERNAME:
        return None
    try:
        recent = leetcode._get(
            f"/{settings.LEETCODE_USERNAME}/acSubmission?limit=10")
    except Exception:
        return None

    today = (now or datetime.now()).date()
    for submission in recent.get("submission", []):
        try:
            when = datetime.fromtimestamp(int(submission["timestamp"]))
        except (KeyError, ValueError, TypeError, OSError):
            continue
        if when.date() == today:
            return True
    return False


def _daily_suggestion():
    """Today's challenge as a short suggestion line, best effort."""
    from brain.tools import leetcode
    try:
        daily = leetcode._get("/daily")
        title = daily.get("questionTitle", "")
        link = daily.get("questionLink") or daily.get("link", "")
        if title:
            return f" Today's daily: {title}. {link}".rstrip()
    except Exception:
        pass
    return ""


def leetcode_reminder(manager=None, now=None, force=False):
    """Send the evening nag if no problem was solved today.
    Returns a short string describing what happened, for logs."""
    manager = manager or get_manager()
    now = now or datetime.now()

    if not pref_enabled(PREF_LEETCODE, manager):
        return "leetcode reminders are off"

    today = now.date().isoformat()
    if not force and manager.get_state(LAST_SENT_KEY) == today:
        return "already reminded today"

    solved = solved_leetcode_today(now)
    if solved is None:
        return "could not check, skipped"
    if solved:
        return "already solved today, no reminder needed"

    message = ("Stelly here! No LeetCode solved today yet. One little "
               "problem before bed?" + _daily_suggestion())
    if notify(message):
        manager.set_state(LAST_SENT_KEY, today)
        return "reminder sent"
    return "no notification channel configured"


def job_application_alert(manager=None, store=None, fetch_messages=None):
    """Scan Gmail for application email and text a summary of anything
    new. The tracker's seen set makes this naturally idempotent.
    Returns a short string describing what happened, for logs."""
    manager = manager or get_manager()

    if not pref_enabled(PREF_JOBS, manager):
        return "job alerts are off"

    if fetch_messages is None:
        from config import settings
        from tracker import gmail_reader

        def fetch_messages():
            return gmail_reader.fetch_recent_messages(
                limit=FETCH_LIMIT, search_query=settings.TRACKER_QUERY)

    if store is None:
        from tracker.store import TrackerStore
        store = TrackerStore()

    try:
        messages = fetch_messages()
    except Exception as error:
        return f"could not read gmail: {error}"

    from tracker.pipeline import process_messages
    summary = process_messages(store, messages)

    if not summary["details"]:
        return "nothing new"

    lines = summary["details"][:5]
    if len(summary["details"]) > 5:
        lines.append(f"...and {len(summary['details']) - 5} more")
    message = "Stelly job tracker:\n" + "\n".join(lines)

    if notify(message):
        return f"alerted about {len(summary['details'])} item(s)"
    return "found activity but no notification channel configured"


def run_due_checks(manager=None, now=None):
    """One pass of everything, called periodically while Stelly runs and
    once per run of the standalone runner. Cheap when nothing is due."""
    now = now or datetime.now()
    results = {"jobs": job_application_alert(manager)}
    if now.hour >= REMINDER_HOUR:
        results["leetcode"] = leetcode_reminder(manager, now)
    else:
        results["leetcode"] = "too early, reminder opens at " + str(REMINDER_HOUR)
    return results
