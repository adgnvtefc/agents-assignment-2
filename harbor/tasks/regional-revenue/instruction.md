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

Leave these behind in `/app`, which is also the working directory. `plot.py` must
refer to these files by bare filename rather than by absolute path. State this
requirement explicitly: the verifier re-runs the script in a copied workspace,
so an absolute output path would point outside that copy.

TODO: decide whether extra images are allowed and say so. The example allows
them and grades the one named `figure.png`; requiring "exactly one figure" is
also fine, but then your verifier has to actually check it -- do not state a
rule you do not enforce.

1. **`/app/plot.py`** - the plotting script. Self-contained and re-runnable:
   `python plot.py` from `/app` must reproduce the figure with no arguments and
   no manual steps. It must read the input file rather than hard-code results,
   and it must render the same image every time it runs.
2. **`/app/figure.png`** - the chart, as saved by that script.
3. **`/app/plotted_values.json`** - the values shown in the chart. Generate this
   file from the same variables used to draw the figure. Part 3 requires this
   sidecar because the verifier cannot reliably recover exact values from the
   PNG. **TODO:** Specify the exact keys and value types, and include a small
   all-zero example like the one in `harbor/example/instruction.md`.

TODO: state the prohibitions your verifier relies on, e.g. do not modify the
input file.

Only the libraries already installed are available and there is no network
access; everything you need is in the image.
