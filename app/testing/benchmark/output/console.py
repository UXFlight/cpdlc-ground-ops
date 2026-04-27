from app.testing.benchmark.models import BenchmarkResult

class ConsolePrinter:
    def print_result(self, result: BenchmarkResult) -> None:
        status = "PASS" if result.passed else "FAIL"

        print()
        print(f"{result.test_id} - {result.title}: {status}")
        print(f"Saved in: {result.run_folder}")

        if result.rows:
            total_messages = sum(row.total_messages for row in result.rows)
            total_errors = sum(row.total_errors for row in result.rows)
            validation_issues = sum(row.validation_issues for row in result.rows)
            polling_issues = sum(row.polling_issues for row in result.rows)

            print(f"Runs: {len(result.rows)}")
            print(f"Messages: {total_messages}")
            print(f"Errors: {total_errors}")
            print(f"Validation issues: {validation_issues}")
            print(f"Polling issues: {polling_issues}")

        failed_checks = [check for check in result.checks if not check.passed]
        if failed_checks:
            print()
            print("Failed checks:")
            for check in failed_checks:
                print(f"- {check.name}")
                if check.details:
                    print(f"  {check.details}")

        if result.notes:
            print()
            print("Notes:")
            for note in result.notes:
                print(f"- {note}")

        print()