"""Generate the five Part 3 tasks (descriptors + synthetic inputs) and print answer keys.

    uv run python scripts/make_tasks.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] / "tasks"
SEED = 7752
rng = np.random.default_rng(SEED)
DENSE, MULTI = "dense-precise-data", "multi-source-join"


def write(task_id, task_class, instructions, frames):
    folder = ROOT / task_id
    (folder / "inputs").mkdir(parents=True, exist_ok=True)
    for name, frame in frames.items():
        frame.to_csv(folder / "inputs" / name, index=False)
    descriptor = {
        "task_id": task_id,
        "task_class": task_class,
        "instructions": instructions,
        "inputs": [{"name": n, "path": f"inputs/{n}"} for n in frames],
    }
    (folder / "task.json").write_text(json.dumps(descriptor, indent=2) + "\n")


# 1. Cleveland dot plot: 40 labels, precise sort order and median line.
states = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
          "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
          "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
          "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
          "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
          "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina"]
commute = pd.DataFrame({"state": states, "minutes": np.round(rng.uniform(16, 38, 40), 1)})
write("commute-dot-plot", DENSE, """Using matplotlib, read commute.csv (columns: state, minutes) and draw a horizontal Cleveland dot plot of the average commute time for each of the 40 states.
Requirements:
- One circular dot per state, sorted so the state with the LONGEST commute is at the TOP and the shortest at the bottom.
- Show every state name as a y tick label (all 40 must be visible).
- Draw a vertical red dashed line at the median of the 40 values.
- Set the x axis limits to 0..45 and label the x axis 'Average commute (minutes)'.
- Set the title to exactly 'Average commute by state'.
- Make the figure 8 by 11 inches.
- Save the figure at 100 dpi.
Save the figure as figure.png.""", {"commute.csv": commute})
print("commute: median", commute.minutes.median(), "| top3", commute.nlargest(3, "minutes").values.tolist(),
      "| bottom", commute.nsmallest(1, "minutes").values.tolist())

# 2. Strip plot: 300 points, timeouts that must be excluded before means.
conditions = ["Baseline", "Low load", "Medium load", "High load"]
rows = []
for index, (condition, mean) in enumerate(zip(conditions, [420, 505, 610, 760])):
    values = np.round(rng.normal(mean, 90 + 25 * index, 75)).clip(180, 1450)
    values[rng.choice(75, 3 + index, replace=False)] = 9999
    rows += [{"participant": f"P{p + 1:02d}", "condition": condition, "rt_ms": int(v)}
             for p, v in enumerate(values)]
trials = pd.DataFrame(rows).sample(frac=1, random_state=1).reset_index(drop=True)
write("reaction-strip-plot", DENSE, """Using matplotlib, read trials.csv (columns: participant, condition, rt_ms). Each row is one reaction-time trial. Timed-out trials are recorded as rt_ms = 9999 and must be excluded before plotting and before computing any statistic.
Draw a strip plot of rt_ms by condition: one column of horizontally jittered dots per condition.
Requirements:
- Conditions left to right in exactly this order: Baseline, Low load, Medium load, High load.
- Jitter each dot horizontally by a small random offset (at most 0.15) from its condition's position.
- Draw the dots with alpha 0.5.
- Overlay each condition's mean (after excluding timeouts) as a short black horizontal bar of width 0.5 centred on its position.
- Set the y axis limits to 0..1600 and label the y axis 'Reaction time (ms)'.
- Give the chart a title.
Save the figure as figure.png.""", {"trials.csv": trials})
valid = trials[trials.rt_ms != 9999]
print("strip: means", valid.groupby("condition").rt_ms.mean().round(1).to_dict(),
      "| n", valid.groupby("condition").size().to_dict())

# 3. Dense scatter: 500 points, fixed category colours, top-5 annotations, fitted slope.
zones = rng.choice(["Arid", "Temperate", "Polar"], 500, p=[0.35, 0.45, 0.2])
elevation = np.round(rng.uniform(0, 4200, 500))
base = pd.Series(zones).map({"Arid": 24, "Temperate": 13, "Polar": -6}).to_numpy()
temperature = np.round(base - 0.0062 * elevation + rng.normal(0, 2.5, 500), 1)
stations = pd.DataFrame({"station_id": [f"ST{i:03d}" for i in range(1, 501)], "elevation_m": elevation,
                         "mean_temp_c": temperature, "climate_zone": zones})
write("station-scatter", DENSE, """Using matplotlib, read stations.csv (columns: station_id, elevation_m, mean_temp_c, climate_zone) and draw a scatter plot of mean temperature (y) against elevation (x) for all 500 weather stations.
Requirements:
- Colour points by climate_zone with exactly these colours: Arid = 'orange', Temperate = 'green', Polar = 'blue', and add a legend for the three zones.
- Annotate the 5 stations with the highest elevation with their station_id, placed next to their points.
- Fit one least-squares straight line to ALL 500 stations (ignoring zone) and draw it as a black dashed line across the full x range; include it in the legend as 'Least-squares fit'.
- Label the x axis 'Elevation (m)' and the y axis 'Mean temperature (°C)'.
- Give the chart a title.
- Make the figure 10 by 7 inches.
Save the figure as figure.png.""", {"stations.csv": stations})
slope = np.polyfit(stations.elevation_m, stations.mean_temp_c, 1)[0] * 1000
print("scatter: slope/km", round(slope, 2), "| top5", stations.nlargest(5, "elevation_m").station_id.tolist())

# 4. Join + filter + unmatched keys: revenue per region.
store_ids = [f"S{i:02d}" for i in range(1, 21)]
region_of = dict(zip(store_ids, rng.choice(["North", "South", "East", "West"], 20)))
months = pd.period_range("2023-12", "2024-12", freq="M").astype(str)
sales = pd.DataFrame([{"store_id": s, "month": m, "revenue_k": round(float(rng.uniform(40, 160)), 1)}
                      for s in store_ids for m in months])
stores = pd.DataFrame({"store_id": store_ids[:18], "region": [region_of[s] for s in store_ids[:18]]})
write("regional-revenue", MULTI, """Using matplotlib, read sales.csv (columns: store_id, month, revenue_k — monthly revenue in thousands of dollars) and stores.csv (columns: store_id, region). Join them on store_id and draw a vertical bar chart of total revenue in calendar year 2024 for each region.
Requirements:
- Use only months 2024-01 through 2024-12; sales.csv also contains 2023-12, which must be excluded.
- Stores that appear in sales.csv but not in stores.csv must be included in a separate bar labelled 'Unassigned'.
- Sort the bars by total revenue in descending order from left to right.
- Label the y axis 'Revenue in 2024 (thousand $)' and the x axis 'Region'.
- Set the title to exactly 'Revenue by region, 2024'.
Save the figure as figure.png.""", {"sales.csv": sales, "stores.csv": stores})
year = sales[sales.month.str.startswith("2024")].merge(stores, on="store_id", how="left").fillna({"region": "Unassigned"})
print("revenue:", year.groupby("region").revenue_k.sum().round(1).sort_values(ascending=False).to_dict())

# 5. Cross-file ratio with unit trap and a missing key.
districts = ["Ashford", "Bramley", "Carlow", "Dunmore", "Elmstead", "Fairview", "Glenside",
             "Harrow Vale", "Ivybridge", "Juniper", "Kestrel", "Linden"]
cases = pd.DataFrame([{"district": d, "year": y, "cases": int(rng.integers(40, 900))}
                      for d in districts for y in (2021, 2022, 2023)])
population = pd.DataFrame({"district": districts[:11],
                           "population_thousands": np.round(rng.uniform(35, 420, 11), 1)})
write("district-case-rates", MULTI, """Using matplotlib, read cases.csv (columns: district, year, cases) and population.csv (columns: district, population_thousands — population in THOUSANDS of people). Compute each district's 2023 case rate per 100,000 residents and draw it as a horizontal bar chart.
Requirements:
- Use only 2023 cases.
- Omit any district that has no entry in population.csv.
- Sort the bars so the highest rate is at the top.
- Draw a vertical black dashed line at the overall 2023 rate across the plotted districts (total cases divided by total population, per 100,000).
- Label the x axis 'Cases per 100,000 residents (2023)'.
- Give the chart a title.
- Make the figure 9 by 6 inches.
Save the figure as figure.png.""", {"cases.csv": cases, "population.csv": population})
c23 = cases[cases.year == 2023].merge(population, on="district")
rates = (c23.cases / (c23.population_thousands * 1000) * 1e5).round(1)
print("rates:", dict(zip(c23.district, rates)), "| overall",
      round(c23.cases.sum() / (c23.population_thousands.sum() * 1000) * 1e5, 1))

# Every ranked or sorted quantity must be tie-free so each task has one correct order.
assert commute.minutes.is_unique, "tie in commute minutes"
assert stations.elevation_m.nlargest(6).is_unique, "tie among top elevations"
assert year.groupby("region").revenue_k.sum().round(1).is_unique, "tie in regional totals"
assert rates.is_unique, "tie in case rates"
print("seed", SEED, "OK: no ties")
