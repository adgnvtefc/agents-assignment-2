#!/bin/bash
# Reference solution for commute-dot-plot -- what `-a oracle` runs.
# Writes plot.py to disk and then runs it, because the task requires a re-runnable
# script to be left behind and the verifier re-executes it.
set -euo pipefail

cat > /app/plot.py <<'PY'
"""Cleveland dot plot of average commute time by state, longest at the top."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

data = pd.read_csv("commute.csv").sort_values("minutes", ascending=False).reset_index(drop=True)
median = float(data["minutes"].median())

fig, ax = plt.subplots(figsize=(8, 11))
positions = range(len(data))
ax.scatter(data["minutes"], positions, marker="o", color="#1f77b4", zorder=3)
ax.set_yticks(list(positions))
ax.set_yticklabels(data["state"])
ax.invert_yaxis()                               # first row (longest commute) at the top
ax.axvline(median, color="red", linestyle="--", label=f"Median ({median:g} min)")
ax.set_xlim(0, 45)
ax.set_xlabel("Average commute (minutes)")
ax.set_title("Average commute by state")
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig("figure.png", dpi=100)

with open("plotted_values.json", "w") as handle:
    json.dump({"states": data["state"].tolist(), "minutes": data["minutes"].tolist(),
               "median": median}, handle, indent=2)
PY

cd /app && python plot.py
