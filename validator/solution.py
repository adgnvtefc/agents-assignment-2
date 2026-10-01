"""The validator you write. This is the only file you need to modify.

Each function evaluates a single run object and returns the errors it finds.
An empty list means that no errors were found. `validator/runner.py` defines
what a run object contains, and `ASSIGNMENT.md` defines the four error families you may report.

Each family is judged from only the evidence it depends on:
- execution_failure: whether figure.png exists (deterministic).
- wrong_data: the request, the agent's final code and a schema of the inputs, then the figure
  to verify the code-based finding.
- wrong_chart: the request and the figure; no code. Plus a deterministic dpi/size check.
- hard_to_read: the figure only, except that overlapping and clipped text are measured by
  re-running the agent's code with matplotlib's text drawing hooked (falling back to the model,
  with a pixel check for clipping, when the code cannot be re-run here).
"""

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import matplotlib
import matplotlib.colors
import numpy as np
import pandas as pd
from PIL import Image

from validator.model import complete
from validator.prediction import Error, ErrorFamily
from validator.runner import Run

MAX_CHARS = 12000        # per text block (code) sent to the model
MAX_OBSERVATION = 300    # characters per observation; stops runaway, truncated JSON
SIZE_TOLERANCE = 0.15    # inches


def _clip(text: str) -> str:
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS // 2] + "\n[...]\n" + text[-MAX_CHARS // 2:]


def final_code(run: Run) -> str:
    """The last figure-saving code the agent wrote or ran."""
    code = ""
    for message in run.messages:
        for call in message.get("tool_calls") or []:
            command = json.loads(call["function"]["arguments"]).get("command", "")
            if "savefig" in command:
                heredoc = re.search(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n(.*?)\n\1\b", command, re.S)
                code = heredoc.group(2) if heredoc else command
    return code


def input_schema(run: Run) -> str:
    """Columns, row count and a few rows of each input -- enough to check logic, not to add up."""
    parts = []
    for name, path in run.inputs.items():
        try:
            frame = pd.read_csv(path)
            parts.append(f"--- {name}: {len(frame)} rows; columns {list(frame.columns)} ---\n"
                         f"{frame.head(5).to_string(index=False)}")
        except Exception:
            parts.append(f"--- {name} (first lines) ---\n{path.read_text(errors='replace')[:800]}")
    return "\n".join(parts) or "(none; any data is given in the request)"


def ask(run: Run, prompt: str, keys: list[str], verdicts: list[str], image: bool = True,
        notes: tuple[str, ...] = ("observation",)) -> dict:
    """Ask for the text fields in `notes` plus a verdict per key; return {key: notes joined} for
    every key whose verdict is the first (problem) verdict. Unparseable output counts as no problem."""
    finding = {"type": "object", "required": [*notes, "verdict"], "properties": {
        **{note: {"type": "string", "maxLength": MAX_OBSERVATION} for note in notes},
        "verdict": {"type": "string", "enum": verdicts}}}
    schema = {"type": "object", "required": keys, "properties": {key: finding for key in keys}}
    content = [{"type": "text", "text": prompt}]
    if image:
        encoded = base64.b64encode(run.figure.read_bytes()).decode()
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}})
    response = complete(
        [{"role": "user", "content": content}],
        max_tokens=2000,
        response_format={"type": "json_schema", "json_schema": {"name": "check", "schema": schema}},
        # The schema allows unlimited whitespace between fields, and the model sometimes
        # loops on it until max_tokens. Well-formed output never has a blank line, so stop there.
        stop=["\n" + " " * width + "\n" for width in range(9)],
    )
    answer = _parse(response["choices"][0]["message"]["content"] or "")
    if answer is None:
        warnings.warn(f"Run {run.run_id}: unparseable model output; treating as no problem.")
        return {}
    found = {}
    for key in keys:
        item = answer.get(key)
        if not isinstance(item, dict) or item.get("verdict") != verdicts[0]:
            continue
        text = " | ".join(f"{note}: {str(item.get(note, '')).strip()}" if len(notes) > 1
                          else str(item.get(note, "")).strip() for note in notes)
        if str(item.get(notes[0], "")).strip():
            found[key] = text
    return found


def _parse(text: str) -> dict | None:
    """Parse the model's JSON, closing it if generation stopped early (keys it never reached are absent)."""
    text = text.rstrip().rstrip(",")
    for closing in ("", "}", "}}", '"}}', '"}}}'):
        try:
            answer = json.loads(text + closing)
            return answer if isinstance(answer, dict) else None
        except json.JSONDecodeError:
            continue
    return None


def _errors(family: ErrorFamily, found: dict) -> list[Error]:
    evidence = "; ".join(f"{key.replace('_', ' ')}: {text}" for key, text in found.items())
    return [Error(family=family, evidence=evidence)] if found else []


def judge_execution(run: Run) -> list[Error]:
    """Whether the run produced a figure to judge at all."""
    if run.figure is None or run.figure.stat().st_size == 0:
        return [Error(family=ErrorFamily.EXECUTION_FAILURE, evidence="the run saved no figure.png")]
    return []


def size_and_dpi(run: Run) -> dict:
    """Compare the dpi and size recorded in the PNG with the ones the request names."""
    with Image.open(run.figure) as image:
        dpi = (image.info.get("dpi") or (None,))[0]
        width, height = image.size
    if not dpi:
        return {}
    found = {}
    want_dpi = re.search(r"(\d+)\s*dpi\b", run.instructions, re.I)
    if want_dpi and round(dpi) != int(want_dpi.group(1)):
        found["dpi"] = f"the request asks for {want_dpi.group(1)} dpi; the figure was saved at {round(dpi)} dpi"
    want_size = re.search(r"(\d+(?:\.\d+)?)\s*(?:by|x|×)\s*(\d+(?:\.\d+)?)\s*inch", run.instructions, re.I)
    # bbox_inches='tight' crops the saved image without changing the figure size, so skip it.
    if want_size and "tight" not in final_code(run):
        want = (float(want_size.group(1)), float(want_size.group(2)))
        got = (width / dpi, height / dpi)
        if any(abs(w - g) > SIZE_TOLERANCE for w, g in zip(want, got)):
            found["figure_size"] = (f"the request asks for {want[0]:g} by {want[1]:g} inches; "
                                    f"the figure is {got[0]:.2f} by {got[1]:.2f} inches")
    return found


MEASURED_NOTE = """
These are measured exactly from the figure and checked separately -- answer "met" for anything that is only
about them: title and axis-label text, whether a legend or colorbar exists, colormap names, axis scales,
tick-label rotation, removed ticks, hidden spines, gridlines, 3D/polar projection, the colours of named series,
figure size and dpi."""


def judge_chart(run: Run, facts: dict | None = None) -> list[Error]:
    keys = ["chart_type", "layout", "axes", "legend_colorbar_annotations", "style"]
    prompt = f"""Check whether the attached figure follows the requested chart DESIGN. Ignore the data values.

Request:
{run.instructions}

For each aspect, write what the request explicitly asks for and what the figure shows, then give a verdict:
- chart_type: chart type or projection (bar vs line, horizontal vs vertical, stacked, 3D, polar, twin axes, inset).
- layout: number and arrangement of subplots, shared axes.
- axes: axis labels, exact title/label text, axis limits, scale (log/linear), ticks, tick labels and rotation, spines, grid.
- legend_colorbar_annotations: legend, colour bar, requested annotations, marked points or value labels.
- style: colormap (including forbidden ones), line style, markers, named colours, fills.
Verdicts: "violated" only if the request explicitly asks for something in this aspect and the figure does not
do it; "met" if it does; "not_requested" if the request says nothing about this aspect.
Ignore figure size and dpi; they are checked separately.""" + (MEASURED_NOTE if facts else "")
    found = ask(run, prompt, keys, ["violated", "met", "not_requested"])
    # Measured findings are added on top of the model's; for the measured aspects the model was told
    # to answer "met", so the deterministic result is the one that counts.
    found |= size_and_dpi(run) | (requirement_findings(run.instructions, facts) if facts else {})
    return _errors(ErrorFamily.WRONG_CHART, found)


def judge_data(run: Run) -> list[Error]:
    code = final_code(run)
    if not code:
        return []
    keys = ["wrong_values", "missing_data", "wrong_selection", "wrong_order"]
    prompt = f"""Decide whether the agent plotted the DATA the request asks for, in two steps.
Judge only the data. These are DESIGN, not data, and are checked separately -- if the only problem you see is
one of them, the verdict is "ok": chart type (e.g. bars instead of a pie), number or arrangement of subplots,
colormaps and colours, marker size or style, value labels, annotations, titles, axis labels, limits and scales.

Step 1, the code (this comes first): read the agent's code and check the STEPS -- filters, joins, unit
conversions, formulas, aggregation, which series are drawn, and order. Do not compute totals yourself.
Step 2, the chart: use the attached figure to verify your step-1 conclusion -- is the requested series or
dimension actually visible, is the order on screen the requested one, is a 3D quantity drawn in 3D?
Do not read exact numbers off the chart; it can confirm structure, not values.

Request:
{run.instructions}

Input files (schema and first rows only):
{input_schema(run)}

Agent's final plotting code:
{_clip(code)}

For each failure mode, write "code" (your step-1 finding), then "chart" (what the figure shows about it),
then a verdict:
- wrong_values: wrong formula, aggregation, scaling, unit conversion, normalisation or sampled range.
- missing_data: a requested series, category, panel or dimension is not plotted.
- wrong_selection: wrong column, subset or filter; a requested filter or exclusion is missing; unrequested series mixed in.
- wrong_order: the plotted order differs from the requested one. Note that with barh(), or with y positions
  0..n-1, the FIRST row is drawn at the BOTTOM unless the y axis is inverted; and that labels must be placed at
  the same positions as the values they name.
Verdicts: "error" only if a specific line of code contradicts a specific phrase in the request AND the chart
does not contradict that finding (it confirms it, or cannot show it, as with a wrong constant); otherwise "ok"."""
    return _errors(ErrorFamily.WRONG_DATA,
                   ask(run, prompt, keys, ["error", "ok"], notes=("code", "chart")))


def judge_data_and_chart(run: Run, facts: dict | None = None) -> list[Error]:
    """Whether the figure plots the requested data, built the requested way."""
    return judge_data(run) + judge_chart(run, facts)


#: Loaded as `sitecustomize` when the agent's code is re-run. At each savefig it records the
#: window extent and colour of every text matplotlib draws, the structure of every axes (titles,
#: labels, scales, ticks, spines, grid, legend, colorbar, series styles) and every colormap called.
#: Any failure leaves the agent's program unchanged.
FIGURE_HOOK = r'''
import json, os
try:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.colors import Colormap, to_rgba
    from matplotlib.figure import Figure
    from matplotlib.text import Text
    _drawn, _cmaps = [], set()
    _cmap_call = Colormap.__call__
    def _cmap_called(self, *args, **kwargs):
        _cmaps.add(self.name)          # catches mappables and colormaps applied by hand
        return _cmap_call(self, *args, **kwargs)
    Colormap.__call__ = _cmap_called
    _text_draw = Text.draw
    def _draw(self, renderer):
        result = _text_draw(self, renderer)
        try:
            if self.get_visible() and self.get_text().strip() and (self.get_alpha() is None or self.get_alpha() > 0):
                box = Text.get_window_extent(self, renderer)   # text only, not an annotation's arrow
                _drawn.append({"text": self.get_text(), "rotation": float(self.get_rotation()),
                               "color": list(to_rgba(self.get_color(), self.get_alpha())),
                               "box": [box.x0, box.y0, box.x1, box.y1],
                               "canvas": [renderer.width, renderer.height]})
        except Exception:
            pass
        return result
    Text.draw = _draw
    # bbox_inches="tight" draws the figure twice, the second time shifted onto the cropped
    # canvas; keep only the texts of the last full pass.
    _figure_draw = Figure.draw
    def _hooked_figure_draw(self, renderer):
        _drawn.clear()
        return _figure_draw(self, renderer)
    Figure.draw = _hooked_figure_draw

    def _style(artist, label):
        if hasattr(artist, "patches"):                    # BarContainer and friends
            artist = artist.patches[0] if len(artist.patches) else None
        if artist is None:
            return None
        if hasattr(artist, "get_linestyle") and hasattr(artist, "get_marker"):      # Line2D
            return {"label": label, "kind": "line", "color": list(to_rgba(artist.get_color(), artist.get_alpha())),
                    "edge": None, "linestyle": str(artist.get_linestyle()), "marker": str(artist.get_marker()),
                    "linewidth": float(artist.get_linewidth())}
        if hasattr(artist, "get_facecolors"):                                         # collections
            face, edge = artist.get_facecolors(), artist.get_edgecolors()
            return {"label": label, "kind": "collection", "color": list(face[0]) if len(face) else None,
                    "edge": list(edge[0]) if len(edge) else None, "linestyle": "", "marker": "",
                    "linewidth": float(artist.get_linewidths()[0]) if len(artist.get_linewidths()) else 0.0}
        if hasattr(artist, "get_facecolor"):                                          # patches
            return {"label": label, "kind": "patch", "color": list(artist.get_facecolor()),
                    "edge": list(artist.get_edgecolor()), "linestyle": "", "marker": "",
                    "linewidth": float(artist.get_linewidth())}
        return None

    def _axes_facts(ax):
        def ticks(labels):
            return [[t.get_text(), float(t.get_rotation())] for t in labels if t.get_visible() and t.get_text().strip()]
        handles, labels = ax.get_legend_handles_labels()
        series = [s for s in (_style(h, l) for h, l in zip(handles, labels)) if s]
        drawn = [s for s in (_style(a, a.get_label()) for a in list(ax.lines) + list(ax.collections)
                 + list(ax.containers)) if s]
        legend = ax.get_legend()
        grid = False
        if ax.name in ("rectilinear", "polar"):
            grid = any(line.get_visible() for line in ax.get_xgridlines() + ax.get_ygridlines())
        return {"name": ax.name,
                "colorbar": getattr(ax, "_colorbar", None) is not None or ax.get_label() == "<colorbar>",
                "titles": [ax.get_title(loc) for loc in ("left", "center", "right")],
                "xlabel": ax.get_xlabel(), "ylabel": ax.get_ylabel(),
                "zlabel": ax.get_zlabel() if hasattr(ax, "get_zlabel") else "",
                "xscale": ax.get_xscale(), "yscale": ax.get_yscale(),
                "xticks": ticks(ax.get_xticklabels()), "yticks": ticks(ax.get_yticklabels()),
                "spines": {side: bool(spine.get_visible()) for side, spine in ax.spines.items()},
                "grid": grid, "legend": bool(legend is not None and legend.get_texts()),
                "facecolor": list(to_rgba(ax.get_facecolor())), "series": series, "drawn": drawn}

    _savefig = Figure.savefig
    def _hooked_savefig(self, fname, *args, **kwargs):
        _drawn.clear()
        try:
            return _savefig(self, fname, *args, **kwargs)
        finally:
            try:
                axes = []
                for ax in self.axes:
                    try:
                        axes.append(_axes_facts(ax))
                    except Exception:
                        pass
                suptitle = self._suptitle.get_text() if getattr(self, "_suptitle", None) else ""
                out = os.environ["FIGURE_FACTS_OUT"]
                records = json.load(open(out)) if os.path.exists(out) else []
                records.append({"file": str(fname), "tight": kwargs.get("bbox_inches") == "tight",
                                "texts": list(_drawn), "axes": axes, "suptitle": suptitle,
                                "figure_legend": bool(self.legends), "cmaps": sorted(_cmaps),
                                "facecolor": list(to_rgba(self.get_facecolor()))})
                json.dump(records, open(out, "w"))
            except Exception:
                pass
    Figure.savefig = _hooked_savefig
except Exception:
    pass
'''
RERUN_TIMEOUT = 60
CONTRAST_MIN = 2.5        # the assignment's threshold for readable text
INVISIBLE_CONTRAST = 1.15  # a series this close to the background colour cannot be seen


def _luminance(rgb) -> float:
    channels = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb[:3]]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(a, b) -> float:
    """WCAG contrast ratio between two RGB(A) colours with components in 0..1."""
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _text_contrasts(record: dict, image_path: Path) -> list:
    """Contrast of each drawn text against the pixels just around it in the re-rendered image."""
    try:
        pixels = np.asarray(Image.open(image_path).convert("RGB")).astype(float) / 255
    except Exception:
        return []
    height, width = pixels.shape[:2]
    out = []
    for item in record["texts"]:
        cw, ch = item["canvas"]
        sx, sy = width / cw, height / ch
        x0, y0, x1, y1 = item["box"]
        left, right = int(x0 * sx) - 3, int(x1 * sx) + 3
        top, bottom = int(height - y1 * sy) - 3, int(height - y0 * sy) + 3
        if right <= 0 or bottom <= 0 or left >= width or top >= height:
            continue
        region = pixels[max(top, 0):min(bottom, height), max(left, 0):min(right, width)]
        inner = np.ones(region.shape[:2], bool)
        inner[3:-3, 3:-3] = False                       # keep only the 3-pixel ring around the text
        ring = region[inner]
        if not len(ring):
            continue
        background = np.median(ring, axis=0)
        r, g, b, alpha = item["color"]
        colour = alpha * np.array([r, g, b]) + (1 - alpha) * background
        out.append([item["text"], contrast(colour, background)])
    return out


def figure_facts(run: Run) -> dict | None:
    """Re-run the agent's final code with FIGURE_HOOK and return what was recorded for figure.png.

    Runs agent-written code in a scratch directory holding copies of the inputs. Returns None
    when the code cannot be re-run here (missing package such as seaborn, absolute paths,
    timeout), in which case every check that needs the facts falls back to the model.
    """
    code = final_code(run)
    if not code:
        return None
    with tempfile.TemporaryDirectory(prefix="validator-rerun-") as scratch:
        scratch = Path(scratch)
        (scratch / "hook").mkdir()
        (scratch / "hook" / "sitecustomize.py").write_text(FIGURE_HOOK)
        work = scratch / "work"
        work.mkdir()
        for name, path in run.inputs.items():
            shutil.copy(path, work / name)
        out = scratch / "facts.json"
        env = {**os.environ, "PYTHONPATH": str(scratch / "hook"), "MPLBACKEND": "Agg",
               "FIGURE_FACTS_OUT": str(out),
               "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '')}"}
        if code.lstrip().startswith(("python", "cd ")):     # inline `python -c "..."` commands
            command = ["bash", "-c", code]
        else:
            (work / "plot.py").write_text(code)
            command = [sys.executable, "plot.py"]
        try:
            subprocess.run(command, cwd=work, env=env, capture_output=True, timeout=RERUN_TIMEOUT)
        except (subprocess.TimeoutExpired, OSError):
            return None
        if not out.exists():
            return None
        records = json.loads(out.read_text())
        named = [record for record in records if record["file"].endswith("figure.png")]
        record = (named or records or [None])[-1]
        if record is not None:
            record["contrasts"] = _text_contrasts(record, work / record["file"])
    return record


def _unique_texts(record: dict) -> list:
    texts, seen = [], set()
    for item in record["texts"]:
        key = (item["text"], *(round(v) for v in item["box"]))
        if key not in seen:
            seen.add(key)
            texts.append(item)
    return texts


def _entirely_outside(item: dict) -> bool:
    x0, y0, x1, y1 = item["box"]
    width, height = item["canvas"]
    return x1 <= 0 or y1 <= 0 or x0 >= width or y0 >= height


def text_findings(record: dict) -> dict:
    """Overlapping and partly clipped text, from the drawn text boxes."""
    texts = _unique_texts(record)
    overlaps = []
    for i, a in enumerate(texts):
        for b in texts[i + 1:]:
            # Axis-aligned boxes of rotated text overlap even when the glyphs do not; skip those.
            if a["rotation"] % 90 or b["rotation"] % 90:
                continue
            (ax0, ay0, ax1, ay1), (bx0, by0, bx1, by1) = a["box"], b["box"]
            width, height = min(ax1, bx1) - max(ax0, bx0), min(ay1, by1) - max(ay0, by0)
            if width <= 2 or height <= 2:
                continue
            smaller = min((ax1 - ax0) * (ay1 - ay0), (bx1 - bx0) * (by1 - by0))
            if smaller > 0 and width * height / smaller > 0.2:
                overlaps.append(f"'{a['text']}' and '{b['text']}' overlap")
    found = {}
    if overlaps:
        found["overlapping_text"] = "; ".join(overlaps[:4]) + (f" (+{len(overlaps) - 4} more)" if len(overlaps) > 4 else "")
    if not record["tight"]:                      # a tight bounding box always contains every text
        clipped = []
        for item in texts:
            x0, y0, x1, y1 = item["box"]
            width, height = item["canvas"]
            outside = x0 < -1 or y0 < -1 or x1 > width + 1 or y1 > height + 1
            if outside and not _entirely_outside(item):   # entirely outside is a missing element (wrong_chart)
                clipped.append(f"'{item['text']}' is cut off by the image edge")
        if clipped:
            found["clipped_text"] = "; ".join(clipped[:4])
    return found


def _close(a, b, tolerance=0.05) -> bool:
    return a is not None and b is not None and all(abs(x - y) <= tolerance for x, y in zip(a[:3], b[:3]))


def colour_findings(record: dict) -> dict:
    """Low-contrast text, invisible series and indistinguishable series, from recorded colours."""
    found = {}
    faint = [f"'{text}' has contrast {ratio:.1f}:1 against its background"
             for text, ratio in record.get("contrasts", []) if ratio < CONTRAST_MIN]
    invisible = []
    for ax in record["axes"]:
        if ax["colorbar"]:
            continue
        background = ax["facecolor"] if ax["facecolor"][3] > 0 else record["facecolor"]
        for s in ax["drawn"]:
            colours = [c for c in (s["color"], s["edge"]) if c is not None and c[3] > 0]
            if s["kind"] == "line" and s["linewidth"] == 0 and s["marker"] in ("None", "", " "):
                colours = []
            if not colours or all(contrast(c, background) < INVISIBLE_CONTRAST for c in colours):
                if not s["label"].startswith("_"):
                    invisible.append(f"the series '{s['label']}' is drawn in the background colour or is invisible")
        for i, a in enumerate(ax["series"]):
            for b in ax["series"][i + 1:]:
                if (a["label"] != b["label"] and a["kind"] == b["kind"] and _close(a["color"], b["color"], 0.03)
                        and a["linestyle"] == b["linestyle"] and a["marker"] == b["marker"]):
                    found.setdefault("indistinguishable_series", f"the series '{a['label']}' and '{b['label']}' "
                                                                 "share the same colour, line style and marker")
    if faint or invisible:
        found["low_contrast_or_invisible"] = "; ".join((faint + invisible)[:4])
    return found


# ------------------------------------------------------------------- requirement checks
# Each check fires only on a recognised, explicit phrasing in the request and only when the
# agent's code could be re-run; anything else is left to the model.

UNIFORM_CMAPS = {"viridis", "plasma", "inferno", "magma", "cividis"}
FORBIDDEN_CMAPS = {"jet", "rainbow", "hsv"}


def _norm(text: str) -> str:
    return " ".join(text.split()).strip().lower()


def requirement_findings(instructions: str, record: dict) -> dict:
    data_axes = [ax for ax in record["axes"] if not ax["colorbar"]]
    titles = {_norm(t) for ax in data_axes for t in ax["titles"] if t.strip()} | (
        {_norm(record["suptitle"])} if record["suptitle"].strip() else set())
    cmaps = {name.lower() for name in record["cmaps"]}
    sentences = re.split(r"(?<=[.;])\s+|\n", instructions)
    found = {}

    def flag(key, text):
        found[key] = f"{found[key]}; {text}" if key in found else text

    for wanted in re.findall(r"title[^`\n.]{0,40}?exactly `([^`]+)`", instructions, re.I):
        if _norm(wanted) not in titles:
            flag("title_text", f"the request asks for the exact title `{wanted}`; the figure's titles are {sorted(titles) or 'none'}")
    if not re.search(r"title[^`\n.]{0,40}?exactly `", instructions, re.I):
        each = re.search(r"\bgive each (?:panel|subplot) a title\b", instructions, re.I)
        if each and not all(any(t.strip() for t in ax["titles"]) for ax in data_axes):
            flag("title", "the request asks for a title on each panel, but at least one panel has none")
        elif re.search(r"\bgive the (?:chart|figure|plot|diagram) a title\b|\badd a title\b", instructions, re.I) and not titles:
            flag("title", "the request asks for a title, but the figure has none")
    for axis, wanted in re.findall(r"\b([xyz]) axis label to exactly `([^`]+)`", instructions, re.I):
        labels = {_norm(ax[f"{axis.lower()}label"]) for ax in data_axes}
        if _norm(wanted) not in labels:
            flag("axis_label_text", f"the request asks for the {axis} axis label `{wanted}`; the figure has {sorted(l for l in labels if l) or 'none'}")
    asked = set()
    for one, two in re.findall(r"\blabel (?:the )?([xyz])(?: and ([xyz]))? axis\b", instructions, re.I):
        asked |= {one.lower(), two.lower()} - {""}
    if re.search(r"\blabel both axes\b", instructions, re.I):
        asked |= {"x", "y"}
    for axis in sorted(asked):
        if not any(ax[f"{axis}label"].strip() for ax in data_axes):
            flag("axis_label", f"the request asks for a {axis} axis label, but no panel has one")
    if re.search(r"\b(?:add|show|include|place) (?:a|the) legend\b", instructions, re.I):
        if not (record["figure_legend"] or any(ax["legend"] for ax in data_axes)):
            flag("legend", "the request asks for a legend, but the figure has none")
    if re.search(r"\b(?:add|include) (?:an? )?colou?r ?bars?\b", instructions, re.I):
        if not any(ax["colorbar"] for ax in record["axes"]):
            flag("colorbar", "the request asks for a colorbar, but the figure has none")
    if re.search(r"do not use (?:the )?jet, rainbow,? or hsv", instructions, re.I):
        used = sorted(c for c in cmaps if c.removesuffix("_r") in FORBIDDEN_CMAPS)
        if used:
            flag("colormap", f"the request forbids jet/rainbow/hsv, but the figure uses {used}")
    for name in re.findall(r"\breversed (\w+) colou?r ?map\b", instructions, re.I):
        if f"{name.lower()}_r" not in cmaps:
            flag("colormap", f"the request asks for the reversed {name} colormap; the figure uses {sorted(cmaps) or 'none'}")
    for name in re.findall(r"\b(?:use|apply|using) the '?(\w+)'? colou?r ?map\b", instructions, re.I):
        if name.lower() in {c.lower() for c in matplotlib.colormaps} and name.lower() not in cmaps:
            flag("colormap", f"the request asks for the {name} colormap; the figure uses {sorted(cmaps) or 'none'}")
    if re.search(r"perceptually uniform colou?r ?map", instructions, re.I):
        if not any(c.removesuffix("_r") in UNIFORM_CMAPS for c in cmaps):
            flag("colormap", f"the request asks for a perceptually uniform colormap; the figure uses {sorted(cmaps) or 'none'}")
    for kind, axis in re.findall(r"\b(log|logit) scale on the ([xy]) axis\b", instructions, re.I):
        if not any(ax[f"{axis.lower()}scale"] == kind.lower() for ax in data_axes):
            flag("scale", f"the request asks for a {kind} {axis} axis, but no panel uses one")
    for axis, angle in re.findall(r"\brotate the ([xy]) tick labels by (-?\d+(?:\.\d+)?) degrees", instructions, re.I):
        angles = [rot for ax in data_axes for _, rot in ax[f"{axis.lower()}ticks"]]
        if angles and not any(min(abs(a - float(angle)) % 360, 360 - abs(a - float(angle)) % 360) <= 1 for a in angles):
            flag("tick_rotation", f"the request asks for {axis} tick labels rotated by {angle} degrees; they are at {sorted(set(angles))[:3]}")
    for sentence in sentences:
        if re.search(r"\bremove the\b.*\bticks\b", sentence, re.I):
            for axis in {a.lower() for pair in re.findall(r"\b([xy])(?: and ([xy]))? ticks\b", sentence, re.I) for a in pair if a}:
                if any(ax[f"{axis}ticks"] for ax in data_axes):
                    flag("ticks", f"the request asks to remove the {axis} ticks, but tick labels are drawn")
        if re.search(r"\bhide the\b.*\bspines?\b", sentence, re.I):
            for side in set(re.findall(r"\b(top|right|left|bottom)\b", sentence, re.I)):
                if any(ax["spines"].get(side.lower()) for ax in data_axes if ax["name"] == "rectilinear"):
                    flag("spines", f"the request asks to hide the {side} spine, but it is drawn")
    if re.search(r"\bturn on (?:the )?grid|\bgrid ?lines? (?:visible|turned on)\b|\bmake the grid ?lines visible\b|\bgridlines in both panels\b",
                 instructions, re.I):
        if not any(ax["grid"] for ax in data_axes) and any(ax["name"] in ("rectilinear", "polar") for ax in data_axes):
            flag("grid", "the request asks for gridlines, but none are drawn")
    if re.search(r"\b3d (?:plot|surface|scatter|bar|line|tricontour|voxel|axes|projection|graph|subplot)s?\b|\bmust be a 3d\b",
                 instructions, re.I) and not any(ax["name"] == "3d" for ax in data_axes):
        flag("projection", "the request asks for a 3D plot, but no panel is 3D")
    if re.search(r"\bpolar (?:projection|plot|axes|chart|coordinate)", instructions, re.I) and not any(
            ax["name"] == "polar" for ax in data_axes):
        flag("projection", "the request asks for a polar plot, but no panel is polar")
    for sentence in sentences:
        if re.search(r"colou?r", sentence, re.I):
            for name, colour in re.findall(r"(\w[\w ]*?) = '([a-z]+)'", sentence):
                try:
                    want = matplotlib.colors.to_rgba(colour)
                except ValueError:
                    continue
                matches = [s for ax in data_axes for s in ax["series"] if _norm(s["label"]) == _norm(name)]
                if matches and not any(_close(s["color"], want, 0.1) for s in matches):
                    flag("named_colour", f"the series '{name}' should be {colour}, but it is drawn in another colour")
    missing = [f"'{item['text']}' lies entirely outside the saved image"
               for item in _unique_texts(record) if not record["tight"] and _entirely_outside(item)]
    if missing:
        flag("text_outside_image", "; ".join(missing[:3]))
    return found


def ink_touches_edge(run: Run) -> bool:
    """Whether anything is drawn on the outermost pixels, i.e. whether text could be clipped."""
    pixels = np.asarray(Image.open(run.figure).convert("L")).astype(int)
    border = np.concatenate([pixels[0], pixels[-1], pixels[:, 0], pixels[:, -1]])
    background = np.median(border)
    return bool((np.abs(border - background) > 40).any())


def judge_readability(run: Run, facts: dict | None = None) -> list[Error]:
    """Whether the figure can be read."""
    keys = ["clipped_text", "overlapping_text", "covered_content", "low_contrast_or_invisible",
            "indistinguishable_series", "squeezed_layout"]
    prompt = """Judge only whether a reader can READ the attached figure. Look for each problem below.
For each, describe what you see, then give a verdict. Say "problem" only if you can name exactly which
text or series is affected and quote it (e.g. "the labels 'ST454' and 'ST325' are printed on top of each other").
- clipped_text: a title, label or annotation is partly cut off by the image edge.
- overlapping_text: tick labels, annotations or titles are drawn on top of each other, or markers cover their labels.
- covered_content: a legend, annotation or text box hides data, labels or other text.
- low_contrast_or_invisible: very faint text (e.g. light grey or white on white), or a series drawn in the
  background colour or otherwise invisible.
- indistinguishable_series: series that must be told apart share the same colour, line style and marker.
- squeezed_layout: data, boxes or panels crushed into an unreadable sliver, or panels overlapping each other."""
    found = ask(run, prompt, keys, ["problem", "fine"])
    if facts is not None:
        # Text geometry and colours are measured exactly; they replace the model's verdicts here.
        for key in ("overlapping_text", "clipped_text", "low_contrast_or_invisible", "indistinguishable_series"):
            found.pop(key, None)
        found |= text_findings(facts) | colour_findings(facts)
    elif "clipped_text" in found and not ink_touches_edge(run):
        del found["clipped_text"]   # nothing is drawn at the edge, so nothing can be cut off
    return _errors(ErrorFamily.HARD_TO_READ, found)


def validate(run: Run) -> list[Error]:
    """Everything wrong with one run."""
    if execution := judge_execution(run):
        return execution
    with ThreadPoolExecutor() as pool:
        data = pool.submit(judge_data, run)            # needs no facts; starts while the code re-runs
        facts = figure_facts(run)
        chart = pool.submit(judge_chart, run, facts)
        readability = pool.submit(judge_readability, run, facts)
        return data.result() + chart.result() + readability.result()
