#!/bin/bash
# Load Testing Script for Database Architecture Layers
# Uses oha (https://github.com/hatoo/oha) for HTTP load testing

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
REQUESTS=${REQUESTS:-1000}
CONCURRENCY=${CONCURRENCY:-50}
RATE_LIMIT=${RATE_LIMIT:-0}  # 0 means no rate limit
USE_DURATION=false
DURATION=10

# Function to print colored output
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Function to check if oha is installed
check_oha() {
    if ! command -v oha &> /dev/null; then
        print_error "oha is not installed"
        echo "Install it from: https://github.com/hatoo/oha"
        echo "Or run: cargo install oha"
        exit 1
    fi
    print_success "oha is installed"
}

# Function to check if a service is healthy
check_health() {
    local port=$1
    local layer_name=$2

    if curl -s -f http://localhost:${port}/health > /dev/null 2>&1; then
        print_success "${layer_name} is healthy on port ${port}"
        return 0
    else
        print_error "${layer_name} is not healthy on port ${port}"
        return 1
    fi
}

# Function to run write load test
run_write_test() {
    local port=$1
    local layer_name=$2
    local layer_num=$3

    print_header "Write Test: ${layer_name}"

    # Create test data file
    local test_data=$(cat <<EOF
{"key": "loadtest_${layer_num}_\${i}", "value": "test_value_\${RANDOM}"}
EOF
)

    echo "${test_data}" > /tmp/oha_write_data_${layer_num}.json

    print_info "Configuration:"
    if [ "$USE_DURATION" = true ]; then
        echo "  - Duration: ${DURATION}s"
        echo "  - Concurrency: ${CONCURRENCY}"
        echo ""
        oha -z ${DURATION}s -c ${CONCURRENCY} \
            -m POST \
            -H "Content-Type: application/json" \
            -d "{\"key\": \"loadtest_${layer_num}_\$RANDOM\", \"value\": \"test_value_\$RANDOM\"}" \
            http://localhost:${port}/write
    else
        echo "  - Requests: ${REQUESTS}"
        echo "  - Concurrency: ${CONCURRENCY}"
        echo ""
        oha -n ${REQUESTS} -c ${CONCURRENCY} \
            -m POST \
            -H "Content-Type: application/json" \
            -d "{\"key\": \"loadtest_${layer_num}_\$RANDOM\", \"value\": \"test_value_\$RANDOM\"}" \
            http://localhost:${port}/write
    fi

    rm -f /tmp/oha_write_data_${layer_num}.json
}

# Function to run read load test
run_read_test() {
    local port=$1
    local layer_name=$2
    local layer_num=$3

    print_header "Read Test: ${layer_name}"

    # First, write some test data
    print_info "Writing test data..."
    for i in {1..10}; do
        curl -s -X POST http://localhost:${port}/write \
            -H "Content-Type: application/json" \
            -d "{\"key\": \"readtest_${i}\", \"value\": \"value_${i}\"}" > /dev/null
    done
    print_success "Test data written"

    print_info "Configuration:"
    if [ "$USE_DURATION" = true ]; then
        echo "  - Duration: ${DURATION}s"
        echo "  - Concurrency: ${CONCURRENCY}"
        echo ""
        oha -z ${DURATION}s -c ${CONCURRENCY} \
            http://localhost:${port}/read/readtest_1
    else
        echo "  - Requests: ${REQUESTS}"
        echo "  - Concurrency: ${CONCURRENCY}"
        echo ""
        oha -n ${REQUESTS} -c ${CONCURRENCY} \
            http://localhost:${port}/read/readtest_1
    fi
}

# Function to run mixed load test (read + write)
run_mixed_test() {
    local port=$1
    local layer_name=$2
    local layer_num=$3

    print_header "Mixed Test (70% Read / 30% Write): ${layer_name}"

    print_info "Configuration:"
    echo "  - Total Requests: ${REQUESTS}"
    echo "  - Concurrency: ${CONCURRENCY}"
    echo "  - Duration: ${DURATION}s"
    echo "  - Read/Write Ratio: 70/30"
    echo ""

    # Calculate read and write requests
    local read_requests=$((REQUESTS * 70 / 100))
    local write_requests=$((REQUESTS * 30 / 100))

    print_info "Running write requests (${write_requests})..."
    oha -n ${write_requests} -c $((CONCURRENCY * 30 / 100)) -q \
        -m POST \
        -H "Content-Type: application/json" \
        -d "{\"key\": \"mixedtest_\$RANDOM\", \"value\": \"value_\$RANDOM\"}" \
        http://localhost:${port}/write &

    WRITE_PID=$!

    print_info "Running read requests (${read_requests})..."
    oha -n ${read_requests} -c $((CONCURRENCY * 70 / 100)) -q \
        http://localhost:${port}/read/readtest_1 &

    READ_PID=$!

    # Wait for both to complete
    wait $WRITE_PID
    wait $READ_PID

    print_success "Mixed test completed"
}

# Function to test a specific layer
test_layer() {
    local layer_num=$1
    local layer_name=$2
    local port=$((8000 + layer_num))
    local test_type=${3:-all}

    print_header "Testing Layer ${layer_num}: ${layer_name}"

    # Check if service is healthy
    if ! check_health ${port} "L${layer_num}"; then
        print_error "Skipping L${layer_num} - service not healthy"
        return 1
    fi

    echo ""

    # Run tests based on type
    case ${test_type} in
        write)
            run_write_test ${port} "${layer_name}" ${layer_num}
            ;;
        read)
            run_read_test ${port} "${layer_name}" ${layer_num}
            ;;
        mixed)
            run_mixed_test ${port} "${layer_name}" ${layer_num}
            ;;
        all)
            run_write_test ${port} "${layer_name}" ${layer_num}
            echo ""
            run_read_test ${port} "${layer_name}" ${layer_num}
            echo ""
            run_mixed_test ${port} "${layer_name}" ${layer_num}
            ;;
    esac

    echo ""
}

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS] [LAYER_NUMBER]"
    echo ""
    echo "Load test database architecture layers using oha"
    echo ""
    echo "Options:"
    echo "  -n NUM        Number of requests (default: 1000, mutually exclusive with -z)"
    echo "  -c NUM        Concurrency (default: 50)"
    echo "  -z SECONDS    Duration in seconds (mutually exclusive with -n)"
    echo "  -t TYPE       Test type: write|read|mixed|all (default: all)"
    echo "  -r RATE       Rate limit (requests per second, 0=unlimited)"
    echo "  -h            Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                    # Test all layers with default settings (1000 requests)"
    echo "  $0 0                  # Test only Layer 0"
    echo "  $0 -n 5000 -c 100 5   # Test Layer 5 with 5000 requests, 100 concurrency"
    echo "  $0 -t write 2         # Test only write performance on Layer 2"
    echo "  $0 -z 30 -t mixed 10  # Run 30-second duration test on Layer 10"
    echo "  $0 -z 60 -c 100 5     # Run 60-second test with 100 concurrency on Layer 5"
    exit 0
}

# Parse command line arguments
TEST_TYPE="all"
SPECIFIC_LAYER=""

while getopts "n:c:z:t:r:h" opt; do
    case ${opt} in
        n)
            REQUESTS=${OPTARG}
            USE_DURATION=false
            ;;
        c)
            CONCURRENCY=${OPTARG}
            ;;
        z)
            DURATION=${OPTARG}
            USE_DURATION=true
            ;;
        t)
            TEST_TYPE=${OPTARG}
            ;;
        r)
            RATE_LIMIT=${OPTARG}
            ;;
        h)
            usage
            ;;
        \?)
            echo "Invalid option: -${OPTARG}" >&2
            usage
            ;;
    esac
done

shift $((OPTIND-1))

# Get specific layer if provided
if [ $# -gt 0 ]; then
    SPECIFIC_LAYER=$1
fi

# Main execution
print_header "Database Architecture Layer Load Testing"
echo "Using oha for HTTP load testing"
echo ""

# Check if oha is installed
check_oha
echo ""

# Layer definitions
declare -A LAYERS
LAYERS[0]="Single DB"
LAYERS[1]="Connection Pooling"
LAYERS[2]="Read Cache"
LAYERS[3]="Read Replicas"
LAYERS[4]="DB Sharding"
LAYERS[5]="Multi-Tier Cache"
LAYERS[6]="Write Buffering"
LAYERS[7]="CQRS"
LAYERS[8]="Polyglot Persistence"
LAYERS[9]="Global Distributed"
LAYERS[10]="Enterprise Grade"

# Test specific layer or all layers
if [ -n "${SPECIFIC_LAYER}" ]; then
    if [ -z "${LAYERS[${SPECIFIC_LAYER}]}" ]; then
        print_error "Invalid layer number: ${SPECIFIC_LAYER}"
        echo "Valid layers: 0-10"
        exit 1
    fi
    test_layer ${SPECIFIC_LAYER} "${LAYERS[${SPECIFIC_LAYER}]}" ${TEST_TYPE}
else
    # Test all layers
    for layer_num in {0..10}; do
        test_layer ${layer_num} "${LAYERS[${layer_num}]}" ${TEST_TYPE}
        echo ""
        echo ""
    done
fi

print_success "Load testing completed!"
