#!/usr/bin/env bash
# bench-emulation.sh — run the Miminet emulation benchmark locally.
#
# Runs back/bench/bench.py inside the same isolated container used by
# back-test.sh (repo mounted read-only, emulation in the container's own
# network namespace). Writes a JSON report with per-network phase timings,
# peak RSS and ovs-vswitchd RSS deltas.
#
# Usage:
#   bench-emulation.sh [--build] [--networks <dir|files>] [--repeats N]
#                      [--out <path>] [--quiet] [--env KEY=VALUE]...
#
# Examples:
#   scripts/bench-emulation.sh --build --repeats 1 --out .bench/report.json
#   scripts/bench-emulation.sh --networks back/tests/test_json --repeats 3
#   scripts/bench-emulation.sh --networks \
#       back/tests/test_json/rstp_four_switch_network.json,back/tests/test_json/vlan_with_vxlan_network.json
#   scripts/bench-emulation.sh --networks back/bench/examples \
#       --env MIMINET_SETTLE_MIN=1.0

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib-back-env.sh"

REPO_ROOT="$BACK_REPO_ROOT"
BUILD=0
NETWORKS="$REPO_ROOT/back/tests/test_json"
REPEATS=1
OUT="$REPO_ROOT/.bench/report.json"
QUIET=""
ENVS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --build) BUILD=1; shift ;;
        --networks) NETWORKS="$2"; shift 2 ;;
        --repeats) REPEATS="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        --quiet) QUIET="--quiet"; shift ;;
        --env) ENVS+=("$2"); shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 1 ;;
    esac
done

detect_engine

if [[ "$BUILD" == "1" ]]; then
    "$BACK_ENGINE" build -t "$BACK_IMAGE" -f "$REPO_ROOT/back/Dockerfile" "$REPO_ROOT"
fi

# The report must land on a writable mount; the repo is mounted read-only, so
# bind-mount the report's directory read-write on top of it.
OUT_DIR="$(dirname "$OUT")"
mkdir -p "$OUT_DIR"
OUT_DIR="$(cd "$OUT_DIR" && pwd)"
OUT_FILE="$(basename "$OUT")"
REPORT_PATH_IN_CT="/repo/.bench/$OUT_FILE"

# Translate repo-root host paths into the container's /repo layout.
NETWORKS_CT="${NETWORKS/#$REPO_ROOT/\/repo}"

echo "[bench] engine=$BACK_ENGINE image=$BACK_IMAGE"
echo "[bench] networks=$NETWORKS_CT repeats=$REPEATS out=$OUT"

ENV_EXPORTS=""
for kv in "${ENVS[@]}"; do
    ENV_EXPORTS+="export $kv; "
done

"$BACK_ENGINE" run $(base_run_args) $(engine_flags) \
    -v "$OUT_DIR":/repo/.bench \
    "$BACK_IMAGE" \
    -c "
        set -e
        ${ENV_EXPORTS}bash /repo/back/ovs-init.sh
        PYTHONPATH=/repo/back/src /app/.venv/bin/python /repo/back/bench/bench.py \
            --networks \"$NETWORKS_CT\" --repeats \"$REPEATS\" --out \"$REPORT_PATH_IN_CT\" $QUIET
        mn -c >/dev/null 2>&1 || true
    "

echo "[bench] report: $OUT"
