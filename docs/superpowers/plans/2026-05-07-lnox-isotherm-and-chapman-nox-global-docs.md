# LNOx isotherm-mode and Chapman + NOx global docs — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Document two recently landed CheMPAS-A capabilities — the isotherm-mode LNOx gating branch, and the global `chapman_nox_global` test case — so they are discoverable and runnable from the existing docs.

**Architecture:** Docs-only. Add one new scheme guide (`docs/chempas/guides/LNOX_INTEGRATION.md`), one new tutorial chapter (`docs/tutorial/04-chapman-nox-global.md`), restructure Tutorial Ch. 2 §2.6 into parallel altitude/isotherm walkthroughs with a figure renumber, update three small index/table files (`docs/tutorial/index.rst`, `test_cases/README.md`, `CLAUDE.md`), update Tutorial Ch. 3's next-steps link, and trim `LNOx.md` to a pointer.

**Tech Stack:** MyST markdown + Sphinx (Read the Docs theme), GitHub Flavored Markdown, no source-code or registry changes.

**Spec:** `docs/superpowers/specs/2026-05-07-lnox-isotherm-and-chapman-nox-global-docs-design.md`

---

## File structure

| File | Action | Responsibility |
|---|---|---|
| `docs/chempas/guides/LNOX_INTEGRATION.md` | create | Scheme guide: both gating modes, namelist options, code paths, calibration |
| `docs/tutorial/04-chapman-nox-global.md` | create | Tutorial Ch. 4: global Chapman + NOx on `x1.40962` mesh |
| `docs/tutorial/02-supercell.md` | modify | §2.6 split into 2.6.1/2.6.2/2.6.3; figure renumber 2.4–2.6 → 2.6–2.8; new Figs 2.4 (isotherm), 2.5 (alt-vs-iso) |
| `docs/tutorial/03-chapman-nox.md` | modify | §3.9 next-steps link updated to point to Ch. 4 |
| `docs/tutorial/index.rst` | modify | Add `04-chapman-nox-global` to toctree |
| `test_cases/README.md` | modify | Add `chapman_nox_global/` row + per-case sequence note |
| `CLAUDE.md` | modify | Add `chapman_nox_global` row to *Test Run Directory* table |
| `LNOx.md` | modify | Trim to a one-paragraph pointer to the new guide (preserve DC3 quote) |

No source code, Registry.xml, MICM/TUV-x configs, or plotting scripts are touched.

---

## Conventions to follow throughout

- **WIP banners:** Every visible subsection in the new and restructured tutorial chapters carries a backtick-fenced MyST admonition:

  ````
  ```{admonition} Work in progress
  :class: warning

  This chapter is being actively written. Commands and expected output
  are provisional; figure slots are left without rendered PNGs until the
  corresponding model runs and plots are archived.
  ```
  ````

  And per-section:

  ````
  ```{admonition} Draft - revisions in progress
  :class: warning

  This section is being revised.
  ```
  ````

  Match Chapter 2 / Chapter 3's existing wording exactly.

- **Figure placeholders:** `**[Figure X.N: caption. To be added.]**` (bolded, period at end). Match existing convention.

- **Inline-code form** for repo-root files: `` `BUILD.md` ``, `` `RUN.md` ``, `` `LNOx.md` ``.

- **Markdown-link form** for in-tree docs:
  `[docs/chempas/guides/LNOX_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/guides/LNOX_INTEGRATION.md)` — i.e., absolute GitHub URLs to `develop`, matching what Ch. 2 / Ch. 3 already do for `MUSICA_INTEGRATION.md` and `TUVX_INTEGRATION.md`.

- **Math blocks** use `$ ... $` and `$$ ... $$` (MyST inline / display math). Chapter 3 §3.7 has examples.

- **Code blocks** use triple backticks with a language tag (`bash`, `fortran`, `python`).

- **Quoted CheMPAS-A paths** never include the repository working-tree path — use `~/EarthSystem/CheMPAS-A/...` only for run-time invocations and `src/...` / `docs/...` for in-repo references.

---

## Task 1: Create the LNOx integration guide

**Files:**
- Create: `docs/chempas/guides/LNOX_INTEGRATION.md`

This is the first deliverable so later tasks can link to it.

- [ ] **Step 1.1: Create `docs/chempas/guides/LNOX_INTEGRATION.md` with the full content below**

````markdown
# LNOx Integration Summary

This note describes CheMPAS-A's lightning-NOx (LNOx) source scheme as
it currently stands in `src/core_atmosphere/chemistry/mpas_lightning_nox.F`.
It supersedes the historical `LNOx.md` note at the repository root,
which is preserved as a stub pointing here.

For the implementation history of the most recent change (the
isotherm-mode gating branch) see
[docs/superpowers/specs/2026-05-06-lnox-isotherm-source-design.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/superpowers/specs/2026-05-06-lnox-isotherm-source-design.md).

## Scope

The LNOx scheme is an operator-split source term that injects NO into
prognostic tracer cells in active convection, ahead of the MICM solver
call within each chemistry timestep. It is independent of the MICM
mechanism YAML and of the TUV-x photolysis configuration: any MICM
mechanism that carries a `qNO` species will receive the source.

Two gating modes are available:

- **Altitude mode** (default, inherited from DAVINCI-MPAS) — emission
  in a fixed altitude window, with rate scaled linearly by updraft
  excess.
- **Isotherm mode** (new, faithful to the LNOx.md DC3 framing) —
  emission in a temperature window matching the mixed-phase layer,
  with constant rate.

Both modes additionally require updraft `w` to exceed
`config_lnox_w_threshold`; outside active convection, no NO is injected.

## Gating modes

| Mode | Gate | Rate |
|---|---|---|
| `altitude` (default) | `z_min ≤ z ≤ z_max` AND `w > w_threshold` | `S = source_rate · (w − w_threshold) / w_ref` |
| `isotherm` (new) | `t_min ≤ T ≤ t_max` AND `w > w_threshold` | `S = source_rate` (constant) |

The 233.15–262.15 K isotherm window is the canonical mixed-phase layer
where charge separation drives lightning in deep convection. The 1 ppbv
NOx target at cloud top, and the constant emission framing, come from
the DC3 supercell parcel-model description preserved in `LNOx.md` at
the repository root.

Altitude mode is retained for backward compatibility with existing
runs and for cases where the user wants to specify a literal injection
volume independent of the storm thermal structure.

## Namelist options

All options are members of the `&musica` namelist group. Defaults
shown match `src/core_atmosphere/Registry.xml`.

| Option | Type | Default | Used in | Description |
|---|---|---|---|---|
| `config_lnox_gating_mode` | character | `'altitude'` | both | Selects the gate; `'altitude'` or `'isotherm'`. Unknown values disable the source and log a critical message. |
| `config_lnox_source_rate` | real | `0.0` | both | Source rate amplitude; ppbv s⁻¹. Zero disables the source. Altitude mode multiplies by `(w − w_threshold) / w_ref`; isotherm mode applies it as a constant. |
| `config_lnox_w_threshold` | real | `5.0` | both | Updraft threshold (m s⁻¹) below which no NO is injected. |
| `config_lnox_w_ref` | real | `10.0` | altitude only | Reference updraft (m s⁻¹) for the altitude-mode rate normalization. Ignored in isotherm mode. |
| `config_lnox_z_min` | real | `5000.0` | altitude only | Lower altitude bound (m). Ignored in isotherm mode. |
| `config_lnox_z_max` | real | `12000.0` | altitude only | Upper altitude bound (m). Ignored in isotherm mode. |
| `config_lnox_t_min` | real | `233.15` | isotherm only | Cold isotherm bound (K). Ignored in altitude mode. |
| `config_lnox_t_max` | real | `262.15` | isotherm only | Warm isotherm bound (K). Ignored in altitude mode. |
| `config_lnox_j_no2` | real | `0.0` | both | Daytime peak `jNO2` for the fallback solar-geometry photolysis path; not part of the LNOx source itself but lives in the same namelist block. |
| `config_lnox_nox_tau` | real | `0.0` | both | Optional NOx relaxation timescale (s); zero disables. |

## Code paths

The implementation lives in two files. File:line references reflect
the state of `develop` at the 2026-05-06 isotherm-source landing.

- `src/core_atmosphere/chemistry/mpas_lightning_nox.F`
  - `lightning_nox_init` (line 68) — parses `config_lnox_gating_mode`,
    sets the module-level integer `mode = MODE_ALTITUDE | MODE_ISOTHERM`,
    validates isotherm-mode bounds, and logs the resolved configuration.
  - `lightning_nox_inject` (line 201) — operates on plain Fortran
    arrays; branches on `mode` (line 229 / 255) for the per-cell loop.
    Accepts an optional `temperature(:,:)` argument; in isotherm mode
    the absence of the argument is treated as a no-op.
- `src/core_atmosphere/chemistry/mpas_atm_chemistry.F`
  - The inject call site (~line 524) computes
    `T = theta_m / (1 + rvord·qv) · exner` into a local
    `(nVertLevels, nCells)` array when the LNOx scheme is active and
    passes it through. Altitude-mode runs skip the temperature
    computation, so they are bit-identical to the pre-isotherm code.

The module does not touch MPAS pools directly — `mpas_atm_chemistry.F`
is the only place that pulls `theta_m`, `exner`, and `index_qv` from
the diag/state pools.

## Calibration notes

The LNOx.md DC3 description targets ~1 ppbv NOx at cloud top in a
supercell with ~5 m s⁻¹ sustained updrafts. For isotherm mode, a
starting point that gives an order-of-magnitude-correct first run is

```
config_lnox_source_rate = 1.0e-3   ! ppbv/s
```

(reasoning: an air parcel takes ~1000 s to traverse the 262–233 K
mixed-phase layer in a strong updraft; 1.0e-3 ppbv/s × 1000 s ≈ 1 ppbv).

Refinement is a manual retune-and-rerun loop: visualize with
`scripts/plot_lnox_o3.py`, inspect peak NOx in the convective core,
adjust `config_lnox_source_rate` by a small factor, and re-run.

For altitude mode, the DAVINCI-era default
`source_rate = 0.5, w_threshold = 5.0, w_ref = 10.0` produces a
visually similar enhancement on the supercell case; calibration there
is also a manual loop.

A regression-suite reference for both modes is planned but not yet
present in this branch — see
[docs/superpowers/specs/2026-04-19-regression-suite-design.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/superpowers/specs/2026-04-19-regression-suite-design.md).

## See also

- [`LNOx.md`](https://github.com/NCAR/CheMPAS-A/blob/develop/LNOx.md) — original DC3 motivation note (preserved as a pointer)
- [docs/superpowers/specs/2026-05-06-lnox-isotherm-source-design.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/superpowers/specs/2026-05-06-lnox-isotherm-source-design.md) — design of the isotherm-mode branch
- [docs/tutorial/02-supercell.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/tutorial/02-supercell.md) — Chapter 2 §2.6 worked examples for both modes
- [docs/chempas/musica/MUSICA_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/musica/MUSICA_INTEGRATION.md) — MUSICA / MICM coupling
- [docs/chempas/guides/TUVX_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/guides/TUVX_INTEGRATION.md) — TUV-x photolysis (the `config_lnox_j_no2` fallback path)
````

- [ ] **Step 1.2: Verify the file renders cleanly with the docs build**

Run:

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A
python -c "import docutils, myst_parser; print('myst ok')" 2>/dev/null || echo "myst not in this env — fall back to markdown lint only"
```

If a `make docs` / `sphinx-build` target exists, run it; otherwise visually inspect the markdown:

```bash
head -40 docs/chempas/guides/LNOX_INTEGRATION.md
wc -l docs/chempas/guides/LNOX_INTEGRATION.md
```

Expected: file present, ~140 lines, no MyST syntax errors at first glance (no unbalanced backticks, table pipes line up).

- [ ] **Step 1.3: Verify the namelist option list matches `Registry.xml`**

Run:

```bash
grep '^[[:space:]]*<nml_option name="config_lnox' src/core_atmosphere/Registry.xml | sed -E 's/.*name="([^"]+)".*default_value="([^"]*)".*/\1 = \2/'
```

Expected (one per line, in any order):

```
config_lnox_source_rate = 0.0
config_lnox_w_threshold = 5.0
config_lnox_w_ref = 10.0
config_lnox_z_min = 5000.0
config_lnox_z_max = 12000.0
config_lnox_j_no2 = 0.0
config_lnox_nox_tau = 0.0
config_lnox_gating_mode = altitude
config_lnox_t_min = 233.15
config_lnox_t_max = 262.15
```

If any option name or default in the table inside the guide does not match this output, fix the guide before committing.

- [ ] **Step 1.4: Commit**

```bash
git add docs/chempas/guides/LNOX_INTEGRATION.md
git commit -m "$(cat <<'EOF'
docs(guides): add LNOX_INTEGRATION.md scheme guide

Documents both gating modes (altitude, isotherm), the full
config_lnox_* namelist surface, the mpas_lightning_nox.F /
mpas_atm_chemistry.F code paths, and calibration notes. Parallels
the existing TUVX_INTEGRATION.md guide; supersedes the terse
repository-root LNOx.md note (which becomes a pointer in a later
commit).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Restructure Tutorial Ch. 2 §2.6 with parallel LNOx walkthroughs

**Files:**
- Modify: `docs/tutorial/02-supercell.md`

This restructures the existing single-mode §2.6 into a three-part subsection covering both gating modes, with a figure renumber. The §2.5 ABBA walkthrough, §2.7–§2.11 sections, and §2.6's introductory framing are all retained — only the body of §2.6 (run with the LNOx + O3 mechanism) changes.

- [ ] **Step 2.1: Replace the §2.6 body in `docs/tutorial/02-supercell.md`**

Locate the existing block from the section heading `## 2.6 Run with the LNOx + O3 mechanism` (line 188 in the tracked file) through the end of the current "What to look for" paragraph just above `## 2.7 Comparing the two runs` (line 268). Replace it with the following content. Read the file first to confirm the exact line range; the surrounding `## 2.5` and `## 2.7` headings must stay untouched.

````markdown
## 2.6 Run with the LNOx + O3 mechanism

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

The LNOx + O3 setup (`micm_configs/lnox_o3.yaml`) is a tropospheric
gas-phase configuration with three prognostic species — NO, NO₂, and
O₃ — and a parameterized lightning-NOx source term. It is the
smallest realistic chemistry case in CheMPAS-A: enough species and
reactions to exercise the MICM solver, TUV-x photolysis, and the LNOx
source coupling, without the cost of a full tropospheric mechanism.

The lightning-NOx source has two gating modes, configurable through
the `&musica` namelist:

- **Altitude-mode** gating (the inherited DAVINCI-MPAS formulation) —
  emit NO in a fixed altitude window, with rate scaled by updraft
  excess.
- **Isotherm-mode** gating (new, faithful to the DC3 mixed-phase
  framing in `LNOx.md`) — emit NO in a temperature window
  corresponding to the 233–262 K layer, at a constant rate.

This section walks through both modes as parallel runs and then
compares them. The full scheme description, namelist surface, and
calibration notes live in
[docs/chempas/guides/LNOX_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/guides/LNOX_INTEGRATION.md).

**Initialize the LNOx tracers.** The supercell init file does not
contain NO / NO₂ / O₃; populate them with a one-time script. Both
gating modes use the same initial state:

```bash
cd ~/Data/CheMPAS/supercell
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/init_lnox_o3.py -i supercell_init.nc
```

This sets NO = 0, NO₂ = 0, and O₃ = 50 ppbv (background) throughout
the domain.

### 2.6.1 LNOx with altitude-mode gating

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

**Edit the namelist.** Replace the `&musica` block in
`namelist.atmosphere` with the altitude-mode configuration:

```fortran
&musica
    config_micm_file = 'lnox_o3.yaml'
    config_tuvx_config_file = 'tuvx_no2.json'
    config_tuvx_top_extension = .true.
    config_tuvx_extension_file = 'tuvx_upper_atm.csv'
    config_lnox_gating_mode = 'altitude'
    config_lnox_source_rate = 0.5
    config_lnox_w_threshold = 5.0
    config_lnox_w_ref = 10.0
    config_lnox_z_min = 5000.0
    config_lnox_z_max = 12000.0
    config_lnox_j_no2 = 0.01
    config_lnox_nox_tau = 0.0
    config_chemistry_latitude = 35.86
    config_chemistry_longitude = -97.93
/
```

In altitude mode, NO is injected into grid cells where the vertical
velocity exceeds `config_lnox_w_threshold` and the height falls
between `config_lnox_z_min` and `config_lnox_z_max`. The per-cell
emission rate is `S = source_rate · (w − w_threshold) / w_ref`, so
stronger updrafts emit more NO.

**Archive prior output and run.** Same pattern as the ABBA run:

```bash
timestamp=$(date +%Y%m%d_%H%M%S)
[ -f output.nc ] && mv output.nc output.${timestamp}.nc
[ -f log.atmosphere.0000.out ] && \
    mv log.atmosphere.0000.out log.atmosphere.0000.${timestamp}.out

mpiexec -n 8 ~/EarthSystem/CheMPAS-A/atmosphere_model
```

**Plot.** The dedicated LNOx plotting script produces the standard
diagnostic set (vertical cross-sections, time series, NO₂
partitioning ratio):

```bash
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/plot_lnox_o3.py
```

**[Figure 2.3: NO, NO₂, O₃ at t = 2 h, LNOx + O3 mechanism, altitude
gating. To be added.]**

What to look for: a localized NO source in the updraft column where
the vertical-velocity threshold is exceeded, downwind transport of
NO + NO₂ along the anvil, and an O₃ depletion signature in the freshly
emitted plume (titration by NO). The injected volume is a fixed
5–12 km altitude band — a slab whose location does not move with the
storm thermal structure.

### 2.6.2 LNOx with isotherm-mode gating

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

**Edit the namelist.** Replace the `&musica` block with the isotherm
configuration:

```fortran
&musica
    config_micm_file = 'lnox_o3.yaml'
    config_tuvx_config_file = 'tuvx_no2.json'
    config_tuvx_top_extension = .true.
    config_tuvx_extension_file = 'tuvx_upper_atm.csv'
    config_lnox_gating_mode = 'isotherm'
    config_lnox_source_rate = 1.0e-3
    config_lnox_w_threshold = 5.0
    config_lnox_t_min = 233.15
    config_lnox_t_max = 262.15
    config_lnox_j_no2 = 0.01
    config_lnox_nox_tau = 0.0
    config_chemistry_latitude = 35.86
    config_chemistry_longitude = -97.93
/
```

In isotherm mode, NO is injected into grid cells where the cell
temperature is between `config_lnox_t_min` and `config_lnox_t_max`
*and* the updraft exceeds `config_lnox_w_threshold`. The emission
rate is constant: `S = source_rate` whenever the gate is open.
`source_rate = 1.0e-3 ppbv/s` is the calibration starting point in
`LNOX_INTEGRATION.md`; expect to retune by a small factor after the
first run.

**Archive prior output and run.** Move the altitude-mode `output.nc`
aside before re-running so the two outputs survive side by side:

```bash
[ -f output.nc ] && mv output.nc output.altitude.nc
[ -f log.atmosphere.0000.out ] && mv log.atmosphere.0000.out log.altitude.out

mpiexec -n 8 ~/EarthSystem/CheMPAS-A/atmosphere_model

[ -f output.nc ] && mv output.nc output.isotherm.nc
[ -f log.atmosphere.0000.out ] && mv log.atmosphere.0000.out log.isotherm.out
```

**Plot.** Same plotting script; point it at the isotherm output:

```bash
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/plot_lnox_o3.py -i output.isotherm.nc \
    -o lnox_isotherm.png
```

**[Figure 2.4: NO, NO₂, O₃ at t = 2 h, LNOx + O3 mechanism, isotherm
gating. To be added.]**

What to look for: NO emission confined to the 233–262 K mixed-phase
layer of the storm — typically ~5–9 km on this thermodynamic profile
but moving with the cloud rather than pinned to a fixed altitude.
The peak NOx in the convective core should be of order 1 ppbv (the
LNOx.md DC3 target). If your peak is off by more than a factor of a
few, retune `config_lnox_source_rate` and re-run.

### 2.6.3 Comparing the gating modes

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

Placing the two LNOx runs side by side highlights what the gating
choice changes. Spatially, altitude mode emits into a fixed slab
(`z_min`–`z_max`), so the NO source volume is the same regardless of
where the storm thermal structure sits; isotherm mode emits into the
mixed-phase layer, so the source volume shifts vertically as the
storm evolves and the 233–262 K layer moves up or down. In rate, the
altitude formulation scales with updraft excess so the strongest
updrafts emit the most NO; the isotherm formulation is flat — once
the gate is open, every active cell emits at the same rate, faithful
to the LNOx.md "constant emission" framing.

The downwind chemistry the two formulations imply — NO + O₃
titration, NO₂ photolysis, anvil-level NOx redistribution — is
identical because the MICM mechanism and TUV-x configuration are the
same; only the emission gating differs.

**[Figure 2.5: Side-by-side qNO, qNO₂, qO₃ final-state cross-sections
at t = 2 h: altitude mode (left column) vs. isotherm mode (right
column). To be added.]**
````

- [ ] **Step 2.2: Update §2.7 to renumber Fig 2.4 → Fig 2.6**

Find the `**[Figure 2.4: Side-by-side comparison of ABBA tracer transport and LNOx + O3 chemistry at t = 2 h. To be added.]**` line in §2.7 and renumber it. The replacement:

```markdown
**[Figure 2.6: Side-by-side comparison of ABBA tracer transport and
LNOx + O3 chemistry at t = 2 h. To be added.]**
```

The §2.7 prose itself does not need to change — it discusses the comparison conceptually and does not cite the figure number inline.

- [ ] **Step 2.3: Update §2.9 *Next steps* to reference the LNOx guide**

Find the §2.9 bullet list. After the existing "MUSICA/MICM coupling internals" bullet, insert one new bullet:

```markdown
- **The LNOx scheme** — both gating modes, full namelist surface,
  and calibration notes — is documented in
  [docs/chempas/guides/LNOX_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/guides/LNOX_INTEGRATION.md).
```

Also append a forward-link to the new chapter at the top of the bullet list (replacing the existing "next chapter" wording that points to Chapter 3, since Chapter 3 is no longer the *only* next-chapter pointer):

Find:

```markdown
- **The next chapter** is
  [Chapman + NOx Photostationary State](03-chapman-nox.md) — a small
  domain where the analytical PSS solution is a clean check on the
  coupled MICM + TUV-x configuration.
```

Replace with:

```markdown
- **The next chapter** is
  [Chapman + NOx Photostationary State](03-chapman-nox.md) — a small
  domain where the analytical PSS solution is a clean check on the
  coupled MICM + TUV-x configuration. Chapter 4 then runs the same
  chemistry on the global `x1.40962` mesh:
  [Chapman + NOx Global](04-chapman-nox-global.md).
```

- [ ] **Step 2.4: Renumber Figs 2.5 and 2.6 in §2.10 and §2.11**

In §2.10 *Standalone ABBA box model*, find:

```markdown
**[Figure 2.5: A, B, AB concentrations from the standalone ABBA box
model over a 2 h integration. To be added.]**
```

Replace `2.5` with `2.7`:

```markdown
**[Figure 2.7: A, B, AB concentrations from the standalone ABBA box
model over a 2 h integration. To be added.]**
```

In §2.11 *Standalone LNOx + O₃ box model*, find:

```markdown
**[Figure 2.6: NO, NO₂, O₃ from the standalone LNOx + O₃ box model.
The first ~minute shows NO/NO₂ relaxing to the Leighton PSS; over
2 h, slow O₃ titration is visible. To be added.]**
```

Replace `2.6` with `2.8`:

```markdown
**[Figure 2.8: NO, NO₂, O₃ from the standalone LNOx + O₃ box model.
The first ~minute shows NO/NO₂ relaxing to the Leighton PSS; over
2 h, slow O₃ titration is visible. To be added.]**
```

- [ ] **Step 2.5: Verify all figure numbers in `02-supercell.md` follow the new mapping**

Run:

```bash
grep -nE '\*\*\[Figure 2\.' docs/tutorial/02-supercell.md
```

Expected (eight figures, in the new ordering):

```
2.1 ... initial state
2.2 ... ABBA
2.3 ... LNOx altitude mode
2.4 ... LNOx isotherm mode
2.5 ... side-by-side altitude vs. isotherm
2.6 ... ABBA vs. LNOx
2.7 ... standalone ABBA box
2.8 ... standalone LNOx box
```

If any number is wrong or any figure is missing, fix it before committing.

- [ ] **Step 2.6: Verify no broken inline references**

Run:

```bash
grep -nE 'Figure 2\.|Fig\. 2\.|fig\. 2\.' docs/tutorial/02-supercell.md
```

Look for prose references that cite a figure number; cross-check each against the new mapping. Existing prose in Ch. 2 mostly does not cite figure numbers in narrative — but the §2.10 / §2.11 captions reference §2.5 and §2.6 in their narrative. Confirm those references still resolve (they refer to chapter sections, not figure numbers, so they should be unchanged).

- [ ] **Step 2.7: Commit**

```bash
git add docs/tutorial/02-supercell.md
git commit -m "$(cat <<'EOF'
docs(tutorial): split Ch. 2 §2.6 into altitude + isotherm LNOx runs

Restructures §2.6 from a single LNOx walkthrough into three
subsections: §2.6.1 altitude-mode (existing content with namelist
gating_mode added), §2.6.2 isotherm-mode (new), §2.6.3 comparison.
Renumbers Figs 2.4–2.6 to 2.6–2.8 to keep figure order aligned with
content order; new Figs 2.4 and 2.5 cover the isotherm-mode result
and the side-by-side comparison. Adds §2.9 cross-link to the new
LNOX_INTEGRATION.md guide and to Chapter 4.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Update Tutorial Ch. 3's next-steps link

**Files:**
- Modify: `docs/tutorial/03-chapman-nox.md` (§3.9 *Next steps*)

- [ ] **Step 3.1: Replace the §3.9 placeholder bullet pointing at "future tutorial chapters … not yet scheduled"**

Find this block (currently around line 405):

```markdown
- **Future tutorial chapters** will cover additional idealized cases
  (mountain wave, JW baroclinic wave, chem box) when they're
  written. *(Not yet scheduled.)*
```

Replace with:

```markdown
- **The next chapter** is
  [Chapman + NOx Global](04-chapman-nox-global.md) — the same
  chemistry on the `x1.40962` global mesh, where the day–night
  photolysis terminator and zonal-mean ozone response become visible.
- **Further idealized cases** (mountain wave, chem box) will be added
  when their tutorial chapters are written. *(Not yet scheduled.)*
```

- [ ] **Step 3.2: Verify no other Ch. 3 references need updating**

Run:

```bash
grep -nE 'chapter 4|Chapter 4|Future tutorial' docs/tutorial/03-chapman-nox.md
```

Expected: only the new "Chapman + NOx Global" forward-link. No "Future tutorial chapters … not yet scheduled" line should remain.

- [ ] **Step 3.3: Commit**

```bash
git add docs/tutorial/03-chapman-nox.md
git commit -m "$(cat <<'EOF'
docs(tutorial): link Ch. 3 next-steps to new Ch. 4 (Chapman global)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Create Tutorial Chapter 4

**Files:**
- Create: `docs/tutorial/04-chapman-nox-global.md`

This is the new global Chapman + NOx tutorial chapter. Eight sections,
mirroring Chapter 3's shape. WIP banners on every visible subsection,
matching Chapter 2 / 3 convention.

- [ ] **Step 4.1: Create the file with the full content below**

````markdown
# Chapter 4: Chapman + NOx — Global

```{admonition} Work in progress
:class: warning

This chapter is being actively written. Commands and expected output
are provisional; figure slots are left without rendered PNGs until the
corresponding model runs and plots are archived.
```

Chapter 3 used the supercell mesh as a column-like sandbox to verify
the Chapman + NOx mechanism against the analytical Leighton
photostationary state. This chapter runs the same chemistry on a
global mesh — the standard MPAS `x1.40962` 120 km quasi-uniform mesh —
and looks at what the diurnal cycle of solar photolysis does when it
sweeps across an entire planet.

## 4.1 What you'll learn

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

By the end of this chapter you will:

- Run the `chapman_nox_global` idealized case on the global
  `x1.40962` mesh in CheMPAS-A.
- See the day–night photolysis terminator sweep across a global jNO₂
  field, four times per day.
- Verify that NO/NO₂ partitioning flips across the terminator —
  daytime tracking the Leighton photostationary state introduced in
  Chapter 3, nighttime relaxing toward NO₂.
- Inspect the global-mean and zonal-mean ozone response over a
  24-hour integration.

## 4.2 The Chapman + NOx global case

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

The case runs the same `chapman_nox.yaml` MICM mechanism and
`tuvx_chapman_nox.json` photolysis configuration as Chapter 3 — six
prognostic species (O₂, O, O¹D, O₃, NO, NO₂), four photolysis rates
(jO₂, jO₃→O, jO₃→O¹D, jNO₂) — but on the global `x1.40962` mesh.
Domain summary:

- 40 962 cells, nominal 120 km spacing, 26 vertical levels (the
  standard JW baroclinic-wave initialization mesh).
- 24-hour integration, 450 s dynamics timestep, 3600 s TUV-x update
  interval.
- `config_chemistry_use_grid_coords = .true.` — every cell uses its
  own (latitude, longitude) for the solar-zenith-angle calculation,
  so jNO₂ at any instant has the day–night terminator built in.
- The TUV-x upper-atmosphere extension (the 50–100 km column
  introduced in Chapter 3 §3.3) is enabled, so photolysis above the
  model lid is treated correctly.

This case borrows the JW baroclinic-wave init mesh purely as a
convenient global initial state for the dynamics; it is not a
baroclinic-wave dynamics demonstration. The Chapman + NOx chemistry
runs on whatever flow the dynamics produce, but the dominant signal
in the chemistry diagnostics is the diurnal photolysis cycle, not
the dynamics.

**[Figure 4.1: AFGL-Gaussian initial qO₃ profile injected globally
by `init_chapman_nox.py`. To be added.]**

## 4.3 Setup

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

Before you run anything, confirm:

```bash
# 1. The atmosphere_model executable exists and is from this branch.
ls -la ~/EarthSystem/CheMPAS-A/atmosphere_model

# 2. The run directory is set up.
mkdir -p ~/Data/CheMPAS/chapman_nox_global
cd ~/Data/CheMPAS/chapman_nox_global

# 3. The global init mesh exists. The standard JW baroclinic-wave
#    init step (test_cases/README.md, §"Setup and Initialization")
#    produces x1.40962.init.nc; copy or symlink it here.
ls ~/Data/CheMPAS/jw_baroclinic_wave/x1.40962.init.nc
ln -sf ~/Data/CheMPAS/jw_baroclinic_wave/x1.40962.init.nc .

# 4. The conda env is active for the tracer-injection script and
#    the plotting script.
conda activate mpas
python -c "import netCDF4, numpy, cartopy, matplotlib; print('ok')"
```

If the JW init file is missing, run the standard JW init step first
(see [`test_cases/README.md`](https://github.com/NCAR/CheMPAS-A/blob/develop/test_cases/README.md)).

Always run with 8 MPI ranks for this case — the partition file in the
run directory (`x1.40962.graph.info.part.8`) is keyed to that rank
count, and a mismatched partition file causes a segfault in the
dynamics solver.

## 4.4 Initializing Chapman + NOx tracers globally

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

The `chapman_nox_global` streams config reads
`x1.40962.chapman_nox_init.nc` — a copy of the JW init NetCDF with
the six Chapman + NOx tracers injected as functions of altitude only.
`scripts/init_chapman_nox.py` does the injection:

```bash
cd ~/Data/CheMPAS/chapman_nox_global
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/init_chapman_nox.py \
    -i x1.40962.init.nc \
    -o x1.40962.chapman_nox_init.nc
```

What the script writes:

- `qO2` — uniform 0.21 mole fraction (≈0.232 kg/kg).
- `qO3` — Gaussian peak of 10 ppmm at 25 km, σ = 7 km.
  Function of altitude only; horizontal structure comes from the
  chemistry's diurnal cycle, not from the initial state.
- `qO`, `qO1D` — small floor (1×10⁻¹². The fast-radical species spin
  up to Chapman quasi-steady-state within seconds on the first
  sunlit step).
- `qNO`, `qNO2` — 1 ppbv background each, uniform with altitude.
  Lower than the stratospheric NOx peak (~10 ppb in §3.5) but
  sufficient to drive a visible terminator-aligned partition flip.

Mass mixing ratios are written in kg/kg; molar masses for the unit
conversion match `scripts/init_chapman.py` and
`scripts/plot_lnox_o3.py`.

## 4.5 Running

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

The tracked configs in
[`test_cases/chapman_nox_global/`](https://github.com/NCAR/CheMPAS-A/blob/develop/test_cases/chapman_nox_global/)
include the namelist, streams, and output-variable list. Copy them
into the run directory along with the partition file:

```bash
cd ~/Data/CheMPAS/chapman_nox_global
cp ~/EarthSystem/CheMPAS-A/test_cases/chapman_nox_global/* .
ln -sf ~/EarthSystem/CheMPAS-A/atmosphere_model .

# The partition file lives next to the JW init.
ln -sf ~/Data/CheMPAS/jw_baroclinic_wave/x1.40962.graph.info.part.8 .
```

The tracked `&musica` block reads:

```fortran
&musica
    config_micm_file = 'chapman_nox.yaml'
    config_tuvx_config_file = 'tuvx_chapman_nox.json'
    config_tuvx_top_extension = .true.
    config_tuvx_extension_file = 'tuvx_upper_atm.csv'
    config_tuvx_update_interval = 3600.0
    config_chemistry_use_grid_coords = .true.
/
```

No `config_chemistry_latitude` / `config_chemistry_longitude` —
`use_grid_coords = .true.` overrides those, and every cell gets its
own SZA. The 3600 s TUV-x update interval is much longer than the
small-domain Ch. 3 case (which used 600 s); on a 24-hour global run
the SZA evolves slowly enough that hourly TUV-x updates resolve the
terminator sweep correctly.

**Archive prior output and run.** Same pattern as Chapter 2 / Chapter 3:

```bash
timestamp=$(date +%Y%m%d_%H%M%S)
[ -f output.nc ] && mv output.nc output.${timestamp}.nc
[ -f log.atmosphere.0000.out ] && \
    mv log.atmosphere.0000.out log.atmosphere.0000.${timestamp}.out

mpiexec -n 8 ./atmosphere_model
```

The 24-hour integration takes longer than the 2-hour supercell case;
expect order-tens-of-minutes wall time on a workstation, dominated by
TUV-x and dynamics rather than MICM.

Verify the run completed cleanly by checking the tail of
`log.atmosphere.0000.out`:

```
Critical error messages = 0
```

## 4.6 Plotting the global response

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

`scripts/plot_chapman_nox_global.py` produces four figures, written
as PNG + PDF, using the NCAR brand styling from `scripts/style.py`:

```bash
cd ~/Data/CheMPAS/chapman_nox_global
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/plot_chapman_nox_global.py \
    -i output.nc -o ./plots
```

The four figures:

- **`jNO2_terminator.png`** — jNO₂ maps at t = 0, 6, 12, 18 UTC.
  The day–night terminator sweeps across the globe four times in this
  panel, visible as a sharp drop in jNO₂ at the photolysis edge.
  Triangulated mesh rendering with antimeridian-spanning triangles
  masked, so the limb is clean.

  **[Figure 4.2: jNO₂ terminator-sweep map at t = 0 / 6 / 12 / 18
  UTC. To be added.]**

- **`tracers_evolution.png`** — qO₃ at level 22 (≈36 km, where the
  Chapman cycle is most active) and qNO₂ at level 17 (≈25 km, near
  the seeded NOx peak), shown at t = 12 h and t = 24 h.

  **[Figure 4.3: qO₃ at ≈36 km and qNO₂ at ≈25 km, t = 12 h and t =
  24 h. To be added.]**

- **`nox_partition.png`** — NO₂ / (NO + NO₂) molar fraction at t = 12 h
  and t = 24 h. Dayside drops toward Leighton (lower fraction —
  jNO₂ converts NO₂ → NO); nightside relaxes toward NO₂ (higher
  fraction — no photolysis, NO + O₃ titrates NO back to NO₂).

  **[Figure 4.4: NO₂ partition fraction at t = 12 h and t = 24 h. To
  be added.]**

- **`o3_profile.png`** — global-mean O₃ vertical profile and the
  zonal-mean ΔO₃ over the 24-hour window. Symmetric-log color norm so
  upper-stratosphere production above ~30 km and lower-altitude
  NOx-driven loss below are both visible in the same figure.

  **[Figure 4.5: Global-mean O₃ profile and zonal-mean ΔO₃ over 24 h.
  To be added.]**

## 4.7 What to look for

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

Three diagnostics worth checking by eye:

- **Terminator alignment.** In `jNO2_terminator.png`, the jNO₂ drop
  should align with the geometric SZA = 90° great circle at each UTC
  hour. If the terminator is rotated or offset, the
  `use_grid_coords` machinery is mis-wired.
- **Partition flip.** In `nox_partition.png`, daytime hemispheres
  should sit at lower NO₂ fractions than nighttime hemispheres. The
  contrast tracks where the integration is in its diurnal cycle —
  t = 12 h and t = 24 h are spaced exactly one local-noon apart at
  the prime meridian.
- **Ozone modulation magnitude.** In `tracers_evolution.png` and
  `o3_profile.png`, expect a few-percent diurnal modulation in qO₃
  at 36 km. The 24-hour integration is too short for the column to
  fully relax; longer runs (multi-day, off the scope of this
  chapter) would show a slow drift toward the steady state.

The fast-radical species (qO, qO¹D) should stay small everywhere
once chemistry has spun up — they are output for diagnostic value
but should not exceed parts-per-billion levels in the column.

## 4.8 Next steps and see also

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

- **The Leighton photostationary state** that this chapter shows
  flipping across the terminator is verified analytically on a small
  domain in
  [Chapter 3 §3.7–§3.8](03-chapman-nox.md). Chapter 3 is the right
  next stop if the partition behaviour here surprises you.
- **The MUSICA/MICM coupling internals** are documented in
  [docs/chempas/musica/MUSICA_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/musica/MUSICA_INTEGRATION.md).
- **TUV-x integration engineering** — the column extension, host
  profile updates, and the `use_grid_coords` machinery — is
  documented in
  [docs/chempas/guides/TUVX_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/guides/TUVX_INTEGRATION.md).
- **The LNOx scheme** — both gating modes, namelist surface, and
  calibration notes — is documented in
  [docs/chempas/guides/LNOX_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/guides/LNOX_INTEGRATION.md).
  The global Chapman + NOx case has no LNOx source, but readers
  exploring chemistry-coupled cases should see the LNOx scheme too.
- **Upstream MUSICA, MICM, and TUV-x docs** are linked from the
  [project landing page](../index.rst) in the *See also* section.
````

- [ ] **Step 4.2: Verify the file's structure**

Run:

```bash
grep -nE '^## 4\.|^# Chapter 4' docs/tutorial/04-chapman-nox-global.md
```

Expected:

```
1:# Chapter 4: Chapman + NOx — Global
17:## 4.1 What you'll learn
... (eight section headings 4.1 through 4.8)
```

- [ ] **Step 4.3: Verify figure-placeholder formatting**

Run:

```bash
grep -nE '\*\*\[Figure 4\.' docs/tutorial/04-chapman-nox-global.md
```

Expected: five figure placeholders (4.1 through 4.5), each in the form `**[Figure 4.N: caption. To be added.]**`.

- [ ] **Step 4.4: Verify all internal links resolve**

Run:

```bash
grep -nE '\((https://github\.com/NCAR/CheMPAS-A/blob/develop/[^)]+)\)' docs/tutorial/04-chapman-nox-global.md
```

For each match, confirm the linked path exists in the working tree:

```bash
for path in \
    test_cases/chapman_nox_global \
    test_cases/README.md \
    docs/chempas/musica/MUSICA_INTEGRATION.md \
    docs/chempas/guides/TUVX_INTEGRATION.md \
    docs/chempas/guides/LNOX_INTEGRATION.md ; do
  ls "/Users/fillmore/EarthSystem/CheMPAS-A/$path" >/dev/null 2>&1 \
    && echo "ok: $path" \
    || echo "MISSING: $path"
done
```

Expected: every line printed `ok:`. If any are `MISSING:`, the link is broken — fix before committing.

- [ ] **Step 4.5: Commit**

```bash
git add docs/tutorial/04-chapman-nox-global.md
git commit -m "$(cat <<'EOF'
docs(tutorial): add Chapter 4 — Chapman + NOx global case

Walks through the new test_cases/chapman_nox_global/ idealized case:
24-hour integration on the x1.40962 global mesh, init via
init_chapman_nox.py, and the four diagnostic figures from
plot_chapman_nox_global.py (terminator-sweep jNO2, tracer evolution,
NOx partition flip across the terminator, global-mean and zonal-mean
O3 response). Figure slots and per-section WIP banners follow the
Chapter 2 / Chapter 3 convention.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Add Chapter 4 to the tutorial toctree

**Files:**
- Modify: `docs/tutorial/index.rst`

- [ ] **Step 5.1: Add `04-chapman-nox-global` to the toctree**

Read the current file:

```bash
cat docs/tutorial/index.rst
```

Find the toctree block:

```rst
.. toctree::
   :maxdepth: 2
   :caption: Chapters

   01-overview
   02-supercell
   03-chapman-nox
```

Add the new chapter at the end:

```rst
.. toctree::
   :maxdepth: 2
   :caption: Chapters

   01-overview
   02-supercell
   03-chapman-nox
   04-chapman-nox-global
```

- [ ] **Step 5.2: Verify the toctree**

Run:

```bash
tail -15 docs/tutorial/index.rst
```

Expected: four chapter entries listed in order.

- [ ] **Step 5.3: Commit**

```bash
git add docs/tutorial/index.rst
git commit -m "$(cat <<'EOF'
docs(tutorial): add Chapter 4 to toctree

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Document `chapman_nox_global` in `test_cases/README.md`

**Files:**
- Modify: `test_cases/README.md`

- [ ] **Step 6.1: Add the case to the table**

Find the existing cases table (currently lines 21–26):

```markdown
| Case | Init Case | Mesh | Cells | Levels | dt (s) | Duration |
|------|-----------|------|-------|--------|--------|----------|
| `supercell/` | 5 | ~500 m | ~40k | 60 (stretched 0–50 km) | 3 | 2 hours |
| `mountain_wave/` | 6 | ~577 m | ~2k | 70 | 6 | 5 hours |
| `jw_baroclinic_wave/` | 2 | 120 km | 40,962 | 26 | 450 | 16 days |
| `chem_box/` | 5 | 500 m periodic 8×8 | 64 | 60 (stretched 0–50 km) | 3 | 1 hour |
```

Add a new row at the end (after `chem_box/`):

```markdown
| `chapman_nox_global/` | (reuses JW init, see below) | 120 km | 40,962 | 26 | 450 | 24 hours |
```

- [ ] **Step 6.2: Add the per-case sequence note**

After the existing paragraph that describes the `chem_box` case (the paragraph ending "See `docs/chempas/plans/2026-04-18-chapman-nox-chem-box-issue.md` for the exact reproduction steps and the chemistry configs it pairs with."), insert a new paragraph:

```markdown
The `chapman_nox_global` case reuses the JW baroclinic-wave init
mesh (`x1.40962.init.nc`) as the dynamics initial state; it is not a
baroclinic-wave dynamics demonstration, just a convenient global
init. Setting it up takes one extra step beyond the standard
download-and-init loop below:

1. Run the standard JW baroclinic-wave init (the
   `init_atmosphere_model` step in the loop below already produces
   `~/Data/CheMPAS/jw_baroclinic_wave/x1.40962.init.nc`).
2. Symlink that file into `~/Data/CheMPAS/chapman_nox_global/`.
3. Run `scripts/init_chapman_nox.py` from the new run directory to
   inject Chapman + NOx tracers into a copy of the init NetCDF. The
   output (`x1.40962.chapman_nox_init.nc`) is what the
   `streams.atmosphere` config reads.
4. Copy the tracked `test_cases/chapman_nox_global/` configs and
   the `x1.40962.graph.info.part.8` partition file into the run
   directory.

See [`docs/tutorial/04-chapman-nox-global.md`](../docs/tutorial/04-chapman-nox-global.md)
§4.3–§4.5 for the full setup walkthrough with explicit commands.
```

- [ ] **Step 6.3: Verify**

Run:

```bash
grep -n 'chapman_nox_global' test_cases/README.md
```

Expected: at least four matches (table row, prose paragraph in two or three places, link to Ch. 4).

- [ ] **Step 6.4: Commit**

```bash
git add test_cases/README.md
git commit -m "$(cat <<'EOF'
docs(test_cases): document chapman_nox_global setup

Adds the case to the cases table and explains the
JW-init-reuse + init_chapman_nox.py setup sequence that distinguishes
it from the standard download-and-init flow.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Add `chapman_nox_global` to the CLAUDE.md test-run table

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 7.1: Add the case to the *Test Run Directory* table**

Find this table in `CLAUDE.md`:

```markdown
| Case | Directory | Duration | Mesh |
|------|-----------|----------|------|
| Supercell | `~/Data/CheMPAS/supercell/` | 2 hours | 60 stretched levels to 50 km (~300 m surface → ~1 km top) |
| Mountain wave | `~/Data/CheMPAS/mountain_wave/` | 5 hours | ~577 m, 70 levels |
| Baroclinic wave | `~/Data/CheMPAS/jw_baroclinic_wave/` | 16 days | 120 km, 26 levels |
```

Add a new row after the baroclinic-wave row:

```markdown
| Chapman + NOx (global) | `~/Data/CheMPAS/chapman_nox_global/` | 24 hours | 120 km, 40,962 cells, 26 levels (reuses JW init) |
```

- [ ] **Step 7.2: Verify**

Run:

```bash
grep -nA 6 'Test Run Directory' CLAUDE.md | head -30
```

Expected: the table now lists four cases, with the new row reading `Chapman + NOx (global)`.

- [ ] **Step 7.3: Commit**

```bash
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
docs(CLAUDE.md): add chapman_nox_global to test-run table

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Trim `LNOx.md` to a pointer file

**Files:**
- Modify: `LNOx.md`

- [ ] **Step 8.1: Rewrite the file**

Replace the entire contents of `LNOx.md` with:

```markdown
# LNOx — DC3 motivation

Original DC3-derived note for the lightning-NOx scheme:

> A constant "lightning-generated" emission source of NO is applied
> between 262.15 K and 233.15 K so that 1 ppbv of NOx is produced
> at cloud top, matching the 0.8 - 1.2 ppbv average enhanced NOx
> sampled from this storm.
> The parcel model is run with two different assumed lightning
> produced NO (LNO) emission profiles.
> For a constant updraft of 5 and 2 m s-1, LNO emissions
> are set to 15 and 8 pptv per 10-second time step, respectively.

The full scheme description, namelist surface, code paths, and
calibration notes live in
[docs/chempas/guides/LNOX_INTEGRATION.md](docs/chempas/guides/LNOX_INTEGRATION.md).
This file is preserved at the repository root as a stable inbound
reference for the historical motivation.
```

- [ ] **Step 8.2: Verify**

Run:

```bash
cat LNOx.md
wc -l LNOx.md
```

Expected: ~16 lines, the original four-line DC3 quote preserved verbatim inside a markdown blockquote, and a pointer to the guide.

- [ ] **Step 8.3: Commit**

```bash
git add LNOx.md
git commit -m "$(cat <<'EOF'
docs: trim LNOx.md to a pointer (full guide is now LNOX_INTEGRATION.md)

Preserves the original four-line DC3 quote as the canonical motivation
record (cited by the design spec and the guide) and delegates the
full scheme description to docs/chempas/guides/LNOX_INTEGRATION.md.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Final verification

**Files:** none modified

End-to-end checks across the whole change set.

- [ ] **Step 9.1: All committed, working tree clean**

Run:

```bash
git status
```

Expected: working tree clean, branch ahead of origin by 8 commits (Task 1 through Task 8).

- [ ] **Step 9.2: Sphinx build (if available)**

Run:

```bash
ls docs/conf.py 2>/dev/null && echo "sphinx project found" || echo "no sphinx project at docs/"
```

If a Sphinx config is present, run a build and watch for warnings on the new and modified files:

```bash
~/miniconda3/envs/mpas/bin/sphinx-build -W -n -b html docs docs/_build/html 2>&1 | tail -40
```

Expected: build completes; no warnings reference `04-chapman-nox-global.md`, `02-supercell.md`, `03-chapman-nox.md`, `LNOX_INTEGRATION.md`, or the toctree. If Sphinx is not installed in the env, skip this step and rely on Step 9.3 / 9.4.

- [ ] **Step 9.3: Cross-link sanity check**

Run:

```bash
# Every in-tree GitHub-blob link from new/modified docs resolves to a real file.
for f in \
    docs/chempas/guides/LNOX_INTEGRATION.md \
    docs/tutorial/02-supercell.md \
    docs/tutorial/03-chapman-nox.md \
    docs/tutorial/04-chapman-nox-global.md \
    test_cases/README.md \
    LNOx.md ; do
  echo "=== $f ==="
  grep -oE 'https://github\.com/NCAR/CheMPAS-A/blob/develop/[^)]+' "$f" \
    | sed 's|https://github\.com/NCAR/CheMPAS-A/blob/develop/||' \
    | while read path; do
        ls "$path" >/dev/null 2>&1 && echo "ok: $path" || echo "MISSING: $path"
      done
done
```

Expected: every link prints `ok:`. Any `MISSING:` is a broken cross-link to fix.

- [ ] **Step 9.4: Registry / guide namelist parity**

Run:

```bash
# Names listed in the guide table.
grep -oE '`config_lnox_[a-z_]+`' docs/chempas/guides/LNOX_INTEGRATION.md \
    | sort -u

# Names declared in Registry.xml.
grep -oE 'name="config_lnox_[a-z_]+"' src/core_atmosphere/Registry.xml \
    | sort -u | sed 's/name="//;s/"$//' | sed 's/^/`/;s/$/`/'
```

Both lists should be identical. If a name appears in one but not the other, fix the guide.

- [ ] **Step 9.5: Tutorial figure number consistency**

Run:

```bash
grep -nE '\*\*\[Figure (2|3|4)\.' \
    docs/tutorial/02-supercell.md \
    docs/tutorial/03-chapman-nox.md \
    docs/tutorial/04-chapman-nox-global.md
```

Expected: 2.1–2.8 (eight figures), 3.1–3.5 (five figures, unchanged), 4.1–4.5 (five figures). No duplicate or skipped numbers.

- [ ] **Step 9.6: Push (optional, ask user first)**

Once all steps above pass, ask the user before pushing. If approved:

```bash
git push origin develop
```

---

## Self-review notes

- **Spec coverage:** Every section of the spec maps to a task — Task 1 → spec §1 guide, Task 2 → spec §2 Ch. 2, Task 3 → spec "modified files" Ch. 3 entry, Task 4 → spec §3 Ch. 4, Task 5 → spec "modified files" toctree entry, Task 6 → spec §4 README, Task 7 → spec §5 CLAUDE.md, Task 8 → spec §6 LNOx.md trim, Task 9 → spec "verification steps".
- **Placeholders:** None. Every code block is final, every command has expected output, every cross-link target is named.
- **Type / name consistency:** All `config_lnox_*` namelist option names cross-checked against `Registry.xml`. Figure numbers in the renumber plan (Task 2.5) match the inserts in Task 2.1 and the renames in Task 2.2 / 2.4. Chapter 4 link targets (`docs/chempas/guides/LNOX_INTEGRATION.md`, etc.) are created by Task 1 / 4 / 5 / 6 / 7 / 8 in dependency order — every link target is created before any task that links to it.
