#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or is not available in PATH for this runner user." >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  compose=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose=(docker-compose)
else
  echo "Docker Compose is not installed. Install docker-compose-plugin or docker-compose." >&2
  exit 1
fi

echo "Host: $(hostname)"
echo "Workdir: $(pwd)"
docker --version
"${compose[@]}" version

case "${1:-deploy}" in
  deploy)
    "${compose[@]}" up --build -d --remove-orphans
    ;;
  logs)
    "${compose[@]}" logs --tail=120 identity-service
    ;;
  ps)
    "${compose[@]}" ps
    ;;
  *)
    echo "Usage: $0 [deploy|logs|ps]" >&2
    exit 2
    ;;
esac
