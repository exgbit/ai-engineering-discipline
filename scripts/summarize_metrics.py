#!/usr/bin/env python3
"""Summarize Spec / Verify / Memory pilot metrics from CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


RATE_FIELDS = {
    "spec_coverage_rate",
    "test_traceability_rate",
    "main_branch_failure_rate",
    "memory_update_rate",
}


def parse_float(value: str) -> float:
    value = value.strip()
    if value.endswith("%"):
        return float(value[:-1]) / 100
    return float(value)


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fmt_value(field: str, value: float) -> str:
    if field in RATE_FIELDS:
        return f"{value * 100:.1f}%"
    return f"{value:.2f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "csv_path",
        nargs="?",
        default="data/sample-adoption-metrics.csv",
        help="Path to adoption metrics CSV.",
    )
    args = parser.parse_args()

    path = Path(args.csv_path)
    rows = load_rows(path)
    if len(rows) < 2:
        raise SystemExit("Need at least two rows: baseline and latest.")

    baseline = rows[0]
    latest = rows[-1]
    fields = [
        "spec_coverage_rate",
        "test_traceability_rate",
        "review_rounds_per_pr",
        "main_branch_failure_rate",
        "escaped_defects",
        "memory_update_rate",
    ]

    print("# Pilot Metrics Summary")
    print()
    print(f"- Baseline: `{baseline['week']}`")
    print(f"- Latest: `{latest['week']}`")
    print()
    print("| Metric | Baseline | Latest | Delta |")
    print("|---|---:|---:|---:|")
    for field in fields:
        start = parse_float(baseline[field])
        end = parse_float(latest[field])
        delta = end - start
        print(
            f"| {field} | {fmt_value(field, start)} | "
            f"{fmt_value(field, end)} | {fmt_value(field, delta)} |"
        )

    print()
    print("Use this summary as directional pilot evidence, not as a universal benchmark.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
