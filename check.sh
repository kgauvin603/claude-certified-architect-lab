#!/usr/bin/env bash
set -u

APP_DIR_DEFAULT="/opt/claude-certified-architect-lab"
SERVICE_NAME="claude-certified-architect-lab"
SERVICE_FILE="${SERVICE_NAME}.service"
ENV_DIR="/etc/claude-certified-architect-lab"
ENV_FILE="${ENV_DIR}/${SERVICE_NAME}.env"

APP_DIR="${1:-$APP_DIR_DEFAULT}"

ok()   { printf 'OK:   %s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*"; }
fail() { printf 'FAIL: %s\n' "$*"; }

check_file() {
  local path="$1"
  if [ -e "$path" ]; then
    ok "exists: $path"
  else
    fail "missing: $path"
  fi
}

check_grep() {
  local path="$1"
  local pattern="$2"
  local label="$3"
  if [ ! -f "$path" ]; then
    fail "$label: file missing ($path)"
    return
  fi
  if grep -Eq "$pattern" "$path"; then
    ok "$label"
  else
    fail "$label"
  fi
}

echo "--- Repo root ---"
if git rev-parse --show-toplevel >/dev/null 2>&1; then
  REPO_ROOT="$(git rev-parse --show-toplevel)"
  ok "git repo root: $REPO_ROOT"
else
  warn "not inside a git repo"
  REPO_ROOT="$(pwd)"
fi

echo
echo "--- Repo files ---"
check_file "$REPO_ROOT/deploy-oci.sh"
check_file "$REPO_ROOT/$SERVICE_FILE"
check_file "$REPO_ROOT/.env.example"
check_file "$REPO_ROOT/src/main.py"

echo
echo "--- Repo content checks ---"
check_grep "$REPO_ROOT/deploy-oci.sh" 'APP_DIR=/opt/claude-certified-architect-lab' "deploy-oci.sh uses APP_DIR=/opt/claude-certified-architect-lab"
check_grep "$REPO_ROOT/deploy-oci.sh" 'APP_USER=claudeapp' "deploy-oci.sh uses APP_USER=claudeapp"
check_grep "$REPO_ROOT/deploy-oci.sh" 'SERVICE=claude-certified-architect-lab' "deploy-oci.sh uses SERVICE=claude-certified-architect-lab"
check_grep "$REPO_ROOT/deploy-oci.sh" '/etc/claude-certified-architect-lab/claude-certified-architect-lab.env' "deploy-oci.sh uses the expected env file path"
check_grep "$REPO_ROOT/deploy-oci.sh" 'claude-certified-architect-lab\.service' "deploy-oci.sh refers to the renamed service file"
check_grep "$REPO_ROOT/$SERVICE_FILE" 'User=claudeapp' "service file uses User=claudeapp"
check_grep "$REPO_ROOT/$SERVICE_FILE" 'Group=claudeapp' "service file uses Group=claudeapp"
check_grep "$REPO_ROOT/$SERVICE_FILE" 'WorkingDirectory=/opt/claude-certified-architect-lab' "service file uses the expected WorkingDirectory"
check_grep "$REPO_ROOT/$SERVICE_FILE" 'EnvironmentFile=/etc/claude-certified-architect-lab/claude-certified-architect-lab.env' "service file uses the expected env file"
check_grep "$REPO_ROOT/$SERVICE_FILE" 'uvicorn src\.main:app' "service file starts uvicorn against src.main:app"
check_grep "$REPO_ROOT/src/main.py" '@app\.get\("/healthz"\)' "src/main.py defines /healthz"
check_grep "$REPO_ROOT/src/main.py" 'ANTHROPIC_API_KEY' "src/main.py checks for ANTHROPIC_API_KEY"

echo
echo "--- Local / deployed path checks ---"
check_file "$APP_DIR"
check_file "$APP_DIR/.venv"
check_file "$APP_DIR/src/main.py"
check_grep "$APP_DIR/src/main.py" '@app\.get\("/healthz"\)' "deployed src/main.py defines /healthz"

echo
echo "--- Systemd checks ---"
if command -v systemctl >/dev/null 2>&1; then
  if systemctl cat "$SERVICE_NAME" >/dev/null 2>&1; then
    ok "systemd unit exists: $SERVICE_NAME"
    systemctl cat "$SERVICE_NAME" | grep -E '^(User|Group|WorkingDirectory|EnvironmentFile|ExecStart)=' || true
  else
    fail "systemd unit not found or unreadable: $SERVICE_NAME"
  fi

  if systemctl is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
    ok "service is enabled"
  else
    warn "service is not enabled"
  fi

  if systemctl is-active "$SERVICE_NAME" >/dev/null 2>&1; then
    ok "service is active"
  else
    warn "service is not active"
  fi
else
  warn "systemctl not available"
fi

echo
echo "--- Env file checks ---"
if sudo test -f "$ENV_FILE"; then
  ok "env file exists: $ENV_FILE"
  if sudo grep -Eq '^ANTHROPIC_API_KEY=.+' "$ENV_FILE"; then
    ok "ANTHROPIC_API_KEY appears set"
  else
    fail "ANTHROPIC_API_KEY is missing or empty in env file"
  fi
else
  fail "env file missing: $ENV_FILE"
fi

echo
echo "--- Health check ---"
if command -v curl >/dev/null 2>&1; then
  if curl -fsS "http://127.0.0.1:8000/healthz" >/tmp/claude_healthz.out 2>/tmp/claude_healthz.err; then
    ok "GET /healthz returned success"
    cat /tmp/claude_healthz.out
    echo
  else
    fail "GET /healthz failed"
    if [ -s /tmp/claude_healthz.err ]; then
      cat /tmp/claude_healthz.err
      echo
    fi
  fi
else
  warn "curl not available"
fi

echo
echo "--- Port check ---"
if command -v ss >/dev/null 2>&1; then
  ss -ltnp | grep ':8000' || warn "nothing listening on 8000"
else
  warn "ss not available"
fi
