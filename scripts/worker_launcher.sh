#!/bin/bash
set -e

MAX_WORKERS=19
REPO="${REPO:-${{ github.repository }}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

QUERY="$1"
if [ -z "$QUERY" ]; then
    echo "❌ Error: query is required"
    exit 1
fi

echo "🧠 Creating worker for query: $QUERY"

# Count running workers
RUNNING=$(python3 "$SCRIPT_DIR/github_ops.py" --count-running "Temporary Worker" 2>/dev/null || echo 0)
if [ "$RUNNING" -ge "$MAX_WORKERS" ]; then
    echo "❌ All $MAX_WORKERS workers are busy. Please wait."
    exit 1
fi

TIMESTAMP=$(date +%s)
FILENAME="worker_${TIMESTAMP}.yaml"

cat > /tmp/worker.yaml << 'WORKER_EOF'
name: Temporary Worker

on:
  workflow_dispatch:

jobs:
  worker:
    runs-on: ubuntu-latest
    timeout-minutes: 360
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          curl -fsSL https://ollama.com/install.sh | sh
          ollama serve &
          sleep 5
          ollama pull granite4:tiny-h
          sudo npm install -g openclaw
          echo "/usr/local/bin" >> $GITHUB_PATH
          mkdir -p ~/.openclaw
          echo '{
            "models": {
              "ollama": {
                "baseUrl": "http://localhost:11434",
                "defaultModel": "granite4:tiny-h"
              }
            },
            "agents": {
              "default": {
                "model": "ollama/granite4:tiny-h"
              }
            }
          }' > ~/.openclaw/openclaw.json

      - name: Execute query
        run: |
          openclaw agent run --task "$QUERY" --output result.json
          mkdir -p upload
          cp result.json upload/
        env:
          QUERY: ${{ github.event.inputs.query }}

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: result
          path: upload/
WORKER_EOF

ESCAPED_QUERY=$(echo "$QUERY" | sed 's/"/\\"/g')
sed -i "s/\$QUERY/$ESCAPED_QUERY/g" /tmp/worker.yaml

# Create workflow via Python helper
echo "📝 Creating workflow $FILENAME..."
SHA=$(python3 "$SCRIPT_DIR/github_ops.py" --create "$FILENAME" "$(cat /tmp/worker.yaml)")
echo "✅ Created (sha=$SHA)"

sleep 5
python3 "$SCRIPT_DIR/github_ops.py" --trigger "$FILENAME"

echo "⏳ Waiting for completion..."
RUN_ID=$(python3 "$SCRIPT_DIR/github_ops.py" --wait "$FILENAME" 600)
echo "✅ Done (run_id=$RUN_ID)"

echo "📥 Downloading result..."
RESULT=$(python3 "$SCRIPT_DIR/github_ops.py" --download "$RUN_ID")
if [ -n "$RESULT" ]; then
    echo "$RESULT" | jq .
else
    echo "⚠️ No result found"
fi

echo "🗑️ Cleaning up..."
python3 "$SCRIPT_DIR/github_ops.py" --delete "$FILENAME" "$SHA"
echo "✅ Done"
echo "$RESULT"
