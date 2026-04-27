
from __future__ import annotations

import argparse

from app.testing.benchmark.defaults import (
    DEFAULT_ATC_CLIENTS,
    DEFAULT_DURATION_S,
    DEFAULT_INTERVAL_S,
    DEFAULT_PILOT_CLIENTS,
    DEFAULT_SERVER_URL,
    R4_PRESETS,
)
from app.testing.benchmark.models import BenchmarkConfig, TestId


def ask_str(label: str, default: str) -> str:
    raw = input(f"{label} [{default}]: ").strip()
    return raw if raw else default


def ask_int(label: str, default: int) -> int:
    raw = input(f"{label} [{default}]: ").strip()
    return int(raw) if raw else default


def ask_float(label: str, default: float) -> float:
    raw = input(f"{label} [{default:g}]: ").strip()
    return float(raw) if raw else default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("test_id", nargs="?", choices=["R1", "R2", "R3", "R4"])
    parser.add_argument("--server", default=DEFAULT_SERVER_URL)
    parser.add_argument("--non-interactive", action="store_true")
    return parser.parse_args()


def collect_config(args: argparse.Namespace) -> tuple[BenchmarkConfig, dict]:
    test_id = args.test_id

    if not test_id:
        test_id = ask_str("Test to run", "R2").upper()

    if test_id not in {"R1", "R2", "R3", "R4"}:
        raise ValueError(f"Unknown test: {test_id}")

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
        answer = ask_str("Use standard interval sweep?", "Y").lower()
        extras["use_sweep"] = answer in {"y", "yes"}

    if test_id == "R3":
        answer = ask_str("Use standard load ladder?", "Y").lower()
        extras["use_ladder"] = answer in {"y", "yes"}

    if test_id == "R4":
        preset = ask_str("Overload preset [1/2/3/custom]", "custom").lower()

        if preset in R4_PRESETS:
            selected = R4_PRESETS[preset]
            atc = selected["atc"]
            pilots = selected["pilots"]
            duration = selected["duration_s"]
            interval = selected["interval_s"]

    return BenchmarkConfig(
        test_id=test_id,  # type: ignore[arg-type]
        server_url=args.server,
        atc=atc,
        pilots=pilots,
        duration_s=duration,
        interval_s=interval,
    ), extras