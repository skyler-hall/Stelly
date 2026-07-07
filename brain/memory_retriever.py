"""
Pulls the right memories into the conversation.

Before each of Stelly's turns, the user's words get scored against every
stored memory: shared meaningful words, weighted by the memory's
importance. The top few relevant memories ride along in the system
prompt so Stelly can reference them naturally, and each one recalled
this way gets touched, refreshing it against fading, exactly like how
remembering something keeps it fresh for a person.

Plain keyword overlap, no embeddings, on purpose: it is fast, fully
local, easy to reason about when it misbehaves, and good enough for one
person talking to one robot. Swapping in something smarter later only
touches this file.
"""

import re

# Common words that carry no memory-matching signal.
_STOPWORDS = frozenset("""
a an and are as at be but by did do does for from had has have he her him
his how i if in is it its me my no not of on or our she so that the their
them they this to was we what when where which who will with you your
stelly
""".split())

_WORD = re.compile(r"[a-z0-9']+")


def _keywords(text):
    return {word for word in _WORD.findall(text.lower())
            if word not in _STOPWORDS and len(word) > 2}


def score(memory, query_words):
    """Relevance of one memory to the current utterance: shared keyword
    count scaled by how much the memory matters."""
    overlap = len(_keywords(memory["content"]) & query_words)
    if overlap == 0:
        return 0
    return overlap * memory["importance"]


def relevant_memories(manager, user_text, limit=4):
    """The most relevant memories for this turn, as a list of content
    strings, best first. Touches everything it returns so recalled
    memories stay fresh. Empty list when nothing relates."""
    query_words = _keywords(user_text)
    if not query_words:
        return []

    scored = []
    for memory in manager.all_memories():
        relevance = score(memory, query_words)
        if relevance > 0:
            scored.append((relevance, memory))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    chosen = [memory for _, memory in scored[:limit]]

    for memory in chosen:
        manager.touch(memory["id"])

    return [memory["content"] for memory in chosen]
