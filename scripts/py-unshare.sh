#!/usr/bin/env bash
# execnet popen wrapper: re-exec the project Python inside an isolated
# namespace so each pytest-xdist worker gets a private network, PID and
# mount stack (with a private /tmp). Needed so concurrent Miminet back test
# networks cannot interfere: bridges/veths/iptables (netns), cleanup()'s
# pkill/pgrep (PID ns) and per-node state under /tmp (mount ns) are all
# scoped per worker. Invoked by execnet as: <this> -u [-c] bootstrap
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REAL_PY="${PYTHON:-$ROOT/.venv/bin/python}"
if [ ! -x "$REAL_PY" ]; then
    REAL_PY="$(command -v python3)"
fi
exec unshare --mount --pid --net --uts --fork --mount-proc bash -c '
    mount -t tmpfs tmpfs /tmp
    exec "$@"
' _ "$REAL_PY" "$@"
