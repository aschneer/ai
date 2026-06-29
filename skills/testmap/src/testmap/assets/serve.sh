#!/usr/bin/env bash
# Serve the testmap report. Run this from anywhere — it serves from its own folder
# (the report fetches its data from one level above report/, so the server must be
# rooted here, not in report/). Stop the server with Ctrl-C.
set -euo pipefail

PORT="${1:-8000}"
cd "$(dirname "$0")"

HOST="$(hostname)"
printf '\nReport ready. Open one of these (Ctrl-C to stop the server):\n'
printf '  Local:  http://localhost:%s/report/report.html\n' "$PORT"
printf '  Remote: http://%s:%s/report/report.html\n\n' "$HOST" "$PORT"

exec python3 -m http.server "$PORT"
