#!/usr/bin/env bash
set -euo pipefail

SERVICE="claude-certified-architect-lab"
PORT="8000"

echo "Stopping ${SERVICE}..."
sudo systemctl stop "${SERVICE}" || true

echo "Checking for stale uvicorn/python processes on port ${PORT}..."
PIDS="$(sudo ss -ltnp 2>/dev/null | awk -v port=":${PORT}" '$4 ~ port {print $0}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u || true)"

if [[ -n "${PIDS}" ]]; then
  echo "Found stale process(es) bound to port ${PORT}: ${PIDS}"
  for pid in ${PIDS}; do
    echo "Killing PID ${pid}..."
    sudo kill "${pid}" || true
  done

  sleep 2

  PIDS_AFTER="$(sudo ss -ltnp 2>/dev/null | awk -v port=":${PORT}" '$4 ~ port {print $0}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u || true)"
  if [[ -n "${PIDS_AFTER}" ]]; then
    echo "Process still bound to port ${PORT}; force killing: ${PIDS_AFTER}"
    for pid in ${PIDS_AFTER}; do
      sudo kill -9 "${pid}" || true
    done
  fi
else
  echo "No stale process found on port ${PORT}."
fi

echo "Starting ${SERVICE}..."
sudo systemctl start "${SERVICE}"

sleep 3

echo
echo "Service status:"
sudo systemctl status "${SERVICE}" --no-pager

echo
echo "Port check:"
sudo ss -ltnp | grep ":${PORT}" || {
  echo "FAIL: nothing is listening on port ${PORT}"
  exit 1
}

echo
echo "Health check:"
curl -fsS "http://127.0.0.1:${PORT}/healthz"
echo

echo
echo "Lab restarted successfully."
echo "Live UI:   http://cca.keithgauvin.activeadvantage.co:${PORT}/lab"
echo "Swagger:   http://cca.keithgauvin.activeadvantage.co:${PORT}/docs"
echo "Health:    http://cca.keithgauvin.activeadvantage.co:${PORT}/healthz"
