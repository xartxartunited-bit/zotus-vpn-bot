#!/bin/bash
# Zotus++ Telegram Bot — launch script for ctrlfree.host
# Runs the bot with webhook, auto-restarts on crash.

cd "$(dirname "$0")"

# Install deps if needed
pip3 install -r requirements.txt -q

# Activate virtual env if exists
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
fi

# Run bot
exec python3 main.py
