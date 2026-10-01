# regional-revenue

<!-- Copied from tasks/regional-revenue/task.json. This is the prompt the three fixed agents
     were given, so do NOT reword it: check-submission holds both your runs
     and this file to the descriptor's wording. Add what your verifier needs
     under the heading below instead. -->

Using matplotlib, read sales.csv (columns: store_id, month, revenue_k — monthly revenue in thousands of dollars) and stores.csv (columns: store_id, region). Join them on store_id and draw a vertical bar chart of total revenue in calendar year 2024 for each region.
Requirements:
- Use only months 2024-01 through 2024-12; sales.csv also contains 2023-12, which must be excluded.
- Stores that appear in sales.csv but not in stores.csv must be included in a separate bar labelled 'Unassigned'.
- Sort the bars by total revenue in descending order from left to right.
- Label the y axis 'Revenue in 2024 (thousand $)' and the x axis 'Region'.
- Set the title to exactly 'Revenue by region, 2024'.
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
   `sales.csv` and `stores.csv` and write both `figure.png` and `plotted_values.json`, with no
   arguments and no manual steps. Do not do the work in a heredoc or with
   `python -c`; the script must survive on disk, and it must compute every value
   from the input file(s) rather than hard-coding it. It must render the same
   image every time it runs: if you use randomness (for example for jitter),
   use a fixed seed.
2. **`/app/figure.png`** - the chart. It must be the file that `plot.py` saves:
   re-running the script must reproduce this exact image.
3. **`/app/plotted_values.json`** - the values shown in the chart, written by
   `plot.py` from the same variables passed to the plotting functions.
   It must contain one JSON object with exactly two keys:
   - `"regions"`: a list of the bar labels (including `"Unassigned"`), in the
     order they appear on the chart from LEFT to RIGHT;
   - `"revenue_k"`: a list of JSON numbers, each bar's 2024 total in thousands
     of dollars, in that same order, unrounded.

   For example (truncated to two bars): `{"regions": ["A", "B"], "revenue_k": [0.0, 0.0]}`

Do not modify `sales.csv` and `stores.csv`.

Only matplotlib, numpy, pandas and Pillow are available, and there is no network
access; everything you need is already installed.
