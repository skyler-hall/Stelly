"""
Standalone reminder runner, for when Stelly himself is not running.

Point Windows Task Scheduler (or cron on the Pi) at:

    python -m reminders.run

on whatever schedule feels right, hourly works well. It runs every check
once, prints what happened, and exits. Everything dedupes itself, so an
aggressive schedule never means duplicate texts, it just means each
check's own dedup window (once a day for LeetCode, twice a day for job
listings) decides when something new actually happens.
"""

from reminders import checks

if __name__ == "__main__":
    results = checks.run_due_checks()
    for name, outcome in results.items():
        print(f"{name}: {outcome}")
