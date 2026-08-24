#!/usr/bin/env python3
"""
==============================================================================
ECES Egyptian Housing Market Pipeline Orchestrator
==============================================================================
Universal single-command runner for data acquisition, dataset export,
deterministic extraction evaluation, test execution, and research metrics.
==============================================================================
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def run_command(desc: str, cmd: list[str]) -> bool:
    """Execute a pipeline command and stream output."""
    print("\n" + "=" * 75)
    print(f"▶ {desc.upper()}")
    print("=" * 75)
    start = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(BASE_DIR))
        duration = time.time() - start
        if proc.returncode == 0:
            print(f"✔ Completed successfully in {duration:.2f}s")
            return True
        else:
            print(f"✖ Failed with return code {proc.returncode} ({duration:.2f}s)")
            return False
    except Exception as e:
        print(f"✖ Execution error: {e}")
        return False


def run_tests() -> bool:
    """Run automated unit tests."""
    return run_command(
        "Running Automated Pipeline Unit Tests",
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
    )


def run_evaluation() -> bool:
    """Run 25 hand-labeled ground-truth evaluation."""
    return run_command(
        "Evaluating Extraction Quality on 25-Listing Gold Standard",
        [sys.executable, "-m", "evaluation.evaluate"],
    )


def run_benchmark() -> bool:
    """Run 4-way comparative methodology benchmark (BS4 vs Rules vs Gemini vs Hybrid)."""
    return run_command(
        "Running 4-Way Comparative Methodology Benchmark (BS4, Rules, Gemini 3.6, Hybrid Gemini 3.1)",
        [sys.executable, "-m", "evaluation.benchmark_techniques"],
    )


def run_fetch() -> bool:
    """Fetch and cache missing detail HTML pages."""
    return run_command(
        "Fetching and Caching Missing Detail HTML Pages",
        [sys.executable, "-m", "src.fetch_all_details"],
    )


def run_export(use_hybrid: bool = False) -> bool:
    """Export canonical dataset (XLSX, CSV, JSONL)."""
    env = dict(os.environ)
    if use_hybrid:
        env["USE_HYBRID"] = "1"
    desc = "Exporting Canonical Dataset (Hybrid Gemini 3.1 Mode)" if use_hybrid else "Exporting Canonical Dataset (Deterministic Mode)"
    return run_command(desc, [sys.executable, "-m", "src.export_dataset"])


def run_metrics() -> bool:
    """Generate single-source analysis metrics."""
    return run_command(
        "Generating Single-Source Analysis Metrics JSON",
        [sys.executable, "-m", "src.generate_report_data"],
    )


def print_summary_banner() -> None:
    """Print clean summary of all deliverables."""
    print("\n" + "=" * 75)
    print("🏆 ECES TAKE-HOME PIPELINE EXECUTION COMPLETE")
    print("=" * 75)
    print("Deliverables Generated:")
    print("  1. Excel Dataset:        data/output/egypt_housing_market_dataset.xlsx")
    print("  2. CSV Dataset:          data/output/egypt_housing_market_dataset.csv")
    print("  3. JSONL Dataset:        data/output/egypt_housing_market_dataset.jsonl")
    print("  4. Clean Failure Log:    data/output/failure_log.csv")
    print("  5. Evaluation Report:    evaluation/evaluation_report.json")
    print("  6. Methodology Report:   evaluation/methodology_benchmark.json")
    print("  7. Research Report:      report.md")
    print("  8. Technical README:     README.md")
    print("=" * 75 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ECES Egyptian Housing Market Data Engineering & Extraction Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                     # Run complete deterministic pipeline (Default, $0 cost, <8s)
  python run.py --all               # Run complete deterministic pipeline end-to-end
  python run.py --benchmark         # Run 4-way comparative benchmark (BS4, Rules, Gemini, Hybrid)
  python run.py --test              # Run 14 unit tests only
  python run.py --eval              # Run 25-listing gold evaluation benchmark
  python run.py --export            # Re-export XLSX, CSV, and JSONL datasets
  python run.py --fetch             # Fetch missing HTML detail pages
  python run.py --metrics           # Recompute statistical analysis metrics
        """,
    )

    parser.add_argument("--all", action="store_true", help="Run full pipeline: tests, evaluation, export, metrics (Deterministic)")
    parser.add_argument("--benchmark", action="store_true", help="Run 4-way comparative methodology benchmark (includes Gemini 3.1 Hybrid)")
    parser.add_argument("--hybrid", action="store_true", help="Use Gemini 3.1 Flash-Lite Hybrid Refiner during dataset export")
    parser.add_argument("--test", action="store_true", help="Run automated unit test suite")
    parser.add_argument("--eval", action="store_true", help="Run 25-listing ground-truth evaluation benchmark")
    parser.add_argument("--fetch", action="store_true", help="Fetch and cache missing detail HTML pages")
    parser.add_argument("--export", action="store_true", help="Re-export canonical housing dataset (XLSX, CSV, JSONL)")
    parser.add_argument("--metrics", action="store_true", help="Recompute statistical analysis metrics JSON")

    args = parser.parse_args()

    # If no specific flag passed, default to running all pipeline steps
    if not any([args.all, args.benchmark, args.hybrid, args.test, args.eval, args.fetch, args.export, args.metrics]):
        args.all = True

    if args.test:
        if not run_tests():
            sys.exit(1)

    if args.eval:
        if not run_evaluation():
            sys.exit(1)

    if args.benchmark:
        if not run_benchmark():
            sys.exit(1)

    if args.fetch:
        if not run_fetch():
            sys.exit(1)

    if args.export or args.hybrid:
        if not run_export(use_hybrid=args.hybrid):
            sys.exit(1)

    if args.metrics:
        if not run_metrics():
            sys.exit(1)

    if args.all:
        print("Starting End-to-End ECES Pipeline Execution (Deterministic Engine)...")
        if not run_tests():
            print("✖ Unit tests failed.")
            sys.exit(1)

        if not run_evaluation():
            print("✖ Evaluation benchmark failed.")
            sys.exit(1)

        if not run_export(use_hybrid=False):
            print("✖ Dataset export failed.")
            sys.exit(1)

        if not run_metrics():
            print("✖ Metrics generation failed.")
            sys.exit(1)

        print_summary_banner()


if __name__ == "__main__":
    main()
