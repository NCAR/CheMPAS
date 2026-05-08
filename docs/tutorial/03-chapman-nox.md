# Chapter 3: Chapman + NOx Photostationary State

```{admonition} Work in progress
:class: warning

This chapter is being actively written. Commands and expected output
are provisional; figure slots are left without rendered PNGs until the
corresponding model runs and plots are archived.
```

The Chapman + NOx photostationary-state (PSS) tutorial walks through a
small-domain integration of the Chapman ozone cycle plus NOx, with
TUV-x photolysis driven by an extended atmosphere column that reaches
above the model lid. The analytical Leighton expression for [NO]/[NO₂]
under steady-state photolysis is a clean numerical sanity check on the
coupled MICM + TUV-x configuration.

## 3.1 What you'll learn

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

By the end of this chapter you will:

- Run the Chapman + NOx idealized stratospheric-chemistry case in
  CheMPAS-A on the supercell mesh.
- Generate the TUV-x upper-atmosphere extension CSV and understand
  why TUV-x needs photons from above the model lid.
- Verify the chemistry against the analytical Leighton photostationary
  state; the planned regression suite will eventually automate the
  reference-value checks.

## 3.2 The Chapman + NOx case

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
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

The MICM solver evolves all six prognostic species (O₂, O, O¹D, O₃,
NO, NO₂) every timestep — including O₃, which is produced by
O + O₂ + M → O₃ and destroyed by both photolysis and titration.
The Chapman O₃ column itself is *not* prescribed. What `init_chapman.py`
does is supply realistic *initial conditions*: starting the run from
zero would force the chemistry to build the column from scratch, which
takes hours in the upper stratosphere where jO₂ is non-negligible and
months-to-years in the lower stratosphere where the Schumann–Runge
bands are extinguished. The AFGL mid-latitude-summer climatology gets
the run close enough to a reasonable starting state that the diurnal
photochemistry the run actually demonstrates is meaningful.

The Chapman cycle is global-stratospheric physics, but
`scripts/init_chapman.py` seeds a 1-D AFGL mid-latitude-summer ozone
profile uniformly across the supercell mesh, and the chemistry has no
feedback on dynamics. This chapter therefore uses the small
(~85 km × 85 km × 50 km top) supercell grid as a column-like sandbox
— what matters is the vertical structure of the photolysis driver and
the chemistry's ability to settle into the PSS, both of which TUV-x
sees through the column extension introduced in section 3.3.
Horizontal dynamics are present but largely irrelevant to the PSS
demonstration.

**[Figure 3.1: AFGL mid-latitude-summer O₃ profile interpolated to the
supercell vertical grid (the initial state qO3 produces). To be added.]**

## 3.3 The TUV-x column extension

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
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
[docs/chempas/guides/TUVX_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/guides/TUVX_INTEGRATION.md).

## 3.4 Generating and verifying the extension CSV

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
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

## 3.5 Initializing the Chapman tracers

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

The Chapman + NOx mechanism needs six prognostic tracers seeded with
realistic vertical profiles. These are *initial conditions only* —
the MICM solver evolves all six over the run via the Chapman cycle
plus NOx reactions:

- `qO2` — uniform 0.2313 kg/kg (the dry-air O₂ mass mixing ratio).
  Effectively constant under the run; O₂ is consumed only by
  Schumann–Runge photolysis, which is small.
- `qO3` — AFGL mid-latitude-summer profile, interpolated to the MPAS
  grid (continuous with the upper-atmosphere extension at the lid).
  Starting near the climatology avoids the months-to-years
  Chapman spin-up in the lower stratosphere.
- `qO`, `qO1D` — zero (fast radicals; chemistry spins them up to
  Chapman quasi-steady-state within seconds).
- `qNO`, `qNO2` — total-NOx profile (0.05 ppb tropospheric background
  → ~10 ppb stratospheric peak around 25–35 km → drop near the lid),
  partitioned ~30 % NO / 70 % NO₂ as a near-Leighton initial guess.
  The Leighton partitioning settles within seconds; the total NOx
  burden is preserved over the run.

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

## 3.6 Run with the Chapman + NOx mechanism

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
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

## 3.7 The photostationary-state diagnostic

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
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

**The Leighton curve** is what you get when you evaluate the right-hand
side of the expression above at every level of the column: it's the
analytical [NO]/[NO₂] partitioning the simple two-reaction system
*should* settle to, given the local jNO₂ and [O₃]. Plotting the
simulated NO/NO₂ ratio alongside the Leighton curve (Figure 3.4 in
§3.8 and the bottom-left panel of the standalone column-model plot in
§3.10) is a direct visual check on the photolysis–titration balance.
Where the two curves agree, the chemistry is at PSS as expected; where
they diverge, either the system hasn't relaxed yet, or some other
reaction the simple expression doesn't capture is perturbing the
partitioning (in the chapman_nox mechanism, the small additional
contribution from O / O¹D photochemistry shows up as a few-tens-of-
percent offset in the stratosphere).

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

## 3.8 Verifying numerically

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

Two complementary checks.

**Regression suite.** The planned regression suite will eventually
provide a source-of-truth numerical check for this case, but the
`scripts/regression.py` entry point and reference YAML files are not
present in this branch yet. See
`docs/superpowers/specs/2026-04-19-regression-suite-design.md` for the
design.

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
    # The TUV-x photolysis-rate variable name is `j_jNO2` per the
    # CheMPAS-A Registry (the `j_j*` prefix is intentional). Confirm
    # with `ncdump -h output.nc | grep -i jno2` if a build differs.
    jNO2 = ds['j_jNO2'][-1]

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

## 3.9 Next steps

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

- **The MUSICA/MICM coupling internals** are documented in
  [docs/chempas/musica/MUSICA_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/musica/MUSICA_INTEGRATION.md).
- **TUV-x integration engineering** (the integration story behind
  `mpas_tuvx.F` and the column extension) is documented in
  [docs/chempas/guides/TUVX_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/guides/TUVX_INTEGRATION.md).
- **Upstream MUSICA, MICM, and TUV-x docs** are linked from the
  [project landing page](../index.rst) in the *See also* section.
- **The next chapter** is
  [Chapman + NOx Global](04-chapman-nox-global.md) — the same
  chemistry on the `x1.40962` global mesh, where the day–night
  photolysis terminator and zonal-mean ozone response become visible.
- **Further idealized cases** (mountain wave, chem box) will be added
  when their tutorial chapters are written. *(Not yet scheduled.)*

## 3.10 Standalone Chapman + NOx column model

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

The standalone counterpart of this whole chapter — same
`chapman_nox.yaml` MICM mechanism, TUV-x photolysis on a vertical
column, no MPAS in the loop. `scripts/musica_python/chapman_nox_column.py`
loads MUSICA's bundled `vTS1` TUV-x calculator (which provides jO₂,
jO₃→O, jO₃→O¹D, jNO₂), maps its TS1 reaction labels to
`chapman_nox.yaml`'s `PHOTO.*` parameter names via a small alias table
in the script, and runs a 12-hour diurnal cycle starting at 06:00
local at the supercell case's nominal lat/lon (Norman, OK). The
column grid is whatever vTS1 dictates — independent of the MPAS mesh
and of the upper-atmosphere extension introduced in §3.3.

Initial profiles come from `scripts/init_chapman.py`'s helpers (AFGL
mid-latitude-summer O₃, total NOx with daytime 30/70 NO/NO₂
partitioning), so the standalone column starts from the same vertical
distribution the CheMPAS-A run does.

Pre-req: see Chapter 1's [Python environment for standalone
examples](01-overview.md) section.

Run:

```bash
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/musica_python/chapman_nox_column.py
```

**[Figure 3.5: Standalone Chapman + NOx column model — solar-noon O₃
profile, solar-noon NO and NO₂ profiles, simulated vs. analytical
Leighton ratio with height, and O₃ time series at 10 / 30 / 45 km. To
be added.]**

What to look for: simulated NO/NO₂ ratio in the stratospheric
column tracks the analytical Leighton expression (the same one
§3.7 motivates) to within a factor of ~1.3 — close enough to
confirm the photolysis–titration balance qualitatively, with the
residual reflecting the O / O¹D coupling the simple [NO]/[NO₂]
formula omits. The O₃ mixing-ratio profile peaks at ~6 ppm near
~42 km (consistent with the AFGL mid-latitude-summer
climatology used by `init_chapman.py`; tropical and US-standard
profiles peak higher, closer to 8–10 ppm). The O₃ *number-density*
peak sits lower in the column, near ~20 km, because air density
falls off faster than mixing ratio rises — a classic stratospheric
O₃ feature. The 12-hour run captures the diurnal SZA cycle from
predawn (SZA ≈ 99°) through solar noon (SZA ≈ 22°) to late
afternoon, so the photolysis-driven O₃ modulation (~10 % swing
at 30 km in the time-series panel) is visible across the column. An independent
numerical check on the same chemistry the chapter's MPAS-coupled
run exercises.
