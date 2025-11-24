#!/usr/bin/env bash

set -euo pipefail

BENCHMARK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_usage() {
    echo "Usage: $0 [quick|medium|full|custom]"
    echo ""
    echo "Predefined test sets:"
    echo "  quick   - Fast tests (3 networks, 5 iterations) ~1 min"
    echo "  medium  - Medium tests (5 networks, 10 iterations) ~5 min"
    echo "  full    - All networks (18+ networks, 10 iterations) ~20+ min"
    echo "  custom  - Specify your own networks"
    echo ""
    echo "Examples:"
    echo "  $0 quick"
    echo "  $0 medium --output-file my_results.txt"
    echo "  $0 custom tests/test_json/router_network.json --iterations 20"
    exit 0
}

if [ $# -eq 0 ]; then
    show_usage
fi

TEST_SET="$1"
shift

case "$TEST_SET" in
    quick)
        echo -e "${BLUE}Running QUICK benchmark (3 networks, 5 iterations)${NC}"
        "$BENCHMARK_DIR/run_benchmark_in_docker.sh" \
            tests/test_json/router_network.json \
            tests/test_json/switch_and_hub_network.json \
            tests/test_json/dhcp_one_host_network.json \
            --iterations 5 \
            "$@"
        ;;
    
    medium)
        echo -e "${BLUE}Running MEDIUM benchmark (5 networks, 10 iterations)${NC}"
        "$BENCHMARK_DIR/run_benchmark_in_docker.sh" \
            tests/test_json/router_network.json \
            tests/test_json/switch_and_hub_network.json \
            tests/test_json/dhcp_one_host_network.json \
            tests/test_json/vlan_access_network.json \
            tests/test_json/rstp_simple_network.json \
            --iterations 10 \
            "$@"
        ;;
    
    full)
        echo -e "${YELLOW}Running FULL benchmark (all networks, 10 iterations)${NC}"
        echo -e "${YELLOW}This may take 20+ minutes!${NC}"
        "$BENCHMARK_DIR/run_benchmark_in_docker.sh" \
            tests/test_json/*_network.json \
            --iterations 10 \
            "$@"
        ;;
    
    custom)
        echo -e "${GREEN}Running CUSTOM benchmark${NC}"
        "$BENCHMARK_DIR/run_benchmark_in_docker.sh" "$@"
        ;;
    
    --help|-h)
        show_usage
        ;;
    
    *)
        echo "Error: Unknown test set '$TEST_SET'"
        echo ""
        show_usage
        ;;
esac
