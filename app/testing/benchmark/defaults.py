from pathlib import Path

DEFAULT_SERVER_URL = "http://127.0.0.1:5321"

DEFAULT_INTERVAL_S = 1.0
DEFAULT_DURATION_S = 60.0
DEFAULT_ATC_CLIENTS = 5
DEFAULT_PILOT_CLIENTS = 20

CONNECT_TIMEOUT_S = 15.0
TEARDOWN_GRACE_S = 2.0
POLL_INTERVAL_S = 1.0
MAX_CONNECT_WORKERS = 25
CONNECT_RETRIES = 2
CONNECT_BATCH_PAUSE_S = 0.25

TESTING_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = TESTING_ROOT / "results"

R1_INTERVALS = [2.0, 1.5, 1.0, 0.5, 0.25]

R3_LOAD_POINTS = [
    (1, 4),
    (5, 20),
    (10, 50),
    (15, 70),
    (20, 90),
    (25, 100),
    (28, 110),
    (30, 120),
    (32, 130),
    (35, 140),
    (38, 150),
    (40, 160),
    (42, 170),
    (45, 180),
    (48, 190),
    (50, 200),
    # (100, 300),
    # (200, 400),
    # (250, 450),
    # (300, 500),
    # (310, 550),
]

R4_PRESETS = {
    "1": {"atc": 350, "pilots": 550, "duration_s": 60.0, "interval_s": 1.0},
    "2": {"atc": 400, "pilots": 550, "duration_s": 60.0, "interval_s": 1.0},
    "3": {"atc": 4000, "pilots": 5500, "duration_s": 60.0, "interval_s": 1.0},
}

TEST_FOLDER_NAMES = {
    "R1": "r1_latency_sensitivity",
    "R2": "r2_state_consistency",
    "R3": "r3_concurrency_capacity",
    "R4": "r4_overload_behavior",
}

TEST_TITLES = {
    "R1": "Latency Sensitivity",
    "R2": "State Consistency",
    "R3": "Concurrency Capacity",
    "R4": "Overload Behavior",
}