"""Tests for brain/memory_manager.py and brain/memory_retriever.py,
the save/lock/fade/forget system and relevance retrieval."""

from datetime import datetime, timedelta, timezone

import pytest

from brain import memory_retriever
from brain.memory_manager import MemoryManager


@pytest.fixture
def memory():
    m = MemoryManager(":memory:")
    yield m
    m.close()


# ---- saving ----

def test_save_and_read_back(memory):
    memory.save("Skyler built Stelly on a Raspberry Pi", kind="fact", importance=4)
    memories = memory.all_memories()
    assert len(memories) == 1
    assert memories[0]["importance"] == 4
    assert memories[0]["kind"] == "fact"


def test_importance_is_clamped(memory):
    memory.save("too big", importance=99)
    memory.save("too small", importance=-5)
    values = {m["content"]: m["importance"] for m in memory.all_memories()}
    assert values["too big"] == 5
    assert values["too small"] == 1


def test_bad_kind_becomes_fact(memory):
    memory.save("weird kind", kind="banana")
    assert memory.all_memories()[0]["kind"] == "fact"


# ---- forgetting and locking ----

def test_unlocked_memory_can_be_forgotten(memory):
    mem_id = memory.save("temporary thing")
    assert memory.forget(mem_id) is True
    assert memory.all_memories() == []


def test_locked_memory_refuses_to_be_forgotten(memory):
    mem_id = memory.save("first day alive", kind="emotional", locked=True)
    assert memory.forget(mem_id) is False
    assert len(memory.all_memories()) == 1


def test_forgetting_nonexistent_returns_false(memory):
    assert memory.forget(12345) is False


# ---- fading ----

def _age_memory(memory, mem_id, days):
    """Backdate a memory's last recall so fading logic sees it as old."""
    old = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    memory._conn.execute(
        "UPDATE memories SET last_recalled_at = ? WHERE id = ?", (old, mem_id)
    )
    memory._conn.commit()


def test_stale_memory_fades_one_point(memory):
    mem_id = memory.save("fading thought", importance=3)
    _age_memory(memory, mem_id, days=15)
    faded, forgotten = memory.fade()
    assert (faded, forgotten) == (1, 0)
    assert memory.all_memories()[0]["importance"] == 2


def test_minimum_importance_stale_memory_is_forgotten(memory):
    mem_id = memory.save("barely mattered", importance=1)
    _age_memory(memory, mem_id, days=15)
    faded, forgotten = memory.fade()
    assert (faded, forgotten) == (0, 1)
    assert memory.all_memories() == []


def test_locked_memory_never_fades(memory):
    mem_id = memory.save("core memory", importance=1, locked=True)
    _age_memory(memory, mem_id, days=400)
    faded, forgotten = memory.fade()
    assert (faded, forgotten) == (0, 0)
    assert memory.all_memories()[0]["importance"] == 1


def test_fresh_memory_does_not_fade(memory):
    memory.save("just happened", importance=3)
    faded, forgotten = memory.fade()
    assert (faded, forgotten) == (0, 0)


# ---- persistent state (mood continuity) ----

def test_mood_persists(memory):
    memory.set_state("mood", "happy")
    assert memory.get_state("mood") == "happy"


def test_state_overwrites(memory):
    memory.set_state("mood", "happy")
    memory.set_state("mood", "sleepy")
    assert memory.get_state("mood") == "sleepy"


def test_missing_state_returns_default(memory):
    assert memory.get_state("nope", default="neutral") == "neutral"


# ---- retrieval ----

def test_relevant_memory_is_retrieved(memory):
    memory.save("Skyler is learning guitar", importance=3)
    memory.save("The Pi uses a HyperPixel display", importance=3)
    found = memory_retriever.relevant_memories(memory, "how is my guitar practice going?")
    assert found == ["Skyler is learning guitar"]


def test_irrelevant_query_returns_nothing(memory):
    memory.save("Skyler is learning guitar", importance=3)
    found = memory_retriever.relevant_memories(memory, "what time is it")
    assert found == []


def test_higher_importance_wins_ties(memory):
    memory.save("guitar lesson was fun", importance=1)
    memory.save("guitar recital is coming", importance=5)
    found = memory_retriever.relevant_memories(memory, "tell me about guitar", limit=1)
    assert found == ["guitar recital is coming"]


def test_retrieval_touches_recall_count(memory):
    mem_id = memory.save("Skyler is learning guitar")
    memory_retriever.relevant_memories(memory, "guitar?")
    recalled = [m for m in memory.all_memories() if m["id"] == mem_id][0]
    assert recalled["recall_count"] == 1


def test_limit_is_respected(memory):
    for i in range(10):
        memory.save(f"guitar fact number {i}")
    found = memory_retriever.relevant_memories(memory, "guitar", limit=4)
    assert len(found) == 4
