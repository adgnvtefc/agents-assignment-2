# commute-dot-plot

<!-- Copied from tasks/commute-dot-plot/task.json. This is the prompt the three fixed agents
     were given, so do NOT reword it: check-submission holds both your runs
     and this file to the descriptor's wording. Add what your verifier needs
     under the heading below instead. -->

Using matplotlib, read commute.csv (columns: state, minutes) and draw a horizontal Cleveland dot plot of the average commute time for each of the 40 states.
Requirements:
- One circular dot per state, sorted so the state with the LONGEST commute is at the TOP and the shortest at the bottom.
- Show every state name as a y tick label (all 40 must be visible).
- Draw a vertical red dashed line at the median of the 40 values.
- Set the x axis limits to 0..45 and label the x axis 'Average commute (minutes)'.
- Set the title to exactly 'Average commute by state'.
- Make the figure 8 by 11 inches.
- Save the figure at 100 dpi.
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
   `commute.csv` and write both `figure.png` and `plotted_values.json`, with no
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
   - `"states"`: a list of the 40 state names, in the order they appear on the
     chart from TOP to BOTTOM;
   - `"minutes"`: a list of 40 JSON numbers, the commute time of each state in
     that same order, unrounded;
   - `"median"`: a JSON number, the value at which the median line is drawn.

   For example (truncated to two states):
   `{"states": ["A", "B"], "minutes": [0.0, 0.0], "median": 0.0}`

Do not modify `commute.csv`.

Only matplotlib, numpy, pandas and Pillow are available, and there is no network
access; everything you need is already installed.
