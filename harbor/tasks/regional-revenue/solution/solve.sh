#!/bin/bash
# Reference solution for regional-revenue -- what `-a oracle` runs.
# Writes plot.py to disk and then runs it, because the task requires a re-runnable
# script to be left behind and the verifier re-executes it.
set -euo pipefail

cat > /app/plot.py <<'PY'
"""Total 2024 revenue per region, from sales.csv joined to stores.csv."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sales = pd.read_csv("sales.csv")
stores = pd.read_csv("stores.csv")
sales = sales[sales["month"].str.startswith("2024-")]             # drop 2023-12
joined = sales.merge(stores, on="store_id", how="left")
joined["region"] = joined["region"].fillna("Unassigned")          # stores with no region
totals = joined.groupby("region")["revenue_k"].sum().sort_values(ascending=False)

fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(totals.index, totals.values, color="#4C78A8")
ax.set_xlabel("Region")
ax.set_ylabel("Revenue in 2024 (thousand $)")
ax.set_title("Revenue by region, 2024")
fig.tight_layout()
fig.savefig("figure.png", dpi=100)

with open("plotted_values.json", "w") as handle:
    json.dump({"regions": totals.index.tolist(), "revenue_k": [float(v) for v in totals.values]},
              handle, indent=2)
PY

cd /app && python plot.py
