#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Source .env for 1Password references
set -a
source .env
set +a

# Resolve SMTP credentials from 1Password
export SMTP_USERNAME SMTP_PASSWORD DIGEST_RECIPIENTS
SMTP_USERNAME=$(op read "$SMTP_USERNAME") || { echo "WARNING: Failed to resolve SMTP username"; exit 1; }
SMTP_PASSWORD=$(op read "$SMTP_PASSWORD") || { echo "WARNING: Failed to resolve SMTP password"; exit 1; }

python3 scripts/send_digest.py "$@"
