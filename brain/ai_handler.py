"""
Routes a conversation turn to the Claude API and handles tool use.

Desk mode only for now, Ollama routing for travel mode comes later once
there is a mode manager deciding which one to call. Give this a message
history and a mood, get back Stelly's final reply text with any tool
calls already resolved along the way.
"""

import re

import anthropic

from brain.stelly_personality import DEFAULT_MOOD, VALID_MOODS, get_system_prompt
from brain.tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS
from config import settings

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 1024

_client = None


def _get_client():
    """Lazy singleton so the Anthropic client is built once per process."""
    global _client
    if _client is None:
        api_key = settings.require(settings.ANTHROPIC_API_KEY, "ANTHROPIC_API_KEY")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def get_response(messages, mood="neutral"):
    """Send a conversation to Claude and return (reply_text, new_mood).

    messages is the running conversation history, a list of
    {"role": "user" | "assistant", "content": ...} dicts. If Claude wants
    to use a tool, this runs the tool locally and sends the result back,
    looping until a plain text reply comes back.

    The personality prompt asks Stelly to open every reply with a mood
    tag like [happy]. That tag gets parsed off here, so callers receive
    clean speakable text plus the mood Stelly says he is feeling now.
    The incoming mood parameter is how he felt going into the turn, it
    shapes the system prompt. The returned mood is how he feels after.
    """
    client = _get_client()
    system_prompt = get_system_prompt(mood)
    conversation = list(messages)

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=conversation,
        )

        if response.stop_reason != "tool_use":
            return _split_mood(_extract_text(response), fallback=mood)

        conversation.append({"role": "assistant", "content": response.content})

        tool_results = [
            _run_tool(block)
            for block in response.content
            if block.type == "tool_use"
        ]
        conversation.append({"role": "user", "content": tool_results})


def _run_tool(tool_use_block):
    """Execute one tool call and package the result the shape the API
    expects back. Errors get caught and handed back as the tool result
    text instead of crashing the conversation, so Stelly can say
    something went wrong instead of the whole turn failing silently."""
    function = TOOL_FUNCTIONS.get(tool_use_block.name)
    if function is None:
        result_text = f"Unknown tool: {tool_use_block.name}"
    else:
        try:
            result_text = function(**tool_use_block.input)
        except Exception as error:
            result_text = f"Tool {tool_use_block.name} failed: {error}"

    return {
        "type": "tool_result",
        "tool_use_id": tool_use_block.id,
        "content": str(result_text),
    }


def _extract_text(response):
    """Pull the plain text out of a Claude response, joining multiple
    text blocks together if there happen to be more than one."""
    return "".join(block.text for block in response.content if block.type == "text")


_MOOD_TAG = re.compile(r"^\s*\[(\w+)\]\s*")


def _split_mood(text, fallback=DEFAULT_MOOD):
    """Split a leading [mood] tag off the reply text.

    Returns (clean_text, mood). If the tag is missing or names a mood
    that does not exist, the fallback mood carries over, a model that
    forgets its tag one turn should not crash or reset Stelly's feelings."""
    match = _MOOD_TAG.match(text)
    if match and match.group(1).lower() in VALID_MOODS:
        return text[match.end():], match.group(1).lower()
    return text, fallback
