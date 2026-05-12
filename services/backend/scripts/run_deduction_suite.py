from __future__ import annotations

import argparse
import os
import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = BACKEND_DIR / "tests"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.chdir(BACKEND_DIR)

from tests.reporting import generate_report


def build_test_summary(result: unittest.TestResult) -> dict[str, int | bool]:
    skipped = len(getattr(result, "skipped", []))
    return {
        "total": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": skipped,
        "successful": result.wasSuccessful(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the deduction backend test suite and generate summary artifacts."
    )
    parser.add_argument(
        "--output-dir",
        default=str(BACKEND_DIR / "test_reports"),
        help="Directory that will receive summary markdown, JSON, and SVG charts.",
    )
    args = parser.parse_args()

    loader = unittest.TestLoader()
    suite = loader.discover(str(TESTS_DIR), pattern="test_*.py", top_level_dir=str(BACKEND_DIR))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    output_dir = Path(args.output_dir)
    report = generate_report(output_dir, build_test_summary(result))

    print("")
    print(f"Summary written to: {output_dir / 'summary.md'}")
    print(
        "Scenario pass rate: "
        f"{report['scenarioSummary']['passedCount']}/{report['scenarioSummary']['scenarioCount']}"
    )

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
