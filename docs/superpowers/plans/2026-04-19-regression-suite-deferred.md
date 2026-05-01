# Numerical Regression Suite Implementation Plan

## Document Status

- `Historical Context:` Task-by-task plan drafted alongside
  `docs/superpowers/specs/2026-04-19-regression-suite-design.md`.
- `Current State:` **Deferred.** Design complete; implementation never
  shipped. As of 2026-04-26 there is no `scripts/regression.py`,
  `scripts/regression_lib.py`, or `test_cases/<case>/regression_reference.yaml`
  in the repo.
- `Use This As:` A starting point if/when the regression suite work is
  picked up. Re-validate paths and assumptions against the current
  codebase before executing — this plan was authored against the
  2026-04-19 state of the repo.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python-driven numerical-regression suite for two CheMPAS-A cases (`chem_box`, `supercell`) that runs each case in an ephemeral run directory, compares min/max/mean of named output fields against a tracked YAML reference table, and reports PASS/FAIL per case. A `bless` flag rewrites the YAML in place (snapshot-test pattern).

**Architecture:** A small helper module (`scripts/regression_lib.py`) handles case discovery, run-dir staging (copy executable + configs, apply namelist overrides, symlink input data + MICM/TUV-x configs), `mpiexec` invocation, NetCDF stat extraction, comparison, and YAML round-trip. A thin CLI driver (`scripts/regression.py`) provides `list`, `run`, and `bless` subcommands via `argparse`. Per-case reference YAMLs live next to existing namelists at `test_cases/<case>/regression_reference.yaml`.

**Tech Stack:** Python 3 (conda `mpas` env), `netCDF4`, `numpy`, `ruamel.yaml`. Standard library: `argparse`, `pathlib`, `subprocess`, `shutil`, `re`. Spec: `docs/superpowers/specs/2026-04-19-regression-suite-design.md`.

---

## File Structure

**New files:**

- `scripts/regression_lib.py` — helper module (~200 lines). One file, focused on the per-case orchestration mechanics and pure-function comparison logic.
- `scripts/regression.py` — CLI entry point (~80 lines). `argparse` setup + dispatch into the lib.
- `test_cases/chem_box/regression_reference.yaml` — chem_box reference (stub on initial commit; populated by `bless`).
- `test_cases/supercell/regression_reference.yaml` — supercell reference (pre-seeded with values from prior TUV-x validation).
- `docs/guides/REGRESSION.md` — one-page usage doc.

**No changes to:** existing scripts, namelists, MICM YAMLs, or the model source. The suite is pure additive infrastructure.

---

### Task 1: Create `scripts/regression_lib.py`

**Files:**
- Create: `scripts/regression_lib.py`

This module encapsulates everything the CLI does *except* argparse + dispatch. Splitting it out keeps the CLI thin and lets the helpers stay testable in isolation.

- [ ] **Step 1: Write the full module**

Create `scripts/regression_lib.py` with the following exact content:

```python
"""
Helpers for the CheMPAS-A numerical regression suite.

See docs/superpowers/specs/2026-04-19-regression-suite-design.md.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import netCDF4 as nc
import numpy as np
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES_DIR = REPO_ROOT / "test_cases"
RUN_DIR_BASE = Path("/tmp/chempas_regression")
DATA_DIR_BASE = Path.home() / "Data" / "CheMPAS"
MICM_CONFIGS_DIR = REPO_ROOT / "micm_configs"

_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.indent(mapping=2, sequence=4, offset=2)


# ---------- Case discovery and reference YAML I/O ----------

def list_cases() -> list[str]:
    """Return sorted case names that have a regression_reference.yaml."""
    cases = []
    for p in sorted(TEST_CASES_DIR.iterdir()):
        if p.is_dir() and (p / "regression_reference.yaml").exists():
            cases.append(p.name)
    return cases


def load_reference(case: str) -> dict:
    """Load the per-case reference YAML, preserving comments."""
    path = TEST_CASES_DIR / case / "regression_reference.yaml"
    with path.open() as f:
        return _yaml.load(f)


def save_reference(case: str, ref: dict) -> None:
    """Write the per-case reference YAML, preserving comments and key order."""
    path = TEST_CASES_DIR / case / "regression_reference.yaml"
    with path.open("w") as f:
        _yaml.dump(ref, f)


# ---------- Run-dir staging ----------

def apply_namelist_overrides(namelist_path: Path, overrides: dict) -> None:
    """In-place edit a namelist.atmosphere file: replace `key = ...` lines.

    Each override key must already exist in the namelist (we don't add new
    keys). Quoted strings get single-quoted; everything else is rendered
    via Python's str().
    """
    text = namelist_path.read_text()
    for key, value in overrides.items():
        if isinstance(value, str):
            new_line = f"    {key} = '{value}'"
        else:
            new_line = f"    {key} = {value}"
        pattern = re.compile(rf"^\s*{re.escape(key)}\s*=.*$", re.MULTILINE)
        if not pattern.search(text):
            raise RuntimeError(f"Namelist override key not found: {key}")
        text = pattern.sub(new_line, text)
    namelist_path.write_text(text)


def stage_run_dir(case: str, ref: dict) -> Path:
    """Build /tmp/chempas_regression/<case>/ from scratch.

    Copies executable + tracked test_cases configs, applies runtime_overrides,
    and symlinks input data + MICM/TUV-x configs.
    """
    run_dir = RUN_DIR_BASE / case
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)

    # Executable
    exe_src = REPO_ROOT / "atmosphere_model"
    if not exe_src.is_file():
        raise RuntimeError(f"atmosphere_model not built at {exe_src}")
    shutil.copy2(exe_src, run_dir / "atmosphere_model")

    # Tracked configs from test_cases/<case>/
    case_dir = TEST_CASES_DIR / case
    for fname in ["namelist.atmosphere", "streams.atmosphere",
                  "stream_list.atmosphere.output"]:
        src = case_dir / fname
        if src.exists():
            shutil.copy2(src, run_dir / fname)

    # Apply runtime overrides to the staged namelist
    overrides = ref.get("runtime_overrides") or {}
    if overrides:
        apply_namelist_overrides(run_dir / "namelist.atmosphere", overrides)

    # Symlink large input data from ~/Data/CheMPAS/<case>/
    data_src = DATA_DIR_BASE / case
    if not data_src.is_dir():
        raise RuntimeError(f"Input data dir missing: {data_src}")
    for entry in data_src.iterdir():
        if entry.is_file() and (
            entry.suffix == ".nc"
            or "graph.info" in entry.name
            or entry.name == "LANDUSE.TBL"
        ):
            (run_dir / entry.name).symlink_to(entry.resolve())

    # Symlink MICM/TUV-x configs named in the staged namelist
    namelist_text = (run_dir / "namelist.atmosphere").read_text()
    for cfg_key in ["config_micm_file", "config_tuvx_config_file"]:
        m = re.search(rf"^\s*{cfg_key}\s*=\s*'([^']*)'",
                      namelist_text, re.MULTILINE)
        if m and m.group(1):
            cfg_name = m.group(1)
            cfg_src = MICM_CONFIGS_DIR / cfg_name
            if cfg_src.exists():
                (run_dir / cfg_name).symlink_to(cfg_src.resolve())

    return run_dir


# ---------- Execute and validate the run ----------

def execute(run_dir: Path, np_ranks: int = 8) -> None:
    """Run `mpiexec -n N ./atmosphere_model` in the given dir."""
    log_path = run_dir / "regression.log"
    with log_path.open("w") as logf:
        proc = subprocess.run(
            ["mpiexec", "-n", str(np_ranks), "./atmosphere_model"],
            cwd=run_dir,
            stdout=logf,
            stderr=subprocess.STDOUT,
        )
    if proc.returncode != 0:
        raise RuntimeError(
            f"mpiexec exited {proc.returncode}; see {log_path}")


def verify_clean_log(run_dir: Path) -> None:
    """Assert log has no CRITICAL ERROR and 'Critical error messages = 0'."""
    log_path = run_dir / "log.atmosphere.0000.out"
    if not log_path.exists():
        raise RuntimeError(f"Model log missing: {log_path}")
    text = log_path.read_text()
    if "CRITICAL ERROR" in text:
        raise RuntimeError(f"CRITICAL ERROR present in {log_path}")
    m = re.search(r"Critical error messages =\s*(\d+)", text)
    if not m or int(m.group(1)) != 0:
        raise RuntimeError(f"Critical error count != 0 in {log_path}")


# ---------- Stat extraction and comparison ----------

def compute_stats(run_dir: Path, fields: dict) -> dict:
    """Open output.nc, compute requested stats per field at the final time.

    `fields` is the YAML's `fields:` mapping. Returns a parallel mapping
    of the same shape but with observed scalar values.
    """
    out_path = run_dir / "output.nc"
    if not out_path.exists():
        raise RuntimeError(f"output.nc missing: {out_path}")
    observed: dict = {}
    with nc.Dataset(out_path) as ds:
        for field, stat_spec in fields.items():
            if field not in ds.variables:
                raise RuntimeError(f"Field '{field}' not in output.nc")
            arr = ds.variables[field][-1]
            observed[field] = {}
            for stat in stat_spec.keys():
                if stat == "min":
                    observed[field]["min"] = float(np.min(arr))
                elif stat == "max":
                    observed[field]["max"] = float(np.max(arr))
                elif stat == "mean":
                    observed[field]["mean"] = float(np.mean(arr))
                else:
                    raise RuntimeError(f"Unknown stat: {field}.{stat}")
    return observed


def is_close(observed: float, expected: float,
             rtol: float, atol: float) -> bool:
    """numpy.isclose-style: |obs - exp| < max(atol, rtol * |exp|)."""
    return abs(observed - expected) < max(atol, rtol * abs(expected))


def _resolve_stat(stat_spec, default_rtol, default_atol):
    """Given a YAML stat spec (scalar or {value, rtol, atol}),
    return (value, rtol, atol)."""
    if isinstance(stat_spec, dict):
        return (stat_spec["value"],
                stat_spec.get("rtol", default_rtol),
                stat_spec.get("atol", default_atol))
    return (stat_spec, default_rtol, default_atol)


def compare(observed: dict, ref: dict) -> tuple[bool, list[str]]:
    """Compare observed stats to reference. Return (all_pass, report_lines)."""
    rtol_default = ref.get("default_rtol", 1.0e-3)
    atol_default = ref.get("default_atol", 1.0e-30)
    fields = ref.get("fields", {})
    all_pass = True
    lines: list[str] = []
    for field, stat_spec in fields.items():
        obs_for_field = observed.get(field, {})
        for stat, expected_spec in stat_spec.items():
            obs = obs_for_field.get(stat)
            value, rtol, atol = _resolve_stat(
                expected_spec, rtol_default, atol_default)
            ok = is_close(obs, value, rtol, atol)
            reldiff = abs(obs - value) / max(abs(value), 1e-30)
            tag = "PASS" if ok else "FAIL"
            lines.append(
                f"  {tag} {field}.{stat:5s}  "
                f"observed={obs:.6e}  expected={value:.6e}  "
                f"reldiff={reldiff:.2e}")
            if not ok:
                all_pass = False
    return all_pass, lines


def update_reference_with_observed(case: str, observed: dict) -> None:
    """Update the per-case YAML's `fields:` block with observed values.

    Preserves comments, key order, and any per-stat tolerance dicts
    ({value, rtol, atol}) — only `value` is updated in those.
    """
    ref = load_reference(case)
    fields = ref.get("fields", {})
    for field, obs_stats in observed.items():
        if field not in fields:
            fields[field] = {}
        for stat, value in obs_stats.items():
            existing = fields[field].get(stat)
            if isinstance(existing, dict):
                existing["value"] = value
            else:
                fields[field][stat] = value
    save_reference(case, ref)
```

- [ ] **Step 2: Verify module imports cleanly**

Run from repo root:
```bash
~/miniconda3/envs/mpas/bin/python -c "
import sys
sys.path.insert(0, 'scripts')
import regression_lib
print('list_cases:', regression_lib.list_cases())
print('REPO_ROOT:', regression_lib.REPO_ROOT)
"
```
Expected: prints `list_cases: []` (no YAMLs exist yet) and the absolute repo root path. No ImportError.

If the import fails on `from ruamel.yaml import YAML`, install via:
```bash
~/miniconda3/envs/mpas/bin/conda install -n mpas -c conda-forge -y ruamel.yaml
```

---

### Task 2: Create `scripts/regression.py` CLI

**Files:**
- Create: `scripts/regression.py`

- [ ] **Step 1: Write the CLI driver**

Create `scripts/regression.py` with the following exact content:

```python
#!/usr/bin/env python3
"""
CheMPAS-A numerical regression suite — CLI entry point.

See docs/superpowers/specs/2026-04-19-regression-suite-design.md.
Helpers live in scripts/regression_lib.py.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# Allow running as `scripts/regression.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import regression_lib as rl  # noqa: E402


def cmd_list(args: argparse.Namespace) -> int:
    for case in rl.list_cases():
        print(case)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    cases = args.cases or rl.list_cases()
    if not cases:
        print("No cases found. (Need test_cases/<case>/regression_reference.yaml)",
              file=sys.stderr)
        return 2

    suite_pass = True
    summary: list[tuple[str, bool]] = []
    for case in cases:
        print(f"=== {case} ===")
        ref = rl.load_reference(case)
        run_dir = rl.stage_run_dir(case, ref)
        try:
            rl.execute(run_dir, np_ranks=args.np)
            rl.verify_clean_log(run_dir)
            observed = rl.compute_stats(run_dir, ref.get("fields", {}))
            all_pass, lines = rl.compare(observed, ref)
            for line in lines:
                print(line)
            print(f"  CASE {'PASS' if all_pass else 'FAIL'}: {case}")
        except Exception as exc:
            print(f"  CASE FAIL ({type(exc).__name__}): {exc}")
            all_pass = False
        summary.append((case, all_pass))
        if not all_pass:
            suite_pass = False
        elif not args.keep:
            shutil.rmtree(run_dir, ignore_errors=True)
        if all_pass and args.keep:
            print(f"  (run dir kept at {run_dir})")
        if not all_pass:
            print(f"  (run dir kept at {run_dir} for debugging)")

    print()
    print("=== summary ===")
    for case, ok in summary:
        print(f"  {'PASS' if ok else 'FAIL'}  {case}")
    return 0 if suite_pass else 1


def cmd_bless(args: argparse.Namespace) -> int:
    case = args.case
    print(f"=== bless {case} ===")
    ref = rl.load_reference(case)
    run_dir = rl.stage_run_dir(case, ref)
    rl.execute(run_dir, np_ranks=args.np)
    rl.verify_clean_log(run_dir)
    observed = rl.compute_stats(run_dir, ref.get("fields", {}))
    rl.update_reference_with_observed(case, observed)
    yaml_path = (rl.TEST_CASES_DIR / case / "regression_reference.yaml")
    print(f"  wrote observed values to {yaml_path}")
    print(f"  review with: git diff {yaml_path}")
    print(f"  commit when satisfied.")
    if not args.keep:
        shutil.rmtree(run_dir, ignore_errors=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="regression.py",
        description="CheMPAS-A numerical regression suite.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List available regression cases.")

    p_run = sub.add_parser("run", help="Run one or more cases and compare.")
    p_run.add_argument("cases", nargs="*",
                       help="Case names (default: all).")
    p_run.add_argument("--keep", action="store_true",
                       help="Keep ephemeral run dirs after PASS.")
    p_run.add_argument("--np", type=int, default=8,
                       help="MPI ranks (default: 8).")

    p_bless = sub.add_parser(
        "bless", help="Run a single case and rewrite its reference YAML.")
    p_bless.add_argument("case", help="Case name to bless.")
    p_bless.add_argument("--keep", action="store_true",
                         help="Keep ephemeral run dir.")
    p_bless.add_argument("--np", type=int, default=8,
                         help="MPI ranks (default: 8).")

    args = parser.parse_args(argv)
    if args.cmd == "list":
        return cmd_list(args)
    if args.cmd == "run":
        return cmd_run(args)
    if args.cmd == "bless":
        return cmd_bless(args)
    parser.error(f"unknown subcommand: {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Make the script executable and verify the CLI parses**

Run:
```bash
chmod +x scripts/regression.py
~/miniconda3/envs/mpas/bin/python scripts/regression.py --help
~/miniconda3/envs/mpas/bin/python scripts/regression.py list
```

Expected:
- `--help` prints the parser usage with `list`, `run`, `bless` subcommands.
- `list` prints nothing (no YAMLs exist yet); exits 0.

---

### Task 3: Create `test_cases/supercell/regression_reference.yaml` (seeded)

**Files:**
- Create: `test_cases/supercell/regression_reference.yaml`

- [ ] **Step 1: Write the seeded YAML**

Create `test_cases/supercell/regression_reference.yaml` with the following exact content:

```yaml
# Regression reference values for the supercell case.
#
# Updated via:    scripts/regression.py bless supercell
# Compared via:   scripts/regression.py run supercell

case: supercell

description: |
  Idealized supercell on a 28080-cell, 40-level grid. dt=3s. Uses
  lnox_o3.yaml MICM mechanism + tuvx_no2.json TUV-x photolysis +
  lightning NOx source. Run for 3 simulated minutes (60 chemistry
  steps) for the regression check.

runtime_overrides:
  config_run_duration: '00:03:00'

# Comparison: |observed - expected| < max(atol, rtol * |expected|)
default_rtol: 1.0e-3
default_atol: 1.0e-30

fields:
  j_jNO2:
    min: 5.671e-05
    max: 1.704e-02
  qNO:
    max: 1.115e-07
  qNO2:
    max: 2.985e-08
  qO3:
    min: 5.162e-08
    max: 8.276e-08
```

- [ ] **Step 2: Verify the suite picks it up**

Run:
```bash
~/miniconda3/envs/mpas/bin/python scripts/regression.py list
```
Expected output: `supercell` (one line).

---

### Task 4: Create `test_cases/chem_box/regression_reference.yaml` (stub)

**Files:**
- Create: `test_cases/chem_box/regression_reference.yaml`

- [ ] **Step 1: Write the stub YAML**

Create `test_cases/chem_box/regression_reference.yaml` with the following exact content:

```yaml
# Regression reference values for the chem_box case.
#
# Updated via:    scripts/regression.py bless chem_box
# Compared via:   scripts/regression.py run chem_box

case: chem_box

description: |
  Pure box-chemistry test. No dynamics. Steps the chosen MICM mechanism
  (read from namelist config_micm_file) with seeded initial concentrations
  for a short simulated duration. Reference values are populated by the
  first `bless` run; chem_box is highly sensitive to the chosen mechanism,
  so initial values are zero placeholders.

runtime_overrides:
  config_run_duration: '00:00:30'

default_rtol: 1.0e-3
default_atol: 1.0e-30

fields:
  qNO:
    max: 0.0
  qNO2:
    max: 0.0
  qO3:
    min: 0.0
    max: 0.0
```

- [ ] **Step 2: Verify both cases listed**

Run:
```bash
~/miniconda3/envs/mpas/bin/python scripts/regression.py list
```
Expected output:
```
chem_box
supercell
```

---

### Task 5: Smoke validation — `list` and `run supercell`

**Files:** none modified. Validates that the supercell run staging, execution, and comparison work end-to-end against the seeded reference values.

- [ ] **Step 1: Verify build state**

Run: `ls -l atmosphere_model && stat -f "%Sm" atmosphere_model 2>/dev/null || stat -c "%y" atmosphere_model`
Expected: `atmosphere_model` exists. If not, build per `BUILD.md`.

- [ ] **Step 2: Verify input data exists**

Run:
```bash
ls -l ~/Data/CheMPAS/supercell/supercell_init.nc \
      ~/Data/CheMPAS/supercell/supercell.graph.info.part.8 2>/dev/null
```
Expected: both files exist.

- [ ] **Step 3: Run the suite for supercell only**

Run:
```bash
~/miniconda3/envs/mpas/bin/python scripts/regression.py run supercell
```
Expected output (line by line):
- A header `=== supercell ===`
- One `PASS j_jNO2.min ...`, `PASS j_jNO2.max ...`, `PASS qNO.max ...`, `PASS qNO2.max ...`, `PASS qO3.min ...`, `PASS qO3.max ...` line each.
- `CASE PASS: supercell`
- A `=== summary ===` block with `PASS  supercell`.
- Exit code `0` (`echo $?` immediately after).

If any stat shows FAIL with a small (<1e-2) reldiff, check for floating-point drift since the seeded values were captured. Re-bless and inspect the diff:
```bash
~/miniconda3/envs/mpas/bin/python scripts/regression.py bless supercell
git diff test_cases/supercell/regression_reference.yaml
```

---

### Task 6: Bless and validate `chem_box`

**Files:** modifies `test_cases/chem_box/regression_reference.yaml` (via `bless`).

- [ ] **Step 1: Verify chem_box input data exists**

Run:
```bash
ls -l ~/Data/CheMPAS/chem_box/ 2>/dev/null | head -20
```
Expected: directory exists with `chem_box_init.nc`, `chem_box_grid.nc`, and a `chem_box.graph.info.part.8` file.

- [ ] **Step 2: Bless chem_box**

Run:
```bash
~/miniconda3/envs/mpas/bin/python scripts/regression.py bless chem_box
```
Expected:
- `=== bless chem_box ===` header
- The model runs for 30 simulated seconds and exits cleanly
- `wrote observed values to test_cases/chem_box/regression_reference.yaml`
- `review with: git diff ...` and commit reminder
- Exit code `0`

- [ ] **Step 3: Inspect the bless diff**

Run:
```bash
git diff test_cases/chem_box/regression_reference.yaml
```
Expected: the four placeholder `0.0` values in the `fields:` block are now non-zero observed values. The comments and `runtime_overrides` block are unchanged.

If the diff shows changes only in the `fields:` block (no spurious whitespace / comment damage), the round-trip is working correctly.

- [ ] **Step 4: Run chem_box and verify it now PASSes against the freshly-blessed reference**

Run:
```bash
~/miniconda3/envs/mpas/bin/python scripts/regression.py run chem_box
```
Expected: every stat reports `PASS`; case-level `CASE PASS: chem_box`; exit 0.

(This is a tautology by construction — we just blessed, so the next run must match. But verifying it explicitly catches any bug in the bless/load round-trip.)

---

### Task 7: End-to-end suite invocation (`run` with no args)

**Files:** none.

- [ ] **Step 1: Run both cases**

Run:
```bash
~/miniconda3/envs/mpas/bin/python scripts/regression.py run
```
Expected: both cases run sequentially, each prints PASS lines, summary prints `PASS  chem_box` then `PASS  supercell` (alphabetical), exit 0.

- [ ] **Step 2: Sanity-check failure mode**

Temporarily perturb the supercell reference to test that FAIL works:

```bash
~/miniconda3/envs/mpas/bin/python -c "
import sys; sys.path.insert(0, 'scripts')
import regression_lib as rl
ref = rl.load_reference('supercell')
ref['fields']['qO3']['max'] = 1.0   # 10^7 too high
rl.save_reference('supercell', ref)
"
~/miniconda3/envs/mpas/bin/python scripts/regression.py run supercell
echo "exit=$?"
```
Expected: `qO3.max` line shows `FAIL`, case-level `CASE FAIL: supercell`, exit code `1`. The run dir is left in place (printed `(run dir kept at /tmp/chempas_regression/supercell for debugging)`).

- [ ] **Step 3: Restore the reference**

Run:
```bash
git checkout test_cases/supercell/regression_reference.yaml
~/miniconda3/envs/mpas/bin/python scripts/regression.py run supercell
echo "exit=$?"
```
Expected: PASS, exit `0`.

---

### Task 8: Create `docs/guides/REGRESSION.md`

**Files:**
- Create: `docs/guides/REGRESSION.md`

- [ ] **Step 1: Write the doc**

Create `docs/guides/REGRESSION.md` with the following exact content:

````markdown
# Regression Suite

A small numerical-regression suite that runs short variants of two test
cases (`chem_box`, `supercell`) and compares min/max/mean of named output
fields against tracked reference values. See the design spec at
[`docs/superpowers/specs/2026-04-19-regression-suite-design.md`](../superpowers/specs/2026-04-19-regression-suite-design.md).

## Prerequisites

- Built `atmosphere_model` at the repo root (per [`BUILD.md`](../../BUILD.md)).
- Input data (init NetCDF, graph partitions) at `~/Data/CheMPAS/<case>/`
  for each case in the suite.
- The `mpas` conda environment with `netCDF4`, `numpy`, and `ruamel.yaml`.

## Usage

List available cases:
```bash
~/miniconda3/envs/mpas/bin/python scripts/regression.py list
```

Run all cases (PASS/FAIL summary, exit 0/1):
```bash
~/miniconda3/envs/mpas/bin/python scripts/regression.py run
```

Run one case:
```bash
~/miniconda3/envs/mpas/bin/python scripts/regression.py run supercell
```

Update the reference values (snapshot-test pattern):
```bash
~/miniconda3/envs/mpas/bin/python scripts/regression.py bless supercell
git diff test_cases/supercell/regression_reference.yaml
git add ... && git commit -m "..."   # commit if the diff is intentional
```

Keep the ephemeral run dir for debugging:
```bash
~/miniconda3/envs/mpas/bin/python scripts/regression.py run --keep supercell
ls /tmp/chempas_regression/supercell/
```

## What the suite checks

Per case, at the final time step of a short simulated run:

- Smoke: model log has zero `Critical error messages` and no `CRITICAL ERROR` string.
- Numerical: min/max/mean of fields named in
  `test_cases/<case>/regression_reference.yaml` match recorded values
  within `numpy.isclose`-style tolerance
  (`|obs - exp| < max(atol, rtol * |exp|)`, default `rtol = 1e-3`,
  `atol = 1e-30`).

## What the suite does NOT check

- Bit-identity (cross-compiler tolerance defeats this; use
  `rtol = 1e-3` instead).
- Long-time integrations (each case runs for seconds to minutes of
  simulated time).
- Cases other than `chem_box` and `supercell` (intentionally limited to
  the two cases under active iteration).

## Reference YAML format

```yaml
case: <case-name>

runtime_overrides:
  # Applied to namelist.atmosphere when staging the run dir.
  config_run_duration: '00:03:00'

default_rtol: 1.0e-3
default_atol: 1.0e-30

fields:
  <field_name>:
    min: <value>      # scalar uses default_rtol/default_atol
    max: <value>
    mean: <value>
    # or per-stat override:
    # max: {value: 1.5e-2, rtol: 5.0e-3, atol: 1.0e-12}
```

## Where things live

| Item | Path |
|------|------|
| CLI driver | `scripts/regression.py` |
| Helper module | `scripts/regression_lib.py` |
| Per-case reference | `test_cases/<case>/regression_reference.yaml` |
| Ephemeral run dirs | `/tmp/chempas_regression/<case>/` |
| Input data | `~/Data/CheMPAS/<case>/` (read-only; symlinked into run dirs) |
````

- [ ] **Step 2: Verify cross-link from docs index**

Open `docs/README.md` and add the following line under the **Subdirectories** section, immediately after the `guides/TUVX_INTEGRATION.md` line:

```
- [guides/REGRESSION.md](guides/REGRESSION.md) - Numerical regression suite
```

Verify:
```bash
grep -n 'REGRESSION.md' docs/README.md
```
Expected: 1 match.

---

### Task 9: Commit everything

**Files:** stages all of the new files from Tasks 1–4 and 8.

- [ ] **Step 1: Inspect what will be committed**

Run:
```bash
git status
```
Expected new files:
- `scripts/regression.py`
- `scripts/regression_lib.py`
- `test_cases/chem_box/regression_reference.yaml`
- `test_cases/supercell/regression_reference.yaml`
- `docs/guides/REGRESSION.md`
- (modified) `docs/README.md` (one new line in the Subdirectories section)

- [ ] **Step 2: Stage and commit**

Run:
```bash
git add \
  scripts/regression.py \
  scripts/regression_lib.py \
  test_cases/chem_box/regression_reference.yaml \
  test_cases/supercell/regression_reference.yaml \
  docs/guides/REGRESSION.md \
  docs/README.md
git commit -m "$(cat <<'EOF'
feat(test): add numerical regression suite for chem_box and supercell

Adds scripts/regression.py (CLI) + scripts/regression_lib.py (helpers)
to drive a per-case numerical regression check. For each case, the
suite stages an ephemeral run dir under /tmp/chempas_regression/<case>/
(copying the executable + tracked test_cases/ configs, applying
runtime_overrides from the per-case reference YAML, and symlinking
input data and MICM/TUV-x configs), runs the model with mpiexec,
verifies a clean log, and compares min/max/mean of named output
fields against the tracked reference. Comparison uses
numpy.isclose-style tolerance (default rtol=1e-3, atol=1e-30).

Three subcommands:
- list  — print available cases
- run   — run cases (default: all) and report PASS/FAIL
- bless — rewrite a case's reference YAML from observed values
          (snapshot-test pattern; user commits the diff)

Per-case reference YAMLs live alongside the case configs at
test_cases/<case>/regression_reference.yaml. The supercell reference
is pre-seeded with values spot-checked through the prior TUV-x work;
the chem_box reference is a stub that the first `bless` populates.

Spec: docs/superpowers/specs/2026-04-19-regression-suite-design.md
Plan: docs/superpowers/plans/2026-04-19-regression-suite-deferred.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 3: Verify the commit**

Run: `git log -1 --stat`
Expected: commit subject `feat(test): add numerical regression suite for chem_box and supercell`; six files in the stat line.

---

## Self-Review Notes

**Spec coverage:**

- Spec § *Goal*, *Scope*, *Files Touched* → covered by Tasks 1–4, 8.
- Spec § *Reference YAML Format* → Task 1 (helpers handle scalar + dict stat-spec form), Tasks 3, 4 (concrete YAML examples).
- Spec § *CLI Surface* (list/run/bless) → Task 2 (CLI driver implements all three subcommands and flags).
- Spec § *Per-case Run Flow* (steps 1–7) → Task 1 implements each helper (`stage_run_dir`, `apply_namelist_overrides`, `execute`, `verify_clean_log`, `compute_stats`, `compare`, `update_reference_with_observed`); Task 2 wires them into `cmd_run` and `cmd_bless` in the documented order.
- Spec § *Per-case Specifics* → Tasks 3 (supercell, seeded), 4 (chem_box, stub), 6 (bless populates chem_box).
- Spec § *Dependencies* → Task 1 Step 2 mentions `ruamel.yaml` install fallback.
- Spec § *Documentation* → Task 8 (REGRESSION.md, cross-link).
- Spec § *Validation* (six items) → Task 5 (run supercell PASS), Task 6 (bless chem_box + run chem_box PASS), Task 7 (run with no args + perturb-and-restore failure mode).
- Spec § *Sequencing* — implementer follows Tasks 1→9 in order.

**Placeholder scan:** No TBD/TODO/vague-instruction patterns. Every step shows the exact code or command. The chem_box YAML's `0.0` placeholders are documented as intentional stubs (the spec calls this out) and Task 6 explicitly populates them.

**Type / name consistency:** Function names — `list_cases`, `load_reference`, `save_reference`, `apply_namelist_overrides`, `stage_run_dir`, `execute`, `verify_clean_log`, `compute_stats`, `is_close`, `_resolve_stat`, `compare`, `update_reference_with_observed`. The CLI dispatch (`cmd_list`, `cmd_run`, `cmd_bless`) calls the same names exactly. Module-level constants (`REPO_ROOT`, `TEST_CASES_DIR`, `RUN_DIR_BASE`, `DATA_DIR_BASE`, `MICM_CONFIGS_DIR`) are referenced consistently.

**Validation note:** The plan assumes `~/Data/CheMPAS/supercell/` and `~/Data/CheMPAS/chem_box/` are populated with the standard input files. Both currently are (verified during the prior TUV-x work). If either is missing on the executor's machine, Task 5 / Task 6 will fail with a clear `Input data dir missing` error from `stage_run_dir`.
