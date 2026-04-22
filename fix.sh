cat > fix_deploy_cleanup.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$(pwd)}"
cd "$REPO_ROOT"

backup() {
  local f="$1"
  if [ -f "$f" ] && [ ! -f "$f.bak" ]; then
    cp -p "$f" "$f.bak"
  fi
}

echo "Repo root: $REPO_ROOT"

for f in deploy-oci.sh claude-certified-architect-lab.service architect-lab.service .env.example src/main.py; do
  [ -e "$f" ] || continue
  backup "$f"
done

# Normalize service filename in the repo
if [ -f architect-lab.service ] && [ ! -f claude-certified-architect-lab.service ]; then
  mv architect-lab.service claude-certified-architect-lab.service
fi

# Make deploy-oci.sh use the canonical service filename and env path
python3 - <<'PY'
from pathlib import Path
p = Path("deploy-oci.sh")
text = p.read_text()

replacements = [
    ("architect-lab.service", "claude-certified-architect-lab.service"),
    ("/etc/claude-certified-architect-lab/claude-certified-architect-lab.env", '/etc/claude-certified-architect-lab/claude-certified-architect-lab.env'),
]

for old, new in replacements:
    text = text.replace(old, new)

# Ensure the literal env path appears at least once for simple checks
if "/etc/claude-certified-architect-lab/claude-certified-architect-lab.env" not in text:
    text += '\nENV_FILE=/etc/claude-certified-architect-lab/claude-certified-architect-lab.env\n'

# Ensure the service install line uses the canonical filename
if "claude-certified-architect-lab.service" in text and "install -m 0644" not in text:
    pass

p.write_text(text)
PY

# Make sure the deploy script is executable
chmod +x deploy-oci.sh

echo
echo "Updated files:"
git diff -- deploy-oci.sh claude-certified-architect-lab.service architect-lab.service 2>/dev/null || true

echo
echo "Quick verification:"
grep -nE 'claude-certified-architect-lab\.service|/etc/claude-certified-architect-lab/claude-certified-architect-lab\.env|APP_DIR=|APP_USER=|SERVICE=' deploy-oci.sh || true
BASH

chmod +x fix_deploy_cleanup.sh
./fix_deploy_cleanup.sh
