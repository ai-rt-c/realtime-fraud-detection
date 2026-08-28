"""Create a portable chart from the Parquet aggregates written by Spark."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import timezone
from pathlib import Path
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plot Spark-generated fraud-detection aggregates from Parquet files."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("output"),
        help="Directory containing the Spark Parquet output.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/stream_summary.png"),
        help="PNG file to create.",
    )
    return parser


def find_parquet_files(input_path: Path) -> list[Path]:
    if not input_path.is_dir():
        raise FileNotFoundError(f"Parquet output directory was not found: {input_path}")
    files = sorted(
        path for path in input_path.rglob("*.parquet") if path.stat().st_size
    )
    if not files:
        raise FileNotFoundError(
            f"No non-empty Parquet files were found in: {input_path}"
        )
    return files


def window_start(value: Any) -> pd.Timestamp:
    """Normalize Spark's nested window representation across parquet readers."""

    if isinstance(value, Mapping):
        value = value.get("start")
    elif hasattr(value, "start"):
        value = value.start
    timestamp = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(timestamp):
        raise ValueError(f"Could not parse a window start value: {value!r}")
    return timestamp


def summarize(parquet_files: list[Path]) -> pd.DataFrame:
    frames = [pd.read_parquet(path) for path in parquet_files]
    data = pd.concat(frames, ignore_index=True)
    required_columns = {"window", "tx_count", "total_amount", "is_suspicious"}
    missing = required_columns - set(data.columns)
    if missing:
        raise ValueError(
            f"Parquet output is missing expected columns: {sorted(missing)}"
        )

    data["window_start"] = data["window"].map(window_start)
    return (
        data.groupby("window_start", as_index=False)
        .agg(
            tx_count=("tx_count", "sum"),
            total_amount=("total_amount", "sum"),
            is_suspicious=("is_suspicious", "max"),
        )
        .sort_values("window_start")
    )


def plot_summary(summary: pd.DataFrame, output_path: Path) -> None:
    if summary.empty:
        raise ValueError("No aggregate rows are available to plot.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, count_axis = plt.subplots(figsize=(12, 6))
    amount_axis = count_axis.twinx()

    count_axis.bar(
        summary["window_start"],
        summary["tx_count"],
        width=0.0005,
        color="#4C78A8",
        alpha=0.8,
        label="Transaction count",
    )
    high_risk = summary[summary["is_suspicious"] == 1]
    if not high_risk.empty:
        count_axis.scatter(
            high_risk["window_start"],
            high_risk["tx_count"],
            color="#E45756",
            marker="D",
            label="Suspicious window",
            zorder=3,
        )
    amount_axis.plot(
        summary["window_start"],
        summary["total_amount"],
        color="#54A24B",
        marker="o",
        label="Total amount",
    )

    count_axis.set_title("Real-Time Transaction Monitoring and Fraud Detection")
    count_axis.set_xlabel("Window start (UTC)")
    count_axis.set_ylabel("Transaction count")
    amount_axis.set_ylabel("Total amount")
    count_axis.xaxis.set_major_locator(
        mdates.MinuteLocator(interval=1, tz=timezone.utc)
    )
    count_axis.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    figure.autofmt_xdate()

    handles, labels = count_axis.get_legend_handles_labels()
    amount_handles, amount_labels = amount_axis.get_legend_handles_labels()
    count_axis.legend(
        handles + amount_handles, labels + amount_labels, loc="upper left"
    )
    figure.tight_layout()
    figure.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    args = build_parser().parse_args()
    summary = summarize(find_parquet_files(args.input))
    plot_summary(summary, args.output)
    print(f"Saved {len(summary)} aggregated windows to {args.output}")


if __name__ == "__main__":
    main()
