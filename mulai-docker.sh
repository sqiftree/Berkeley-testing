#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose belum tersedia. Aktifkan Docker dan integrasi WSL distro ini." >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    echo "Docker belum siap. Jalankan Docker Engine/Desktop, lalu coba lagi." >&2
    exit 1
fi
echo "Setelah server siap, buka http://localhost:${BERKELEY_PORT:-8000} di browser Windows."
echo "Tekan Ctrl+C untuk berhenti."
exec docker compose up --build
