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
   `cases.csv` and `population.csv` and write both `figure.png` and `plotted_values.json`, with no
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
   - `"districts"`: a list of the plotted district names, in the order their
     bars appear on the chart from TOP to BOTTOM;
   - `"rates"`: a list of JSON numbers, each district's 2023 cases per 100,000
     residents, in that same order, unrounded;
   - `"overall_rate"`: a JSON number, the value at which the dashed line is drawn.

   For example (truncated to two bars): `{"districts": ["A", "B"], "rates": [0.0, 0.0], "overall_rate": 0.0}`

Do not modify `cases.csv` and `population.csv`.

Only matplotlib, numpy, pandas and Pillow are available, and there is no network
access; everything you need is already installed.
