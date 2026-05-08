#!/usr/bin/env bash
set -euo pipefail

if command -v docker-compose >/dev/null 2>&1; then
  docker-compose -f deployment/docker/docker-compose.yml down
else
  docker compose -f deployment/docker/docker-compose.yml down
fi

