#!/bin/zsh

set -e

PROJECT_DIR="/Users/elishetlar/Documents/ChatGPT/OptionsELI"
PYTHON="$PROJECT_DIR/.venv/bin/python"
URL="http://localhost:8501"

cd "$PROJECT_DIR"

if [[ ! -x "$PYTHON" ]]; then
  osascript -e 'display alert "OptionsELI cannot start" message "The project virtual environment is missing. Please ask Codex to repair OptionsELI." as critical'
  exit 1
fi

if /usr/bin/curl --silent --fail --max-time 2 "$URL/_stcore/health" >/dev/null 2>&1; then
  /usr/bin/open "$URL"
  exit 0
fi

export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
export PYTHONPYCACHEPREFIX="$PROJECT_DIR/.python-cache"

"$PYTHON" -m streamlit run app.py --server.headless true --server.port 8501 &
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

for attempt in {1..60}; do
  if /usr/bin/curl --silent --fail --max-time 2 "$URL/_stcore/health" >/dev/null 2>&1; then
    /usr/bin/open "$URL"
    echo "OptionsELI is running at $URL"
    echo "Keep this window open. Press Control-C to stop OptionsELI."
    wait "$SERVER_PID"
    exit $?
  fi
  if ! kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    echo "OptionsELI stopped before startup completed. Review the error above."
    read -k 1 "?Press any key to close."
    exit 1
  fi
  sleep 1
done

echo "OptionsELI did not become ready within 60 seconds."
read -k 1 "?Press any key to close."
exit 1
