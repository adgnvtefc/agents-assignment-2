"""The validator you write. This is the only file you need to modify.

Each function evaluates a single run object and returns the errors it finds.
An empty list means that no errors were found. `validator/runner.py` defines
what a run object contains, and `ASSIGNMENT.md` defines the four error families you may report.
"""

import base64
import json
import re
from concurrent.futures import ThreadPoolExecutor

from validator.model import complete
from validator.prediction import Error, ErrorFamily
from validator.runner import Run

MAX_CHARS = 12000  # per text block (code, each input file) sent to the model


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


def ask(run: Run, prompt: str, keys: list[str]) -> list[str]:
    """Ask about each key with the figure attached; return the flagged observations."""
    finding = {"type": "object", "required": ["observation", "error"],
               "properties": {"observation": {"type": "string"}, "error": {"type": "boolean"}}}
    schema = {"type": "object", "required": keys, "properties": {key: finding for key in keys}}
    image = base64.b64encode(run.figure.read_bytes()).decode()
    response = complete(
        [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image}"}},
        ]}],
        max_tokens=2000,
        response_format={"type": "json_schema", "json_schema": {"name": "check", "schema": schema}},
    )
    answer = json.loads(response["choices"][0]["message"]["content"])
    return [f"{key}: {answer[key]['observation']}" for key in keys
            if answer[key]["error"] and answer[key]["observation"].strip()]


def _errors(family: ErrorFamily, found: list[str]) -> list[Error]:
    return [Error(family=family, evidence="; ".join(found))] if found else []


def judge_execution(run: Run) -> list[Error]:
    """Whether the run produced a figure to judge at all."""
    if run.figure is None or run.figure.stat().st_size == 0:
        return [Error(family=ErrorFamily.EXECUTION_FAILURE, evidence="the run saved no figure.png")]
    return []


def judge_chart(run: Run) -> list[Error]:
    keys = ["chart_type", "layout", "axes", "legend_colorbar_annotations", "style"]
    prompt = f"""Check whether the attached figure follows the requested chart DESIGN (not the data values).

Request:
{run.instructions}

Agent's final plotting code:
{_clip(final_code(run))}

For each aspect, note what the request explicitly asks for and what the figure does, then set "error":
- chart_type: chart type or projection (bar vs line, horizontal vs vertical, stacked, 3D, polar, twin axes, inset).
- layout: number and arrangement of subplots, shared axes.
- axes: axis labels, exact title/label text, axis limits, scale (log/linear), ticks, tick labels and rotation, spines, grid.
- legend_colorbar_annotations: legend, colour bar, requested annotations or value labels.
- style: colormap (including forbidden ones), line style, markers, named colours, fills.
Set "error" true only for an explicit requirement that is not met; trust the image over the code."""
    return _errors(ErrorFamily.WRONG_CHART, ask(run, prompt, keys))


def judge_data(run: Run) -> list[Error]:
    keys = ["wrong_values", "missing_data", "wrong_selection", "wrong_order"]
    inputs = "\n".join(f"--- {name} ---\n{_clip(path.read_text(errors='replace'))}"
                       for name, path in run.inputs.items())
    prompt = f"""Check whether the attached figure plots the requested DATA. Ignore styling, colours, labels and layout.

Request:
{run.instructions}

Input files:
{inputs or '(none)'}

Agent's final plotting code:
{_clip(final_code(run))}

For each failure mode, compare the request with what the code computes, then set "error":
- wrong_values: wrong formula, aggregation, scaling, normalisation or sampled range.
- missing_data: a requested series, category, panel or dimension is not plotted.
- wrong_selection: wrong column, subset or filter; unrequested series mixed in.
- wrong_order: order differs from the requested one.
Set "error" true only if a specific line of code contradicts a specific phrase in the request."""
    return _errors(ErrorFamily.WRONG_DATA, ask(run, prompt, keys))


def judge_data_and_chart(run: Run) -> list[Error]:
    """Whether the figure plots the requested data, built the requested way."""
    return judge_data(run) + judge_chart(run)


def judge_readability(run: Run) -> list[Error]:
    """Whether the figure can be read."""
    keys = ["clipped_text", "overlapping_text", "covered_content", "low_contrast_or_invisible",
            "indistinguishable_series", "squeezed_layout"]
    prompt = """Judge only whether a reader can READ the attached figure. For each problem type,
describe what you see, then set "error" true only if you can say exactly where it is:
- clipped_text: text partly cut off by the image edge.
- overlapping_text: labels or annotations drawn on top of each other.
- covered_content: a legend or text box hiding data or text.
- low_contrast_or_invisible: very faint text, or a series in the background colour.
- indistinguishable_series: series that must be told apart look the same.
- squeezed_layout: data or panels crushed into a sliver, or overlapping panels."""
    return _errors(ErrorFamily.HARD_TO_READ, ask(run, prompt, keys))


def validate(run: Run) -> list[Error]:
    """Everything wrong with one run."""
    if execution := judge_execution(run):
        return execution
    with ThreadPoolExecutor() as pool:
        results = pool.map(lambda judge: judge(run), [judge_data, judge_chart, judge_readability])
        return [error for errors in results for error in errors]
