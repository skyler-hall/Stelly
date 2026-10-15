"""
Job listing alerts: watches public new-grad job feeds and texts Skyler
when something matching his preferences shows up.

This is a different concern from tracker/, which follows up on emails
about applications Skyler already sent. This package instead watches for
brand new postings he hasn't applied to yet.

Two sources feed the alert, see simplify_source.py and ba_source.py for
each one's shape and quirks. preferences.py decides what counts as a
match, store.py remembers what has already been texted, pipeline.py ties
the three together.
"""
