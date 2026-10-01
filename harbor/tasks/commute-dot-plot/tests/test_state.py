"""Verifier for commute-dot-plot.

Runs as root in the agent's container after the agent phase; /app is the agent's
finished workspace. The checks, cheapest first:

  S1  the delivered files: figure.png is a real, non-blank PNG, the input files
      are byte-for-byte unchanged, and plot.py was left behind.
  S2  plotted_values.json has exactly the promised keys and types, and every
      value matches the answer derived by hand (the literals in EXPECTED below,
      which were computed once, outside this file; nothing here re-implements
      the aggregation).
  S3  plot.py re-runs in a scrubbed copy of the workspace (inputs + plot.py only)
      and reproduces the same plotted_values.json and the same pixels, so the
      sidecar and figure really come from the script.

Not checked: anything only visible in the rendered image -- whether the order in
the sidecar is the order on screen, colours, label text, and legibility.
"""

import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

APP = Path("/app")
FIGURE = APP / "figure.png"
SIDECAR = APP / "plotted_values.json"
SCRIPT = APP / "plot.py"
REEXEC_TIMEOUT = 120
TOLERANCE = 0.01   # sidecar numbers must match to 0.01 in absolute terms

INPUTS = {
    "commute.csv": "37fac92c95ac0226ab4f3141dfdc6d9ca2ded0b74191d2e54e459dc4d411bbec"
}

EXPECTED = {
    "states": [
        "North Dakota",
        "Oregon",
        "Florida",
        "Maryland",
        "Kentucky",
        "Kansas",
        "Minnesota",
        "North Carolina",
        "Louisiana",
        "Indiana",
        "Missouri",
        "Arkansas",
        "Georgia",
        "Illinois",
        "California",
        "Nebraska",
        "Mississippi",
        "Nevada",
        "Alaska",
        "Maine",
        "New Mexico",
        "Oklahoma",
        "Ohio",
        "Rhode Island",
        "South Carolina",
        "Massachusetts",
        "Michigan",
        "Colorado",
        "Alabama",
        "New Jersey",
        "New Hampshire",
        "Pennsylvania",
        "Delaware",
        "Idaho",
        "Arizona",
        "Connecticut",
        "Hawaii",
        "New York",
        "Montana",
        "Iowa"
    ],
    "minutes": [
        37.3,
        36.7,
        36.2,
        35.1,
        34.7,
        33.7,
        33.0,
        32.3,
        32.0,
        31.2,
        30.9,
        29.4,
        29.2,
        28.6,
        28.5,
        28.3,
        27.9,
        27.7,
        27.3,
        26.4,
        25.1,
        25.0,
        24.8,
        24.5,
        23.9,
        23.5,
        23.0,
        22.7,
        22.6,
        22.5,
        22.1,
        21.9,
        21.5,
        21.0,
        20.5,
        20.1,
        19.3,
        17.1,
        16.5,
        16.0
    ],
    "median": 25.75
}


# ------------------------------------------------------------------------ S1
def test_s1_figure_exists():
    assert FIGURE.exists(), f"no figure at {FIGURE}; the task requires one"


def test_s1_figure_is_a_valid_nonblank_png():
    size = FIGURE.stat().st_size
    assert size > 1000, f"{FIGURE} is only {size} bytes, so it is not a real chart"
    with Image.open(FIGURE) as image:
        image.verify()
    with Image.open(FIGURE) as image:
        assert image.format == "PNG", f"{FIGURE} is a {image.format}, not a PNG"
        assert min(image.size) > 100, f"{FIGURE} is {image.size}, too small to be a chart"
        pixels = np.asarray(image.convert("RGB")).reshape(-1, 3)
    distinct = len(np.unique(pixels, axis=0))
    assert distinct > 4, f"{FIGURE} has {distinct} distinct colours: it is a blank canvas"


@pytest.mark.parametrize("name", sorted(INPUTS))
def test_s1_input_file_was_not_modified(name):
    digest = hashlib.sha256((APP / name).read_bytes()).hexdigest()
    assert digest == INPUTS[name], f"{name} was modified (sha256 {digest[:12]}...)"


def test_s1_plotting_script_was_left_behind():
    assert SCRIPT.exists(), "no /app/plot.py; the task requires the plotting script"
    assert "/app/" not in SCRIPT.read_text(), "plot.py uses an absolute /app path"


# ------------------------------------------------------------------------ S2
def _sidecar():
    assert SIDECAR.exists(), f"no {SIDECAR}; the task requires it"
    declared = json.loads(SIDECAR.read_text())
    assert isinstance(declared, dict), f"{SIDECAR} is not a JSON object"
    return declared


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _same(got, want):
    """True when got matches want: exact for strings/ints, within TOLERANCE for floats."""
    if isinstance(want, dict):
        return isinstance(got, dict) and sorted(got) == sorted(want) and all(
            _same(got[key], want[key]) for key in want)
    if isinstance(want, list):
        return isinstance(got, list) and len(got) == len(want) and all(
            _same(g, w) for g, w in zip(got, want))
    if isinstance(want, str):
        return got == want
    if isinstance(want, int) and not isinstance(want, bool) and not isinstance(want, float):
        return isinstance(got, int) and not isinstance(got, bool) and got == want
    return _is_number(got) and abs(got - want) <= TOLERANCE


def _types_match(got, want):
    if isinstance(want, dict):
        return isinstance(got, dict) and sorted(got) == sorted(want) and all(
            _types_match(got[key], want[key]) for key in want)
    if isinstance(want, list):
        return isinstance(got, list) and all(
            _types_match(item, want[0]) for item in got) if want else isinstance(got, list)
    if isinstance(want, str):
        return isinstance(got, str)
    return _is_number(got)


def test_s2_sidecar_has_the_promised_keys_and_types():
    declared = _sidecar()
    assert sorted(declared) == sorted(EXPECTED), (
        f"plotted_values.json has keys {sorted(declared)}, expected {sorted(EXPECTED)}")
    for key, want in EXPECTED.items():
        assert _types_match(declared[key], want), f"plotted_values.json[{key!r}] has the wrong type or shape"


@pytest.mark.parametrize("key", list(EXPECTED))
def test_s2_sidecar_value_matches_the_answer(key):
    declared = _sidecar()
    assert key in declared, f"plotted_values.json has no {key!r}"
    assert _same(declared[key], EXPECTED[key]), (
        f"plotted_values.json[{key!r}] is {declared[key]!r}; expected {EXPECTED[key]!r}")


# ------------------------------------------------------------------------ S3
@pytest.fixture(scope="module")
def rerun():
    """Re-run plot.py in a scratch copy holding only the inputs and the script."""
    workdir = Path(tempfile.mkdtemp(prefix="rerun-"))
    for name in INPUTS:
        shutil.copy(APP / name, workdir / name)
    shutil.copy(SCRIPT, workdir / "plot.py")
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    env["MPLBACKEND"] = "Agg"
    proc = subprocess.run(["/usr/local/bin/python3", "plot.py"], cwd=workdir, env=env,
                          capture_output=True, text=True, timeout=REEXEC_TIMEOUT)
    assert proc.returncode == 0, f"re-running plot.py failed:\n{proc.stderr[-2000:]}"
    return workdir


def test_s3_rerun_reproduces_the_sidecar(rerun):
    fresh = rerun / "plotted_values.json"
    assert fresh.exists(), "re-running plot.py did not write plotted_values.json"
    assert json.loads(fresh.read_text()) == _sidecar(), (
        "re-running plot.py wrote a different plotted_values.json than the one delivered")


def test_s3_rerun_reproduces_the_figure(rerun):
    fresh = rerun / "figure.png"
    assert fresh.exists(), "re-running plot.py did not write figure.png"
    with Image.open(fresh) as a, Image.open(FIGURE) as b:
        assert a.size == b.size, f"re-rendered figure is {a.size}, delivered is {b.size}"
        same = np.array_equal(np.asarray(a.convert("RGB")), np.asarray(b.convert("RGB")))
    assert same, "re-running plot.py renders a different image than the delivered figure.png"
