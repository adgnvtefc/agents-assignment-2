# reaction-strip-plot

<!-- Copied from tasks/reaction-strip-plot/task.json. This is the prompt the three fixed agents
     were given, so do NOT reword it: check-submission holds both your runs
     and this file to the descriptor's wording. Add what your verifier needs
     under the heading below instead. -->

Using matplotlib, read trials.csv (columns: participant, condition, rt_ms). Each row is one reaction-time trial. Timed-out trials are recorded as rt_ms = 9999 and must be excluded before plotting and before computing any statistic.
Draw a strip plot of rt_ms by condition: one column of horizontally jittered dots per condition.
Requirements:
- Conditions left to right in exactly this order: Baseline, Low load, Medium load, High load.
- Jitter each dot horizontally by a small random offset (at most 0.15) from its condition's position.
- Draw the dots with alpha 0.5.
- Overlay each condition's mean (after excluding timeouts) as a short black horizontal bar of width 0.5 centred on its position.
- Set the y axis limits to 0..1600 and label the y axis 'Reaction time (ms)'.
- Give the chart a title.
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
   `trials.csv` and write both `figure.png` and `plotted_values.json`, with no
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
   - `"conditions"`: a list of the four condition names, in the order they
     appear on the chart from LEFT to RIGHT;
   - `"n"`: a list of four JSON integers, the number of trials plotted for each
     condition, in that same order;
   - `"means"`: a list of four JSON numbers, the mean reaction time (ms) drawn
     as each condition's black bar, in that same order, unrounded.

   For example: `{"conditions": ["A", "B", "C", "D"], "n": [0, 0, 0, 0], "means": [0.0, 0.0, 0.0, 0.0]}`

Do not modify `trials.csv`.

Only matplotlib, numpy, pandas and Pillow are available, and there is no network
access; everything you need is already installed.
