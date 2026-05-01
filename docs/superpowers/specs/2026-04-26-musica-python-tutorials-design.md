# Standalone MUSICA-Python Tutorials — Design

Date: 2026-04-26
Status: Implemented

Target files (new):
- `scripts/musica_python/README.md`
- `scripts/musica_python/abba_box.py`
- `scripts/musica_python/lnox_box.py`
- `scripts/musica_python/chapman_nox_column.py`

Target files (modified):
- `docs/tutorial/02-supercell.md` — add §§2.10 and 2.11 at chapter end
- `docs/tutorial/03-chapman-nox.md` — add §3.10 at chapter end

## Goal

Add three standalone MUSICA-Python example scripts under
`scripts/musica_python/` that exercise the same MICM mechanism configs
(`abba.yaml`, `lnox_o3.yaml`, `chapman_nox.yaml`) and TUV-x photolysis
config (`tuvx_chapman_nox.json`) the CheMPAS-A tutorial chapters
already feature, *without* MPAS in the loop. Document each script
with a new tutorial section appended to the matching chapter.

The scripts are pedagogical: they let a reader exercise the chemistry
in isolation (e.g., to tweak initial conditions, temperatures, or
photolysis rates) without rebuilding or rerunning MPAS, and they
provide an independent numerical sanity check on the same Leighton
photostationary state Chapter 3 §3.7 motivates.

## Scope

**In scope:**

- Three Python scripts under `scripts/musica_python/`:
  - `abba_box.py` — single-cell box model, ~60 lines, no photolysis.
  - `lnox_box.py` — single-cell box model, ~80 lines, hardcoded
    `jNO2 = 0.01 s⁻¹` (matches CheMPAS-A's `config_lnox_j_no2`).
  - `chapman_nox_column.py` — column model, ~200–250 lines, TUV-x
    photolysis from our project's `tuvx_chapman_nox.json`.
- A one-page `README.md` in the new directory listing dependencies
  and pointing at the tutorial sections.
- Each script produces both a NetCDF (`<case>.nc`) and a PNG
  (`<case>.png`); plotting uses `scripts/style.py`
  (NCAR palette + project label/title rules).
- New tutorial sections at chapter ends:
  - `docs/tutorial/02-supercell.md` §2.10 (ABBA box) and §2.11
    (LNOx + O₃ box).
  - `docs/tutorial/03-chapman-nox.md` §3.10 (Chapman + NOx column).
- Each section carries a WIP admonition banner and a figure
  placeholder, consistent with the rest of the tutorial draft.

**Out of scope:**

- Modifying any existing tutorial section (2.1–2.9, 3.1–3.9). The
  new sections are appended; existing prose and section numbers do
  not change.
- Modifying any existing CheMPAS-A code, mechanism YAMLs, or TUV-x
  JSON. The scripts consume the existing configs read-only.
- Generating real PNG plots that replace the figure placeholders.
  The scripts produce real PNGs as a side effect, but wiring those
  PNGs into the rendered docs (in `docs/_static/tutorial/`) is a
  future polish pass.
- Installing `musica`, `ussa1976`, or `pvlib` into the `mpas` conda
  environment. The README documents the install command; whether
  to install now or defer is the user's call.
- Adding regression-suite or unit-test coverage for the scripts
  themselves. The scripts are pedagogical examples, not production
  code.
- Authoring new mechanism variants. Existing `abba.yaml`,
  `lnox_o3.yaml`, `chapman_nox.yaml`, `tuvx_chapman_nox.json` are
  used as-is.

## File Layout

New directory:

```
scripts/musica_python/
├── README.md                 # one-page overview + install pointer
├── abba_box.py               # ABBA box model
├── lnox_box.py               # LNOx + O₃ box model with hardcoded jNO₂
└── chapman_nox_column.py     # Chapman + NOx column with TUV-x
```

Each script:

- Imports `style` from the parent `scripts/` dir via a
  `sys.path.insert` shim and calls `style.setup()` at top of `main()`.
- References the project mechanism configs by absolute path
  (`REPO_ROOT / "micm_configs" / "<mechanism>.yaml"`), where
  `REPO_ROOT = Path(__file__).parent.parent.parent`.
- Writes a NetCDF (`<case>.nc`, xarray Dataset, scipy engine) and a
  PNG (`<case>.png`) into the same directory it lives in.
- Runs from any working directory (paths are resolved from
  `__file__`).

## Script 1 — `abba_box.py`

Single-grid-cell box model that loads `micm_configs/abba.yaml`,
seeds qAB = 1.0 mol m⁻³ with qA = qB = 0, runs for 2 hours at
60-second output cadence, and plots the three species vs time.

Key design points:

- **Conditions:** T = 273 K, P = 101325 Pa (standard reference).
- **Rates:** ABBA's two reactions are `type: USER_DEFINED`. The
  script supplies the per-reaction rate parameters via
  `state.get_user_defined_rate_parameters()` and
  `state.set_user_defined_rate_parameters(...)`. Concretely:
  `USER.forward_AB_to_A_B = 2.0e-3` (forward) and
  `USER.reverse_A_B_to_AB = 1.0e-3` (reverse), matching the
  scaling factors in `abba.yaml`.
- **Time loop:** outer loop steps `dt_out = 60 s` until `t = 7200 s`;
  inner `while elapsed < dt_out` loop calls `solver.solve(...)` and
  accumulates `result.stats.final_time` until the output interval
  is reached. Identical pattern to MUSICA's bundled `chapman.py`.
- **Plot:** single panel, A / B / AB vs time (in minutes), three
  curves with the project's NCAR palette colors. `style.setup()` at
  top of `main()`; explicit axis labels in the project's title-case
  / unit-bracket convention.

Expected output: AB decays slowly (~1% over 2 hours) toward
equilibrium with A and B; matches the "advection-dominated" framing
of §2.5.

## Script 2 — `lnox_box.py`

Single-grid-cell box model that loads `micm_configs/lnox_o3.yaml`,
seeds 1 ppb total NOx (50/50 NO/NO₂) and 50 ppb O₃, hardcodes
`jNO2 = 0.01 s⁻¹`, runs for 2 hours, plots NO / NO₂ / O₃ vs time.

Key design points:

- **Conditions:** T = 240 K, P = 5×10⁴ Pa (mid-troposphere ~5–8 km,
  representative of the layer where the CheMPAS-A LNOx source is
  active). Documented as constants at the top of the script.
- **Unit conversion:** a `ppb_to_mol_m3(ppb, T, P)` helper using
  `n = ppb × 10⁻⁹ × P / (R T)` (with `R = musica.constants.GAS_CONSTANT`).
- **Initial conditions:** total NOx = 1 ppb partitioned 50/50 into
  NO and NO₂ (so the reader sees PSS relaxation in the early time);
  O₃ = 50 ppb (matches `init_lnox_o3.py` background).
- **Photolysis rate:** the LNOx mechanism has one `type: PHOTOLYSIS`
  reaction (`name: jNO2`). The script sets
  `state.get_user_defined_rate_parameters()['PHOTO.jNO2'] = [0.01]`
  once and leaves it constant for the whole run.
- **Lightning source intentionally absent:** the docstring explicitly
  notes that the lightning-NOx source is a CheMPAS-A operator-split
  injection (in `mpas_lightning_nox.F`), not part of the MICM
  mechanism, and is therefore not part of the standalone box model.
- **Time loop:** same pattern as `abba_box.py`, 60-s output cadence,
  2 h total.
- **Plot:** 3 panels (NO, NO₂, O₃ vs time). Optional log time-axis
  on the first ~5 min so the PSS relaxation is visible — the
  implementer can decide between log-axis or a 2-row layout
  ("zoom on first 5 min" + "full 2 h").

Expected output: NO/NO₂ partitioning settles within ~1 minute to
the Leighton ratio; O₃ slowly titrates over the 2 h run while
keeping NO/NO₂ near steady state. A direct independent check of
the analytical PSS computation referenced in §2.7.

## Script 3 — `chapman_nox_column.py`

Vertical-column model that loads `micm_configs/chapman_nox.yaml` and
sources photolysis from our project's `micm_configs/tuvx_chapman_nox.json`,
runs a 12-hour diurnal cycle, and plots vertical profiles + time
series.

Key design points:

- **TUV-x loading (target / fallback):**
  - **Target:** `musica.tuvx.TUVx(config_path=str(TUVX_JSON))` (or
    whatever the public path-driven constructor is named in the
    current MUSICA-Python release). This is the cleanest path because
    `tuvx_chapman_nox.json` already names the four reactions
    (`jO2`, `jO3_O`, `jO3_O1D`, `jNO2`) the mechanism expects.
  - **Fallback:** if the API does not expose path-driven loading,
    use `musica.tuvx.vTS1.get_tuvx_calculator()` and supply a custom
    alias-mapping dict mapping TS1's reaction names to
    `PHOTO.jO2 / PHOTO.jO3_O / PHOTO.jO3_O1D / PHOTO.jNO2`. The
    fallback is documented inline (a short comment block plus a
    `try / except` around the constructor call) so the maintainer
    sees the intent.
- **Column grid:** independent of MPAS. The TUV-x JSON dictates the
  vertical grid (height edge / midpoint values come from
  `tuvx.get_grid_map()['height', 'km']`); the script does not
  attempt to coincide with the supercell mesh's stretched 60-level
  grid or with the upper-atmosphere extension's 5-km layers.
- **T / P column:** `ussa1976.compute(z=z_mids_km × 1000,
  variables=['t','p'])` (US Standard Atmosphere 1976) at column
  midpoints.
- **Initial profile:** mirrors `scripts/init_chapman.py`:
  - O₂ uniform 0.20946 VMR, converted to mol m⁻³ per cell.
  - O₃ from AFGL mid-latitude-summer profile, interpolated to
    `z_mids_km`. The script either re-imports the AFGL table from
    `init_chapman.py` (if its profile function is importable) or
    duplicates the table inline; copying is acceptable since the
    table is small and tracked in the script for reproducibility.
  - O and O¹D zero (chemistry spins them up within seconds).
  - Total NOx profile: 0.05 ppb tropospheric → ~10 ppb stratospheric
    peak at 25–35 km → drop near the column top, partitioned 30/70
    NO/NO₂.
- **Time loop:** 12-hour diurnal run starting at 06:00 local in the
  Norman, OK timezone (`America/Chicago`; matches the `lat = 35.86,
  lon = -97.93` in the supercell namelist), 30-minute output cadence.
  At each step: compute zenith via `pvlib.solarposition`, rerun
  TUV-x for new column photolysis rates, update the four
  `PHOTO.*` user-defined rate parameters (per cell), step the
  solver. Pattern parallels MUSICA's bundled `chapman.py`.
- **Output dataset (xarray):** dims `time × height`, variables for
  each chemistry species (O₂, O, O¹D, O₃, NO, NO₂) and each
  photolysis rate (jO₂, jO₃→O, jO₃→O¹D, jNO₂); coords `time`
  (datetime64) and `height` (km).
- **Plot:** 2×2 grid (uses `style.setup()`):
  - Top row: vertical profiles of O₃, NO, NO₂ at solar noon.
  - Bottom-left: simulated [NO]/[NO₂] vs height at solar noon, with
    the analytical Leighton ratio
    `jNO₂ / (k_{NO+O₃}(T) · [O₃])` overplotted (uses the same
    Arrhenius constants as §3.7: A = 1.7×10⁻¹², Ea/R = 1310 K).
  - Bottom-right: O₃ time series at three altitudes (10 km,
    30 km, 45 km).

Expected output: simulated NO/NO₂ ratio tracks the analytical
Leighton expression in the stratospheric column (the "where it
should hold" layer §3.7 calls out); O₃ peak settles near 25–30 km;
daytime PSS visibly breaks down at sunset in the time series.

## `scripts/musica_python/README.md`

One page (~40 lines):

- Header: "Standalone MUSICA-Python examples for the CheMPAS-A
  tutorial."
- Three one-line script descriptions and the chapter section each
  pairs with.
- Install pointer:
  `pip install musica ussa1976 pvlib` (or `pip install 'musica[tutorial]'`).
  Note that `numpy`, `xarray`, `matplotlib`, `netCDF4` are already
  in the `mpas` conda env.
- Note that each script can be invoked with the env's python:
  `~/miniconda3/envs/mpas/bin/python <script>.py`.
- Pointer to `scripts/style.py` (the script imports this via path
  shim) for the project plotting conventions.
- Pointer to the three tutorial sections that document each script.

## Tutorial section content

### §2.10 Standalone ABBA box model (`docs/tutorial/02-supercell.md`)

Appended at the end of Chapter 2 (after §2.9). WIP banner; brief
framing as the standalone counterpart of §2.5; pre-req note (`pip
install musica`); run command; figure placeholder (Figure 2.5);
"what to look for" closing.

### §2.11 Standalone LNOx + O₃ box model (`docs/tutorial/02-supercell.md`)

Appended after §2.10. WIP banner; framing as the standalone
counterpart of §2.6 *minus the lightning-NOx source* (which is
CheMPAS-A's operator-split injection, not in the MICM mechanism);
mention of the hardcoded `jNO2 = 0.01 s⁻¹` matching
`config_lnox_j_no2`; run command; figure placeholder (Figure 2.6);
"what to look for" closing pointing at PSS relaxation and slow
titration.

### §3.10 Standalone Chapman + NOx column model (`docs/tutorial/03-chapman-nox.md`)

Appended at the end of Chapter 3 (after §3.9). WIP banner; framing
as the standalone counterpart of the whole Chapter 3 (TUV-x
photolysis on a column independent of the MPAS mesh, same chemistry
configs); pre-req note (`pip install musica ussa1976 pvlib`); run
command; figure placeholder (Figure 3.5: vertical profiles +
Leighton overlay + O₃ time series); "what to look for" closing.

## Conventions

- **WIP banner** on every new tutorial section (per the project's
  draft-pass convention), MyST backtick-fenced
  ``` ```{admonition} Work in progress :class: warning ``` ```.
- **Figure placeholders** in the technical-description style:
  `**[Figure N.M: caption. To be added.]**`. Used for Figures 2.5,
  2.6, 3.5.
- **Inline-code form** for repo-root files (`BUILD.md`, `RUN.md`).
  **Markdown links** for in-tree docs.
- **Plot style:** every script imports `style` from the parent
  `scripts/` directory and calls `style.setup()` at the top of
  `main()` (NCAR palette + project label/title conventions).
- **Commit prefixes:**
  - Script + README commits: `feat(scripts):`
  - Tutorial section commits: `docs(tutorial):`

## Build verification

After all changes land:

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && make html
```

Acceptable: pre-existing warnings carry over from `develop`.
**Not acceptable:** any new warning whose path contains `tutorial/`.

For the scripts, smoke-testing the three with:

```bash
~/miniconda3/envs/mpas/bin/python scripts/musica_python/abba_box.py
~/miniconda3/envs/mpas/bin/python scripts/musica_python/lnox_box.py
~/miniconda3/envs/mpas/bin/python scripts/musica_python/chapman_nox_column.py
```

…each producing its `<case>.nc` and `<case>.png` is the runtime
acceptance check. **However:** smoke-testing depends on `musica`
(and `ussa1976`, `pvlib`) being installed in the env, which is out
of scope for this spec. The implementation plan should make the
runtime acceptance *optional* and gate it behind whether those
packages are available — the build-time acceptance (clean Sphinx
build, no new tutorial-pathed warnings) is the hard gate.

## Non-goals (explicit)

- This spec does not produce real PNG plots embedded in the rendered
  docs; placeholders only.
- This spec does not modify existing tutorial sections (2.1–2.9,
  3.1–3.9).
- This spec does not modify CheMPAS-A source, mechanism YAMLs, or
  TUV-x JSON.
- This spec does not change the `mpas` conda env or install MUSICA
  Python packages globally.
- This spec does not add regression coverage for the scripts.
