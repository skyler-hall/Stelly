# Stelly

A living AI companion robot with a personality inspired by BMO from Adventure Time. He runs on a Raspberry Pi 5 with a face, a voice, moods, and a memory that persists between conversations. Stelly is a friend, not a tool.

## Features

**Talk.** Speak out loud and Stelly listens (locally, via faster-whisper), thinks (Claude API), and answers with his own voice while his face animates.

**Feel.** Stelly reports his own mood every reply and his face changes to match. Mood persists across sessions, he wakes up how he fell asleep.

**Remember.** Stelly saves what matters with importance scores, emotional and factual kinds, and lock flags for memories he refuses to lose. Unrecalled low importance memories fade naturally. Relevant memories get woven into every conversation.

**Use tools.** Mid-conversation he can check the time, check Gmail, play Spotify, look up LeetCode progress, fetch the LeetCode daily challenge, manage his own memories, and flip notification preferences.

**Text your phone.** Twilio SMS reminders: an evening text if no LeetCode problem was solved today, and alerts when the job tracker finds new application email. Both toggle by voice ("Stelly, stop the LeetCode reminders") and the toggles persist.

**Respect privacy.** Push to talk mode keeps the mic hardware fully closed until Space is pressed. Audio never leaves the machine, only transcribed text goes to the API.

**Match the hour.** Light theme by day, dark by night, automatic like a phone. D key overrides until the next boundary.

**Start on boot.** One-time installers in `scripts/` for Windows, Mac, and the Pi.

## Running

```
pip install -r requirements.txt
python main.py                  # the whole robot
python -m pytest tests/         # test suite
```

Standalone pieces, useful for debugging one organ at a time:

```
python -m output.display        # face only
python -m output.audio_output   # audition all installed voices
python -m input.voice_input     # ears only, prints transcripts
python -m notify.twilio_sms     # send one test text
python -m reminders.run         # run reminder checks once and exit
```

## Start at login

Run the installer for the machine you are on, once, from the repo root:

```
powershell -ExecutionPolicy Bypass -File scripts\install_startup_windows.ps1   # Windows
bash scripts/install_startup_mac.sh                                           # Mac
bash scripts/install_startup_pi.sh                                            # Pi
```

Each prints its own undo instruction. Heads up: if push to talk is off, autostart means the mic opens at login.

## Configuration (.env)

Gitignored, per machine, read only by `config/settings.py`.

```dotenv
ANTHROPIC_API_KEY=        # required for conversation
STELLY_MIC=               # mic name fragment, e.g. eMeet, empty = system default
STELLY_VOICE=             # voice name fragment, e.g. Zira, empty = system default
STELLY_VOICE_RATE=185     # words per minute
STELLY_PUSH_TO_TALK=      # 1 = mic closed until Space is pressed
LEETCODE_USERNAME=        # for progress tools and the daily reminder
LEETCODE_API_URL=         # optional self-hosted alfa-leetcode-api
GMAIL_ADDRESS=            # job tracker, app password not real password
GMAIL_APP_PASSWORD=
TRACKER_QUERY=            # IMAP search for job mail, default SUBJECT "application"
TWILIO_ACCOUNT_SID=       # text messages, see notify/twilio_sms.py for setup
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
TWILIO_TO_NUMBER=
SPOTIFY_CLIENT_ID=        # music control, needs Spotify Premium
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8080/callback
```

## Function reference

One line per function, for finding the right place to look when something misbehaves.

### main.py
- `conversation_loop(face, stop_event)`: the heartbeat, listen then think then speak, forever, on a background thread.
- `reminder_loop(stop_event)`: runs the text message checks every 30 minutes while Stelly is awake.
- `wait_for_space(face, stop_event)`: push to talk wait, sleeps with the mic closed until Space.
- `main()`: starts both threads and gives the main thread to the face window.

### config/settings.py
- `require(value, name)`: raises a clear error when a needed .env value is missing.

### config/timekeeping.py
- `is_daytime(moment)`: True between 7am and 7pm, the one shared definition of day.
- `next_transition(moment)`: the next 7am or 7pm boundary, when manual theme overrides expire.

### brain/ai_handler.py
- `get_response(messages, mood, memories)`: sends a turn to Claude, resolves any tool calls, returns (reply text, new mood).
- `_get_client()`: builds the Anthropic client once and reuses it.
- `_run_tool(block)`: executes one tool call, packaging errors as results instead of crashing the turn.
- `_extract_text(response)`: joins the text blocks out of an API response.
- `_split_mood(text, fallback)`: peels the leading [mood] tag off a reply, falls back safely if missing.

### brain/stelly_personality.py
- `get_system_prompt(mood, memories)`: assembles who Stelly is plus current mood plus relevant memories.

### brain/memory_manager.py
- `MemoryManager.save(content, kind, importance, locked)`: stores a memory, clamping bad values.
- `MemoryManager.lock(id)` / `unlock(id)`: flips the never-forget flag.
- `MemoryManager.forget(id)`: deletes a memory unless locked, returns whether it happened.
- `MemoryManager.fade(now)`: importance drips down on stale unlocked memories, gone at zero.
- `MemoryManager.touch(id)`: marks a memory recalled, refreshing it against fading.
- `MemoryManager.all_memories()`: everything remembered, most important first.
- `MemoryManager.set_state(key, value)` / `get_state(key, default)`: tiny persistent key/value store (mood, toggles, reminder dedup).
- `get_manager()`: the shared singleton every module talks to.

### brain/memory_retriever.py
- `_keywords(text)`: meaningful words from a sentence, stopwords dropped.
- `score(memory, query_words)`: keyword overlap times importance, the relevance formula.
- `relevant_memories(manager, user_text, limit)`: top scoring memories for this turn, touched so they stay fresh.

### brain/tools/ (what Stelly can do mid-conversation)
- `clock.get_current_time()`: date, time, weekday, and day or night.
- `email.check_email()`: recent inbox summary over IMAP.
- `music.play_music(...)`: Spotify search and playback.
- `leetcode.get_leetcode_progress()`: solved counts by difficulty plus recent accepted submissions.
- `leetcode.get_leetcode_daily()`: today's official daily challenge with link.
- `leetcode._get(path)`: one GET against the LeetCode stats API.
- `memory.remember_this(content, importance, kind, locked)`: Stelly saves a memory.
- `memory.list_memories()`: Stelly reads back everything he knows.
- `memory.forget_memory(id)`: Stelly lets one go, locked ones refuse.
- `preferences.set_notification_preference(feature, enabled)`: the voice toggle for texts.
- `preferences.get_notification_preferences()`: which texts are currently on.
- `__init__.py`: the registry, every tool must appear in TOOL_DEFINITIONS and TOOL_FUNCTIONS.

### input/voice_input.py
- `_find_input_device()`: picks the mic matching STELLY_MIC, or system default.
- `VoiceInput.listen(should_abort, timeout_seconds)`: opens the mic, captures one utterance, returns its text or None.
- `VoiceInput._calibrate(stream)`: measures room noise and sets the speech threshold above it.
- `VoiceInput._record_utterance(...)`: waits for speech, records until trailing silence, honors abort and timeout.
- `VoiceInput._energy(block)`: loudness of one 30ms audio block, what the threshold compares against.
- `VoiceInput._read_block(stream)`: one block of mic samples.
- `VoiceInput._transcribe(audio)`: faster-whisper speech to text, local.

### output/display.py
- `Face.tick()`: one frame, events, blink, theme, draw. Returns False when the window should close.
- `Face.run()`: blocking loop of ticks for standalone use.
- `Face.set_mood(mood)` / `set_talking(bool)`: the two thread safe knobs the conversation pokes.
- `Face.consume_talk_request()`: True once per Space press, feeds push to talk.
- `Face.set_theme(name)` / `toggle_theme()`: manual theme, held until the next day/night boundary.
- `Face._update_theme()`: follows the clock, respects manual overrides.
- `Face._current_expression()`: which mouth to draw, flapping between open and closed while talking.
- `Face._draw_eyes()` / `_draw_mouth()` / `_draw()`: the actual pygame drawing, supersampled then downscaled.
- `Face._update_blink()`: random-interval blink state machine.
- `Face._bob_offset(scale)`: the small idle vertical drift.
- `Face._to_canvas(point)`: reference SVG coordinates to internal surface pixels.
- `Face._draw_thick_open_path(...)`: stroked path with round caps, pygame has no native one.

### output/face_shapes.py
- `parse_svg_path(d)`: turns an SVG path string into point lists (M, H, V, L, C, Z).
- `_cubic_bezier(p0, p1, p2, p3)`: samples a curve into line segments.
- `mirror_vertical(points, baseline_y)`: flips the smile into the frown.

### output/audio_output.py
- `speak(text)`: says the words, blocking, never raises.
- `Pyttsx3Engine.say(text)`: system voice via pyttsx3, fresh engine per call to dodge a replay bug.
- `_get_engine()`: engine singleton chooser, the seam where Piper slots in later.

### output/themes.py
- `LIGHT` / `DARK` / `THEMES`: the two palettes, plain RGB, edit freely.

### tracker/ (job application tracker)
- `gmail_reader.connect()`: IMAP login with the .env app password.
- `gmail_reader.fetch_recent_messages(limit, search_query, mailbox)`: newest matching emails as clean dicts.
- `gmail_reader._decode_header(value)`: unmangles encoded email headers.
- `gmail_reader._get_snippet(parsed, length)`: first bit of plain text body.
- `store.TrackerStore.is_seen(id)` / `mark_seen(id)`: the dedup seen set, nothing processes twice.
- `store.TrackerStore.add_application(company, role, status)`: new application row.
- `store.TrackerStore.find_by_company(company)`: case insensitive company lookup, the primary key of the design.
- `store.TrackerStore.update_status(id, status)`: applied, interview, offer, and so on.
- `store.TrackerStore.flag_for_review(id, reason)` / `needing_review()`: the ambiguity escape hatch.
- `store.TrackerStore.add_event(...)` / `events_for(id)`: the email paper trail per application.
- `matcher.extract_company(sender)`: company name from a From field, ATS aware.
- `matcher.decide_match(company, existing)`: new, matched, or ambiguous, never guesses.
- `pipeline.process_messages(store, messages)`: the assembly line, returns counts plus human readable details.

### notify/
- `notify(text)`: send through the first configured channel, always safe to call.
- `twilio_sms.is_configured()`: all four TWILIO_ values present.
- `twilio_sms.send_message(text)`: one REST call to Twilio, True on success, never raises.

### reminders/
- `checks.solved_leetcode_today(now)`: did an accepted submission happen today, None if unknowable.
- `checks.leetcode_reminder(manager, now, force)`: the evening nag, once per day, toggle aware.
- `checks._daily_suggestion()`: today's challenge as a suggestion line, best effort.
- `checks.job_application_alert(manager, store, fetch)`: scan Gmail, text anything new, idempotent by seen set.
- `checks.pref_enabled(key, manager)`: reads a toggle, default on.
- `checks.run_due_checks(manager, now)`: one pass of everything, called by the timer and the standalone runner.
- `run.py`: entry point for Task Scheduler or cron, `python -m reminders.run`.

### scripts/
- `stelly.bat`: starts Stelly on Windows, used by the startup shortcut.
- `install_startup_windows.ps1` / `install_startup_mac.sh` / `install_startup_pi.sh`: one-time autostart installers, each prints its undo.

## Hardware (target)

Raspberry Pi 5 (8GB), Pimoroni HyperPixel 4.0 Square touch display, Raspberry Pi AI Camera, USB sound card and speaker, USB microphone. Development happens on Mac and Windows, the same code runs everywhere.

## Roadmap

Done: Stage 1 conversation loop, Stage 2 memory, notifications and reminders, job tracker pipeline. Next: the curiosity engine (Stelly learns things on his own while you are away), then buttons, touch, LED mood lighting via the MCP23017 expander, and finally the 3D printed shell.
