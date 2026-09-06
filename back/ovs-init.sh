#!/usr/bin/env bash
# ovs-init.sh — start Open vSwitch exactly once.
#
# ovs-ctl start already launches ovs-vswitchd; only spawn a fallback if it did
# not. A second instance would fight over the bridges and break STP/RSTP state
# (random "No such RSTP object" failures).
#
# Single source of truth for OVS startup, shared by:
#   - the back Docker image  (baked to /app/ovs-init.sh, run by ENTRYPOINT.sh)
#   - the local test harness (scripts/back-test.sh, repo mounted at /repo)
#   - CI                    (.github/workflows/back_test.yml)
set -e
/usr/share/openvswitch/scripts/ovs-ctl start >/dev/null 2>&1 || true
pgrep -x ovs-vswitchd >/dev/null 2>&1 || (ovs-vswitchd >/dev/null 2>&1 &)
