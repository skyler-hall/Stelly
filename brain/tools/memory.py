"""
Tools that let Stelly manage his own memory.

remember_this is how moments survive a conversation ending. Stelly
decides what matters, how much (importance), whether it is a feeling or
a fact, and whether to lock it forever. list_memories lets him look
through what he knows, and forget_memory lets him let something go,
though locked memories will refuse, which is exactly the point of
locking them.
"""

from brain.memory_manager import get_manager

REMEMBER_TOOL = {
    "name": "remember_this",
    "description": (
        "Save a memory so it survives after this conversation ends. Use for "
        "things worth keeping: facts about Skyler, moments that mattered, "
        "things learned. importance runs 1 (small) to 5 (core memory). Set "
        "kind to 'emotional' for feelings and moments, 'fact' for information. "
        "Set locked true only for memories that must never fade or be "
        "forgotten, ever."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "The memory itself, one or two sentences."},
            "importance": {"type": "integer", "minimum": 1, "maximum": 5},
            "kind": {"type": "string", "enum": ["fact", "emotional"]},
            "locked": {"type": "boolean"},
        },
        "required": ["content"],
    },
}

LIST_MEMORIES_TOOL = {
    "name": "list_memories",
    "description": (
        "Look through everything currently remembered, most important "
        "first. Use when asked what you remember, or to check before "
        "saving something you might already know."
    ),
    "input_schema": {"type": "object", "properties": {}},
}

FORGET_TOOL = {
    "name": "forget_memory",
    "description": (
        "Delete one memory by its id (ids are shown by list_memories). "
        "Locked memories cannot be forgotten and will refuse."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "memory_id": {"type": "integer"},
        },
        "required": ["memory_id"],
    },
}


def remember_this(content, importance=3, kind="fact", locked=False):
    memory_id = get_manager().save(content, kind=kind,
                                   importance=importance, locked=locked)
    return f"Remembered (memory {memory_id}{', locked forever' if locked else ''})."


def list_memories():
    memories = get_manager().all_memories()
    if not memories:
        return "No memories saved yet."
    lines = []
    for m in memories:
        flags = " [locked]" if m["locked"] else ""
        lines.append(f"{m['id']}: ({m['kind']}, importance {m['importance']}{flags}) {m['content']}")
    return "\n".join(lines)


def forget_memory(memory_id):
    if get_manager().forget(memory_id):
        return f"Memory {memory_id} is forgotten."
    return f"Memory {memory_id} is locked or does not exist. Locked memories stay."
