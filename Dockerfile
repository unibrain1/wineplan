# hadolint global ignore=DL3008
FROM python:3.12-slim AS base

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install system packages + Node.js for Claude Code CLI + git for self-updating
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx curl jq cron unzip nodejs npm git \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
# hadolint ignore=DL3016
RUN npm install -g @anthropic-ai/claude-code

# Install 1Password CLI (multi-arch: works on both amd64 and arm64)
RUN ARCH=$(dpkg --print-architecture) \
    && curl -sSfL "https://cache.agilebits.com/dist/1P/op2/pkg/v2.30.3/op_linux_${ARCH}_v2.30.3.zip" \
       -o /tmp/op.zip \
    && unzip -o /tmp/op.zip -d /usr/local/bin/ op \
    && rm /tmp/op.zip \
    && chmod +x /usr/local/bin/op

# Install Python dependencies (copied separately for layer caching)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

WORKDIR /app

# Repo is mounted at /app via docker-compose volume
# nginx.conf is symlinked at startup from the mounted repo

EXPOSE 80

ENTRYPOINT ["/app/entrypoint.sh"]
