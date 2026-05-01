# CheMPAS-A Tutorial Chapter 3 (Chapman + NOx) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Chapter 3 placeholder (`docs/tutorial/03-chapman-nox.md`, nine `**[To be added.]**` stubs from the 2026-04-26 tutorial-scaffold pass) with a fleshed-out chapter covering the small-domain Chapman + NOx photostationary-state (PSS) tutorial, integrating the TUV-x extended atmosphere column as a prerequisite topic.

**Architecture:** A single Markdown chapter file under `docs/tutorial/`, mirroring Chapter 2's structure (one chapter, nine numbered subsections, each wearing the WIP admonition banner). The chapter reuses `~/Data/CheMPAS/supercell/` as the run directory and walks the reader through column-extension generation → tracer initialization → namelist swap → run → PSS diagnostic → verification.

**Tech Stack:** Sphinx, MyST parser. Admonitions use backtick-fenced ``` ```{admonition} ``` ``` syntax (the `colon_fence` extension is NOT enabled). Math expressions use the `dollarmath` extension (which IS enabled). Code blocks use `bash`, `fortran`, and `python` language tags. Figure placeholders follow the technical-description style `**[Figure 3.N: caption. To be added.]**`.

**Spec:** `docs/superpowers/specs/2026-04-26-chapman-nox-tutorial-design.md`

---

## File Structure

Modified file (only):

- `docs/tutorial/03-chapman-nox.md` — entire body replaced.

No other files touched. No `conf.py` changes. No new files created.

---

## Task 1: Replace the placeholder with a fully-banner-stamped skeleton

**Files:**
- Modify: `docs/tutorial/03-chapman-nox.md` (entire-file replacement)

This task wipes the existing nine `**[To be added.]**` placeholder and writes a clean skeleton: chapter title, brief page-level intro, all nine numbered sections with WIP banners, and four figure placeholders in the right sections (3.2, 3.4, 3.6, 3.8). Tasks 2–5 fill prose under each WIP banner.

- [ ] **Step 1.1: Replace the entire file**

Use the Write tool (it overwrites). The new content of `/Users/fillmore/EarthSystem/CheMPAS-A/docs/tutorial/03-chapman-nox.md` is exactly:

````markdown
# Chapter 3: Chapman + NOx Photostationary State

```{admonition} Work in progress
:class: warning

This chapter is being actively written. Commands and expected output
are provisional; figures are placeholders.
```

The Chapman + NOx photostationary-state (PSS) tutorial walks through a
small-domain integration of the Chapman ozone cycle plus NOx, with
TUV-x photolysis driven by an extended atmosphere column that reaches
above the model lid. The analytical Leighton expression for [NO]/[NO₂]
under steady-state photolysis is a clean numerical sanity check on the
coupled MICM + TUV-x configuration.

## 3.1 What you'll learn

```{admonition} Work in progress
:class: warning

Section content coming.
```

## 3.2 The Chapman + NOx case

```{admonition} Work in progress
:class: warning

Section content coming.
```

**[Figure 3.1: AFGL mid-latitude-summer O₃ profile interpolated to the
supercell vertical grid (the initial state qO3 produces). To be added.]**

## 3.3 The TUV-x column extension

```{admonition} Work in progress
:class: warning

Section content coming.
```

## 3.4 Generating and verifying the extension CSV

```{admonition} Work in progress
:class: warning

Section content coming.
```

**[Figure 3.2: Stitched T, n_air, and n_O₃ vertical profiles from
mpas_tuvx.F. MPAS region (below 50 km) and extension-CSV region
(above 50 km) overplotted. To be added.]**

## 3.5 Initializing the Chapman tracers

```{admonition} Work in progress
:class: warning

Section content coming.
```

## 3.6 Run with the Chapman + NOx mechanism

```{admonition} Work in progress
:class: warning

Section content coming.
```

**[Figure 3.3: Vertical profiles of qO3, qNO, qNO2, and the NO/NO₂
ratio at t = 2 h, mid-domain column, Chapman + NOx mechanism. To be
added.]**

## 3.7 The photostationary-state diagnostic

```{admonition} Work in progress
:class: warning

Section content coming.
```

## 3.8 Verifying numerically

```{admonition} Work in progress
:class: warning

Section content coming.
```

**[Figure 3.4: Simulated vs. analytical Leighton [NO]/[NO₂] ratio vs.
height at the final timestep. To be added.]**

## 3.9 Next steps

```{admonition} Work in progress
:class: warning

Section content coming.
```
````

(Note: the outer 4-backtick fence in this plan is just a wrapper so you can see the file content. The actual file starts with `# Chapter 3:` and ends at the closing triple-backtick of section 3.9's WIP admonition followed by a trailing newline.)

- [ ] **Step 1.2: Build and verify**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && make html
```

Acceptable: pre-existing warnings (~111 across the develop baseline). NOT acceptable: any new warning whose path contains `tutorial/`. Verify with:

```bash
make html 2>&1 | grep -iE "warning|error" | grep -i "tutorial/" || echo "no tutorial warnings"
```

- [ ] **Step 1.3: Verify the rendered HTML**

Confirm the rebuilt page exists:

```bash
ls -la /Users/fillmore/EarthSystem/CheMPAS-A/docs/_build/html/tutorial/03-chapman-nox.html
```

The file should exist and `wc -l` of the rendered HTML should be substantially larger than the prior placeholder (the new skeleton has more structure: nine WIP admonitions and four figure placeholders).

- [ ] **Step 1.4: Commit**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A
git add docs/tutorial/03-chapman-nox.md
git commit -m "$(cat <<'EOF'
docs(tutorial): rewrite Chapter 3 placeholder with WIP-stamped skeleton

Replaces the nine "[To be added.]" stubs in the original placeholder
with a clean skeleton matching Chapter 2's pattern: chapter title,
brief page-level intro, nine numbered subsections each carrying a
WIP banner, and four figure placeholders in sections 3.2, 3.4, 3.6,
and 3.8. Section prose follows in subsequent commits.

Spec: docs/superpowers/specs/2026-04-26-chapman-nox-tutorial-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Flesh sections 3.1 and 3.2 (intro and case description)

**Files:**
- Modify: `docs/tutorial/03-chapman-nox.md`

- [ ] **Step 2.1: Replace section 3.1 ("What you'll learn")**

Find the section 3.1 heading and its WIP-banner-only body. The whole section currently reads:

````markdown
## 3.1 What you'll learn

```{admonition} Work in progress
:class: warning

Section content coming.
```
````

Replace with:

````markdown
## 3.1 What you'll learn

```{admonition} Work in progress
:class: warning

Section content coming.
```

By the end of this chapter you will:

- Run the Chapman + NOx idealized stratospheric-chemistry case in
  CheMPAS-A on the supercell mesh.
- Generate the TUV-x upper-atmosphere extension CSV and understand
  why TUV-x needs photons from above the model lid.
- Verify the chemistry against the analytical Leighton photostationary
  state and the regression suite.
````

- [ ] **Step 2.2: Replace section 3.2 ("The Chapman + NOx case")**

The whole section currently reads:

````markdown
## 3.2 The Chapman + NOx case

```{admonition} Work in progress
:class: warning

Section content coming.
```

**[Figure 3.1: AFGL mid-latitude-summer O₃ profile interpolated to the
supercell vertical grid (the initial state qO3 produces). To be added.]**
````

Replace with:

````markdown
## 3.2 The Chapman + NOx case

```{admonition} Work in progress
:class: warning

Section content coming.
```

The Chapman cycle is the canonical four-reaction pure-oxygen
photochemistry that maintains a stratospheric ozone column:

$$
\begin{aligned}
\mathrm{O_2} + h\nu &\rightarrow 2\,\mathrm{O} \\
\mathrm{O} + \mathrm{O_2} + \mathrm{M} &\rightarrow \mathrm{O_3} + \mathrm{M} \\
\mathrm{O_3} + h\nu &\rightarrow \mathrm{O} + \mathrm{O_2} \\
\mathrm{O} + \mathrm{O_3} &\rightarrow 2\,\mathrm{O_2}
\end{aligned}
$$

Adding NOx introduces the catalytic
NO–NO₂–O₃ cycle (NO + O₃ → NO₂ + O₂; NO₂ + hν → NO + O), which
modulates ozone titration by tying its evolution to NOx photolysis.
On any timescale longer than a few seconds, [NO] / [NO₂] in sunlight
relaxes to the **Leighton photostationary state**, the analytical
target of section 3.7.

The Chapman cycle is global-stratospheric physics, but
`scripts/init_chapman.py` seeds a 1-D AFGL mid-latitude-summer ozone
profile uniformly across the supercell mesh, and the chemistry has no
feedback on dynamics. This chapter therefore uses the small
(~30 km × 30 km × 50 km top) supercell grid as a column-like sandbox
— what matters is the vertical structure of the photolysis driver and
the chemistry's ability to settle into the PSS, both of which TUV-x
sees through the column extension introduced in section 3.3.
Horizontal dynamics are present but largely irrelevant to the PSS
demonstration.

**[Figure 3.1: AFGL mid-latitude-summer O₃ profile interpolated to the
supercell vertical grid (the initial state qO3 produces). To be added.]**
````

- [ ] **Step 2.3: Build and verify**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && make html 2>&1 | grep -iE "warning|error" | grep -i "tutorial/" || echo "no tutorial warnings"
```

Expected: no tutorial-pathed warnings. The math block uses `dollarmath` (enabled in `conf.py`), so `$$ ... $$` should render.

- [ ] **Step 2.4: Commit**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A
git add docs/tutorial/03-chapman-nox.md
git commit -m "$(cat <<'EOF'
docs(tutorial): flesh out Chapman chapter sections 3.1–3.2

Adds prose for the chapter intro and the Chapman + NOx case
description: the four canonical Chapman reactions (rendered as a
math block via dollarmath), the catalytic NO–NO₂–O₃ cycle, and the
rationale for using the supercell mesh as a column-like sandbox for
this global-stratospheric chemistry.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Flesh sections 3.3 and 3.4 (TUV-x column extension)

**Files:**
- Modify: `docs/tutorial/03-chapman-nox.md`

- [ ] **Step 3.1: Replace section 3.3 ("The TUV-x column extension")**

The whole section currently reads:

````markdown
## 3.3 The TUV-x column extension

```{admonition} Work in progress
:class: warning

Section content coming.
```
````

Replace with:

````markdown
## 3.3 The TUV-x column extension

```{admonition} Work in progress
:class: warning

Section content coming.
```

The MPAS atmosphere lid for the supercell case sits at 50 km — that's
roughly stratopause level, but Chapman-cycle photolysis depends on UV
radiation that has already been attenuated by the entire ozone column
*above* the photolysis cell, including the ~50–100 km region MPAS
itself does not simulate. Without an extension, TUV-x sees vacuum
above 50 km, jO₃ and jNO₂ are off by a non-trivial factor at high
altitudes, and the Chapman steady state never establishes properly.

The fix is `micm_configs/tuvx_upper_atm.csv`: a tracked CSV carrying
temperature, air number density, and ozone number density on a
uniform 5-km grid from 50 to 100 km. The temperature and air values
come from the US Standard Atmosphere 1976 tables; the ozone values
come from the AFGL mid-latitude-summer constituent profile. At
runtime, `mpas_tuvx.F::load_extension_csv` stitches MPAS midpoint
values (lower slice) and CSV midpoint values (upper slice) into a
single radiator column for TUV-x, blending across the boundary so
the profile is continuous.

The stitch lives in `src/core_atmosphere/chemistry/mpas_tuvx.F`; for
the broader integration story, see
[docs/chempas/guides/TUVX_INTEGRATION.md](../chempas/guides/TUVX_INTEGRATION.md).
````

- [ ] **Step 3.2: Replace section 3.4 ("Generating and verifying the extension CSV")**

The whole section currently reads:

````markdown
## 3.4 Generating and verifying the extension CSV

```{admonition} Work in progress
:class: warning

Section content coming.
```

**[Figure 3.2: Stitched T, n_air, and n_O₃ vertical profiles from
mpas_tuvx.F. MPAS region (below 50 km) and extension-CSV region
(above 50 km) overplotted. To be added.]**
````

Replace with:

````markdown
## 3.4 Generating and verifying the extension CSV

```{admonition} Work in progress
:class: warning

Section content coming.
```

**Generate the CSV.** The generator is parameterized but defaults to
the configuration the runtime expects (50–100 km, 10 layers, 5-km
spacing). Run:

```bash
cd ~/EarthSystem/CheMPAS-A
~/miniconda3/envs/mpas/bin/python \
    scripts/gen_tuvx_upper_atm.py --out micm_configs/tuvx_upper_atm.csv
```

The script emits a header line followed by one row per edge with
columns `z_km, T_K, n_air_molec_cm3, n_O3_molec_cm3`. The output path
must match the `config_tuvx_extension_file` value in the namelist
(set in section 3.6 below).

**Verify the stitched column.** The companion plotter overlays the
MPAS region with the extension-CSV region as TUV-x actually sees
them, including the edge-blending the runtime applies at the 50-km
boundary:

```bash
cd ~/Data/CheMPAS/supercell
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/plot_extension_profiles.py \
    -i output.nc
```

Note: this verification requires an `output.nc` from a CheMPAS-A run.
You can run it now against any prior supercell `output.nc` (for
example, the LNOx run from Chapter 2) just to inspect the column
shape, and then run it again after the Chapman + NOx run lands in
section 3.6 below to see the stitched column the actual run used.

**[Figure 3.2: Stitched T, n_air, and n_O₃ vertical profiles from
mpas_tuvx.F. MPAS region (below 50 km) and extension-CSV region
(above 50 km) overplotted. To be added.]**
````

- [ ] **Step 3.3: Build and verify**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && make html 2>&1 | grep -iE "warning|error" | grep -i "tutorial/" || echo "no tutorial warnings"
```

Expected: no tutorial-pathed warnings. The cross-link to `../chempas/guides/TUVX_INTEGRATION.md` should resolve cleanly (this same link works in `02-supercell.md`).

- [ ] **Step 3.4: Commit**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A
git add docs/tutorial/03-chapman-nox.md
git commit -m "$(cat <<'EOF'
docs(tutorial): flesh out Chapman chapter sections 3.3–3.4

Adds the TUV-x column-extension content: section 3.3 explains why
the extension exists (Chapman photolysis depends on UV that has been
attenuated by the column above the model lid; without an extension,
TUV-x sees vacuum above 50 km and jO₃, jNO₂ are wrong); section 3.4
walks through the gen_tuvx_upper_atm.py and plot_extension_profiles.py
commands to generate and verify the CSV.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Flesh sections 3.5 and 3.6 (initialize and run)

**Files:**
- Modify: `docs/tutorial/03-chapman-nox.md`

- [ ] **Step 4.1: Replace section 3.5 ("Initializing the Chapman tracers")**

The whole section currently reads:

````markdown
## 3.5 Initializing the Chapman tracers

```{admonition} Work in progress
:class: warning

Section content coming.
```
````

Replace with:

````markdown
## 3.5 Initializing the Chapman tracers

```{admonition} Work in progress
:class: warning

Section content coming.
```

The Chapman + NOx mechanism needs six tracers seeded with realistic
vertical profiles:

- `qO2` — uniform 0.2313 kg/kg (the dry-air O₂ mass mixing ratio)
- `qO3` — AFGL mid-latitude-summer profile, interpolated to the MPAS
  grid (continuous with the upper-atmosphere extension at the lid)
- `qO`, `qO1D` — zero (fast radicals; chemistry spins them up within
  seconds)
- `qNO`, `qNO2` — total-NOx profile (0.05 ppb tropospheric background
  → ~10 ppb stratospheric peak around 25–35 km → drop near the lid),
  partitioned ~30 % NO / 70 % NO₂ as a near-Leighton initial guess

`scripts/init_chapman.py` writes these six tracers into
`supercell_init.nc`:

```bash
cd ~/Data/CheMPAS/supercell
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/init_chapman.py
```

Note: this rewrites tracers in `supercell_init.nc` in place. If
you've been running the supercell + LNOx case from Chapter 2 and
plan to switch back, copy `supercell_init.nc` aside first or be
prepared to re-run `init_atmosphere_model` to regenerate it.
````

- [ ] **Step 4.2: Replace section 3.6 ("Run with the Chapman + NOx mechanism")**

The whole section currently reads:

````markdown
## 3.6 Run with the Chapman + NOx mechanism

```{admonition} Work in progress
:class: warning

Section content coming.
```

**[Figure 3.3: Vertical profiles of qO3, qNO, qNO2, and the NO/NO₂
ratio at t = 2 h, mid-domain column, Chapman + NOx mechanism. To be
added.]**
````

Replace with:

````markdown
## 3.6 Run with the Chapman + NOx mechanism

```{admonition} Work in progress
:class: warning

Section content coming.
```

**Edit the namelist.** Replace the `&musica` block in
`~/Data/CheMPAS/supercell/namelist.atmosphere` with the Chapman + NOx
configuration:

```fortran
&musica
    config_micm_file = 'chapman_nox.yaml'
    config_tuvx_config_file = 'tuvx_chapman_nox.json'
    config_tuvx_top_extension = .true.
    config_tuvx_extension_file = 'tuvx_upper_atm.csv'
    config_chemistry_latitude = 35.86
    config_chemistry_longitude = -97.93
/
```

Six fields, no LNOx source terms — Chapman has no lightning channel.
The `tuvx_chapman_nox.json` photolysis configuration provides the
four rates the mechanism consumes (jO₂, jO₃→O, jO₃→O¹D, jNO₂); its
description in the JSON file says explicitly that it pairs with
`chapman_nox.yaml`.

**Archive prior output and run.** Same pattern as the Chapter 2
supercell runs:

```bash
timestamp=$(date +%Y%m%d_%H%M%S)
[ -f output.nc ] && mv output.nc output.${timestamp}.nc
[ -f log.atmosphere.0000.out ] && \
    mv log.atmosphere.0000.out log.atmosphere.0000.${timestamp}.out

mpiexec -n 8 ~/EarthSystem/CheMPAS-A/atmosphere_model
```

Verify the run completed cleanly by checking the tail of
`log.atmosphere.0000.out`:

```
Critical error messages = 0
```

**Plot.** `scripts/plot_chemistry_profiles.py` produces
horizontal-mean vertical profiles of the Chapman + NOx species and
the four photolysis rates:

```bash
cd ~/Data/CheMPAS/supercell
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/plot_chemistry_profiles.py
```

Panels: O₃, NO, NO₂ in ppb; atomic oxygen O = qO + qO1D summed;
photolysis rates jO₂, jO₃→O, jO₃→O¹D, jNO₂ in s⁻¹.

**[Figure 3.3: Vertical profiles of qO3, qNO, qNO2, and the NO/NO₂
ratio at t = 2 h, mid-domain column, Chapman + NOx mechanism. To be
added.]**

What to look for: O₃ and NOx maxima in the seeded stratospheric
layer (~25–35 km); jNO₂ rising sharply with altitude as the column
above thins; NO/NO₂ ratio settling to a height-dependent Leighton
value within the first few model timesteps (the reader will check
this analytically in section 3.8).
````

- [ ] **Step 4.3: Build and verify**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && make html 2>&1 | grep -iE "warning|error" | grep -i "tutorial/" || echo "no tutorial warnings"
```

Expected: no tutorial-pathed warnings. The Fortran namelist block should syntax-highlight cleanly.

- [ ] **Step 4.4: Commit**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A
git add docs/tutorial/03-chapman-nox.md
git commit -m "$(cat <<'EOF'
docs(tutorial): flesh out Chapman chapter sections 3.5–3.6

Section 3.5 documents the six tracers init_chapman.py seeds (qO2,
qO3 AFGL profile, qO/qO1D zeros, qNO/qNO2 with stratospheric NOx
peak and ~30/70 daytime partitioning) and the rewrite-in-place
caveat for readers switching from the LNOx case. Section 3.6 gives
the chapman_nox.yaml + tuvx_chapman_nox.json &musica block, the
archive-and-rerun pattern matching Chapter 2, and points readers
at scripts/plot_chemistry_profiles.py for the standard
diagnostic panel set.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Flesh sections 3.7, 3.8, 3.9 (PSS diagnostic, verify, next steps)

**Files:**
- Modify: `docs/tutorial/03-chapman-nox.md`

- [ ] **Step 5.1: Replace section 3.7 ("The photostationary-state diagnostic")**

The whole section currently reads:

````markdown
## 3.7 The photostationary-state diagnostic

```{admonition} Work in progress
:class: warning

Section content coming.
```
````

Replace with:

````markdown
## 3.7 The photostationary-state diagnostic

```{admonition} Work in progress
:class: warning

Section content coming.
```

In sunlight, the NO–NO₂–O₃ system relaxes within seconds to a steady
state where NO₂ photolysis (NO₂ + hν → NO + O, rate jNO₂) is balanced
by the reverse NO + O₃ titration. This is the **Leighton
photostationary state**:

$$
\frac{[\mathrm{NO}]}{[\mathrm{NO_2}]}
= \frac{j_{\mathrm{NO_2}}}{k_{\mathrm{NO+O_3}}\,[\mathrm{O_3}]}
$$

where the temperature-dependent reaction rate

$$
k_{\mathrm{NO+O_3}}(T)
= 1.7\times10^{-12}\,\exp\!\left(-\frac{1310}{T}\right)
\;\;\text{cm}^3\,\text{molec}^{-1}\,\text{s}^{-1}
$$

comes from JPL kinetics.

**Where it should hold.** In the seeded stratospheric NOx peak layer
(~25–35 km), photolysis is strong, [O₃] is high, and the partitioning
relaxation timescale is seconds — well below the 3-second model
timestep. Simulated [NO]/[NO₂] there should track the Leighton
expression to within a few percent after the first few minutes of
model time.

**Where it shouldn't.** Near the surface in shadow or in the lowest
model layers where the photolysis driver is weak, the PSS expression
loses meaning — jNO₂ → 0 makes the ratio diverge analytically while
the simulated NOx is just sitting at its initial conditions.
Spin-up note: 10–15 minutes of model time is plenty for partitioning
to settle in the stratospheric column.
````

- [ ] **Step 5.2: Replace section 3.8 ("Verifying numerically")**

The whole section currently reads:

````markdown
## 3.8 Verifying numerically

```{admonition} Work in progress
:class: warning

Section content coming.
```

**[Figure 3.4: Simulated vs. analytical Leighton [NO]/[NO₂] ratio vs.
height at the final timestep. To be added.]**
````

Replace with:

````markdown
## 3.8 Verifying numerically

```{admonition} Work in progress
:class: warning

Section content coming.
```

Two complementary checks.

**Regression suite.** The same source-of-truth used in Chapter 2:

```bash
cd ~/EarthSystem/CheMPAS-A
python scripts/regression.py run --case supercell
```

A PASS means every reference statistic in
`test_cases/supercell/regression_reference.yaml` is within the
configured relative tolerance (default `1e-3`). The regression YAML
— not this tutorial — is the source of truth for expected numerical
values.

**Analytical PSS check.** Pull jNO₂, [O₃], [NO], [NO₂] from
`output.nc` at the final timestep and compare the simulated ratio
against Leighton:

```python
import numpy as np
from netCDF4 import Dataset

# JPL kinetics for NO + O3 -> NO2 + O2 at a representative
# stratospheric temperature.
A, Ea_R, T_ref = 1.7e-12, 1310.0, 230.0
k_NO_O3 = A * np.exp(-Ea_R / T_ref)

with Dataset('output.nc') as ds:
    qNO  = ds['qNO'][-1]
    qNO2 = ds['qNO2'][-1]
    qO3  = ds['qO3'][-1]
    # The TUV-x photolysis-rate variable name written by mpas_tuvx.F
    # may differ between builds; check `ncdump -h output.nc | grep -i no2`
    # to confirm. Common forms: 'j_NO2', 'photolysis_rate_NO2'.
    jNO2 = ds['j_NO2'][-1]

# Leighton: [NO]/[NO2] = jNO2 / (k * [O3]). The mass-mixing-ratio
# version is up to a per-cell unit factor; for a stratospheric
# layer where the factor is approximately constant, the ratio
# comparison is meaningful.
leighton = jNO2 / np.maximum(k_NO_O3 * qO3, 1e-30)
sim     = qNO / np.maximum(qNO2, 1e-30)
print('median ratio agreement (sim / Leighton):',
      float(np.nanmedian(sim / leighton)))
```

Pass criterion: ratio agreement to within ~5 % in the stratospheric
layer (looser than the regression-suite tolerance because the PSS
isn't bit-exact and the constant-T approximation here introduces a
small bias).

**[Figure 3.4: Simulated vs. analytical Leighton [NO]/[NO₂] ratio vs.
height at the final timestep. To be added.]**
````

- [ ] **Step 5.3: Replace section 3.9 ("Next steps")**

The whole section currently reads:

````markdown
## 3.9 Next steps

```{admonition} Work in progress
:class: warning

Section content coming.
```
````

Replace with:

````markdown
## 3.9 Next steps

```{admonition} Work in progress
:class: warning

Section content coming.
```

- **The MUSICA/MICM coupling internals** are documented in
  [docs/chempas/musica/MUSICA_INTEGRATION.md](../chempas/musica/MUSICA_INTEGRATION.md).
- **TUV-x integration engineering** (the integration story behind
  `mpas_tuvx.F` and the column extension) is documented in
  [docs/chempas/guides/TUVX_INTEGRATION.md](../chempas/guides/TUVX_INTEGRATION.md).
- **Upstream MUSICA, MICM, and TUV-x docs** are linked from the
  [project landing page](../index.rst) in the *See also* section.
- **Future tutorial chapters** will cover additional idealized cases
  (mountain wave, JW baroclinic wave, chem box) when they're
  written. *(Not yet scheduled.)*
````

- [ ] **Step 5.4: Build and verify**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && make html 2>&1 | grep -iE "warning|error" | grep -i "tutorial/" || echo "no tutorial warnings"
```

Expected: no tutorial-pathed warnings. The Python code block should syntax-highlight; the math blocks (sections 3.7 has two `$$ ... $$` displays) should render via `dollarmath`.

- [ ] **Step 5.5: Commit**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A
git add docs/tutorial/03-chapman-nox.md
git commit -m "$(cat <<'EOF'
docs(tutorial): flesh out Chapman chapter sections 3.7–3.9

Section 3.7 documents the Leighton photostationary state with two
math-block expressions (the [NO]/[NO2] ratio and the JPL k_{NO+O3}(T)
form) and explains where the PSS does and does not hold in the
modeled column. Section 3.8 gives both the regression-suite invocation
and an inline ~20-line Python snippet that pulls jNO2, qO3, qNO, qNO2
from output.nc and compares the simulated ratio to the analytical
Leighton expression. Section 3.9 closes with onward links to the
MUSICA/MICM/TUV-x docs and a one-line note on future tutorial
chapters.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Final clean build + Chrome verify

**Files:** none modified.

- [ ] **Step 6.1: Clean build**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && rm -rf _build && make html
```

Expected: build succeeds; warnings carry the develop baseline; zero
warnings under `tutorial/`.

- [ ] **Step 6.2: Compare warning count to baseline**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs
make html 2>&1 | grep -iE "warning|error" | grep -i "tutorial/" | tee /tmp/chap3_warnings.txt
wc -l /tmp/chap3_warnings.txt
```

Confirm the line count is 0.

- [ ] **Step 6.3: Browser walk-through**

```bash
open -a "Google Chrome" /Users/fillmore/EarthSystem/CheMPAS-A/docs/_build/html/tutorial/03-chapman-nox.html
```

In the rendered page, verify:

- The page-level WIP admonition (orange) appears at the top.
- Nine numbered subsections (3.1–3.9), each carrying its own WIP
  banner.
- The math blocks in sections 3.2 and 3.7 render (the four-reaction
  Chapman cycle in 3.2; the two Leighton expressions in 3.7).
- The Fortran namelist block in section 3.6 is syntax-highlighted.
- The Python code block in section 3.8 is syntax-highlighted.
- All four figure placeholders (Figures 3.1–3.4) appear in bold
  bracketed style in sections 3.2, 3.4, 3.6, 3.8.
- The cross-links in sections 3.3 and 3.9 (to TUVX_INTEGRATION.md,
  MUSICA_INTEGRATION.md, and the root index) all resolve when
  clicked.
- Sidebar: **CheMPAS-A Tutorial** still has three child entries; the
  Chapman + NOx page is now substantive (no longer a `[To be added.]`
  stub page).

- [ ] **Step 6.4: Optional polish commit**

If any rendering issue surfaces in Step 6.3 (math expression doesn't render, syntax highlighting wrong, broken cross-link), fix inline and commit:

```bash
git add docs/tutorial/03-chapman-nox.md
git commit -m "$(cat <<'EOF'
docs(tutorial): polish Chapter 3 render issues from final review

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

If everything renders cleanly, no commit is needed — Tasks 1–5 already committed all changes.

---

## Self-Review Notes

- Spec coverage:
  - Skeleton with WIP banners and figure placeholders → Task 1
  - Section 3.1 (What you'll learn) and 3.2 (case description, including supercell-domain rationale and Figure 3.1) → Task 2
  - Section 3.3 (column-extension concept) and 3.4 (gen + verify, with Figure 3.2) → Task 3
  - Section 3.5 (init_chapman.py + six tracers documented) and 3.6 (chapman_nox.yaml + tuvx_chapman_nox.json namelist + run + plot, with Figure 3.3) → Task 4
  - Section 3.7 (Leighton PSS with math blocks) and 3.8 (regression suite + analytical snippet, with Figure 3.4) and 3.9 (forward links) → Task 5
  - Build verification (clean rebuild + browser walk-through) → Task 6
- Placeholder scan: all "Section content coming." text comes from the WIP-banner template (this is the user's explicit convention, not a plan failure). Otherwise no "TBD" / "implement later" tokens.
- Type / name consistency:
  - Section numbers (3.1–3.9) consistent across Tasks 1–5.
  - Figure numbers (3.1–3.4) consistent: Figure 3.1 in 3.2, 3.2 in 3.4, 3.3 in 3.6, 3.4 in 3.8.
  - Mechanism file pairing consistent: `chapman_nox.yaml` ↔ `tuvx_chapman_nox.json` everywhere it's referenced.
  - Variable names in the analytical-PSS Python snippet (`qNO`, `qNO2`, `qO3`, `j_NO2`) match the MPAS tracer-naming convention (`q` prefix for advected mass mixing ratio); the snippet has an explicit `ncdump -h` caveat for the photolysis-rate variable name in case the actual output.nc differs.
  - Run-directory references consistent: all commands operate from either `~/Data/CheMPAS/supercell/` or `~/EarthSystem/CheMPAS-A/`.
