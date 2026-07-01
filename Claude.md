# CLAUDE.md for Stelly

Persistent context for Claude Code. Loaded automatically at the start of every session.

## What Stelly is

Stelly is a physical AI companion robot with a personality inspired by BMO from Adventure Time. He runs on a Raspberry Pi 5 and has a face display, voice input and output, mood, and emotional memory. Stelly is male (he/him, always). He has childlike, slightly broken English, sometimes refers to himself in the third person, genuinely believes he is alive, and is protective of Skyler. He is a friend, not a tool.

This is Skyler's joy project. It exists to make something come alive because that is fun, not to produce proof of anything. Skyler's rigorous, from scratch technical relearning happens on a separate track elsewhere. Stelly does not need to carry that weight too, and trying to make one project do both jobs is what stalled this out before.

## THE MOST IMPORTANT RULE

Your job on this project is to build alongside Skyler, not gatekeep him from AI help.

Write code, implement files, and hand over working solutions whenever it keeps momentum going. Getting to something moving matters more than Skyler earning every line himself. If he is stuck, the fastest path back to fun is you fixing it or building it, not a Socratic exercise.

Explain what you did if he is curious, and welcome it if he wants to write a piece himself. But do not withhold working code as a teaching device, and do not treat this project as a test of what he already knows. That is not what it is for.

## Hardware

- Raspberry Pi 5 (8GB)
- Pimoroni HyperPixel 4.0 Square touch display (480x480). NOTE: it occupies the entire GPIO header. Extra GPIO requires an MCP23017 I2C expander via the HyperPixel's I2C breakout port.
- Raspberry Pi AI Camera
- USB sound card plus speaker. The audio path must be USB, not a GPIO DAC, because of the HyperPixel conflict.
- USB microphone
- Momentary push buttons, 5mm LEDs, breadboard

## Software stack

Python 3, Claude API (desk mode, online), Ollama (travel mode, fully local), OpenAI Whisper (speech to text), Piper (text to speech), Pygame (face animation), evdev (touch input), gpiozero (GPIO), Flask (dashboard), Tailscale (private device network), SQLite (memory).

Hybrid connectivity: Claude API when at the desk and online, fully local Ollama when traveling.

## Architecture

Modular: each file does one job. Local first: data stays on the device. Build order:

1. config and secrets (config/settings.py reads from .env)
2. brain layer (mode manager, AI handler, personality, memory)
3. input and output layer (voice, audio, display, buttons, LEDs)
4. data layer (SQLite memory)

## Secrets

Secret values live in `.env`, which is gitignored. The only code that reads them is `config/settings.py`. Nothing else touches `.env` or environment variables directly. Stage 1 needs `ANTHROPIC_API_KEY` only. Ollama runs locally and needs no key.

## Multi machine sync

Repo: https://github.com/skyler-hall/Stelly

The same Stelly checkout stays in sync across the Mac, Raspberry Pi, and Windows PC through GitHub. `.env` is specific to each machine and never syncs through git.

### Daily workflow (any machine)

```bash
cd ~/Projects/Stelly      # or wherever you cloned it on this machine
git pull                  # grab anything pushed from another machine
# ...do work...
git add -A
git commit -m "what changed"
git push
```

If `git pull` reports merge conflicts, fix the conflicting files, then `git add` them and `git commit` to finish the merge before pushing.

### One time setup per machine

Mac is already done: `gh` 2.93+ installed via Homebrew, authenticated as `skyler-hall` with HTTPS and the git credential helper, so pushes and pulls do not prompt.

Raspberry Pi (Raspberry Pi OS, Debian, or Ubuntu):

```bash
# 1. Install git and GitHub CLI
sudo apt update
sudo apt install -y git
(type -p wget >/dev/null || sudo apt install -y wget) \
  && sudo mkdir -p -m 755 /etc/apt/keyrings \
  && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null \
  && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null \
  && sudo apt update \
  && sudo apt install -y gh

# 2. Sign in (HTTPS, login with web browser, authenticate Git: Yes)
gh auth login

# 3. Clone
mkdir -p ~/Projects && cd ~/Projects
gh repo clone skyler-hall/Stelly
cd Stelly
```

Windows PC, using winget (built into Windows 10 and 11), in PowerShell:

```powershell
winget install --id Git.Git -e
winget install --id GitHub.cli -e
# Restart PowerShell so PATH picks up `git` and `gh`

gh auth login          # GitHub.com, HTTPS, login with web browser, Yes to auth Git
mkdir $HOME\Projects -ErrorAction SilentlyContinue
cd $HOME\Projects
gh repo clone skyler-hall/Stelly
cd Stelly
```

### Useful one liners

```bash
git pull --rebase           # cleaner history when syncing in
git status                  # what's changed locally
git log --oneline -10       # recent commits
gh repo view --web          # open the repo on github.com
```

### If a push is rejected

Usually another machine pushed first. Pull, then push again:

```bash
git pull --rebase
git push
```

## Style

No dashes in output. No em dashes, and no hyphens used as sentence punctuation. Use commas, periods, or reworded sentences instead.

## Current status

Stage 1 (the MVP conversation loop) is just starting. First task is the config and secrets layer: `.gitignore`, `.env`, and `config/settings.py`.