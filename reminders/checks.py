"""
The checks behind Stelly's text message reminders.

Three checks live here. The LeetCode reminder fires in the evening if no
accepted submission happened today, and includes today's daily challenge
as a concrete suggestion. The job application alert runs the tracker
pipeline against Gmail and texts whatever new application activity it
found (the seen set guarantees nothing is ever texted twice). The job
listing alert watches public new-grad job feeds and texts anything new
that matches Skyler's preferences (see jobs/preferences.py), at most
once every JOB_LISTINGS_INTERVAL_HOURS.

All three are toggleable by talking to Stelly ("stop the leetcode
reminders"), the preferences persist in his memory database, and all are
safe to call as often as you like: they dedupe themselves, skip quietly
when turned off or unconfigured, and never raise.
"""

from datetime import datetime

from brain.memory_manager import get_manager
from notify import notify

REMINDER_HOUR = 18          # leetcode nag opens for business at 6pm local
PREF_LEETCODE = "pref_leetcode_reminders"
PREF_JOBS = "pref_job_alerts"
PREF_JOB_LISTINGS = "pref_job_listing_alerts"
LAST_SENT_KEY = "leetcode_reminder_sent"

FETCH_LIMIT = 15

JOB_LISTINGS_INTERVAL_HOURS = 12   # twice a day
JOB_LISTINGS_LAST_RUN_KEY = "job_listings_last_run_ts"
JOB_LISTINGS_CUTOFF_KEY = "job_listings_cutoff_ts"


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


def job_listing_alert(manager=None, store=None, now=None, force=False):
    """Check public new-grad job feeds for postings matching Skyler's
    preferences and text anything new. Runs at most once every
    JOB_LISTINGS_INTERVAL_HOURS regardless of how often this is called,
    that interval is what makes this "twice a day" rather than the
    calling schedule. Returns a short string describing what happened,
    for logs."""
    manager = manager or get_manager()
    now = now or datetime.now()

    if not pref_enabled(PREF_JOB_LISTINGS, manager):
        return "job listing alerts are off"

    last_run = manager.get_state(JOB_LISTINGS_LAST_RUN_KEY)
    if not force and last_run:
        elapsed_hours = (now.timestamp() - float(last_run)) / 3600
        if elapsed_hours < JOB_LISTINGS_INTERVAL_HOURS:
            remaining = JOB_LISTINGS_INTERVAL_HOURS - elapsed_hours
            return f"checked recently, next check in about {remaining:.1f}h"

    if store is None:
        from jobs.store import JobAlertStore
        store = JobAlertStore()

    cutoff = int(float(manager.get_state(JOB_LISTINGS_CUTOFF_KEY, "0")))

    from jobs.pipeline import find_new_matches
    try:
        matched, new_cutoff = find_new_matches(store, cutoff)
    except Exception as error:
        return f"could not fetch job listings: {error}"

    # The interval gate is about fetch frequency, so it advances whether
    # or not anything matched or the text actually went out.
    manager.set_state(JOB_LISTINGS_CUTOFF_KEY, str(new_cutoff))
    manager.set_state(JOB_LISTINGS_LAST_RUN_KEY, str(now.timestamp()))

    if not matched:
        return "nothing new"

    lines = [f"{item['company']}: {item['title']} ({', '.join(item['locations'])})"
             for item in matched[:5]]
    if len(matched) > 5:
        lines.append(f"...and {len(matched) - 5} more")
    message = "Stelly job listings:\n" + "\n".join(lines)

    if notify(message):
        for item in matched:
            store.mark_notified(item["id"])
        return f"alerted about {len(matched)} listing(s)"
    return "found new listings but no notification channel configured"


def run_due_checks(manager=None, now=None):
    """One pass of everything, called periodically while Stelly runs and
    once per run of the standalone runner. Cheap when nothing is due."""
    now = now or datetime.now()
    results = {
        "jobs": job_application_alert(manager),
        "job_listings": job_listing_alert(manager, now=now),
    }
    if now.hour >= REMINDER_HOUR:
        results["leetcode"] = leetcode_reminder(manager, now)
    else:
        results["leetcode"] = "too early, reminder opens at " + str(REMINDER_HOUR)
    return results
