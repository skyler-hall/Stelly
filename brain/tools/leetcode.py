"""
Stelly's window into Skyler's LeetCode grind.

Talks to alfa-leetcode-api (github.com/alfaarghya/alfa-leetcode-api),
a REST wrapper around LeetCode's GraphQL. Two tools: one reads progress
(total solved, split by difficulty, plus the most recent accepted
submissions), one fetches the official daily challenge so Stelly can
suggest a concrete next problem instead of vague encouragement.

The public instance at alfa-leetcode-api.onrender.com runs on a free
tier that sleeps when idle, so the first call after a quiet stretch can
be slow or time out, trying again a minute later usually works. It is
also rate limited, another reason these tools fetch only when the
conversation calls for it. LEETCODE_API_URL in .env can point at a
self hosted docker copy later for speed and no limits.
"""

import requests

from config import settings

TIMEOUT_SECONDS = 30
RECENT_SUBMISSIONS = 5

GET_LEETCODE_PROGRESS_TOOL = {
    "name": "get_leetcode_progress",
    "description": (
        "Check Skyler's LeetCode progress: how many problems he has solved "
        "in total and by difficulty, and his most recent accepted "
        "submissions. Use when he asks about his progress, wants "
        "encouragement or accountability about coding practice, or asks "
        "what he has been working on."
    ),
    "input_schema": {"type": "object", "properties": {}},
}

GET_DAILY_CHALLENGE_TOOL = {
    "name": "get_leetcode_daily",
    "description": (
        "Get today's official LeetCode daily challenge: its title, "
        "difficulty, topic tags, and link. Use when Skyler asks what to "
        "practice, wants a problem suggestion, or when nudging him to get "
        "one more question done today."
    ),
    "input_schema": {"type": "object", "properties": {}},
}


def _get(path):
    """One GET against the API, returning parsed JSON or raising with a
    message friendly enough to hand straight back to the model."""
    base = settings.LEETCODE_API_URL.rstrip("/")
    response = requests.get(f"{base}{path}", timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def get_leetcode_progress():
    username = settings.LEETCODE_USERNAME
    if not username:
        return "LEETCODE_USERNAME is not set in .env, so progress cannot be checked yet."

    try:
        solved = _get(f"/{username}/solved")
        recent = _get(f"/{username}/acSubmission?limit={RECENT_SUBMISSIONS}")
    except requests.exceptions.Timeout:
        return ("The LeetCode stats service is waking up (it sleeps when idle). "
                "Try again in a minute.")
    except Exception as error:
        return f"Could not reach LeetCode stats: {error}"

    lines = [
        f"LeetCode progress for {username}:",
        f"Total solved: {solved.get('solvedProblem', '?')}",
        f"Easy: {solved.get('easySolved', '?')}, "
        f"Medium: {solved.get('mediumSolved', '?')}, "
        f"Hard: {solved.get('hardSolved', '?')}",
    ]

    submissions = recent.get("submission", [])
    if submissions:
        lines.append("Most recent accepted solutions:")
        for sub in submissions:
            lines.append(f"- {sub.get('title', 'unknown')} ({sub.get('lang', '?')})")

    return "\n".join(lines)


def get_leetcode_daily():
    try:
        daily = _get("/daily")
    except requests.exceptions.Timeout:
        return ("The LeetCode service is waking up (it sleeps when idle). "
                "Try again in a minute.")
    except Exception as error:
        return f"Could not fetch the daily challenge: {error}"

    tags = ", ".join(tag.get("name", "") for tag in daily.get("topicTags", []))
    link = daily.get("questionLink") or daily.get("link", "")
    return (
        f"Today's LeetCode daily challenge: {daily.get('questionTitle', 'unknown')} "
        f"({daily.get('difficulty', '?')})."
        + (f" Topics: {tags}." if tags else "")
        + (f" Link: {link}" if link else "")
    )
