#!/usr/bin/env bash
# start_ollama.sh — Start Ollama server and ensure gemma4:e4b is available
# Usage: ./scripts/start_ollama.sh

set -euo pipefail

MODEL="gemma4:e4b"
OLLAMA_URL="http://localhost:11434"
MAX_WAIT=30  # seconds to wait for server readiness

echo "=== VIA: Ollama Setup ==="

# 1. Check if ollama CLI is installed
if ! command -v ollama &>/dev/null; then
    echo "[ERROR] ollama CLI not found."
    echo ""
    echo "Install Ollama:"
    echo "  macOS:   brew install ollama"
    echo "  or visit https://ollama.com/download"
    echo ""
    exit 1
fi

echo "[OK] ollama CLI found: $(command -v ollama)"

# 2. Check if ollama serve is already running
if curl -sf "${OLLAMA_URL}/api/tags" &>/dev/null; then
    echo "[OK] Ollama server is already running at ${OLLAMA_URL}"
else
    echo "[INFO] Starting ollama serve in background..."
    ollama serve &>/dev/null &
    OLLAMA_PID=$!
    echo "[INFO] ollama serve started (PID: ${OLLAMA_PID})"

    # 3. Wait for server to be ready
    echo -n "[INFO] Waiting for server readiness"
    elapsed=0
    while [ $elapsed -lt $MAX_WAIT ]; do
        if curl -sf "${OLLAMA_URL}/api/tags" &>/dev/null; then
            echo ""
            echo "[OK] Ollama server is ready."
            break
        fi
        echo -n "."
        sleep 1
        elapsed=$((elapsed + 1))
    done

    if [ $elapsed -ge $MAX_WAIT ]; then
        echo ""
        echo "[ERROR] Ollama server did not become ready within ${MAX_WAIT}s."
        exit 1
    fi
fi

# 4. Check if model is pulled; if not, pull it
MODELS=$(curl -sf "${OLLAMA_URL}/api/tags" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    print(m['name'])
" 2>/dev/null || echo "")

if echo "$MODELS" | grep -q "^${MODEL}"; then
    echo "[OK] Model '${MODEL}' is already available."
else
    echo "[INFO] Model '${MODEL}' not found. Pulling..."
    ollama pull "${MODEL}"
    echo "[OK] Model '${MODEL}' pulled successfully."
fi

# 5. Status summary
echo ""
echo "=== Status Summary ==="
echo "  Ollama URL:  ${OLLAMA_URL}"
echo "  Model:       ${MODEL}"
echo "  Available models:"
curl -sf "${OLLAMA_URL}/api/tags" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    size_gb = m.get('size', 0) / (1024**3)
    print(f'    - {m[\"name\"]} ({size_gb:.1f} GB)')
" 2>/dev/null || echo "    (could not fetch model list)"
echo ""
echo "=== Ollama is ready for VIA ==="
