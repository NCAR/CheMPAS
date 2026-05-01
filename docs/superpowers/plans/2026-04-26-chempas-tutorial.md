# CheMPAS-A Tutorial Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new top-level **CheMPAS-A Tutorial** section to the Sphinx docs, scaffolded with three chapters and the supercell chapter (Chapter 2) fleshed out for both the ABBA and LNOx + O3 mechanisms. Every visible subsection wears an orange "Work in progress" banner; figures are textual placeholders.

**Architecture:** A new `docs/tutorial/` directory parallel to `docs/users-guide/` and `docs/technical-description/`, registered in the root `docs/index.rst` toctree. Markdown chapters with a `.rst` toctree landing page, matching the existing `users-guide/` pattern so no `conf.py` changes are needed.

**Tech Stack:** Sphinx, MyST parser (`{admonition}` directive for the WIP banner; `dollarmath` and `amsmath` are the only enabled MyST extensions, so all admonitions use backtick-fenced syntax — `:::`-fenced syntax would require `colon_fence` and is NOT enabled).

**Spec:** `docs/superpowers/specs/2026-04-26-chempas-tutorial-design.md`

---

## File Structure

New files:

- `docs/tutorial/index.rst` — toctree landing page
- `docs/tutorial/01-overview.md` — orientation chapter (fleshed)
- `docs/tutorial/02-supercell.md` — supercell + ABBA + LNOx (fleshed)
- `docs/tutorial/03-chapman-nox.md` — placeholder chapter (stubs only)

Modified files:

- `docs/index.rst` — add `tutorial/index` to root toctree

No code changes outside `docs/`. No `conf.py` changes.

---

## Task 1: Create tutorial skeleton and wire it into the root toctree

**Files:**
- Create: `docs/tutorial/index.rst`
- Create: `docs/tutorial/01-overview.md`
- Create: `docs/tutorial/02-supercell.md` (skeleton only; sections fleshed in Tasks 2–4)
- Create: `docs/tutorial/03-chapman-nox.md`
- Modify: `docs/index.rst`

This task is structural. The supercell chapter is created with all 9 section headings, WIP banners, and figure placeholders, but no prose content yet — that lands in Tasks 2–4. The overview and Chapman + NOx chapters are fully written in this task because both are short.

- [ ] **Step 1.1: Create `docs/tutorial/index.rst`**

```rst
CheMPAS-A Tutorial
================

A hands-on walkthrough of CheMPAS-A's idealized chemistry test cases. This
tutorial complements the imported MPAS-Atmosphere User's Guide (which is a
verbatim port of the upstream MPAS v8.3.1 reference documentation) with
worked examples specific to CheMPAS-A's MUSICA/MICM coupling.

.. admonition:: Work in progress
   :class: warning

   This tutorial is being actively written. All chapters carry a
   per-section WIP banner; figures are placeholders that will be
   replaced with rendered PNGs in a later pass.

.. toctree::
   :titlesonly:
   :caption: Chapters

   01-overview
   02-supercell
   03-chapman-nox
```

- [ ] **Step 1.2: Create `docs/tutorial/01-overview.md`**

````markdown
# Chapter 1: Overview

```{admonition} Work in progress
:class: warning

This chapter is being actively written. Commands and cross-references
are provisional and may change.
```

The CheMPAS-A Tutorial walks through CheMPAS-A's idealized chemistry test
cases, the same cases driven by the numerical regression suite
(`scripts/regression.py`). Where the [User's Guide](../users-guide/index.rst)
is reference-style — a verbatim port of the upstream MPAS-Atmosphere
documentation — this tutorial is narrative: run the case, look at the
output, understand what the chemistry is doing.

## What this tutorial assumes

- `atmosphere_model` is built. See [BUILD.md](../../BUILD.md) and
  [Chapter 3 of the User's Guide](../users-guide/03-building.md).
- `~/Data/CheMPAS/<case>/` is set up with the namelist, streams, graph
  partition, and (where needed) initial-condition files. See
  [RUN.md](../../RUN.md) and `test_cases/README.md`.
- The conda environment `mpas` is available for plotting:
  `conda activate mpas`.

## Chapters

- [Chapter 2: Supercell with ABBA and LNOx](02-supercell.md) — idealized
  deep convection, run with two MUSICA/MICM mechanisms, with a
  side-by-side comparison.
- [Chapter 3: Chapman + NOx Photostationary State](03-chapman-nox.md) —
  small-domain Chapman cycle plus NOx, where the analytical PSS solution
  is a clean numerical sanity check. *(Placeholder; content coming.)*

## Verifying numerically

The tutorial focuses on what each run looks like. For numerical match
against tracked reference values, the source of truth is the regression
suite:

```bash
python scripts/regression.py run --case supercell
```

See `docs/superpowers/specs/2026-04-19-regression-suite-design.md` for
the regression suite's design.
````

- [ ] **Step 1.3: Create `docs/tutorial/02-supercell.md` (skeleton)**

Write the chapter with all 9 section headings, each containing only the
WIP banner and (where applicable) a figure placeholder. Tasks 2–4 fill
in prose and code blocks.

````markdown
# Chapter 2: Supercell with ABBA and LNOx

## 2.1 What you'll learn

```{admonition} Work in progress
:class: warning

Section content coming.
```

## 2.2 The supercell case

```{admonition} Work in progress
:class: warning

Section content coming.
```

**[Figure 2.1: Supercell initial state — potential temperature and
moisture cross-section. To be added.]**

## 2.3 Setup checklist

```{admonition} Work in progress
:class: warning

Section content coming.
```

## 2.4 Initialization

```{admonition} Work in progress
:class: warning

Section content coming.
```

## 2.5 Run with the ABBA mechanism

```{admonition} Work in progress
:class: warning

Section content coming.
```

**[Figure 2.2: qA, qB, qAB at t = 2 h, ABBA mechanism. To be added.]**

## 2.6 Run with the LNOx + O3 mechanism

```{admonition} Work in progress
:class: warning

Section content coming.
```

**[Figure 2.3: NO, NO₂, O₃ at t = 2 h, LNOx + O3 mechanism. To be added.]**

## 2.7 Comparing the two runs

```{admonition} Work in progress
:class: warning

Section content coming.
```

**[Figure 2.4: Side-by-side comparison of ABBA tracer transport and
LNOx + O3 chemistry at t = 2 h. To be added.]**

## 2.8 Verifying numerically

```{admonition} Work in progress
:class: warning

Section content coming.
```

## 2.9 Next steps

```{admonition} Work in progress
:class: warning

Section content coming.
```
````

- [ ] **Step 1.4: Create `docs/tutorial/03-chapman-nox.md`**

````markdown
# Chapter 3: Chapman + NOx Photostationary State

```{admonition} Work in progress
:class: warning

This chapter is a placeholder. The small-domain Chapman + NOx case is
the next tutorial chapter to be written.
```

The Chapman + NOx photostationary-state (PSS) tutorial walks through a
short, small-domain integration of the Chapman ozone cycle plus NOx,
where the analytical PSS expression for [NO]/[NO₂] under steady-state
photolysis is a clean numerical sanity check on the coupled
MICM + TUV-x configuration.

## 3.1 What you'll learn

**[To be added.]**

## 3.2 The Chapman + NOx case

**[To be added.]**

## 3.3 Setup checklist

**[To be added.]**

## 3.4 Initialization

**[To be added.]**

## 3.5 Run

**[To be added.]**

## 3.6 The photostationary-state diagnostic

**[To be added.]**

## 3.7 Comparing to the analytical PSS solution

**[To be added.]**

## 3.8 Verifying numerically

**[To be added.]**

## 3.9 Next steps

**[To be added.]**
````

- [ ] **Step 1.5: Update `docs/index.rst` toctree**

In `docs/index.rst`, locate the existing toctree at the bottom of the file:

```rst
.. toctree::
   :titlesonly:

   users-guide/index
   technical-description/index
```

Replace it with:

```rst
.. toctree::
   :titlesonly:

   users-guide/index
   tutorial/index
   technical-description/index
```

- [ ] **Step 1.6: Build the docs and verify the skeleton renders**

Run:

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && make html
```

Expected: build succeeds. Acceptable: pre-existing warnings carried
over from `develop`. Not acceptable: any new warning whose path
contains `tutorial/`.

If a `tutorial/`-related warning appears, read the warning text, fix
the offending file, and re-run `make html`. Common causes: missing
trailing newline, incorrect MyST admonition syntax (must use backtick
fence; `:::` is not enabled), broken cross-reference path.

- [ ] **Step 1.7: Spot-check in a browser**

```bash
open -a "Google Chrome" /Users/fillmore/EarthSystem/CheMPAS-A/docs/_build/html/tutorial/index.html
```

Verify in the rendered page:
- Sidebar shows **CheMPAS-A Tutorial** as a top-level entry between
  **CheMPAS-A User's Guide** and **MPAS-Atmosphere Technical Description**.
- Three child entries listed: Overview, Supercell with ABBA and LNOx,
  Chapman + NOx Photostationary State.
- Clicking each child loads the page; the WIP banner renders as an
  orange admonition.
- The Supercell page shows nine numbered section headings (2.1–2.9),
  each with a WIP banner; figure placeholders render as bold bracketed
  text.

- [ ] **Step 1.8: Commit**

```bash
git add docs/tutorial/ docs/index.rst
git commit -m "$(cat <<'EOF'
docs(tutorial): scaffold CheMPAS-A Tutorial section

New top-level docs/tutorial/ section with three chapters:
  - 01-overview.md: orientation and prerequisites (fleshed)
  - 02-supercell.md: skeleton with 9 sections (prose to follow)
  - 03-chapman-nox.md: placeholder for next chapter

Wired into the root index.rst toctree between users-guide/ and
technical-description/. All visible subsections carry a WIP
admonition banner; figures are textual placeholders.

Spec: docs/superpowers/specs/2026-04-26-chempas-tutorial-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Flesh out Supercell sections 2.1–2.4 (intro, case, setup, init)

**Files:**
- Modify: `docs/tutorial/02-supercell.md`

This task fills in the "set the stage" half of the chapter — the
descriptive material and prerequisites before the reader runs anything.

- [ ] **Step 2.1: Replace section 2.1 ("What you'll learn")**

Find the section 2.1 heading and its WIP-banner-only body. Replace the
body of the section (keeping the heading and the WIP banner) with:

````markdown
## 2.1 What you'll learn

```{admonition} Work in progress
:class: warning

Section content coming.
```

By the end of this chapter you will:

- Run the supercell idealized convection case in CheMPAS-A.
- Switch between two MUSICA/MICM chemistry mechanisms — the toy ABBA
  reactant set and the LNOx + O3 lightning-NOx tropospheric setup —
  by editing the `&musica` namelist block.
- Compare what tracer transport looks like in isolation (ABBA) against
  what it looks like coupled to active gas-phase chemistry and a
  lightning-NOx source (LNOx + O3).
````

- [ ] **Step 2.2: Replace section 2.2 ("The supercell case")**

````markdown
## 2.2 The supercell case

```{admonition} Work in progress
:class: warning

Section content coming.
```

The supercell test case is an idealized deep-convection setup adapted
from Klemp et al. (1978): a single rotating updraft initialized in a
horizontally homogeneous environment with strong low-level shear and a
warm bubble triggering convection. CheMPAS-A's tracked configuration
uses 60 stretched vertical levels spanning 0–50 km (~300 m at the
surface, ~1 km near the lid), a 3-second dynamics timestep, Kessler
warm-rain microphysics, and a 2-hour integration.

It is a useful chemistry testbed for two reasons. First, the rotating
updraft produces strong, well-organized vertical transport that lifts
boundary-layer tracers into the upper troposphere; the cold-pool
outflow then spreads species horizontally near the surface. Second,
the dynamics are deterministic and the chemistry adds no feedback to
the dynamics — which means a chemistry change shows up cleanly as a
chemistry-only signal, rather than confounded with a different storm
evolution.

**[Figure 2.1: Supercell initial state — potential temperature and
moisture cross-section. To be added.]**
````

- [ ] **Step 2.3: Replace section 2.3 ("Setup checklist")**

````markdown
## 2.3 Setup checklist

```{admonition} Work in progress
:class: warning

Section content coming.
```

Before you run anything, confirm:

```bash
# 1. The atmosphere_model executable exists and is from this branch.
ls -la ~/EarthSystem/CheMPAS-A/atmosphere_model

# 2. The supercell run directory is set up.
cd ~/Data/CheMPAS/supercell
ls namelist.atmosphere streams.atmosphere supercell.graph.info.part.8

# 3. The vertical-level file is in place (read by init_atmosphere_model).
ls supercell_zeta_levels.txt

# 4. The conda env is active for plotting.
conda activate mpas
python -c "import netCDF4, numpy, matplotlib; print('ok')"
```

If any of these fail, see [BUILD.md](../../BUILD.md) for the model
build, [RUN.md](../../RUN.md) for the run-directory layout, and
`test_cases/README.md` for the data download.
````

- [ ] **Step 2.4: Replace section 2.4 ("Initialization")**

````markdown
## 2.4 Initialization

```{admonition} Work in progress
:class: warning

Section content coming.
```

If `supercell_init.nc` is already in the run directory, you can skip
ahead to running the model. To regenerate the initial condition from
scratch:

```bash
cd ~/Data/CheMPAS/supercell
mpiexec -n 8 ~/EarthSystem/CheMPAS-A/init_atmosphere_model
```

This produces `supercell_init.nc`, which contains the prognostic state
on the unstructured Voronoi mesh, the stretched vertical levels read
from `supercell_zeta_levels.txt`, and the Kessler microphysics
variables.

Always run with 8 MPI ranks for the supercell case — the partition
file in the run directory (`supercell.graph.info.part.8`) is keyed to
that rank count, and a mismatched partition file causes a segfault in
the dynamics solver. See [RUN.md](../../RUN.md) for the full
rank-vs-partition table.
````

- [ ] **Step 2.5: Build and verify**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && make html
```

Expected: clean build, no new warnings under `tutorial/`. Refresh the
page in Chrome and verify sections 2.1–2.4 now show prose content
under each WIP banner, and Figure 2.1 placeholder appears at the end
of section 2.2.

- [ ] **Step 2.6: Commit**

```bash
git add docs/tutorial/02-supercell.md
git commit -m "$(cat <<'EOF'
docs(tutorial): flesh out Supercell chapter sections 2.1–2.4

Adds prose for the chapter intro, supercell case description, setup
checklist, and initialization step. Sections 2.5–2.9 (the runs and
comparison) follow in the next commit.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Flesh out Supercell sections 2.5–2.6 (ABBA and LNOx runs)

**Files:**
- Modify: `docs/tutorial/02-supercell.md`

These two sections are the heart of the chapter — both runs use the
same dynamics, differing only in the `&musica` namelist block and (for
LNOx) a one-time tracer initialization step.

The exact contents of the two `&musica` namelist variants are taken
verbatim from the commented-out templates in
`test_cases/supercell/namelist.atmosphere` (the LNOx variant) and from
`docs/chempas/results/TEST_RUNS.md` / `RUN.md` (the ABBA variant).

- [ ] **Step 3.1: Replace section 2.5 ("Run with the ABBA mechanism")**

````markdown
## 2.5 Run with the ABBA mechanism

```{admonition} Work in progress
:class: warning

Section content coming.
```

The ABBA mechanism (`micm_configs/abba.yaml`) is a toy reactant set —
qA, qB, and qAB — used as a transport-only sandbox: chemistry advances
the species, but the rate constants are chosen so that on the run
duration the field is dominated by advection rather than reaction.
This makes it a clean way to verify that tracers are being carried by
the dynamics correctly before adding real chemistry on top.

**Edit the namelist.** Open `namelist.atmosphere` in
`~/Data/CheMPAS/supercell/` and ensure the `&musica` block reads:

```fortran
&musica
    config_micm_file = 'abba.yaml'
/
```

ABBA does not need TUV-x photolysis or the lightning-NOx options, so
the block is minimal.

**Archive any prior output and run.** MPAS defaults to
`clobber_mode = never_modify`; if `output.nc` already exists the run
will silently skip all output writes. Always move the previous output
aside before re-running:

```bash
cd ~/Data/CheMPAS/supercell

timestamp=$(date +%Y%m%d_%H%M%S)
[ -f output.nc ] && mv output.nc output.${timestamp}.nc
[ -f log.atmosphere.0000.out ] && \
    mv log.atmosphere.0000.out log.atmosphere.0000.${timestamp}.out

mpiexec -n 8 ~/EarthSystem/CheMPAS-A/atmosphere_model
```

**Verify the run completed cleanly.** The tail of
`log.atmosphere.0000.out` should report zero critical errors:

```
Critical error messages = 0
```

**Plot.** With the conda env active:

```bash
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/plot_chemistry.py -o supercell_abba.png
```

**[Figure 2.2: qA, qB, qAB at t = 2 h, ABBA mechanism. To be added.]**

What to look for: qA and qB are conserved tracers transported by the
flow; qAB is produced where qA and qB co-exist. In the supercell, the
strongest gradients sit along the updraft and in the cold-pool
outflow.
````

- [ ] **Step 3.2: Replace section 2.6 ("Run with the LNOx + O3 mechanism")**

````markdown
## 2.6 Run with the LNOx + O3 mechanism

```{admonition} Work in progress
:class: warning

Section content coming.
```

The LNOx + O3 setup (`micm_configs/lnox_o3.yaml`) is a tropospheric
gas-phase configuration with three prognostic species — NO, NO₂, and
O₃ — and a parameterized lightning-NOx source term tied to the model's
vertical velocity. It is the smallest realistic chemistry case in
CheMPAS-A: enough species and reactions to exercise the MICM solver,
TUV-x photolysis, and the LNOx source coupling, without the cost of a
full tropospheric mechanism.

**Initialize the LNOx tracers.** The supercell init file does not
contain NO / NO₂ / O₃; populate them with a one-time script:

```bash
cd ~/Data/CheMPAS/supercell
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/init_lnox_o3.py -i supercell_init.nc
```

This sets NO = 0, NO₂ = 0, and O₃ = 50 ppbv (background) throughout
the domain.

**Edit the namelist.** Replace the `&musica` block in
`namelist.atmosphere` with the full LNOx tropospheric setup:

```fortran
&musica
    config_micm_file = 'lnox_o3.yaml'
    config_tuvx_config_file = 'tuvx_no2.json'
    config_tuvx_top_extension = .true.
    config_tuvx_extension_file = 'tuvx_upper_atm.csv'
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

The lightning-NOx source injects NO into grid cells where the vertical
velocity exceeds `config_lnox_w_threshold` and the height falls
between `config_lnox_z_min` and `config_lnox_z_max`. See
[docs/guides/TUVX_INTEGRATION.md](../chempas/guides/TUVX_INTEGRATION.md)
for the TUV-x configuration files referenced in the block.

**Archive prior output and run.** Same pattern as the ABBA run:

```bash
timestamp=$(date +%Y%m%d_%H%M%S)
[ -f output.nc ] && mv output.nc output.${timestamp}.nc
[ -f log.atmosphere.0000.out ] && \
    mv log.atmosphere.0000.out log.atmosphere.0000.${timestamp}.out

mpiexec -n 8 ~/EarthSystem/CheMPAS-A/atmosphere_model
```

**Plot.** The dedicated LNOx plotting script produces the standard
diagnostic set (vertical cross-sections, time series, NO₂ partitioning
ratio):

```bash
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/plot_lnox_o3.py
```

**[Figure 2.3: NO, NO₂, O₃ at t = 2 h, LNOx + O3 mechanism. To be added.]**

What to look for: a localized NO source in the updraft column where
the vertical-velocity threshold is exceeded, downwind transport of
NO + NO₂ along the anvil, and an O₃ depletion signature in the freshly
emitted plume (titration by NO).
````

- [ ] **Step 3.3: Build and verify**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && make html
```

Expected: clean build. Refresh `02-supercell.html` in Chrome and
verify sections 2.5 and 2.6 now show prose, code blocks (Fortran
namelist + bash), and the figure placeholders for Figures 2.2 and 2.3.

- [ ] **Step 3.4: Commit**

```bash
git add docs/tutorial/02-supercell.md
git commit -m "$(cat <<'EOF'
docs(tutorial): flesh out Supercell chapter sections 2.5–2.6

Adds full walk-throughs for running the supercell case with the ABBA
toy reactant set and the LNOx + O3 tropospheric setup, including the
exact &musica namelist blocks, the init_lnox_o3.py initialization step,
archive-output-before-rerun guidance, and plotting commands.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Flesh out Supercell sections 2.7–2.9 (compare, verify, next steps)

**Files:**
- Modify: `docs/tutorial/02-supercell.md`

The closing three sections — what to take away from the two runs, how
to confirm the run is numerically correct, and where to go next.

- [ ] **Step 4.1: Replace section 2.7 ("Comparing the two runs")**

````markdown
## 2.7 Comparing the two runs

```{admonition} Work in progress
:class: warning

Section content coming.
```

Placing the two final-state plots side by side highlights what's
shared and what differs. The dynamics are identical: the ABBA tracer
qAB and the LNOx tracer NO₂ are both transported by the same wind
field, so the spatial pattern of "tracer enhanced near the updraft"
matches between the two runs. The chemistry, on the other hand,
diverges. ABBA's qA + qB → qAB reaction is slow on the run duration,
so the qAB enhancement is essentially a transport signal. In the LNOx
+ O3 run the lightning-NOx source localizes NO emission to a small
volume in the updraft column, fast NO–NO₂–O₃ photochemistry
redistributes the partitioning, and an O₃-titration signature appears
where fresh NO is concentrated.

This is the pedagogical payoff of running the same dynamics with two
mechanisms: it isolates "what the flow does" from "what the chemistry
does."

**[Figure 2.4: Side-by-side comparison of ABBA tracer transport and
LNOx + O3 chemistry at t = 2 h. To be added.]**
````

- [ ] **Step 4.2: Replace section 2.8 ("Verifying numerically")**

````markdown
## 2.8 Verifying numerically

```{admonition} Work in progress
:class: warning

Section content coming.
```

Visual agreement is reassuring but not sufficient. To check that the
final-state min/max/mean of the prognostic fields match a tracked
reference, run the regression suite from the repo root:

```bash
cd ~/EarthSystem/CheMPAS-A
python scripts/regression.py run --case supercell
```

A PASS means every reference statistic in
`test_cases/supercell/regression_reference.yaml` is within the
configured relative tolerance (default `1e-3`). A FAIL prints the
offending field and its observed-vs-expected values.

The regression YAML — not this tutorial — is the source of truth for
expected numerical values. If the YAML changes (`--bless`), the
tutorial does not need to be edited.
````

- [ ] **Step 4.3: Replace section 2.9 ("Next steps")**

````markdown
## 2.9 Next steps

```{admonition} Work in progress
:class: warning

Section content coming.
```

- **The next chapter** is
  [Chapman + NOx Photostationary State](03-chapman-nox.md) — a small
  domain where the analytical PSS solution is a clean check on the
  coupled MICM + TUV-x configuration. *(Coming soon.)*
- **The MUSICA/MICM coupling internals** are documented in
  [docs/chempas/musica/MUSICA_INTEGRATION.md](../chempas/musica/MUSICA_INTEGRATION.md).
- **TUV-x photolysis** configuration is documented in
  [docs/chempas/guides/TUVX_INTEGRATION.md](../chempas/guides/TUVX_INTEGRATION.md).
- **Upstream MUSICA, MICM, and TUV-x docs** are linked from the
  [project landing page](../index.rst) in the *See also* section.
````

- [ ] **Step 4.4: Build and verify**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && make html
```

Expected: clean build. Refresh `02-supercell.html` and verify all nine
sections now show prose, the cross-references in section 2.9 resolve
(Chrome won't 404 when you click them), and Figure 2.4 placeholder
appears at the end of section 2.7.

- [ ] **Step 4.5: Commit**

```bash
git add docs/tutorial/02-supercell.md
git commit -m "$(cat <<'EOF'
docs(tutorial): flesh out Supercell chapter sections 2.7–2.9

Closes the chapter with a side-by-side comparison of the ABBA and
LNOx + O3 runs (the pedagogical payoff: same dynamics, divergent
chemistry), a pointer to scripts/regression.py for numerical
verification, and onward links to the next chapter and MUSICA/MICM
documentation.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Final build verification and browser check

**Files:** none modified.

Sanity check the whole tutorial as a unit before declaring done.

- [ ] **Step 5.1: Clean build**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && rm -rf _build && make html
```

A clean rebuild surfaces caching artifacts that an incremental build
hides. Expected: build succeeds; the only warnings are pre-existing
ones from `develop` (not under `tutorial/`).

- [ ] **Step 5.2: Compare warning count to baseline**

Capture warnings from the new build:

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs
make html 2>&1 | grep -iE "warning|error" | grep -v "^build succeeded" | tee /tmp/tutorial_warnings.txt
wc -l /tmp/tutorial_warnings.txt
```

Inspect `/tmp/tutorial_warnings.txt`. Confirm: zero entries whose path
contains `tutorial/`. (Warnings from elsewhere in the tree are
pre-existing and out of scope for this plan.)

- [ ] **Step 5.3: Browser walk-through**

```bash
open -a "Google Chrome" /Users/fillmore/EarthSystem/CheMPAS-A/docs/_build/html/index.html
```

In the rendered page, verify each item:

- The root page shows three top-level sections in the sidebar:
  CheMPAS-A User's Guide, CheMPAS-A Tutorial, MPAS-Atmosphere Technical
  Description (in that order).
- Click **CheMPAS-A Tutorial**. The landing page shows a page-level WIP
  admonition (orange) and a chapter list with three entries.
- Click **Chapter 1: Overview**. Page renders; cross-links to
  `BUILD.md`, `RUN.md`, and the User's Guide work.
- Click **Chapter 2: Supercell with ABBA and LNOx**. Page renders with
  9 numbered subsections, each carrying its own WIP banner. Code
  blocks (Fortran namelist + bash) are syntax-highlighted. All four
  figure placeholders (`**[Figure 2.N: ... To be added.]**`) appear in
  bold bracketed style.
- Click **Chapter 3: Chapman + NOx Photostationary State**. Page
  renders with a page-level WIP banner and 9 stub subsections, each
  containing only `**[To be added.]**`.

- [ ] **Step 5.4: Optional polish commit**

If any rendering issue surfaces in step 5.3 (broken cross-link,
admonition not rendering, etc.), fix it inline and commit:

```bash
git add docs/tutorial/
git commit -m "$(cat <<'EOF'
docs(tutorial): polish render issues from final review

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

If everything renders cleanly, no commit is needed — Tasks 1–4 already
committed all changes.

---

## Self-Review Notes

- Spec coverage:
  - "New top-level docs/tutorial/ section parallel to users-guide and
    technical-description" → Task 1.1, 1.5
  - "01-overview.md orienting the reader" → Task 1.2
  - "02-supercell.md fleshed out: one chapter, two mechanisms, ending
    comparison" → Tasks 1.3, 2, 3, 4
  - "03-chapman-nox.md as structural placeholder with same headings"
    → Task 1.4
  - "WIP banner at the top of every numbered subsection" → Task 1.3
    (skeleton creates them) and Tasks 2–4 (preserve them when adding
    prose)
  - "Figure placeholders in technical-description style" → Task 1.3
    (creates Figures 2.1–2.4)
  - "Build verification" → Task 5
- Placeholder scan: every step contains either an exact file path,
  exact code/markdown, or an exact command. No "TBD" / "implement
  later" / "similar to Task N" tokens.
- Type / name consistency: file paths agree across tasks
  (`docs/tutorial/02-supercell.md`); section numbers (2.1–2.9)
  agree between Task 1 (skeleton) and Tasks 2–4 (replacements);
  figure numbering (2.1–2.4) agrees between the skeleton and the
  fleshed sections.
