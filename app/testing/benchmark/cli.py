from __future__ import annotations

import argparse

from app.testing.benchmark.defaults import (
    DEFAULT_ATC_CLIENTS,
    DEFAULT_DURATION_S,
    DEFAULT_INTERVAL_S,
    DEFAULT_PILOT_CLIENTS,
    DEFAULT_SERVER_URL,
    R1_INTERVALS,
    R3_LOAD_POINTS,
    R4_PRESETS,
)
from app.testing.benchmark.models import BenchmarkConfig, TestId


TEST_ALIASES: dict[str, TestId] = {
    "1": "R1",
    "R1": "R1",
    "LATENCY": "R1",
    "LATENCY_SENSITIVITY": "R1",

    "2": "R2",
    "R2": "R2",
    "STATE": "R2",
    "STATE_CONSISTENCY": "R2",

    "3": "R3",
    "R3": "R3",
    "CAPACITY": "R3",
    "CONCURRENCY": "R3",
    "CONCURRENCY_CAPACITY": "R3",

    "4": "R4",
    "R4": "R4",
    "OVERLOAD": "R4",
    "OVERLOAD_BEHAVIOR": "R4",
}


def normalize_test_id(value: str | None) -> TestId | None:
    if value is None:
        return None

    cleaned = value.strip().upper().replace("-", "_").replace(" ", "_")

    if not cleaned:
        return None

    return TEST_ALIASES.get(cleaned)


def format_load_points(points: list[tuple[int, int]]) -> str:
    return ", ".join(f"{atc}/{pilots}" for atc, pilots in points)


def format_intervals(intervals: list[float]) -> str:
    return ", ".join(f"{value:g}s" for value in intervals)


def ask_str(label: str, default: str) -> str:
    try:
        raw = input(f"{label} [{default}]: ").strip()
    except EOFError:
        return default

    return raw if raw else default


def ask_int(label: str, default: int) -> int:
    while True:
        raw = ask_str(label, str(default))

        try:
            return int(raw)
        except ValueError:
            print(f"[CLI] Invalid integer value: {raw}. Please enter an integer.")


def ask_float(label: str, default: float) -> float:
    while True:
        raw = ask_str(label, f"{default:g}")

        try:
            return float(raw)
        except ValueError:
            print(f"[CLI] Invalid numeric value: {raw}. Please enter a number.")


def ask_test_id(default: TestId = "R2") -> TestId:
    while True:
        raw = ask_str(
            "Test to run",
            default,
        )

        test_id = normalize_test_id(raw)

        if test_id is not None:
            return test_id

        print(f"[CLI] Unknown test: {raw}. Use R1/R2/R3/R4 or 1/2/3/4.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "test_id",
        nargs="?",
        help="Test to run: R1/R2/R3/R4 or 1/2/3/4.",
    )
    parser.add_argument("--server", default=DEFAULT_SERVER_URL)
    parser.add_argument("--non-interactive", action="store_true")
    return parser.parse_args()


def collect_config(args: argparse.Namespace) -> tuple[BenchmarkConfig, dict]:
    test_id = normalize_test_id(args.test_id)

    if test_id is None:
        if args.non_interactive:
            test_id = "R2"
        else:
            test_id = ask_test_id(default="R2")

    extras: dict = {}

    if args.non_interactive:
        return BenchmarkConfig(
            test_id=test_id,
            server_url=args.server,
            atc=DEFAULT_ATC_CLIENTS,
            pilots=DEFAULT_PILOT_CLIENTS,
            duration_s=DEFAULT_DURATION_S,
            interval_s=DEFAULT_INTERVAL_S,
        ), extras

    interval = ask_float("Interval seconds", DEFAULT_INTERVAL_S)
    duration = ask_float("Duration seconds", DEFAULT_DURATION_S)
    atc = ask_int("ATC clients", DEFAULT_ATC_CLIENTS)
    pilots = ask_int("Pilot clients", DEFAULT_PILOT_CLIENTS)

    if test_id == "R1":
        answer = ask_str(
            f"Use standard interval sweep? ({format_intervals(R1_INTERVALS)})",
            "Y",
        ).lower()
        extras["use_sweep"] = answer in {"y", "yes"}

    if test_id == "R3":
        answer = ask_str(
            f"Use standard load ladder? ATC/pilots = {format_load_points(R3_LOAD_POINTS)}",
            "Y",
        ).lower()
        extras["use_ladder"] = answer in {"y", "yes"}

    if test_id == "R4":
        preset = ask_str("Overload preset [1/2/3/custom]", "custom").lower()

        if preset in R4_PRESETS:
            selected = R4_PRESETS[preset]
            atc = selected["atc"]
            pilots = selected["pilots"]
            duration = selected["duration_s"]
            interval = selected["interval_s"]
        elif preset != "custom":
            print(f"[CLI] Unknown R4 preset: {preset}. Using custom values entered above.")

    return BenchmarkConfig(
        test_id=test_id,
        server_url=args.server,
        atc=atc,
        pilots=pilots,
        duration_s=duration,
        interval_s=interval,
    ), extras