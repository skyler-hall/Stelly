"""
Tools that let Stelly change his own voice.

"Stelly, use the Henchman voice" should just work. The voices are the
VoiceLab presets whose files are synced on this machine (see
output/audio_output.py). The choice persists in the memory database, so
he keeps the voice across restarts until asked to change it again.
"""

import re

from brain.memory_manager import get_manager
from config import settings
from output import audio_output

# Words that mean "go back to your normal voice".
_DEFAULT_WORDS = {"default", "normal", "usual", "regular", "original", "your own", "your voice"}

SET_VOICE_TOOL = {
    "name": "set_voice",
    "description": (
        "Change the voice Stelly speaks with. Use when Skyler asks Stelly to "
        "sound different, to use a named voice, or to go back to his normal "
        "voice (pass 'default'). Names can be loose, like 'henchman' for "
        "'The Henchman'. Call list_voices first if unsure what exists. The "
        "change lasts until Skyler asks for another voice."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "voice": {
                "type": "string",
                "description": "Voice name, or 'default' for Stelly's normal voice.",
            },
        },
        "required": ["voice"],
    },
}

LIST_VOICES_TOOL = {
    "name": "list_voices",
    "description": (
        "List the voices Stelly can switch to on this machine, and which "
        "one he is using right now."
    ),
    "input_schema": {"type": "object", "properties": {}},
}


def _simplify(name):
    """Lowercase letters and digits only, without a leading 'the'."""
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower()).split()
    if words and words[0] == "the":
        words = words[1:]
    return "".join(words)


def match_voice(asked, choices):
    """Best preset for what Skyler said, or None. Exact first, then the
    same name ignoring case, spaces and 'the', then a unique partial match."""
    if asked in choices:
        return asked
    want = _simplify(asked)
    if not want:
        return None
    same = [c for c in choices if _simplify(c) == want]
    if same:
        return same[0]
    partial = [c for c in choices if want in _simplify(c) or _simplify(c) in want]
    return partial[0] if len(partial) == 1 else None


def set_voice(voice):
    ready = audio_output.ready_presets()
    if not ready:
        return "Stelly can't change voices on this machine. VoiceLab isn't set up here yet."

    if voice.strip().lower() in _DEFAULT_WORDS:
        get_manager().set_state(audio_output.VOICE_STATE_KEY, "")
        return f"Okay, Stelly is back to his normal voice, {settings.VOICE_PRESET}."

    match = match_voice(voice, ready)
    if match is None:
        return f"Stelly doesn't have a voice called {voice}. Voices here: {', '.join(ready)}."
    get_manager().set_state(audio_output.VOICE_STATE_KEY, match)
    return f"Okay, Stelly's voice is now {match}."


def list_voices():
    ready = audio_output.ready_presets()
    if not ready:
        return "Stelly only has one voice on this machine. VoiceLab isn't set up here yet."
    current = audio_output.current_preset()
    lines = [f"{name} (using now)" if name == current else name for name in ready]
    return "Voices Stelly can use:\n" + "\n".join(lines)
