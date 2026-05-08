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

**[Figure 4.1: Gaussian initial qO₃ profile (peak 10 ppmm at 25 km,
σ = 7 km) injected globally by `init_chapman_nox.py`. To be added.]**

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
- `qO` — small floor (1×10⁻¹²). `qO1D` is not seeded; the runtime
  default of zero is fine for a fast radical that the chemistry
  spins up to Chapman quasi-steady-state within seconds on the first
  sunlit step (consistent with Ch. 3 §3.5).
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
own SZA. The 3600 s TUV-x update interval is a deliberate choice
for this case; the Ch. 3 small-domain run does not set
`config_tuvx_update_interval` and falls back to the registry default
of 0.0 (TUV-x runs every chemistry step). On a 24-hour global run
the SZA evolves slowly enough that hourly TUV-x updates resolve the
terminator sweep correctly without running TUV-x on every chemistry
step.

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

- **`jNO2_terminator.png`** — jNO₂ maps at t = 3, 9, 15, 21 UTC.
  The day–night terminator sweeps across the globe four times in
  this panel, visible as a sharp drop in jNO₂ at the photolysis
  edge. (t = 0 is skipped because TUV-x has not yet fired at the
  initial output frame, so jNO₂ is identically zero there.)
  Triangulated mesh rendering with antimeridian-spanning triangles
  masked, so the limb is clean.

  **[Figure 4.2: jNO₂ terminator-sweep map at t = 3 / 9 / 15 / 21
  UTC. To be added.]**

- **`tracers_evolution.png`** — qO₃ at level 22 (≈36 km, where the
  Chapman cycle is most active) and qNO₂ at level 17 (≈25 km, near
  the seeded NOx peak), shown at t = 12 h and t = 24 h. The level
  indices are tied to the JW 26-level grid via the `LEVEL_O3` and
  `LEVEL_NO2` constants in `plot_chapman_nox_global.py`; if the
  vertical grid changes, those constants need to be retuned.

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
  `o3_profile.png`, expect a small diurnal modulation in qO₃ at
  36 km, visible as a difference between the t = 12 h and t = 24 h
  panels. The 24-hour integration is too short for the column to
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
