#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Source .env for 1Password references
set -a
source .env
set +a

# Resolve SMTP credentials from 1Password (skip for --dry-run)
export SMTP_USERNAME SMTP_PASSWORD DIGEST_RECIPIENTS
if [[ ! " $* " =~ " --dry-run " ]]; then
  SMTP_USERNAME=$(op read "$SMTP_USERNAME") || { echo "ERROR: Failed to resolve SMTP username"; exit 1; }
  SMTP_PASSWORD=$(op read "$SMTP_PASSWORD") || { echo "ERROR: Failed to resolve SMTP password"; exit 1; }
fi

python3 scripts/send_digest.py "$@"
