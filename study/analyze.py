#!/usr/bin/env python3
"""Analyze study results and export paper figures."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", default="study/results.csv")
    parser.add_argument("--out", dest="out_dir", default="paper/figures")
    args = parser.parse_args()

    in_path = Path(args.in_path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(in_path)
    df["comprehension"] = df[["q1", "q2", "q3"]].mean(axis=1)

    # Figure 1: comprehension
    summary = df.groupby("condition")["comprehension"].mean().sort_index()
    ax = summary.plot(kind="bar")
    ax.set_ylabel("Mean comprehension (Q1–Q3)")
    ax.set_title("Baseline vs X-SHIELD comprehension")
    plt.tight_layout()
    plt.savefig(out_dir / "comprehension_baseline_vs_xshield.png")
    plt.close()

    # Figure 2: Likert
    likert = df.groupby("condition")[["clarity", "trust", "actionability"]].mean().sort_index()
    ax = likert.plot(kind="bar")
    ax.set_ylabel("Mean rating (1–5)")
    ax.set_title("Baseline vs X-SHIELD Likert ratings")
    plt.tight_layout()
    plt.savefig(out_dir / "likert_baseline_vs_xshield.png")
    plt.close()

    print(f"Saved figures to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

