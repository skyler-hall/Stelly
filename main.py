"""
Stelly comes alive.

Wires the whole Stage 1 loop together: ears listen, brain thinks, voice
speaks, face reacts. Run this file and talk to him.

Threading shape, and why: pygame insists on running its window loop on
the main thread, and listening plus thinking plus speaking are all slow
blocking work that would freeze the animation if they ran there too. So
the face owns the main thread and the conversation runs on a background
thread, poking the face through two thread safe knobs, set_mood and
set_talking. The conversation thread is a daemon, closing the face
window ends the program without needing a shutdown handshake.

The mic is deliberately not open while Stelly speaks, otherwise he hears
his own voice, transcribes it, and answers himself forever. listen()
only runs between utterances, so the loop is: listen, think, speak,
listen again.
"""

import threading
import time

from brain import ai_handler
from config import settings
from input.voice_input import VoiceInput
from output import audio_output
from output.display import Face

HISTORY_MAX_TURNS = 20  # user plus assistant messages kept, oldest dropped first
PUSH_TO_TALK_WINDOW = 10  # seconds the mic stays open after Space with no speech


def wait_for_space(face, stop_event):
    """Push to talk: sleep, mic fully closed, until Space is pressed in
    Stelly's window or the program is shutting down."""
    while not stop_event.is_set():
        if face.consume_talk_request():
            return True
        time.sleep(0.05)
    return False


def conversation_loop(face, stop_event):
    """Background thread: listen, think, speak, forever."""
    ears = VoiceInput()
    history = []
    mood = "neutral"

    if settings.PUSH_TO_TALK:
        print("\nPush to talk is ON. Click Stelly's window, press SPACE, then speak.")
        print("The microphone stays closed until you press Space.\n")
    else:
        print("\nStelly is listening! Talk to him. Close the window to stop.\n")

    while not stop_event.is_set():
        if settings.PUSH_TO_TALK:
            if not wait_for_space(face, stop_event):
                break
            heard = ears.listen(should_abort=stop_event.is_set,
                                timeout_seconds=PUSH_TO_TALK_WINDOW)
        else:
            heard = ears.listen(should_abort=stop_event.is_set)
        if stop_event.is_set():
            break
        if not heard:
            continue  # silence or noise, keep listening

        print(f"You: {heard}")
        history.append({"role": "user", "content": heard})

        try:
            reply, mood = ai_handler.get_response(history, mood)
        except Exception as error:
            print(f"(brain hiccup: {error})")
            history.pop()  # drop the unanswered message so history stays valid
            continue

        history.append({"role": "assistant", "content": reply})
        del history[:-HISTORY_MAX_TURNS]  # keep memory of this session bounded

        print(f"Stelly [{mood}]: {reply}\n")
        face.set_mood(mood)

        face.set_talking(True)
        try:
            audio_output.speak(reply)
        finally:
            face.set_talking(False)


def main():
    face = Face()
    stop_event = threading.Event()

    worker = threading.Thread(
        target=conversation_loop, args=(face, stop_event), daemon=True
    )
    worker.start()

    try:
        face.run()  # blocks on the main thread until the window closes
    except KeyboardInterrupt:
        pass  # Ctrl+C is a normal way to say goodnight, not a crash
    stop_event.set()
    print("Stelly is going to sleep. Bye!")


if __name__ == "__main__":
    main()
