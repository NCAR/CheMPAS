# Chapter 2: Supercell with ABBA and LNOx

## 2.1 What you'll learn

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

By the end of this chapter you will:

- Run the supercell idealized convection case in CheMPAS-A.
- Switch between two MUSICA/MICM chemistry mechanisms — the toy ABBA
  reactant set and the LNOx + O3 lightning-NOx tropospheric setup —
  by editing the `&musica` namelist block.
- Compare what tracer transport looks like in isolation (ABBA) against
  what it looks like coupled to active gas-phase chemistry and a
  lightning-NOx source (LNOx + O3).

## 2.2 The supercell case

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

The supercell test case is an idealized deep-convection setup adapted
from Weisman and Klemp (1982): a horizontally homogeneous, strongly
sheared environment perturbed by a warm bubble that triggers a
long-lived rotating storm. CheMPAS-A's tracked configuration
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

## 2.3 Setup checklist

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
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

If any of these fail, see `BUILD.md` in the repository root for the
model build, `RUN.md` in the repository root for the run-directory
layout, and `test_cases/README.md` for the data download.

## 2.4 Initialization

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
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
the dynamics solver. See `RUN.md` in the repository root for the full
rank-vs-partition table.

## 2.5 Run with the ABBA mechanism

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

The ABBA mechanism (`micm_configs/abba.yaml`) is a three-species toy
set — qA, qB, qAB — used as an advection-dominated sandbox. The
mechanism initializes qAB to a uniform 1.0 and runs a slow two-way
reaction (qAB → qA + qB at scaling 2e-3, qA + qB → qAB at 1e-3); on
the supercell run duration the chemistry barely advances, so the
tracer fields are dominated by transport rather than reaction. This
makes ABBA a clean way to verify that tracers are being carried by
the dynamics correctly before adding real chemistry on top.

**Initialize the ABBA tracer.** Give qAB a horizontal sine pattern so
the supercell flow has something to advect (without this step, qAB is
uniform and the resulting plot has no structure):

```bash
cd ~/Data/CheMPAS/supercell
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/init_tracer_sine.py \
    -i supercell_init.nc -t qAB --waves-x 2 --amplitude 0.4 --offset 0.6
```

This sets qAB to a sine pattern with mean 0.6 and amplitude 0.4 across
two horizontal wavelengths.

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

What to look for: the qAB sine pattern is advected and distorted by
the updraft and cold-pool outflow, so qAB at t = 2 h is essentially
the initial sine field carried by the flow. qA and qB grow slowly
from zero where qAB is dissociating; on this run duration their
amplitude is small but their pattern mirrors qAB.

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

# Name the altitude-mode artifacts so they survive the §2.6.2 run.
[ -f output.nc ] && mv output.nc output.altitude.nc
[ -f log.atmosphere.0000.out ] && mv log.atmosphere.0000.out log.altitude.out
```

**Plot.** The dedicated LNOx plotting script produces the standard
diagnostic set (vertical cross-sections, time series, NO₂
partitioning ratio):

```bash
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/plot_lnox_o3.py \
    -i output.altitude.nc -o lnox_altitude.png
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

**Run, then name the artifacts.** §2.6.1 already left
`output.altitude.nc` in place; this run produces `output.isotherm.nc`
so §2.6.3 can read both side-by-side:

```bash
mpiexec -n 8 ~/EarthSystem/CheMPAS-A/atmosphere_model

# Name the isotherm-mode artifacts so the §2.6.3 comparison can read both.
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
layer of the storm — approximately mid-troposphere on the
Weisman–Klemp sounding used here — but moving with the cloud rather
than pinned to a fixed altitude.
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

## 2.7 Comparing the two runs

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

("LNOx + O3" in this section refers to either gating mode — the
ABBA vs. LNOx contrast applies the same way to both.)
Placing the two final-state plots side by side highlights what's
shared and what differs. The dynamics are identical: the same updraft
and cold-pool outflow advect qAB in the ABBA run and NO/NO₂/O₃ in the
LNOx + O3 run, so the spatial pattern of "tracer carried by the flow"
matches between the two runs. The chemistry, on the other hand,
diverges. ABBA's qAB → qA + qB reaction is slow on the run duration,
so the qAB field at t = 2 h is essentially the initial sine pattern
deformed by the storm; qA and qB grow slowly from zero everywhere
qAB is dissociating. In the LNOx + O3 run the lightning-NOx source
localizes NO emission to a small volume in the updraft column, fast
NO–NO₂–O₃ photochemistry redistributes the partitioning, and an
O₃-titration signature appears where fresh NO is concentrated.

This is the pedagogical payoff of running the same dynamics with two
mechanisms: it isolates "what the flow does" from "what the chemistry
does."

**[Figure 2.6: Side-by-side comparison of ABBA tracer transport and
LNOx + O3 chemistry at t = 2 h. To be added.]**

## 2.8 Verifying numerically

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

Visual agreement is reassuring but not sufficient. The planned regression
suite will compare final-state min/max/mean statistics against tracked
reference YAML files, but that tooling is not present in this branch yet.
See `docs/superpowers/specs/2026-04-19-regression-suite-design.md` for
the design.

For now, use this section as a manual checklist: confirm the log reports
`Critical error messages = 0`, inspect the plotted tracer fields, and
spot-check the key fields with `ncdump`, `ncks`, or a short Python script.

## 2.9 Next steps

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

- **The next chapter** is
  [Chapman + NOx Photostationary State](03-chapman-nox.md) — a small
  domain where the analytical PSS solution is a clean check on the
  coupled MICM + TUV-x configuration. Chapter 4 then runs the same
  chemistry on the global `x1.40962` mesh:
  [Chapman + NOx Global](04-chapman-nox-global.md).
- **The MUSICA/MICM coupling internals** are documented in
  [docs/chempas/musica/MUSICA_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/musica/MUSICA_INTEGRATION.md).
- **The LNOx scheme** — both gating modes, full namelist surface,
  and calibration notes — is documented in
  [docs/chempas/guides/LNOX_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/guides/LNOX_INTEGRATION.md).
- **TUV-x photolysis** configuration is documented in
  [docs/chempas/guides/TUVX_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/guides/TUVX_INTEGRATION.md).
- **Upstream MUSICA, MICM, and TUV-x docs** are linked from the
  [project landing page](../index.rst) in the *See also* section.

## 2.10 Standalone ABBA box model

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

The same chemistry as §2.5, exercised in pure Python with no MPAS in
the loop. `scripts/musica_python/abba_box.py` loads
`micm_configs/abba.yaml` into a single-cell MICM solver, seeds qAB at
1 mol m⁻³, runs the slow two-way reaction for 2 hours, and writes
`abba_box.nc` plus `abba_box.png` next to the script. Useful for
poking at initial conditions or temperatures without rebuilding MPAS.

Pre-req: see Chapter 1's [Python environment for standalone
examples](01-overview.md) section.

Run:

```bash
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/musica_python/abba_box.py
```

**[Figure 2.7: A, B, AB concentrations from the standalone ABBA box
model over a 2 h integration. To be added.]**

What to look for: AB drops from 1 mol m⁻³ toward the analytical
equilibrium (AB ≈ 0.268, A = B ≈ 0.732, set by k_fwd / k_rev = 2
mol m⁻³) within the first ~30 minutes of the run; the rest of the
2 h sits at steady state. The visible chemistry contrasts with
§2.5's "transport-dominated" framing — same reactions, but without
advection the box runs to its endpoint instead of being shaped by
the storm flow.

**Source listings.** Both files are reproduced inline below for
reference; they are the same files used by the script invocation
above.

```{literalinclude} ../../scripts/musica_python/abba_box.py
:caption: scripts/musica_python/abba_box.py
:language: python
:linenos:
```

The script imports the MUSICA bindings (`MICM`, the mechanism-config
parser, `SolverState`) plus `numpy`, `xarray`, and `matplotlib` for
I/O and plotting, and the project's `scripts/style.py` for
NCAR-palette plotting. After parsing `abba.yaml`, it constructs a
Rosenbrock standard-order solver, creates a single-cell state at
T = 273 K and P = 101 325 Pa, and seeds A = B = 0, AB = 1 mol m⁻³.

The two `USER.<reaction-name>` rate parameters are *multipliers* on
the YAML `scaling factor`; setting both to 1.0 gives effective rates
of k_fwd = 2 × 10⁻³ s⁻¹ and k_rev = 1 × 10⁻³ m³ mol⁻¹ s⁻¹ — the same
values the MPAS-coupled run sees in §2.5, where the Fortran side
leaves the multipliers at 1. The integration loop runs for 7 200 s
with a 60-second output cadence; the inner `while elapsed < dt_out`
drives MICM through whatever sub-stepping the solver chooses while
ensuring each output sample lands exactly on the cadence.

Output is written next to the script: `abba_box.nc` (xarray Dataset
with `time` in minutes and species in mol m⁻³) and `abba_box.png`
(mixing-ratio time series in ppm, converted via VMR = nRT / P).

```{literalinclude} ../../micm_configs/abba.yaml
:caption: micm_configs/abba.yaml
:language: yaml
:linenos:
```

The mechanism declares three gas-phase species (`A`, `B`, `AB`) and
a single `gas` phase that lists them. Each species declaration
carries CheMPAS-A extension fields under `__`-prefixed keys
(`do advect`, `absolute tolerance`, `molar mass`,
`initial concentration`); these are non-standard and are read by the
CheMPAS-A chemistry coupler to wire each species into MPAS's tracer
transport.

The two reactions are both `USER_DEFINED`: AB → A + B with
`scaling factor: 2.0e-3` and A + B → AB with `scaling factor:
1.0e-3`. `USER_DEFINED` means the host code (the Python script above
or, in the MPAS-coupled case, `mpas_musica.F`) supplies a runtime
multiplier on top of the YAML factor — this is what
`state.set_user_defined_rate_parameters(...)` does in the script.
The 2:1 ratio of the forward and reverse scaling factors fixes the
analytical equilibrium quoted earlier (AB ≈ 0.268, A = B ≈ 0.732
mol m⁻³ for the seeded mass budget).

## 2.11 Standalone LNOx + O₃ box model

```{admonition} Draft - revisions in progress
:class: warning

This section is being revised.
```

The standalone counterpart of §2.6, *minus* the lightning-NOx source
(which is a CheMPAS-A operator-split injection in
`mpas_lightning_nox.F`, not part of the MICM mechanism).
`scripts/musica_python/lnox_box.py` loads `micm_configs/lnox_o3.yaml`
into a single-cell MICM solver at mid-tropospheric conditions
(T = 240 K, P = 5×10⁴ Pa), seeds 1 ppb total NOx (50/50 NO/NO₂) and
50 ppb O₃, hardcodes `PHOTO.jNO2 = 0.01 s⁻¹` (matching CheMPAS-A's
`config_lnox_j_no2`), and runs for 2 hours.

Pre-req: see Chapter 1's [Python environment for standalone
examples](01-overview.md) section.

Run:

```bash
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/musica_python/lnox_box.py
```

**[Figure 2.8: NO, NO₂, O₃ from the standalone LNOx + O₃ box model.
The first ~minute shows NO/NO₂ relaxing to the Leighton PSS; over
2 h, slow O₃ titration is visible. To be added.]**

What to look for: NO and NO₂ partitioning settles within ~1 minute
to the Leighton ratio (jNO₂ / k_{NO+O₃}·[O₃]) — at the script's
conditions the simulated [NO]/[NO₂] reaches ~2.2, matching the
analytical expression. O₃ stays essentially constant: in this
simplified mechanism the back-reaction NO₂ + hν → NO + O₃ exactly
balances NO + O₃ → NO₂ + O₂ once PSS is reached, so there is no
net titration on the run duration. A direct independent check of
the analytical PSS computation referenced in Chapter 3 §3.8.
