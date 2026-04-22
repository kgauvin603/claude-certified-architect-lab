#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/claude-certified-architect-lab
APP_USER=claudeapp
APP_GROUP=claudeapp
ENV_DIR=/etc/claude-certified-architect-lab
ENV_FILE="$ENV_DIR/claude-certified-architect-lab.env"
SERVICE=claude-certified-architect-lab

# 1. System packages
dnf install -y python3.11 python3.11-pip nodejs npm git curl
npm install -g @anthropic-ai/claude-code

# 2. App user/group
if ! getent group "$APP_GROUP" &>/dev/null; then
    groupadd --system "$APP_GROUP"
fi
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /sbin/nologin --gid "$APP_GROUP" "$APP_USER"
fi

# 3. App directory
mkdir -p "$APP_DIR"
rsync -a --delete --exclude='.venv' --exclude='data' . "$APP_DIR/"
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"

# 4. Virtual env + dependencies
python3.11 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR/.venv"

# 5. Environment file
mkdir -p "$ENV_DIR"
chmod 750 "$ENV_DIR"
if [[ ! -f "$ENV_FILE" ]]; then
    cp "$APP_DIR/.env.example" "$ENV_FILE"
    chmod 640 "$ENV_FILE"
    chown root:"$APP_GROUP" "$ENV_FILE"
    echo "WARNING: populate $ENV_FILE with ANTHROPIC_API_KEY before starting the service"
fi

# 6. Data directories
mkdir -p "$APP_DIR/data/scratchpads" "$APP_DIR/data/sessions"
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR/data"

# 7. Systemd unit
install -m 0644 "$APP_DIR/claude-certified-architect-lab.service" /etc/systemd/system/claude-certified-architect-lab.service
systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"

# 8. Verify deployment
check_deploy() {
    local venv="$APP_DIR/.venv/bin/python"
    local failures=0

    echo "--- Verifying venv ---"
    if [[ -x "$venv" ]]; then
        echo "OK: venv found at $venv ($($venv --version))"
    else
        echo "FAIL: venv not found at $venv"
        (( failures++ ))
    fi

    echo "--- Verifying env file ---"
    if [[ -f "$ENV_FILE" ]]; then
        if grep -q "^ANTHROPIC_API_KEY=your_key_here" "$ENV_FILE"; then
            echo "WARN: $ENV_FILE still contains placeholder ANTHROPIC_API_KEY"
        else
            echo "OK: env file exists and key appears set"
        fi
    else
        echo "FAIL: env file not found at $ENV_FILE"
        (( failures++ ))
    fi

    echo "--- Verifying service status ---"
    if systemctl is-active --quiet "$SERVICE"; then
        echo "OK: $SERVICE is active"
    else
        echo "FAIL: $SERVICE is not active"
        systemctl status "$SERVICE" --no-pager || true
        (( failures++ ))
    fi

    echo "--- Verifying /healthz ---"
    local port
    port=$(grep -E "^APP_PORT=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)
    port=${port:-8000}
    local resp
    resp=$(curl -sf "http://127.0.0.1:${port}/healthz" 2>&1) || true
    if echo "$resp" | grep -q '"ok"'; then
        echo "OK: /healthz returned $resp"
    else
        echo "FAIL: /healthz did not return expected response (got: $resp)"
        (( failures++ ))
    fi

    echo "---"
    if [[ $failures -eq 0 ]]; then
        echo "Deployment verified successfully."
    else
        echo "Deployment verification failed ($failures check(s) failed)."
        exit 1
    fi
}

sleep 3
check_deploy

ENV_FILE=/etc/claude-certified-architect-lab/claude-certified-architect-lab.env
