#!/usr/bin/env bash
# Run the back test suite in parallel with pytest-xdist, every worker inside
# its own isolated namespace (see py-unshare.sh). Usage:
#   run-tests-parallel.sh [-j N] [pytest args...]
# -j N overrides the worker count; the default is the number of CPUs.
# pytest-timeout runs with --timeout-method=thread because the signal method
# does not work in execnet popen workers.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="$ROOT/back/src${PYTHONPATH:+:$PYTHONPATH}"

N="${XDIST_WORKERS:-}"
ARGS=()
while [ $# -gt 0 ]; do
    case "$1" in
        -j) shift; N="${1:?missing worker count after -j}"; shift ;;
        -j*) N="${1#-j}"; shift ;;
        *) ARGS+=("$1"); shift ;;
    esac
done
if [ -z "$N" ]; then
    N="$(nproc)"
fi
if [ ${#ARGS[@]} -eq 0 ]; then
    ARGS=(back/tests)
fi

WRAPPER="$ROOT/scripts/py-unshare.sh"
if [ ! -x "$WRAPPER" ]; then
    echo "error: isolation wrapper not found or not executable: $WRAPPER" >&2
    exit 1
fi

VENV_PY="${PYTHON:-$ROOT/.venv/bin/python}"
if [ ! -x "$VENV_PY" ]; then
    VENV_PY="$(command -v python3)"
fi

echo "==> pytest-xdist workers: $N (isolated namespaces)"
exec "$VENV_PY" -m pytest \
    -p no:cacheprovider \
    --dist=loadscope \
    --timeout-method=thread \
    --tx "${N}*popen//python=${WRAPPER}" \
    "${ARGS[@]}"
