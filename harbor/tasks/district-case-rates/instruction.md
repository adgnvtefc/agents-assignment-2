# district-case-rates

<!-- Copied from tasks/district-case-rates/task.json. This is the prompt the three fixed agents
     were given, so do NOT reword it: check-submission holds both your runs
     and this file to the descriptor's wording. Add what your verifier needs
     under the heading below instead. -->

Using matplotlib, read cases.csv (columns: district, year, cases) and population.csv (columns: district, population_thousands — population in THOUSANDS of people). Compute each district's 2023 case rate per 100,000 residents and draw it as a horizontal bar chart.
Requirements:
- Use only 2023 cases.
- Omit any district that has no entry in population.csv.
- Sort the bars so the highest rate is at the top.
- Draw a vertical black dashed line at the overall 2023 rate across the plotted districts (total cases divided by total population, per 100,000).
- Label the x axis 'Cases per 100,000 residents (2023)'.
- Give the chart a title.
- Make the figure 9 by 6 inches.
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
