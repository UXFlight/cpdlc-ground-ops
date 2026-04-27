from app.testing.benchmark.cli import collect_config, parse_args
from app.testing.benchmark.runner import BenchmarkRunner
from app.testing.benchmark.tests.concurrency_capacity import ConcurrencyCapacityTest
from app.testing.benchmark.tests.latency_sensitivity import LatencySensitivityTest
from app.testing.benchmark.tests.overload_behavior import OverloadBehaviorTest
from app.testing.benchmark.tests.state_consistency import StateConsistencyTest


def build_test(config, extras):
    if config.test_id == "R1":
        return LatencySensitivityTest(config, use_sweep=extras.get("use_sweep", True))

    if config.test_id == "R2":
        return StateConsistencyTest(config)

    if config.test_id == "R3":
        return ConcurrencyCapacityTest(config, use_ladder=extras.get("use_ladder", True))

    if config.test_id == "R4":
        return OverloadBehaviorTest(config)

    raise ValueError(f"Unsupported test: {config.test_id}")


def main() -> None:
    args = parse_args()
    config, extras = collect_config(args)

    test = build_test(config, extras)
    runner = BenchmarkRunner()
    runner.run_test(test)


if __name__ == "__main__":
    main()