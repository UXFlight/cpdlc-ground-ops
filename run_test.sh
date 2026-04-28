set -u
set -o pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT" || exit 1

PYTHON_BIN="${PYTHON_BIN:-python3}"
SERVER_URL="${SERVER_URL:-http://127.0.0.1:5321}"
LOG_ROOT="${LOG_ROOT:-app/testing/results/_run_logs}"
RUN_ID="$(date +%Y-%m-%d_%H-%M-%S)"
LOG_DIR="$LOG_ROOT/$RUN_ID"

mkdir -p "$LOG_DIR"

wait_for_server() {
    local max_wait_s="${1:-10}"
    local start_ts
    start_ts="$(date +%s)"

    while true; do
        if curl -sf "$SERVER_URL/testing/benchmark/state" >/dev/null 2>&1; then
            return 0
        fi

        if (( "$(date +%s)" - start_ts >= max_wait_s )); then
            return 1
        fi

        sleep 1
    done
}

reset_server() {
    curl -sf -X POST "$SERVER_URL/testing/benchmark/reset" >/dev/null 2>&1 || true
}

run_test() {
    local name="$1"
    local answers="$2"
    local log_file="$LOG_DIR/${name}.log"

    echo
    echo "[RUNNER] Running $name..."
    echo "[RUNNER] Log: $log_file"

    reset_server

    set +e
    printf "%b" "$answers" | "$PYTHON_BIN" -m app.testing.benchmark 2>&1 | tee "$log_file"
    local status="${PIPESTATUS[1]}"
    set -e

    reset_server

    if [[ "$status" -eq 0 ]]; then
        echo "[RUNNER] $name completed."
    else
        echo "[RUNNER] $name exited with status $status."
    fi

    return "$status"
}

echo "[RUNNER] Project root: $PROJECT_ROOT"
echo "[RUNNER] Logs: $LOG_DIR"
echo "[RUNNER] Using benchmark server at: $SERVER_URL"

if ! wait_for_server 10; then
    echo "[RUNNER] ERROR: No benchmark server found at $SERVER_URL"
    echo "[RUNNER] Start it first with:"
    echo "         CPDLC_BENCHMARK=1 CPDLC_LOGS_DISABLE=1 python3 main.py"
    exit 1
fi

echo "[RUNNER] Benchmark server detected."
reset_server

FAILED=0

# R1:
# Test to run, interval default, duration default, ATC default, pilots default, sweep default Y
run_test "R1_latency_sensitivity" "R1\n\n\n\n\nY\n" || FAILED=1

# R2:
# Test to run, interval default, duration default, ATC default, pilots default
run_test "R2_state_consistency" "R2\n\n\n\n\n" || FAILED=1

# R3:
# Test to run, interval default, duration default, ATC default, pilots default, load ladder default Y
run_test "R3_concurrency_capacity" "R3\n\n\n\n\nY\n" || FAILED=1

# R4:
# Test to run, interval default, duration default, ATC default, pilots default, then default test-specific answer
run_test "R4_overload_behavior" "R4\n\n\n\n\n\n" || FAILED=1

echo
echo "[RUNNER] Finished."
echo "[RUNNER] Logs saved in: $LOG_DIR"

if [[ "$FAILED" -eq 0 ]]; then
    echo "[RUNNER] All tests completed successfully."
else
    echo "[RUNNER] One or more tests reported failure or exited non-zero."
fi

exit "$FAILED"