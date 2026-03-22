#!/usr/bin/env bash
set -euo pipefail

# Auto rebuild and restart the container on file changes using Docker Compose watch.
cd "$(dirname "$0")"

echo "Starting docker compose watch (auto rebuild + restart on changes)..."
exec docker compose watch
