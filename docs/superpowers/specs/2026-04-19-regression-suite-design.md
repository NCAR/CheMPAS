# Numerical Regression Suite — Design

Date: 2026-04-19
Status: Deferred — design complete; implementation not shipped as of 2026-04-26
Target files (new):
- `scripts/regression.py`
- `scripts/regression_lib.py`
- `test_cases/chem_box/regression_reference.yaml`
- `test_cases/supercell/regression_reference.yaml`
- `docs/guides/REGRESSION.md`

## Goal

A numerical-regression suite for CheMPAS-A that runs short variants of
`chem_box` and `supercell` against a tracked YAML reference table and
reports PASS/FAIL per case. Each case is set up in an ephemeral run
directory under `/tmp/chempas_regression/<case>/`, with input data
(init NetCDF, graph partitions) symlinked from the canonical
`~/Data/CheMPAS/<case>/` location. The reference table records
min/max/mean of a small set of key fields at the final time step;
comparison uses relative tolerance `1e-3` by default. Reference values
are seeded and updated via an explicit `--bless` flag that rewrites the
YAML, leaving the user to commit the diff deliberately (snapshot-test
pattern). The suite is invoked via a single Python entry point
(`scripts/regression.py`) with `run`, `bless`, and `list` subcommands.

## Scope

**In scope:**
- Two cases: `chem_box`, `supercell`
- Min/max/mean of named fields at the final time step
- Relative tolerance `1e-3` default, with optional per-stat override
  (`numpy.isclose`-style: `|obs - exp| < max(atol, rtol * |exp|)`)
- Smoke check baked in: assert `Critical error messages = 0` and no
  `CRITICAL ERROR` string in `log.atmosphere.0000.out`
- Ephemeral run dirs at `/tmp/chempas_regression/<case>/`, rebuilt per
  invocation; large input data symlinked from `~/Data/CheMPAS/<case>/`
- `--bless` rewrites the per-case YAML; user commits the diff
- `--keep` leaves the run dir for debugging; default cleans up on
  success and keeps on failure

**Out of scope:**
- Bit-identity checks (cross-platform / cross-compiler tolerance
  defeats this; spec uses relative tolerance instead)
- `mountain_wave` and `jw_baroclinic_wave` cases (deferred)
- CI integration (manual invocation only; automation is a separate
  downstream decision)
- Behavioral / range-based assertions (numerical regression only)
- Reference NetCDF storage (spec uses summary statistics, not
  full-field reference files)
- Parallel execution of cases (sequential)

## Files Touched

### New files

- `scripts/regression.py` — single Python entry point (~200 lines).
  Subcommands: `run`, `bless`, `list`.
- `scripts/regression_lib.py` — small helper module with per-case
  orchestration (setup, mpiexec invocation, NetCDF read, comparison,
  YAML I/O). Keeps `regression.py` focused on argparse + dispatch.
- `test_cases/chem_box/regression_reference.yaml` — reference values
  for chem_box. Stub on first commit; populated by the first `bless`
  run.
- `test_cases/supercell/regression_reference.yaml` — reference values
  for supercell. Pre-populated with the values we have been spot-checking
  through the TUV-x work; first `bless` will refresh.
- `docs/guides/REGRESSION.md` — one-page usage doc: how to invoke,
  what to expect, how to bless, where reference values live.

### Not changed

- `test_cases/<case>/namelist.atmosphere`, `streams.atmosphere`,
  `stream_list.atmosphere.output` — stay as the iteration-friendly
  versions. The suite stages copies into the ephemeral run dir and
  applies `runtime_overrides` from the reference YAML at stage time.
- `~/Data/CheMPAS/<case>/` — read-only as far as the suite is
  concerned. Suite symlinks the init NetCDF and graph partition files
  in; never writes there.
- Existing scripts (`run_tuvx_phase_gate.sh`, `check_tuvx_phase.py`,
  `verify_ox_conservation.py`) — these remain for ad-hoc / phase-gate
  use; the suite is a separate, parallel mechanism.

### Ephemeral run dirs at runtime

```
/tmp/chempas_regression/
├── chem_box/
│   ├── atmosphere_model       (copy from $REPO/atmosphere_model)
│   ├── namelist.atmosphere    (copy from test_cases/, with run-duration override)
│   ├── streams.atmosphere     (copy from test_cases/)
│   ├── stream_list.atmosphere.output  (copy from test_cases/)
│   ├── <init NetCDF symlink → ~/Data/CheMPAS/chem_box/chem_box_init.nc>
│   ├── <grid NetCDF symlink → ~/Data/CheMPAS/chem_box/chem_box_grid.nc>
│   ├── <graph partition symlink → ~/Data/CheMPAS/chem_box/chem_box.graph.info.part.8>
│   ├── <MICM/TUV-x configs symlinked from $REPO/micm_configs/>
│   └── output.nc              (produced by the run)
└── supercell/                 (analogous)
```

Each invocation of `regression.py run` rebuilds these dirs from scratch
(`rm -rf` the per-case dir, then re-stage). User state in
`~/Data/CheMPAS/` is never touched.

## Reference YAML Format

Per-case YAML structure (`test_cases/<case>/regression_reference.yaml`):

```yaml
case: <case-name>

description: |
  Free-text description of the case.

runtime_overrides:
  # Applied to namelist.atmosphere when staging the run dir.
  config_run_duration: '00:03:00'

# Default tolerances applied to every field unless overridden per-stat.
# Comparison: |observed - expected| < max(atol, rtol * |expected|)
default_rtol: 1.0e-3
default_atol: 1.0e-30

# Fields to check at the final time step.
# Each entry lists the statistics to compare (min, max, mean — any subset).
fields:
  <field_name>:
    min: <value>      # scalar uses default_rtol/default_atol
    max: <value>
    mean: <value>
```

**Comparison rule** (mirrors `numpy.isclose`): a stat passes if
`|observed - expected| < max(atol, rtol * |expected|)`. The `atol`
term saves us from divide-by-zero when a reference value is exactly
`0.0` (e.g., `qNO min` at startup); default `1e-30` essentially says
"must be exactly zero unless `value` is nonzero."

**Per-stat tolerance override** (used when a field is dominated by
floating-point noise and needs a looser bound):

```yaml
fields:
  qNO2:
    max: {value: 2.985e-08, rtol: 5.0e-3, atol: 1.0e-12}
```

The `bless` flow always emits the compact scalar form; explicit
per-stat tolerance is something the user hand-adds when needed. Loose
tolerance defaults to never get blessed away accidentally.

## CLI Surface

Single entry point `scripts/regression.py` with three subcommands:

```
scripts/regression.py list
scripts/regression.py run [<case> ...] [--keep] [--np N]
scripts/regression.py bless <case> [--np N]
```

### `list`

Prints the available cases (those with a `regression_reference.yaml`)
one per line. Useful for shell completion / scripting.

### `run [<case> ...]`

Runs each case (or all if no case specified), staging, executing,
comparing, and reporting.

Flags:
- `--keep` — leave the ephemeral run dir in place after the run
  (default: clean up on success, keep on failure for debugging).
- `--np N` — number of MPI ranks (default: 8, matching project
  convention from CLAUDE.md and existing run dirs).

Exit code: `0` if all cases passed, `1` if any failed (suite-level),
`2` for setup/usage errors.

### `bless <case>`

Runs the case as `run` does, but instead of comparing, captures the
observed min/max/mean and rewrites the case's `regression_reference.yaml`
with the new values. Always operates on a single named case (no
implicit "bless all"). Output: a summary of values written and a
reminder to `git diff` and commit.

## Per-case Run Flow

Used by both `run` and `bless`:

1. **Verify prerequisites:** `$REPO/atmosphere_model` exists and is
   executable; required input data exists at the expected location.
2. **Stage ephemeral run dir** at `/tmp/chempas_regression/<case>/`:
   - `rm -rf` any prior contents
   - `cp` `atmosphere_model` from repo root
   - `cp` `namelist.atmosphere`, `streams.atmosphere`,
     `stream_list.atmosphere.output` from `test_cases/<case>/`
   - Apply `runtime_overrides` from the reference YAML to the staged
     `namelist.atmosphere` (in-place edit; e.g., set
     `config_run_duration`)
   - Symlink large input data files (init NetCDF, grid NetCDF, graph
     partitions) from `~/Data/CheMPAS/<case>/`
   - Symlink MICM YAML and TUV-x JSON configs from
     `$REPO/micm_configs/` — names read from the staged namelist's
     `config_micm_file` and `config_tuvx_config_file`
3. **Execute:** `mpiexec -n N ./atmosphere_model` from the staged dir,
   capturing stdout/stderr to `regression.log` in the same dir.
4. **Verify clean exit:** check the produced `log.atmosphere.0000.out`
   for `Critical error messages = 0` and the absence of the string
   `CRITICAL ERROR`. (This is the smoke-regression layer baked into
   the numerical-regression flow.)
5. **Read produced `output.nc`:** open with `netCDF4`, extract each
   `(field, stat)` pair from the YAML, compute the statistic at the
   final time step.
6. **Compare or bless:**
   - `run`: assert each stat against reference using the
     `numpy.isclose`-style rule. Print one line per stat:
     ```
     PASS j_jNO2.max   observed=1.704e-02  expected=1.704e-02  reldiff=0.0e+00
     ```
     Print case-level summary at end.
   - `bless`: load reference YAML, replace each `(field, stat)` value
     with the observed value (preserving the YAML's comments and
     `runtime_overrides` block via `ruamel.yaml` round-trip), write
     back. Do not commit.
7. **Cleanup:** `rm -rf` the ephemeral run dir on success unless
   `--keep` is set; always keep on failure for debugging.

**Suite-level orchestration** (`run` with multiple cases): runs each
case sequentially, prints a final summary table (per-case PASS/FAIL
count), exits with appropriate code.

## Per-case Specifics

### `supercell`

`test_cases/supercell/regression_reference.yaml`:

```yaml
case: supercell

description: |
  Idealized supercell on a 28080-cell, 40-level grid. dt=3s. Uses
  lnox_o3.yaml MICM mechanism + tuvx_no2.json TUV-x photolysis +
  lightning NOx source. Run for 3 simulated minutes (60 chemistry steps).

runtime_overrides:
  config_run_duration: '00:03:00'

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

Initial values are seeded directly from the values spot-checked through
the TUV-x work; first `bless` run will refresh them to current observed
values, and the diff will tell us if anything moved.

### `chem_box`

`test_cases/chem_box/regression_reference.yaml`:

```yaml
case: chem_box

description: |
  Pure box-chemistry test. No dynamics. Steps the chosen MICM mechanism
  with seeded initial concentrations for a short simulated duration.

runtime_overrides:
  config_run_duration: '00:00:30'

default_rtol: 1.0e-3
default_atol: 1.0e-30

fields:
  qNO:
    max: 0.0   # placeholder; bless will populate
  qNO2:
    max: 0.0
  qO3:
    min: 0.0
    max: 0.0
```

The chem_box reference is a stub on first commit; the `bless` flow
seeds it on first run. (For supercell we already have observed values
to seed manually so the suite is immediately useful even before
`bless`.)

### Per-case data location assumptions

| Case | Init data | Graph partitions | MICM/TUV-x configs |
|---|---|---|---|
| `supercell` | `~/Data/CheMPAS/supercell/supercell_init.nc`, `supercell_grid.nc` | `~/Data/CheMPAS/supercell/supercell.graph.info.part.8` | symlink from `$REPO/micm_configs/{lnox_o3.yaml,tuvx_no2.json}` |
| `chem_box` | `~/Data/CheMPAS/chem_box/chem_box_init.nc`, `chem_box_grid.nc` | `~/Data/CheMPAS/chem_box/chem_box.graph.info.part.8` | symlink from `$REPO/micm_configs/<mechanism>` per the namelist |

The suite reads the namelist's `config_micm_file` (and
`config_tuvx_config_file` if set) to determine which configs to
symlink — no per-case hardcoding in the script.

## Dependencies

Python packages required (all already available in the project's
`mpas` conda environment per CLAUDE.md):
- `netCDF4` — read `output.nc`
- `numpy` — `min`/`max`/`mean` and `isclose`-style comparison
- `pyyaml` or `ruamel.yaml` — read/write the reference YAML.
  Recommend `ruamel.yaml` for `bless` because it preserves comments
  and key ordering on round-trip; if not present in the conda env, the
  implementer should add it (cheap, conda-forge has it).

System dependencies:
- `mpiexec` (already required for project)
- `~/miniconda3/envs/mpas/bin/python` (already required for project)

## Documentation

`docs/guides/REGRESSION.md` — one page covering:
- What the suite is and what it catches
- How to invoke (`list`, `run`, `bless` examples)
- How to interpret PASS/FAIL output
- How to bless and commit a reference change
- Where reference YAMLs live and what they look like

Cross-link from `docs/README.md` index and from `RUN.md`.

## Validation

This spec is for new infrastructure (no existing behavior to preserve),
so "validation" means demonstrating the suite works end-to-end:

1. **`list`** prints exactly two lines: `chem_box`, `supercell`.
2. **`run supercell`** stages the run dir, runs the model, compares
   against the seeded reference values, prints per-stat PASS lines,
   case-level PASS, exits 0.
3. **`bless chem_box`** stages the run dir, runs the model, observes
   values, rewrites the chem_box YAML with non-zero values,
   exits 0.
4. **`run chem_box` after bless** passes against the freshly-blessed
   reference values.
5. **`run`** (no args) runs both cases sequentially and reports a
   summary; exits 0.
6. **Failure mode** (e.g., the user temporarily edits the supercell
   reference YAML to a value 10× off): `run supercell` prints a FAIL
   line for the perturbed stat, leaves the ephemeral run dir in place,
   and exits 1. Restoring the YAML and rerunning passes.

## Sequencing

This is independent of the in-flight TUV-x work and can land any time.
Recommended ordering:
1. Implementer creates the suite skeleton (Tasks 1–3 of the plan: lib,
   driver, docs).
2. Seed `supercell` reference YAML from observed values (Task 4) and
   verify `run supercell` PASSes.
3. Bless `chem_box` reference YAML from a real run (Task 5) and verify
   `run chem_box` PASSes.
4. Document and commit.

The suite becomes an artifact of the workflow: every PR that touches
chemistry code can be gated by `python scripts/regression.py run`.
