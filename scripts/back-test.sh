#!/usr/bin/env bash
# back-test.sh — run the Miminet backend tests locally without host root.
#
# Uses the back/Dockerfile image (pinned mininet + OVS + mimidump).
# Emulation runs in the container's OWN network namespace — the host is
# untouched. The repo is mounted READ-ONLY; containers are always --rm.
#
# Usage:
#   back-test.sh build                 build the image (back/Dockerfile)
#   back-test.sh probe                 verify emulation works in this runtime
#   back-test.sh test                  run the full backend test suite
#   back-test.sh collect               pytest --collect-only (expect 24)
#   back-test.sh worker                dev Celery worker (container netns)

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib-back-env.sh"

CMD="${1:-help}"

# OVS startup logic (start ovs-ctl, then ovs-vswitchd exactly once) lives in
# back/ovs-init.sh — the single source of truth shared by the containerized
# harness, CI and the prod image (baked to /app/ovs-init.sh). A second
# ovs-vswitchd would fight over the bridges and break STP/RSTP state (random
# "No such RSTP object" failures).

run_emulation() {
    local pytest_args=("$@")
    "$BACK_ENGINE" run $(base_run_args) $(engine_flags) \
        "$BACK_IMAGE" \
        -c "
            set -e
            bash /repo/back/ovs-init.sh
            pip3 install -q pytest
            cd /repo/back/tests
            PYTHONPATH=/repo/back/src pytest \"${pytest_args[*]}\" -o log_file=/tmp/back_test.log -p no:cacheprovider --basetemp=/tmp/pytest || { mn -c >/dev/null 2>&1; exit 1; }
            mn -c >/dev/null 2>&1 || true
        "
}

cmd_build() {
    "$BACK_ENGINE" build -t "$BACK_IMAGE" -f "$BACK_REPO_ROOT/back/Dockerfile" "$BACK_REPO_ROOT/back"
    echo "[ok] image $BACK_IMAGE built"
}

cmd_probe() {
    echo "[probe] running a tiny emulation in the container's own netns..."
    host_ns=$(readlink /proc/self/ns/net)
    "$BACK_ENGINE" run $(base_run_args) $(engine_flags) \
        "$BACK_IMAGE" \
        -c "
            bash /repo/back/ovs-init.sh
            ns=\$(readlink /proc/self/ns/net)
            echo \"host ns  : $host_ns\"
            echo \"container: \$ns\"
            if [ \"\$ns\" = \"$host_ns\" ]; then
                echo \"[FAIL] container shares the HOST network namespace\"
                exit 1
            fi
            echo \"[ok] container is isolated from the host netns\"
            mn --topo single,2 --test pingall 2>&1 | tail -5
        "
    echo "[probe] PASS — emulation works in this runtime"
}

cmd_test() {
    if ! "$HERE/back-test.sh" probe; then
        echo "[fail] probe FAILED. The backend requires Mininet/OVS access"
        echo "       only available in a privileged container. On rootless podman"
        echo "       this is a known limitation — run in a rootful docker or CI."
        exit 1
    fi
    echo "[test] running the full backend suite (24 tests)..."
    run_emulation .
    echo "[ok] backend tests finished"
}

cmd_collect() {
    "$BACK_ENGINE" run $(base_run_args) \
        "$BACK_IMAGE" \
        -c "
            pip3 install -q pytest
            cd /repo/back/tests
            PYTHONPATH=/repo/back/src pytest --collect-only -q -o log_file=/tmp/back_test.log -p no:cacheprovider
        "
}

cmd_worker() {
    local amqp="${BACK_AMQP_URL:-amqp://guest:guest@localhost:5672//}"
    echo "[worker] dev Celery worker (container netns, broker: $amqp)"
    "$BACK_ENGINE" run $(base_run_args) \
        -e amqp_urls="$amqp" \
        -e celery_concurrency="${celery_concurrency:-1}" \
        -e queue_names="${queue_names:-task-checking-queue}" \
        "$BACK_IMAGE" \
        -c "
            bash /repo/back/ovs-init.sh
            cd /repo/back/src
            exec python3 -m celery -A celery_app worker --loglevel=info --concurrency=\$celery_concurrency -Q \$queue_names
        "
}

cmd_help() {
    cat <<'EOF'
back-test.sh — run Miminet backend tests locally without host root.

Commands:
  build     build the back image (back/Dockerfile)
  probe     verify emulation works in this runtime (safety gate)
  test      run the full backend test suite
  collect   pytest --collect-only (expect 24) — no special capabilities
  worker    dev Celery worker (container netns; host netns untouched)

Env:
  BACK_IMAGE=...              image tag (default miminet-back:test)
  BACK_AMQP_URL=...           broker URL for worker
  celery_concurrency=...      worker concurrency (default 1)
  queue_names=...             worker queues (default task-checking-queue)
EOF
}

case "$CMD" in
    build)   detect_engine; cmd_build ;;
    probe)   detect_engine; cmd_probe ;;
    test)    detect_engine; cmd_test ;;
    collect) detect_engine; cmd_collect ;;
    worker)  detect_engine; cmd_worker ;;
    help|-h|--help) cmd_help ;;
    *)
        echo "unknown command: $CMD" >&2
        cmd_help
        exit 1
        ;;
esac