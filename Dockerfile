# hadolint global ignore=DL3008
FROM python:3.12-slim AS base

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install system packages + Node.js for Claude Code CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx curl jq cron unzip nodejs npm \
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

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY scripts/ /app/scripts/
COPY site/ /app/site/
COPY pipeline.sh fetch_docker.sh entrypoint.sh /app/
COPY nginx.conf /etc/nginx/sites-available/default

WORKDIR /app

RUN mkdir -p /app/data && chmod +x /app/entrypoint.sh /app/fetch_docker.sh /app/pipeline.sh

EXPOSE 80

ENTRYPOINT ["/app/entrypoint.sh"]
