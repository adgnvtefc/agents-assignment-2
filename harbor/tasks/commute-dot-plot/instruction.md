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
