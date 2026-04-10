#!/usr/bin/env bash
set -euo pipefail

export HOME="${HOME:-/home/umbrel}"
export EAIA_DATA_DIR="${EAIA_DATA_DIR:-/data}"
export EAIA_UI_PORT="${EAIA_UI_PORT:-3000}"
export EAIA_LANGGRAPH_PORT="${EAIA_LANGGRAPH_PORT:-2024}"

mkdir -p \
  "${EAIA_DATA_DIR}/config" \
  "${EAIA_DATA_DIR}/secrets" \
  "${EAIA_DATA_DIR}/logs" \
  "${EAIA_DATA_DIR}/state"

if [[ ! -f "${EAIA_DATA_DIR}/config/config.yaml" ]]; then
cat > "${EAIA_DATA_DIR}/config/config.yaml" <<'EOF'
email: you@example.com
full_name: Your Name
name: YourName
background: >
  Brief background about who you are and what kinds of emails this assistant should handle.
schedule_preferences: >
  Default meeting preferences.
background_preferences: >
  People to loop in, escalation rules, or business context.
response_preferences: >
  Preferences for what to include in responses.
timezone: "Europe/Berlin"
rewrite_preferences: >
  Tone and style rules for drafted emails.
triage_no: >
  Emails to ignore.
triage_notify: >
  Emails that should notify you instead of drafting.
triage_email: >
  Emails that should be drafted automatically.
memory: true
EOF
fi

if [[ ! -f "${EAIA_DATA_DIR}/app.env" ]]; then
cat > "${EAIA_DATA_DIR}/app.env" <<'EOF'
# Restart the app after editing this file.
LANGSMITH_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
EAIA_APPROVAL_MODE=agent_inbox
EAIA_ENABLE_POLLER=false
EAIA_POLL_INTERVAL_SECONDS=300
EAIA_INGEST_LOOKBACK_MINUTES=120
EOF
fi

if [[ -f "${EAIA_DATA_DIR}/app.env" ]]; then
  set -a
  source "${EAIA_DATA_DIR}/app.env"
  set +a
fi

mkdir -p /app/eaia-upstream/eaia/.secrets
ln -sf "${EAIA_DATA_DIR}/config/config.yaml" /app/eaia-upstream/eaia/main/config.yaml

if [[ -f "${EAIA_DATA_DIR}/secrets/secrets.json" ]]; then
  ln -sf "${EAIA_DATA_DIR}/secrets/secrets.json" /app/eaia-upstream/eaia/.secrets/secrets.json
fi

touch "${EAIA_DATA_DIR}/logs/langgraph.log" "${EAIA_DATA_DIR}/logs/poller.log" "${EAIA_DATA_DIR}/logs/ui.log"

cleanup() {
  if [[ -n "${LANGGRAPH_PID:-}" ]]; then kill "${LANGGRAPH_PID}" 2>/dev/null || true; fi
  if [[ -n "${POLLER_PID:-}" ]]; then kill "${POLLER_PID}" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

(
  cd /app/eaia-upstream
  langgraph dev --host 0.0.0.0 --port "${EAIA_LANGGRAPH_PORT}" >> "${EAIA_DATA_DIR}/logs/langgraph.log" 2>&1
) &
LANGGRAPH_PID=$!

/usr/local/bin/start-poller.sh &
POLLER_PID=$!

exec uvicorn app:app --host 0.0.0.0 --port "${EAIA_UI_PORT}" --app-dir /opt/umbrel-ui >> "${EAIA_DATA_DIR}/logs/ui.log" 2>&1
