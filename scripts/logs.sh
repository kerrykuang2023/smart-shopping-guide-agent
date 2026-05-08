#!/usr/bin/env bash
set -euo pipefail

if command -v docker-compose >/dev/null 2>&1; then
  docker-compose -f deployment/docker/docker-compose.yml logs -f --tail=200
else
  docker compose -f deployment/docker/docker-compose.yml logs -f --tail=200
fi

