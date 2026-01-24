#!/usr/bin/env python3
"""Create demo study results so the analysis pipeline can run end-to-end.

This generates *synthetic* results for pipeline testing only.
Replace study/results.csv with real participant responses for the paper.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import pandas as pd


SCENARIOS = ["s01", "s02", "s03", "s04", "s05", "s06", "s07", "s08"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="study/results.csv")
    parser.add_argument("--n_participants", type=int, default=8)
    args = parser.parse_args()

    random.seed(7)

    rows = []
    for pid in range(1, args.n_participants + 1):
        participant_id = f"P{pid:02d}"
        for s in SCENARIOS:
            # Simple within-subject counterbalance: odd P => first 4 baseline, even P => first 4 xshield
            idx = int(s[1:]) - 1
            if pid % 2 == 1:
                condition = "baseline" if idx < 4 else "xshield"
            else:
                condition = "xshield" if idx < 4 else "baseline"

            # Synthetic correctness: xshield a bit higher on average
            base_p = 0.55 if condition == "baseline" else 0.75
            q1 = 1 if random.random() < base_p else 0
            q2 = 1 if random.random() < base_p else 0
            q3 = 1 if random.random() < base_p else 0

            # Likert: xshield slightly higher
            likert_center = 2.8 if condition == "baseline" else 3.8
            clarity = max(1, min(5, round(random.gauss(likert_center, 0.6))))
            trust = max(1, min(5, round(random.gauss(likert_center, 0.6))))
            actionability = max(1, min(5, round(random.gauss(likert_center, 0.6))))

            rows.append({
                "participant_id": participant_id,
                "scenario": s,
                "condition": condition,
                "q1": q1,
                "q2": q2,
                "q3": q3,
                "clarity": clarity,
                "trust": trust,
                "actionability": actionability,
                "notes": "synthetic_demo",
            })

    df = pd.DataFrame(rows)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

