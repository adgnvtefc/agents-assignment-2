#!/bin/bash
# MUTANT overlapping_labels: Correct data, colours, fit line and sidecar, but every top-5 label uses the same offset, so labels of nearby stations print on top of each other (what the GLM and Ministral agents did).
# Writes plot.py to disk and then runs it, because the task requires a re-runnable
# script to be left behind and the verifier re-executes it.
set -euo pipefail

cat > /app/plot.py <<'PY'
"""Scatter of mean temperature against elevation for 500 stations."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COLOURS = {"Arid": "orange", "Temperate": "green", "Polar": "blue"}
stations = pd.read_csv("stations.csv")

fig, ax = plt.subplots(figsize=(10, 7))
counts = {}
for zone, colour in COLOURS.items():
    rows = stations[stations["climate_zone"] == zone]
    ax.scatter(rows["elevation_m"], rows["mean_temp_c"], s=12, alpha=0.6, color=colour, label=zone)
    counts[zone] = int(len(rows))

slope, intercept = np.polyfit(stations["elevation_m"], stations["mean_temp_c"], 1)
xs = np.array([stations["elevation_m"].min(), stations["elevation_m"].max()])
ax.plot(xs, slope * xs + intercept, "k--", label="Least-squares fit")

top5 = stations.nlargest(5, "elevation_m")
for _, row in top5.iterrows():
    ax.annotate(row["station_id"], (row["elevation_m"], row["mean_temp_c"]),
                xytext=(5, 5), textcoords="offset points", fontsize=11)

ax.set_xlabel("Elevation (m)")
ax.set_ylabel("Mean temperature (°C)")
ax.set_title("Mean temperature against elevation for 500 stations")
ax.legend(loc="lower left")
fig.savefig("figure.png", dpi=100)

with open("plotted_values.json", "w") as handle:
    json.dump({"top5": top5["station_id"].tolist(), "slope_per_km": float(slope * 1000),
               "zone_counts": counts}, handle, indent=2)
PY

cd /app && python plot.py
