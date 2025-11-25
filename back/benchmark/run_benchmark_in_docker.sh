#!/usr/bin/env bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'


DOCKER_IMAGE="miminet-benchmark:latest"
CONTAINER_NAME="miminet-benchmark-$$"
BENCHMARK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACK_DIR="$(dirname "$BENCHMARK_DIR")"
SCRIPT_DIR="$BACK_DIR"


ITERATIONS=5
OUTPUT_FILE=""
CONTINUE_ON_ERROR=""
NETWORK_FILES=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --iterations)
            ITERATIONS="$2"
            shift 2
            ;;
        --output-file)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --continue-on-error)
            CONTINUE_ON_ERROR="--continue-on-error"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 <network_json_file> [network_json_file2...] [--iterations N] [--output-file FILE] [--continue-on-error]"
            echo ""
            echo "Options:"
            echo "  --iterations N           Number of iterations per network (default: 5)"
            echo "  --output-file FILE       Output file basename (without extension, default: print to console)"
            echo "  --continue-on-error      Continue benchmark even if some iterations fail"
            echo "  --help, -h               Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 tests/test_json/router_network.json"
            echo "  $0 tests/test_json/*.json --iterations 10 --output-file results"
            exit 0
            ;;
        *)
            NETWORK_FILES+=("$1")
            shift
            ;;
    esac
done

if [ ${#NETWORK_FILES[@]} -eq 0 ]; then
    echo -e "${RED}ERROR: No network JSON files specified${NC}"
    echo "Usage: $0 <network_json_file> [options]"
    exit 1
fi

for file in "${NETWORK_FILES[@]}"; do
    if [ ! -f "$SCRIPT_DIR/$file" ]; then
        echo -e "${RED}ERROR: Network file not found: $file${NC}"
        exit 1
    fi
done

echo -e "${BLUE}=== Miminet Emulation Benchmark ===${NC}"
echo -e "${BLUE}Network files: ${#NETWORK_FILES[@]}${NC}"
echo -e "${BLUE}Iterations: $ITERATIONS${NC}"
echo ""

echo -e "${YELLOW}Building Docker image...${NC}"
cd "$BACK_DIR"
docker build -f benchmark/Dockerfile -t "$DOCKER_IMAGE" . > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Docker image built successfully${NC}"
else
    echo -e "${RED}✗ Failed to build Docker image${NC}"
    exit 1
fi

echo -e "${YELLOW}Running benchmark in Docker container...${NC}"
echo ""

TMP_OUTPUT_DIR="$BENCHMARK_DIR/benchmark_output_$$"
mkdir -p "$TMP_OUTPUT_DIR"

for file in "${NETWORK_FILES[@]}"; do
    cp "$SCRIPT_DIR/$file" "$TMP_OUTPUT_DIR/"
done

CONTAINER_ARGS=""
for file in "${NETWORK_FILES[@]}"; do
    CONTAINER_ARGS="$CONTAINER_ARGS /app/output/$(basename "$file")"
done

OUTPUT_ARG=""
if [ -n "$OUTPUT_FILE" ]; then
    OUTPUT_ARG="--output-file /app/output/$(basename "$OUTPUT_FILE")"
fi

docker run --rm \
    --name "$CONTAINER_NAME" \
    --privileged \
    --network host \
    -v "$TMP_OUTPUT_DIR:/app/output" \
    "$DOCKER_IMAGE" \
    python3 benchmark_emulation.py \
        --networks $CONTAINER_ARGS \
        --iterations "$ITERATIONS" \
        $OUTPUT_ARG \
        $CONTINUE_ON_ERROR \
    2>&1

DOCKER_EXIT_CODE=$?

if [ -n "$OUTPUT_FILE" ]; then
    # Remove any extension if provided by user
    BASE_NAME="$OUTPUT_FILE"
    BASE_NAME="${BASE_NAME%.bench}"
    BASE_NAME="${BASE_NAME%.txt}"
    BASE_NAME="${BASE_NAME%.json}"
    
    BENCH_FILE="${BASE_NAME}.bench"
    JSON_FILE="${BASE_NAME}.bench.json"
    
    if [ -f "$TMP_OUTPUT_DIR/$(basename "$BENCH_FILE")" ]; then
        cp "$TMP_OUTPUT_DIR/$(basename "$BENCH_FILE")" "$BENCHMARK_DIR/$BENCH_FILE"
        echo -e "${GREEN}✓ Results saved to: benchmark/$BENCH_FILE${NC}"
    fi
    
    if [ -f "$TMP_OUTPUT_DIR/$(basename "$JSON_FILE")" ]; then
        cp "$TMP_OUTPUT_DIR/$(basename "$JSON_FILE")" "$BENCHMARK_DIR/$JSON_FILE"
        echo -e "${GREEN}✓ JSON results saved to: benchmark/$JSON_FILE${NC}"
    fi
fi

rm -rf "$TMP_OUTPUT_DIR"

if [ $DOCKER_EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=== Benchmark completed successfully ===${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}=== Benchmark failed with exit code $DOCKER_EXIT_CODE ===${NC}"
    exit $DOCKER_EXIT_CODE
fi
