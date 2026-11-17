#!/bin/bash
# Pull the latest code, then run one full download pass.
# Used by the systemd service in deploy/ (replaces the old self-calling puller.sh).
set -u
cd "$(dirname "$0")"

if ! mountpoint -q /mnt/UBERVAULT; then
    echo "/mnt/UBERVAULT is not mounted; refusing to download onto the local disk" >&2
    exit 1
fi

git pull --ff-only || echo "git pull failed; continuing with current code" >&2
exec "${PYTHON:-python3}" main.py
