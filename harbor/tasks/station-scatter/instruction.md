# station-scatter

<!-- Copied from tasks/station-scatter/task.json. This is the prompt the three fixed agents
     were given, so do NOT reword it: check-submission holds both your runs
     and this file to the descriptor's wording. Add what your verifier needs
     under the heading below instead. -->

Using matplotlib, read stations.csv (columns: station_id, elevation_m, mean_temp_c, climate_zone) and draw a scatter plot of mean temperature (y) against elevation (x) for all 500 weather stations.
Requirements:
- Colour points by climate_zone with exactly these colours: Arid = 'orange', Temperate = 'green', Polar = 'blue', and add a legend for the three zones.
- Annotate the 5 stations with the highest elevation with their station_id, placed next to their points.
- Fit one least-squares straight line to ALL 500 stations (ignoring zone) and draw it as a black dashed line across the full x range; include it in the legend as 'Least-squares fit'.
- Label the x axis 'Elevation (m)' and the y axis 'Mean temperature (°C)'.
- Give the chart a title.
- Make the figure 10 by 7 inches.
Save the figure as figure.png.

## Required outputs

Leave these three files behind in `/app`, which is also the working directory.
In `plot.py`, refer to the input file(s) and to `figure.png` and
`plotted_values.json` by bare filename rather than by absolute path: the
verifier re-runs the script in a copied workspace, so an absolute path would
point outside that copy.

Saving extra images is allowed; the answer is graded from the figure saved as
`figure.png`. Give any extra image a different stem, so it cannot collide with
`figure.png`.

1. **`/app/plot.py`** - the plotting script. It must be a self-contained,
   re-runnable Python program: running `python plot.py` from `/app` must read
   `stations.csv` and write both `figure.png` and `plotted_values.json`, with no
   arguments and no manual steps. Do not do the work in a heredoc or with
   `python -c`; the script must survive on disk, and it must compute every value
   from the input file(s) rather than hard-coding it. It must render the same
   image every time it runs: if you use randomness (for example for jitter),
   use a fixed seed.
2. **`/app/figure.png`** - the chart. It must be the file that `plot.py` saves:
   re-running the script must reproduce this exact image.
3. **`/app/plotted_values.json`** - the values shown in the chart, written by
   `plot.py` from the same variables passed to the plotting functions.
   It must contain one JSON object with exactly three keys:
   - `"top5"`: a list of the five annotated station_id strings, highest
     elevation first;
   - `"slope_per_km"`: a JSON number, the slope of the drawn least-squares line
     in degrees Celsius per kilometre, unrounded;
   - `"zone_counts"`: a JSON object mapping each of `"Arid"`, `"Temperate"` and
     `"Polar"` to the number of points plotted in that colour, as a JSON integer.

   For example: `{"top5": ["A", "B", "C", "D", "E"], "slope_per_km": 0.0, "zone_counts": {"Arid": 0, "Temperate": 0, "Polar": 0}}`

Do not modify `stations.csv`.

Only matplotlib, numpy, pandas and Pillow are available, and there is no network
access; everything you need is already installed.
