#!/bin/bash
# Makes Stelly start automatically when the Pi's desktop session starts.
# Run once from the repo root:  bash scripts/install_startup_pi.sh
# Undo any time:  rm ~/.config/autostart/stelly.desktop
#
# Desktop autostart (not systemd) on purpose: the face is a pygame
# window, so Stelly needs the graphical session to exist first. This
# also inherits the session's display and audio setup for free.

set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
AUTOSTART="$HOME/.config/autostart"

mkdir -p "$AUTOSTART"
cat > "$AUTOSTART/stelly.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Stelly
Comment=Stelly the companion robot
Exec=bash -c "cd $REPO && python3 main.py >> /tmp/stelly.log 2>&1"
X-GNOME-Autostart-enabled=true
EOF

echo "Done. Stelly will start with the desktop. Logs: /tmp/stelly.log"
echo "To undo: rm $AUTOSTART/stelly.desktop"
