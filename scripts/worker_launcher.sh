#!/bin/bash
# Read incoming JSON parameters from OpenClaw
QUERY=$(echo "$1" | jq -r '.query')

# Count current running worker workflows to protect limit (Max 19)
CURRENT_RUNS=$(gh run list --workflow=worker.yml --status=in_progress --json databaseId | jq '. | length')

if [ "$CURRENT_RUNS" -ge 19 ]; then
    echo "❌ Execution blocked: Maximum worker threshold (19) reached."
    exit 1
fi

# Generate a highly unpredictable random string for the Holesail P2P network channel
SECURE_HOLESAIL_KEY=$(openssl rand -hex 16)

# Start a background Holesail connector instance on the Queen side to accept worker data
holesail --listen 12001 --key "$SECURE_HOLESAIL_KEY" &
HOLESAIL_PID=$!

# Trigger the detached GitHub action worker workflow via Github CLI
gh workflow run worker.yml \
  -f query="$QUERY" \
  -f connection_secret="$SECURE_HOLESAIL_KEY"

echo "⏳ Worker dispatched successfully over secure network channel: $SECURE_HOLESAIL_KEY"

# Wait for the worker to pipe results back over Holesail, then clean up process
# (In a production environment, you would use netcat/websockets to fetch output here)
sleep 60
kill $HOLESAIL_PID 2>/dev/null
