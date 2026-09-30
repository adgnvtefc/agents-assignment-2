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
