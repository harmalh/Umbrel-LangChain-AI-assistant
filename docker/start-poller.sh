#!/usr/bin/env bash
set -euo pipefail

EAIA_DATA_DIR="${EAIA_DATA_DIR:-/data}"
POLL_SECONDS="${EAIA_POLL_INTERVAL_SECONDS:-300}"
LOOKBACK_MINUTES="${EAIA_INGEST_LOOKBACK_MINUTES:-120}"

while true; do
  if [[ "${EAIA_ENABLE_POLLER:-false}" == "true" ]]; then
    (
      cd /app/eaia-upstream
      python scripts/run_ingest.py --minutes-since "${LOOKBACK_MINUTES}" --early 1 --rerun 0
    ) >> "${EAIA_DATA_DIR}/logs/poller.log" 2>&1 || true
  fi
  sleep "${POLL_SECONDS}"
done
