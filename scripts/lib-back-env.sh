#!/usr/bin/env bash
# lib-back-env.sh — shared helpers for the miminet backend test harness.
#
# Detects the container engine (docker if reachable, else podman), defines the
# image tag and repo root, and provides engine-aware run flags.

set -euo pipefail

: "${BACK_IMAGE:=miminet-back:test}"

BACK_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

detect_engine() {
    if [[ -n "${BACK_ENGINE:-}" ]]; then
        if command -v "$BACK_ENGINE" >/dev/null 2>&1; then
            return 0
        fi
        echo "[warn] BACK_ENGINE=$BACK_ENGINE not found; auto-detecting" >&2
    fi
    if command -v docker >/dev/null 2>&1; then
        if docker info >/dev/null 2>&1; then
            BACK_ENGINE="docker"
            return 0
        fi
        echo "[warn] docker CLI found but daemon unreachable; trying podman" >&2
    fi
    if command -v podman >/dev/null 2>&1; then
        BACK_ENGINE="podman"
        return 0
    fi
    echo "ERROR: no container engine (docker or podman) available." >&2
    exit 1
}

engine_flags() {
    case "$BACK_ENGINE" in
        docker) echo "--privileged" ;;
        # Privileged to mirror the production celery container (writable net
        # sysctls for MIMINET_DISABLE_IPV6, /dev/net/tun for veths).
        podman) echo "--privileged" ;;
    esac
}

base_run_args() {
    echo "--rm --entrypoint /bin/bash -v ${BACK_REPO_ROOT}:/repo:ro -w /repo"
}