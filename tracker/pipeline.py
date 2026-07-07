"""
The tracker's assembly line: fetched emails go in, tracked applications
come out.

For each message: skip it if the seen set already has its message ID,
extract a company name from the sender, look that company up, and apply
the matching rule. New company means a new application row. Exactly one
existing application means attach the email as an event. Multiple open
applications at the same company means flag for manual review, because
guessing wrong silently is worse than asking.

Every processed message ends up in the seen set no matter which branch
it took, so reruns are always safe.
"""

from tracker import matcher


def process_messages(store, messages):
    """Run fetched messages through dedup, matching, and storage.

    Returns a summary dict of what happened, handy for logging and for
    Stelly to narrate later ("Two new applications today!").
    """
    summary = {"new": 0, "matched": 0, "ambiguous": 0,
               "skipped_seen": 0, "unparseable": 0, "details": []}

    for message in messages:
        message_id = (message.get("message_id") or "").strip()
        if not message_id:
            summary["unparseable"] += 1
            continue
        if store.is_seen(message_id):
            summary["skipped_seen"] += 1
            continue

        company = matcher.extract_company(message.get("sender", ""))
        if not company:
            # Nothing trustworthy to key on: park it as an unmatched
            # application row flagged for review, never guess.
            app_id = store.add_application(company="(unknown)", role="")
            store.flag_for_review(app_id, f"Could not extract company from: "
                                          f"{message.get('sender', '')!r}")
            store.add_event(app_id, message_id=message_id,
                            subject=message.get("subject", ""),
                            sender=message.get("sender", ""))
            store.mark_seen(message_id)
            summary["unparseable"] += 1
            continue

        existing = store.find_by_company(company)
        decision, application = matcher.decide_match(company, existing)

        subject = message.get("subject", "")
        if decision == "new":
            app_id = store.add_application(company=company)
            summary["new"] += 1
            summary["details"].append(f"New: {company} ({subject})")
        elif decision == "matched":
            app_id = application["id"]
            summary["matched"] += 1
            summary["details"].append(f"Update from {company}: {subject}")
        else:  # ambiguous
            app_id = existing[0]["id"]
            store.flag_for_review(app_id, f"{len(existing)} open applications "
                                          f"at {company}, attach manually")
            summary["ambiguous"] += 1
            summary["details"].append(f"Needs review, {company}: {subject}")

        store.add_event(app_id, message_id=message_id,
                        subject=message.get("subject", ""),
                        sender=message.get("sender", ""))
        store.mark_seen(message_id)

    return summary
