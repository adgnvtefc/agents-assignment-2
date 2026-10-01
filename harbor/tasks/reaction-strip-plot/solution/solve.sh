#!/bin/bash
# Reference solution for reaction-strip-plot -- what `-a oracle` runs.
# Writes plot.py to disk and then runs it, because the task requires a re-runnable
# script to be left behind and the verifier re-executes it.
set -euo pipefail

cat > /app/plot.py <<'PY'
"""Strip plot of reaction times by condition, timeouts (9999) excluded."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ORDER = ["Baseline", "Low load", "Medium load", "High load"]
trials = pd.read_csv("trials.csv")
trials = trials[trials["rt_ms"] != 9999]          # drop timed-out trials first

rng = np.random.default_rng(0)                    # fixed seed: same jitter every run
fig, ax = plt.subplots(figsize=(8, 6))
counts, means = [], []
for position, condition in enumerate(ORDER):
    values = trials.loc[trials["condition"] == condition, "rt_ms"].to_numpy()
    jitter = rng.uniform(-0.15, 0.15, len(values))
    ax.scatter(position + jitter, values, alpha=0.5, s=18, color="#1f77b4")
    mean = float(values.mean())
    ax.hlines(mean, position - 0.25, position + 0.25, color="black", linewidth=2.5)
    counts.append(int(len(values)))
    means.append(mean)
ax.set_xticks(range(len(ORDER)))
ax.set_xticklabels(ORDER)
ax.set_ylim(0, 1600)
ax.set_ylabel("Reaction time (ms)")
ax.set_title("Reaction time by condition (timeouts excluded)")
fig.tight_layout()
fig.savefig("figure.png", dpi=100)

with open("plotted_values.json", "w") as handle:
    json.dump({"conditions": ORDER, "n": counts, "means": means}, handle, indent=2)
PY

cd /app && python plot.py
