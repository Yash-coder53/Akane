#!/data/data/com.termux/files/usr/bin/bash

# Kill any existing Python processes
pkill -f "python bot.py"

# Navigate to bot directory
cd /path/to/your/bot/directory

# Set up environment
export PATH=$PATH:/data/data/com.termux/files/usr/bin
export PYTHONPATH=/data/data/com.termux/files/usr/lib/python3.11/site-packages

# Run the bot and auto-restart on crash
while true; do
    echo "Starting Music Bot..."
    python bot.py
    echo "Bot crashed/stopped. Restarting in 5 seconds..."
    sleep 5
done
