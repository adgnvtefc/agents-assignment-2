#!/bin/bash
# MUTANT thousands_unit: Forgets that population is in thousands, so every rate is 1000x too large (the mistake the Qwen agent made in its own run).
# Writes plot.py to disk and then runs it, because the task requires a re-runnable
# script to be left behind and the verifier re-executes it.
set -euo pipefail

cat > /app/plot.py <<'PY'
"""2023 case rate per 100,000 residents by district (population is in thousands)."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

cases = pd.read_csv("cases.csv")
population = pd.read_csv("population.csv")
merged = cases[cases["year"] == 2023].merge(population, on="district", how="inner")  # drops unmatched
residents = merged["population_thousands"]  # BUG: ignores thousands
merged["rate"] = merged["cases"] / residents * 100_000
merged = merged.sort_values("rate", ascending=False).reset_index(drop=True)
overall = float(merged["cases"].sum() / residents.sum() * 100_000)

fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(merged["district"], merged["rate"], color="#4C78A8")
ax.invert_yaxis()                                  # highest rate at the top
ax.axvline(overall, color="black", linestyle="--", label=f"Overall rate ({overall:.1f})")
ax.set_xlabel("Cases per 100,000 residents (2023)")
ax.set_title("District case rates, 2023")
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig("figure.png", dpi=100)

with open("plotted_values.json", "w") as handle:
    json.dump({"districts": merged["district"].tolist(), "rates": merged["rate"].tolist(),
               "overall_rate": overall}, handle, indent=2)
PY

cd /app && python plot.py
