#!/bin/bash
# Makes Stelly start automatically at login on the Mac.
# Run once from the repo root:  bash scripts/install_startup_mac.sh
# Undo any time:  launchctl unload ~/Library/LaunchAgents/com.skyler.stelly.plist && rm ~/Library/LaunchAgents/com.skyler.stelly.plist

set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.skyler.stelly.plist"
PYTHON="$(command -v python3)"

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.skyler.stelly</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$REPO</string>
    <key>RunAtLoad</key>
    <true/>
    <key>LimitLoadToSessionType</key>
    <string>Aqua</string>
    <key>StandardOutPath</key>
    <string>/tmp/stelly.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/stelly.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Done. Stelly will start at login. Logs: /tmp/stelly.log"
echo "To undo: launchctl unload $PLIST && rm $PLIST"
