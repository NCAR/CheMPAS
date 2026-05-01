# Chapman + NOx explodes qO3 on chem_box — open issue

## Problem

On the 64-cell `chem_box` mesh, running `chapman_nox.yaml` +
`tuvx_chapman_nox.json` (all four photolysis rates) produces an
explosion in qO3 within the first chemistry step:

```
t=0    qO3 max=23,981 ppb   qO max=0     (AFGL init)
t=5m   qO3 max=93,929,448 ppb   qO max=1.9e7 ppb
t=10m  qO3 max=105,028,599 ppb  qO max=1.9e7 ppb
```

qO3 saturates near 0.15 kg/kg (≈ 10 % mass fraction of air) — about
four orders of magnitude too large. qO pegs at ≈ 0.01 kg/kg.

Per-cell mass balance is preserved (total oxygen atoms conserved),
and the saturation value stays the same across several yaml tweaks,
which looks like a fixed point of whatever the mechanism is
actually solving — not a blow-up.

## Test case (64-cell chem_box)

All files are tracked in the repo so the run is reproducible:

- `test_cases/chem_box/namelist.atmosphere` — `config_dt = 3.0 s`,
  10–60 min run, 8-MPI-rank partition, `config_micm_file =
  chapman_nox.yaml`, `config_tuvx_config_file = tuvx_chapman_nox.json`,
  `config_tuvx_top_extension = .true.`,
  `config_tuvx_extension_file = tuvx_upper_atm.csv`.
- `test_cases/chem_box/streams.atmosphere`,
  `streams.init_atmosphere`, `stream_list.atmosphere.output`,
  `supercell_zeta_levels.txt`, `namelist.init_atmosphere`.
- `micm_configs/chapman_nox.yaml` — full Chapman + NOx mechanism (7
  species incl. M, O1D; 9 reactions; 4 photolysis channels).
- `micm_configs/chapman_nox_noO1D.yaml` — reduced variant with O1D
  folded into jO3_O1D → O (see hypothesis #2 below). Same 4-photolysis
  wiring so `tuvx_chapman_nox.json` works unchanged.
- `micm_configs/tuvx_chapman_nox.json` — TUV-x config: 4 photolysis
  reactions (jO2, jO3_O1D, jO3_O, jNO2), air/O2/O3 radiators all
  driven from MPAS host state.
- `micm_configs/tuvx_upper_atm.csv` — 10-layer 50→100 km US-Std-Atm
  extension (z, T, n_air, n_O3) appended above the MPAS column by
  `mpas_tuvx.F`.

Run directory: `~/Data/CheMPAS/chem_box/`. Init file
(`chem_box_init.nc`) has AFGL qO3 (max ≈ 24 ppb at surface, ≈ 8 ppm
at the stratopause), qO2 = 0.23141 kg/kg (dry air VMR 0.2095), qNO
and qNO2 with small smooth profiles, qO = qO1D = 0.

### Mesh and grid build (how the 64-cell case was constructed)

The chem_box mesh is a doubly-periodic planar hexagonal mesh, 8×8
cells at 500 m centre-to-centre spacing (domain 4000 m × 3464 m,
`on_a_sphere = "NO"`, `is_periodic = "YES"`). Vertical grid is 60
stretched levels to 50 km, reusing the supercell zeta profile. All
tools come from the `mpas` conda env (`mpas-tools` + `metis`
packages on conda-forge).

Exact reproduction from scratch, run in the chem_box run directory:

```bash
# 1. Build the 64-cell periodic hex mesh (8x8 at 500 m).
#    planar_hex writes an MPAS-format grid directly — no conversion
#    needed for atmosphere_model input.
~/miniconda3/envs/mpas/bin/planar_hex --nx 8 --ny 8 --dc 500 \
    -o chem_box_grid.nc

# 2. Derive the METIS graph description from the grid. MpasMeshConverter
#    writes a graph.info file as a side effect of converting; we use
#    the graph.info and discard the "converted" grid file since the
#    planar_hex output already matches MPAS format exactly.
~/miniconda3/envs/mpas/bin/MpasMeshConverter.x \
    chem_box_grid.nc /tmp/_converted.nc
mv graph.info chem_box.graph.info
rm -f /tmp/_converted.nc

# 3. Partition the graph for the MPI rank counts you'll run.
#    gpmetis is from conda-forge's `metis` package. The partition is
#    randomized, so the .part.N files won't byte-match another run,
#    but any valid 8-way partition works identically at runtime.
~/miniconda3/envs/mpas/bin/gpmetis chem_box.graph.info 8
~/miniconda3/envs/mpas/bin/gpmetis chem_box.graph.info 4

# 4. Copy the reference configs from the repo.
cp ~/EarthSystem/CheMPAS/test_cases/chem_box/* .

# 5. Initialize. init_case = 5 is the supercell (Weisman-Klemp)
#    thermodynamic sounding; chem_box reuses it for its moisture
#    column and as a background state for chemistry. Runs with
#    any of the partitions you generated (use -n matching a
#    .part.N file).
ln -sf ~/EarthSystem/CheMPAS/init_atmosphere_model .
mpiexec -n 4 ./init_atmosphere_model

# 6. Stage chemistry config + atmosphere executable.
ln -sf ~/EarthSystem/CheMPAS/atmosphere_model .
ln -sf ~/EarthSystem/CheMPAS/LANDUSE.TBL .
cp ~/EarthSystem/CheMPAS/micm_configs/chapman_nox.yaml .
cp ~/EarthSystem/CheMPAS/micm_configs/tuvx_chapman_nox.json .
cp ~/EarthSystem/CheMPAS/micm_configs/tuvx_upper_atm.csv .
```

Run the model with `mpiexec -n 8 ./atmosphere_model`. Outputs land
in `output.nc` (one snapshot per `output_interval` in
`streams.atmosphere`; set to `00:00:03` when debugging step-by-step
photolysis behaviour, `00:05:00` for normal runs).

Global attributes on `chem_box_grid.nc` captured by `ncdump -h` for
verification: `dc = 500.0 m`, `nx = 8`, `ny = 8`, `x_period = 4000 m`,
`y_period ≈ 3464.1 m`, 64 cells, 192 edges, 128 vertices.

## What was verified (facts, not hypotheses)

**Rate constants are correct.** Every ARRHENIUS rate, at T = 220 K,
matches JPL 2020 within 1 % after the cgs → SI conversion
(`×N_A × 10⁻⁶` for bimolecular, `×N_A² × 10⁻¹²` for termolecular).
Compared against the known-good `lnox_o3.yaml` `NO + O3` rate as a
ground-truth calibration point.

**MICM Arrhenius form** (from
`MUSICA/build/_deps/micm-src/include/micm/process/rate_constant/arrhenius_rate_constant.hpp`):
`k = A × exp(C/T) × (T/D)^B × (1 + E·P)` with defaults `D = 300`,
`E = 0`. Omitting D/E from the YAML is fine.

**Third-body M is handled correctly by MICM.** Earlier notes here
claimed `is_third_body` was parsed but never consumed. That was
wrong. Trace through the installed MUSICA library:

- `MUSICA/src/micm/v1_parse.cpp:38-41` → calls
  `s.SetThirdBody()` when the YAML sets `is third body: true`.
- `micm-src/include/micm/system/species.hpp:162` →
  `SetThirdBody` installs `parameterize_ = [](c){ return c.air_density_; }`.
- `micm-src/include/micm/system/phase.hpp:66-90` → parameterized
  species are filtered out of `StateSize`, `UniqueNames`, and
  `SpeciesNames`.
- `micm-src/include/micm/process/chemical_reaction.hpp:127-132` →
  during rate-constant evaluation, parameterized reactants are
  multiplied into `fixed_reactants` via `parameterize_(conditions)`,
  so R2 = A·(T/300)^B · air_density · [O] · [O2] (correct termolecular).
- Runtime log (`~/Data/CheMPAS/chem_box/log.atmosphere.0000.out:583-590`)
  confirms `state%species_ordering` lists **6** species (NO2, NO, O,
  O3, O2, O1D) — M is correctly excluded.
- `air_density_` units are mol m⁻³ (`conditions.hpp:14`), matching
  what the coupler sets (`rho / M_AIR`).

**Mesh & dynamics are fine.** `chem_box` with `lnox_o3.yaml` +
`tuvx_no2.json` runs cleanly for 10 min (qO3 stable at 50 ppb,
NO at 0). The same mesh with `chapman_nox.yaml` explodes in 5 min.

**TUV-x photolysis rates look reasonable by altitude** (extracted
from the `j_*` diagnostic fields in `output.nc` at t=5 min):

```
    z (km)          jO2        jO3_O      jO3_O1D         jNO2
     0.1    0.000e+00    2.758e-11    0.000e+00    2.786e-06
     9.2    0.000e+00    3.877e-10   3.723e-225    3.722e-05
    21.5    0.000e+00    2.393e-08    1.494e-53    1.390e-03
    35.4    0.000e+00    4.564e-06    2.150e-09    5.973e-03
    49.5    1.736e-10    4.407e-04    4.242e-04    8.438e-03
```

`jO2` is effectively zero everywhere except the MPAS top, as expected
(Schumann-Runge bands attenuated out). This is the **first** CheMPAS-A
run that has O2 photolysis in the mechanism; prior runs had `jNO2`
only via `lnox_o3.yaml`.

**Variants tried (all still explode):**
1. `A: 8.018e-17` (original, cgs units) — R2 too slow, qO3 DECAYS
   exponentially to ~0.4 ppb in 1 h.
2. `A: 6.0e-34` + M as reactant — same behaviour as #1 (wrong scale).
3. `A: 2.18e2` + M as reactant — qO3 EXPLODES as above.
4. Copied from canonical `MUSICA/configs/v1/chapman/config.yaml`
   (`A: 217.6, B: -2.4, D: 300, E: 0`) — same explosion as #3.
5. Removed `__tracer type: CONSTANT` from O2 — qO2 now depletes to
   25 % of initial, confirming mass balance, but qO3 still at same
   saturation value.
6. `chapman_nox_noO1D.yaml` — O1D dropped, jO3_O1D channel wired to
   produce O(3P) directly (R6 quenching collapsed into photolysis).
   **Output bit-for-bit identical to the full mechanism**; rules out
   O1D stiffness / zero-initial-value as the trigger.

## What the standalone MICM column model shows

`MUSICA/fortran/examples/column_model.F90` ships as a coupled TUV-x
+ MICM 1-D Chapman driver (120 layers, 0–120 km, Boulder CO, June
21, 15-min steps over 24 h). Rebuilt with `MUSICA_ENABLE_TESTS=ON`
and run against the canonical `MUSICA/configs/v1/chapman/config.yaml`:

```
t=0h : O3_max = 6.902e-06 mol/m³ at z = 21.5 km (AFGL-like init)
t=6h : O3_max = 6.902e-06 mol/m³              O_max = 5.5e-9
t=12h: O3_max = 6.929e-06 mol/m³              O_max = 5.7e-8
t=18h: O3_max = 6.995e-06 mol/m³              O_max = 1.1e-7
t=24h: O3_max = 6.995e-06 mol/m³              O_max = 6.3e-8
```

Stratopause O3 stays pinned at a physical ~15 ppm over 24 h. **No
explosion.** So the bug is NOT in MICM's Chapman mechanism itself —
it is specific to the CheMPAS-A + MUSICA coupling.

## The smoking gun: step-1 photolysis rates

Setting `output_interval = 00:00:03` (one snapshot per chemistry
step) and printing `[MUSICA] jO3_O min/max` at every step reveals a
dramatic anomaly at **step 1 only**:

```
step  1: jO3_O min= 3.634e-04  max= 5.627e-04   (nearly UNIFORM, TOA value everywhere)
step  2: jO3_O min= 1.661e-09  max= 4.518e-04   (normal column attenuation)
step  5: jO3_O min= 7.097e-10  max= 4.404e-04
step 10: jO3_O min= 3.433e-10  max= 4.404e-04
step 50: jO3_O min= 5.767e-11  max= 4.405e-04
step 200: jO3_O min= 1.375e-11  max= 4.409e-04   (correct surface attenuation)
```

At step 1, **every cell and level** is receiving the top-of-
atmosphere rate (no O3 column attenuation). From step 2 onward, the
profile is attenuated correctly. The column in `j_jO3_O` diagnostics
in `output.nc` at t=3 s matches the `[MUSICA]` log output for step 1
(3.6e-4 uniform), confirming this is not a logging artifact.

Given the rate constant R2 ≈ 45 000 × [O2] [M] s⁻¹ at surface, a
bootstrap pulse of O atoms from the step-1 UV blast is enough to
produce ~0.02 kg/kg of qO3 in one 3-s step (observed). On step 2
the now-huge O3 column heavily attenuates UV (proper operation of
TUV-x), but the damage has been done — the system has already
landed in the wrong attractor and cannot recover.

## Debug instrumentation confirmed the input to TUV-x is correct

Temporary instrumentation in `tuvx_compute_photolysis` (reverted
after use) logged the profile values handed to TUV-x at the first
few calls:

```
[DEBUG tuvx] call=0  air_nd(1)=2.36e19   temp_mid(1)=299 K
                     o3_nd(1)=6.34e11 molec/cm³  (≈ 20 ppb surface)
                     o3_ld col_sum=9.18e18 molec/cm²  (≈ 340 DU — realistic!)
```

Readback via `o3_profile%get_layer_densities` after
`set_layer_densities` returned **exactly** the same numbers we
passed in, so TUV-x's internal profile storage is populated
correctly on the first call.

**Warmup test** — calling `tuvx_solver%run()` twice at the first
chemistry step produced identical photolysis rates both times, so
this is NOT a lazy-initialization / first-call-is-stale issue
inside TUV-x.

Something downstream of the correctly-set profile is producing the
wrong radiative transfer result at step 1. Expected surface OD for
a 340 DU column at ~300 nm is ~3.7 → transmission ~2.5 %. TUV-x is
giving transmission ~26 % at the surface (OD ~1.3), about 12× less
attenuation than physics would predict.

## Line A results: what MICM actually sees and produces at step 1

Instrumented `MICM_from_chemistry`, `musica_set_photolysis_rates`,
and `MICM_to_chemistry` to dump, at cell 1 / level 1 / surface, for
the first two chemistry steps:

- all four `state%rate_parameters(PHOTO.*)` values,
- `state%conditions(1)%{temperature, pressure, air_density}`,
- the in-concentrations (`MICM-in`) and post-solve concentrations
  (`MICM-out`) for every non-parameterized species,
- stride layout (`species_strides`, `rate_parameters_strides`).

Stride layout is `cell_stride = n_species`, `var_stride = 1`
(row-major by grid cell), with MICM's own variable_map order
putting O2 at stride 1, O at stride 2, O3 at stride 3, NO at 4,
NO2 at 5 — matches the iteration order returned by MICM's
`species_ordering` when the Fortran coupler pairs names with
stride indices, so the MPAS↔MICM copy is correctly routed.

### Step-1 inputs are correct

```
[DEBUG MICM-in] T=299.09 K  P=98321 Pa  rho=1.14 kg/m³  air_density=39.2 mol/m³
[DEBUG MICM-in] NO2 conc=1.37e-9   q=5.56e-11
[DEBUG MICM-in] NO  conc=5.88e-10  q=1.55e-11
[DEBUG MICM-in] O3  conc=1.05e-6   q=4.45e-8
[DEBUG MICM-in] O   conc=0         q=0
[DEBUG MICM-in] O2  conc=8.21      q=0.2314
[DEBUG RP-in]   PHOTO.jNO2    = 6.74e-3
[DEBUG RP-in]   PHOTO.jO3_O1D = 8.87e-6
[DEBUG RP-in]   PHOTO.jO3_O   = 3.63e-4
[DEBUG RP-in]   PHOTO.jO2     = 3.92e-38
```

Everything we hand MICM at step 1 is what the coupler should hand
it: environment is correct, concentrations match the AFGL init, the
photolysis slots hold exactly the (anomalous-TOA) values TUV-x
emitted. The step-1 explosion is not a result of the coupler
overwriting with garbage.

### Step-1 MICM solve output has impossible mass imbalance

```
[DEBUG MICM-out] NO2 conc=0
[DEBUG MICM-out] NO  conc=8.67e-7   ← was 5.88e-10, grew 1475×
[DEBUG MICM-out] O3  conc=0.315     ← was 1.05e-6,  grew ~300 000×
[DEBUG MICM-out] O   conc=1.53e-6
[DEBUG MICM-out] O2  conc=7.74      ← was 8.21,      dropped 6%
```

Oxygen-atom balance is preserved at the cell level (the O2 loss
exactly accounts for the O + 3×O3 gain). **Nitrogen balance is
not** — total N at this cell grows from 1.96e-9 to 8.67e-7 mol m⁻³
(443×). Across the whole column the mean total-N mole fraction
grows 32× between t=0 and t=3 s, then stays constant through step
2 onward.

The Chapman steady state predicted by the rate constants for the
step-1 anomalous photolysis rates is `[O]_ss ≈ 5e-15 mol m⁻³` at
surface, with `d[O3]/dt ≈ 2e-11 mol m⁻³ s⁻¹` — i.e. qO3 should
barely move over 3 s. MICM evolves [O3] to 0.315 mol m⁻³ in that
single step, which is the wrong fixed point by ~13 orders of
magnitude.

### What this rules in and out

- **It is not a coupler data-transfer bug.** Inputs are verified
  clean at the cell level.
- **It is not a rate_parameter scaling_factor issue.** All our
  photolysis reactions default to `scaling_factor = 1.0` and MICM
  applies `k = custom_parameter × scaling_factor`, so the
  effective j equals exactly what TUV-x wrote. Ruled out.
- **It is not a stride/indexing mixup.** Stride layout is verified.
- **It IS a solver fidelity problem inside MICM.** The combination
  of a huge (anomalous) step-1 photolysis rate, zero initial [O],
  a very stiff Chapman cycle (R2 timescale ~14 μs at surface), and
  a 3 s outer dt, drives Rosenbrock into an unphysical attractor
  where oxygen is conserved at the cell level but N is created and
  O3 overshoots by ~5 orders. The solver reports "9 accepted, 0
  rejected" — it thinks it converged.

This leaves TWO independent problems to fix:

1. **Step-1 TOA photolysis rates.** TUV-x must attenuate through
   the provided O3 column on the first call. (Lines B work.)
2. **MICM Rosenbrock robustness.** Even if photolysis is correct,
   the current combination of tolerance settings and dt seems
   fragile. Worth testing loosened `__absolute tolerance`, a small
   non-zero seed for [O], or a different solver family.

### Backward Euler solver test

Swapped `musica_init` from `RosenbrockStandardOrder` to
`BackwardEulerStandardOrder` in `mpas_musica.F` and reran the same
chem_box + `chapman_nox_noO1D.yaml` case. Result:

```
              qO3 mean (kg/kg)       Total N (mol N / kg air)
t=0           5.07e-6                1.19e-7
t=3 s         1.52e-2  (3000× up)    1.19e-7  (conserved)
t=6 s         1.98e-2                1.19e-7
```

**Backward Euler preserves nitrogen mass balance at step 1.** The
32×-column-mean N-creation that Rosenbrock produces is gone
entirely with BE. This is direct evidence that the step-1 N
imbalance was a Rosenbrock-specific numerical artifact (probably
the implicit step evaluating the Jacobian at a near-degenerate
state with tight 1e-12 absolute tolerances and zero initial [O]),
NOT a mechanism or coupler bug.

**Backward Euler does not prevent the qO3 explosion.** qO3 still
jumps from 5e-6 to 1.5e-2 kg/kg (mean) in one 3 s step — slightly
less than Rosenbrock's ~5× bigger jump, but still ~3000× too high.
BE faithfully integrates the rate equations; it can't compensate
for a physical photolysis forcing that is 5 orders of magnitude too
strong. The step-1 TOA-photolysis problem is the primary driver of
the O3 blowup, not the solver.

**Decision:** keep Backward Euler as the production solver for now.
It removes the N-balance violation, makes MICM's output physically
interpretable under every condition we've tested, and has no
apparent downsides for this mechanism (3 s dt, tightly-coupled
null cycles). The Rosenbrock path can be revisited if/when we find
a mechanism that demonstrably needs higher-order stiff accuracy.

## Line B results: TUV-x is not the bug

B1 (analytical sanity check) corrected an earlier misreading of
the step-1 rates. Comparing each channel to published WACCM/ACOM
reference values at noon mid-latitude conditions:

| Channel            | Observed step 1 | Published (noon mid-lat) | Status |
|--------------------|-----------------|--------------------------|--------|
| jO2 (SR bands)     | ~0              | ~0 (absorbed above)      | ✓      |
| jO3_O (Chappuis)   | 3.6e-4          | 2–5e-4                   | ✓      |
| jO3_O1D (Hartley)  | 8.87e-6         | 1–5e-5                   | ✓      |
| jNO2 (UV-Vis)      | 6.7e-3          | ~1e-2                    | ✓      |

The earlier narrative that jO3_O was "5 orders too high at surface"
came from comparing the Chappuis `jO3_O` (weakly self-absorbed by
O3, so surface ≈ TOA/few) against expectations for the strongly-
attenuated Hartley `jO3_O1D` channel. Chappuis surface rates of
~10⁻⁴ s⁻¹ are physically normal. The step-1 rates are correct.

B2 (standalone `MUSICA/fortran/examples/test_tuvx_v54` built
against the installed MUSICA) confirms this. At SZA = 0 with the
US-Std-Atm column, TUV-x emits `jO3_O = 4.98e-4` and `jO3_O1D =
4.83e-5` at the surface — consistent with our chem_box step-1
rates after scaling down for SZA ≈ 58° (cos scaling gives the
observed ~0.7× for Chappuis and ~0.2× for Hartley).

B3 + B4 (coupling completeness fixes) implemented in
`mpas_tuvx.F`: `set_edge_values` is now called for the O3 and O2
profiles (previously only midpoints + layer densities were set,
leaving edge arrays at their constructor zeros), and
`calculate_exo_layer_density(7 km)` populates the air profile's
exo layer density so spherical-geometry slant-path integration
accounts for air above the 100 km extension top. These are real
correctness fixes that should be in even though they did **not**
change any photolysis output in the chem_box test — the surface
rates for a 340-DU column at SZA = 58° are physically what we
were already seeing, and the base radiator's optical-depth
calculation uses `layer_dens_` (which we were already writing
correctly), not edge values.

B5 (direct TUV-x radiator instrumentation) was not pursued: B1+B2
make it clear the RT solver is doing the right thing for this
column, and deeper instrumentation is unlikely to find a bug that
isn't there.

**Line B conclusion:** TUV-x is producing the physically correct
photolysis rates at step 1. The qO3 explosion is driven entirely
by the MICM solver's response to full-strength photolysis applied
to an initial state with `[O] = 0`. Even Backward Euler, with a
3 s outer dt that is 10⁵–10⁶ larger than the fastest Chapman mode,
lands on an implicit fixed point where [O2] has been converted to
[O3] + [O] at levels far above what the Chapman/NOx chemistry
should produce physically. Total oxygen atoms ARE conserved at
the cell level (verified at cell 1 surface: 16.42 in = 16.42 out
mol m⁻³ of O). The mechanism moves a large fraction of [O2] into
[O3] + [O] in a single 3 s step, which is numerically self-
consistent with BE's implicit step but not what Chapman physics
would give in a well-resolved transient.

## What actually fixes the explosion

None of the Line A or Line B work above addresses the root cause
directly — they rule hypotheses out. Real fixes to try, in rough
order of cost:

1. **Seed qO with a small non-zero value at init.** Modifying
   `scripts/init_chapman.py` to write a small [O] profile
   (e.g. Chapman quasi-steady-state values, or just `1e-15`
   everywhere) may be enough to break the degeneracy that lets
   BE's Newton iteration land on the wrong implicit fixed point.
2. **Loosen `__absolute tolerance` on O / O1D / NO / NO2 from
   `1e-12` to `1e-10` or `1e-8`** in `chapman_nox.yaml`. The
   very tight tolerance on species that start at zero makes the
   BE Newton solve prone to picking self-consistent but non-
   physical end states.
3. **Shorten `config_dt` for the first few steps** (run a pre-
   dawn spinup, or reduce `config_dt` to 0.1 s for the first
   10 s). Avoid presenting BE with a 3 s step while the fast
   Chapman null cycle is spinning up from zero.
4. **Start `config_start_time` at night (cos_sza ≤ 0)** so
   photolysis ramps up naturally and [O] has time to track.
   This is what `MUSICA/fortran/examples/column_model.F90` does,
   and it doesn't explode.

Option 4 is closest to the MUSICA reference usage pattern and is
the cheapest to try first.

## Tests of options 1 + 2 — did NOT fix the explosion

On 2026-04-18, tried options 1 and 2 together:

- `scripts/init_chapman.py` changed to write `qO = 1e-12 kg/kg`
  (uniform) instead of exactly zero. Corresponds to `[O] ≈ 7e-11
  mol/m³` at surface and `3e-10 mol/m³` at the stratopause — well
  above any MICM absolute tolerance but chemically negligible.
  Committed.
- `chapman_nox.yaml` and `chapman_nox_noO1D.yaml` changed from
  `__absolute tolerance: 1e-12` to `1e-10` on all radical species.
  Also tested with tolerance relaxed all the way to `1e-6`.
  Committed at 1e-10.

Result: **output is bit-for-bit identical to the pre-change
Backward Euler run.** qO3 still jumps from 5.07e-6 → 1.52e-2
(mean, kg/kg) in one 3 s step. The implicit fixed point Backward
Euler lands on does not depend on the initial [O] value or the
absolute-tolerance floor.

### Why these knobs didn't matter (important correction)

The reason is adaptive sub-stepping. MICM's Rosenbrock and
Backward Euler solvers are both adaptive: within a single
`micm%solve(dt, ...)` call for MPAS dt = 3 s, the solver takes
multiple internal sub-steps (Rosenbrock took 9 accepted sub-steps
per earlier logs). Which sub-step sizes the solver chooses is
driven by its **step-size error controller**, which compares step
estimates against the error tolerances.

- `absolute_tolerance` matters mostly for species near zero; it
  sets the floor below which error is considered negligible.
  Loosening it 1e-12 → 1e-6 only relaxes the floor — it does not
  force smaller sub-steps during the stiff transient.
- `relative_tolerance` (default `1e-6`, set via the solver
  parameters API, not the YAML) controls the per-species
  tolerance relative to magnitude. This is what drives the
  sub-step size through the stiff Chapman null-cycle transient.
  Tightening it forces the adaptive controller to take smaller
  internal steps.

Options 1+2 don't touch `relative_tolerance`, which is why they
make no difference: the adaptive controller keeps accepting the
same ~0.3 s sub-steps that land the implicit Newton iterate on
the wrong fixed point.

### Deeper reason: "adaptive and converged" ≠ "correct"

The adaptive controller only measures *local* truncation error
against the tolerances. It has no view of physical correctness.
For a Backward Euler implicit solve of stiff Chapman chemistry
starting from `[O] = 0` with full-strength photolysis, the
implicit equation

```
y_{n+1} - y_n - dt · f(t_{n+1}, y_{n+1}) = 0
```

has more than one physically-distinct root within the 3 s outer
dt: the true gradual-ramp-up trajectory where [O] slowly builds
from photolysis, and the far-field attractor where [O2] has
already been converted to [O3] + [O] at ~10% mass-fraction
levels. Newton lands on whichever root is closer to its
linearization, not necessarily the physical one.

The adaptive controller sub-divides when its estimate of the
local error |y_new − y_old_extrapolated| exceeds the tolerance.
But if Newton is converging to the wrong root at *every*
sub-step, those local errors can still be small — the solver
has no way to tell "the root I'm finding is physically wrong."
That's why the Line A logs show "9 accepted, 0 rejected" — the
solver literally thinks it converged.

**What shortening the outer dt does** (that no internal stepper
can replicate): shrink the neighborhood where the implicit
equation has multiple roots. At `dt = 0.1 s`, `dt · f` is small,
so Newton is forced to land near the initial state — i.e., on
the physical trajectory. With many short outer steps, [O]
builds up stepwise from photolysis and the Chapman null cycle
tracks reality. By the time outer dt returns to 3 s, the state
is no longer degenerate.

Corollary: **starting at night** (`cos_sza < 0`, option 4) has
the same effect for free. With photolysis rates at zero,
`dt · f ≈ 0` regardless of outer dt, so the implicit solve is
trivial. As photolysis ramps up smoothly through dawn, [O]
builds up gradually at naturally-small j-values. No Newton
degeneracy ever develops. This is why the MUSICA column model
(`fortran/examples/column_model.F90`) never sees the
explosion — it starts pre-dawn by construction.

Operator splitting is a secondary factor: chemistry and
dynamics are split at the outer-dt boundary with the photolysis
rates frozen during the MICM solve. Shorter outer dt means less
splitting error when j-values are changing rapidly (e.g. across
sunrise). This is first-order in outer dt and cannot be
recovered by any amount of internal adaptive stepping.

## Next planned test — tighten `relative_tolerance`

Extend `musica_init` in `mpas_musica.F` to call
`micm%set_backward_euler_solver_parameters(params, error)` right
after `get_state`, where `params` is a
`backward_euler_solver_parameters_t` with:

- `relative_tolerance = 1e-9` (or tighter, 1e-12, to bracket)
- `max_number_of_steps = 30` (default 11 — give the adaptive
  controller more budget to take many small sub-steps)
- `time_step_reductions = [0.1, 0.1, 0.1, 0.1, 0.01]` (default
  [0.5, 0.5, 0.5, 0.5, 0.1] — be more aggressive when Newton
  fails to converge)

If tighter `relative_tolerance` makes the step-1 trajectory
physically reasonable, that both confirms the diagnosis and
gives us a production fix. If it still lands on the wrong fixed
point, the next move is to instrument MICM's Newton iterate
itself (log the residual and iterate count per sub-step) —
that's a MICM-side change and probably worth an upstream issue.

### Handoff status at 2026-04-18 end-of-session

Committed on `develop`:
- `eac18d5` — solver switch Rosenbrock → Backward Euler.
- `6f95416` — TUV-x edge values + exo layer density (coupling
  completeness, does not affect the explosion).
- Pending this commit — `__absolute tolerance` 1e-12 → 1e-10,
  `qO` seed 1e-12 kg/kg in `init_chapman.py`, Line B results,
  "tests of options 1 + 2" and "next planned test" sections.

Run-directory state (`~/Data/CheMPAS/chem_box/`, not tracked):
- `chem_box_init.nc` re-initialized with the new qO seed via
  `python scripts/init_chapman.py --input ...`.
- `chapman_nox.yaml` copied from repo's `chapman_nox_noO1D.yaml`
  (for the reduced-mechanism test path).

Not committed — open work:
- Implement `set_backward_euler_solver_parameters` call in
  `mpas_musica.F::musica_init` with tighter `relative_tolerance`
  as described above.
- Rebuild, rerun, compare qO3 trajectory against the
  pre-tolerance-change baseline.
- If successful, decide on production tolerance values and
  whether to expose them via namelist.

## 2026-04-18 update: handoff API gap + pivoting to option 4

Picked up the handoff on the macOS side. Two findings before
running the next test:

1. **The Fortran binding `set_backward_euler_solver_parameters`
   doesn't exist** in the installed MUSICA-Fortran. Searched
   `MUSICA-LLVM/fortran/{micm,state}.F90`, the C interface
   (`src/micm/{micm,state}_c_interface.cpp`), and
   `libmusica.a` symbols — no `Set*SolverParameters`, no
   `SetRelativeTolerance`, nothing tolerance-related beyond
   what v1 parses from YAML (`absolute_tolerance` per species
   only).
2. **Upstream `BackwardEulerSolverParameters` does not contain
   `relative_tolerance`.** From
   `build/_deps/micm-src/include/micm/solver/backward_euler_solver_parameters.hpp`
   it has only `{small_, h_start_, max_number_of_steps_,
   time_step_reductions_}`. `relative_tolerance_` is a scalar
   on `State` (default `1e-06`, `micm-src/.../solver/state.hpp:34`),
   set via direct C++ assignment — not exposed via any C API.

So following the handoff literally requires a cross-repo MUSICA
API addition (new C shim for `state.relative_tolerance_` and
BE param setters, matching Fortran bindings, rebuild MUSICA-LLVM,
rebuild CheMPAS-A). Deferring that; trying option 4 first —
pre-dawn start — since it targets the same root cause
(degenerate implicit-solve neighborhood at full-strength
photolysis) with only a namelist edit.

Test plan (option 4):
- `config_start_time = '0000-01-01_10:00:00'` (04:00 local at
  chem_lat 35.86, chem_lon -97.93 → pre-dawn, cos_sza < 0)
- `config_run_duration = '09:00:00'` → finishes 19:00 UTC
  (13:00 local, ~30 min past solar noon)
- dt = 3 s unchanged, BE solver unchanged, qO seed unchanged.
- Crosses civil-twilight (~12:35 UTC) and sunrise (~13:30 UTC);
  photolysis ramps up from zero over ~1 h.
- Pass condition: qO3 stays within ~2× AFGL profile through
  noon; no 1e4× saturation.
- Fail condition: same saturation as daytime start — implies
  the Newton-degeneracy happens again at the sunrise crossing,
  which would mean shortening dt across dawn (not just starting
  earlier) is the real fix.

## Hypotheses still on the table

1. **TUV-x radiator update ordering.** `radiator_from_host_t::update_state`
   in `MUSICA/build/_deps/tuvx-src/src/radiative_transfer/radiators/from_host.F90`
   is a no-op. The "base" radiator (used by air/O2/O3 in our TUV-x
   config) has an `update_state` in `radiator.F90:169-230` that reads
   `radiator_profile%layer_dens_` to compute `layer_OD_`, and is
   called from `radiative_transfer%calculate:170-177`. In principle
   this should run on every `tuvx_solver%run()`. Worth confirming
   that on step 1 the base radiator's `layer_OD_` actually reflects
   our provided `layer_dens_`.
2. **MICM photolysis scaling_factor.** `UserDefinedRateConstant::Calculate`
   returns `custom_parameter × scaling_factor_`. Default is 1.0, but
   if our YAML's photolysis reactions inherit a different factor, the
   effective rate would be amplified. Worth grepping `scaling_factor`
   in the running build and logging the actual `k` MICM computes
   per photolysis reaction at step 1.
3. **Profile edge values never set for O3/O2.** `tuvx_compute_photolysis`
   calls `set_midpoint_values` + `set_layer_densities` for O3 and O2,
   but not `set_edge_values`. `edge_val_` stays at the constructor
   default of zero. The canonical `profile_from_host_t::update()`
   (not exposed via C bindings) REQUIRES edge_values. Possibly the
   radiative transfer solver reads edge_val_ somewhere.
4. **`exo_layer_dens_(N+1)` never updated.** `internal_set_layer_densities`
   populates `layer_dens_(1:N)` and `exo_layer_dens_(1:N)` but leaves
   `exo_layer_dens_(N+1)` at the constructor zero. The canonical
   `update()` sets it from `edge_val_(N+1) * hscale_`. Used by
   spherical geometry air-mass in `radiative_transfer%calculate`
   (air profile only). Probably not the bug — air column has zero
   above the extension anyway — but worth ruling out.
5. **Rosenbrock stiffness failure.** With `__absolute tolerance: 1e-12`
   on O/O1D and an initial state of exactly zero, the first Jacobian
   could be degenerate. Looser tolerances (`1e-10`) and seeding a
   small non-zero qO haven't been tried yet. But removing O1D
   entirely (variant #6 above) didn't help, which argues against
   pure solver stiffness as the culprit.

## Current state shipped

- `chapman_nox.yaml` in canonical MICM-v1 form with SI rate
  constants (correct per JPL); the explosion is reproducible.
- `chapman_nox_noO1D.yaml` reduced mechanism; also explodes.
- `chem_box` test case can be used for multi-day LNOx diurnal-cycle
  work with `lnox_o3.yaml` while this is being debugged.
- All multi-photolysis plumbing (mpas_tuvx.F multi-rate,
  `musica_set_photolysis_rates`, `j_<name>` diagnostic fields) is
  working correctly — confirmed by TUV-x rates appearing in the
  output with sensible altitude dependence from step 2 onward.
- Standalone MICM column model (`MUSICA/fortran/examples/`) is
  built and runs the canonical Chapman config successfully — use
  this as a reference oracle when debugging.

## Path forward

Two parallel lines of investigation:

**Line A — confirm MICM rate constants at step 1.** Briefly
instrument MICM (or dump `state%rate_constants_`) to confirm the
effective `k` for each reaction at step 1 is what we expect from
the j-values we fed in. Rules in/out hypothesis #2.

**Line B — accept step-1 photo rates as the trigger; ask why
TUV-x produces TOA rates for a 340-DU column.** Candidates:
hypothesis #1 (radiator refresh), #3 (missing edge values), #4
(exo layer density). Could also be reproduced in a pure-TUV-x
standalone driver fed the same profile.

Lower-risk workaround if neither A nor B resolves quickly: skip
chemistry on the very first step (let dynamics run once, then
allow chem to start). That sidesteps the bootstrap without
addressing the root cause. Not a real fix — flag it as mitigation
only.

## 2026-04-18 pm session: root cause pinned to stiffness

Two new shipped commits:
- Re-entrant `micm%solve` loop in `mpas_musica.F::musica_step` and
  `musica_step_ref`: if the solver returns early with
  `solver_stats%final_time() < time_step`, resubmit the remainder
  until the full `time_step` is covered. Matches the pattern in
  `MUSICA/fortran/examples/column_model.F90:217-229`.
- `config_chem_substeps` namelist option (default 1) and outer loop
  in `mpas_atm_chemistry.F::chemistry_step` that calls
  `musica_step(dt/N)` N times per MPAS step, with the TUV-x
  photolysis rates frozen across sub-steps. No MUSICA changes.

### The handoff plan's `relative_tolerance` proposal required cross-repo work

`set_backward_euler_solver_parameters` does not exist as a Fortran
binding in installed MUSICA-Fortran. Searched
`MUSICA-LLVM/fortran/{micm,state}.F90`,
`src/micm/{micm,state}_c_interface.cpp`, and `libmusica.a` symbols —
no `Set*SolverParameters`, no `SetRelativeTolerance`. Upstream
`BackwardEulerSolverParameters` does not even contain
`relative_tolerance_`; that scalar lives on `State` (default `1e-06`,
`micm-src/.../solver/state.hpp:34`) and has no C accessor. Pursuing
the proposal as written would need new entry points in MUSICA-LLVM.

### Sub-stepping alone does NOT fix the full Chapman run

Ran `chapman_nox.yaml` with `config_chem_substeps = 30` (dt = 0.1 s)
at 18:00 UTC. Result: **qO3 explodes identically** — 24000 → 9.4e7 ppb
at 5 min, same as `config_chem_substeps = 1`.

Reason: the R2 termolecular (O + O2 + M → O3 + M) has
`k2·[O2]·[M] ≈ 4.5e4 s⁻¹` at surface, so `τ_O ≈ 14 µs`. At dt = 0.1 s,
`dt/τ_O ≈ 1e4` — still massively stiff. Newton's multi-root pathology
persists. Shortening dt by finite factors cannot outrun a µs-scale
stiffness; you would need dt < 1 µs.

### Sanity tests — what the solver actually does

Three progressively-simpler mechanisms tested on `chem_box` at 18:00 UTC,
dt=3s, `config_chem_substeps = 1`:

**Test A: atom-non-conservative `O2 → 2 O3`.** Broken stoichiometry
(creates 4 O atoms per photolysis). qO3 mean grew 5e-6 → 0.29 kg/kg at
5 min; qO2 mean dropped 0.23 → 0.13; net O-atom mass change
+0.19 kg / kg air. **BE landed on an unphysical root specifically
because unbalanced stoichiometry gave the implicit equation extra roots
to find.** Lesson: sanity checks must preserve atom conservation or
they fail for uninformative reasons.

**Test B: atom-conservative decay-only `chapman_nox_no_O.yaml`.**
No [O], no [O1D], no production of O3 from O2. Reactions:
`O3 → (nothing)` (jO3_O sink), `NO + O3 → NO2 + O2`,
`NO2 → NO` (jNO2 sink). qO3 max decayed monotonically
24000 → 750 → 23 ppb (t = 0, 5, 10 min). qO2 unchanged. qNO/qNO2
fluctuate stably through the Leighton cycle. **No explosion.**
MICM/BE handles atom-conservative non-stiff chemistry cleanly.

**Test C: `chapman_nox_slow.yaml` — same topology, rates scaled 1e-6 on
R2 and R6.** `τ_O` 14 µs → 14 s, `τ_O1D` ~1 µs → ~1 s; no longer stiff
at dt = 3 s. Full species set {M, O, O1D, O2, O3, NO, NO2} and all 9
reactions present. Result: qO3 max 24000 → 1668 → 1660 ppb, qO rises
to 0.22 kg/kg at column top (unphysical equilibrium for the bogus
rates, but the system is on the attractor those rates define). **Atom
balance exact at every level, every timestep:
qO + qO2 + qO3 = 0.2314 kg/kg everywhere.** No runaway, no wrong root.

### Conclusion

Stiffness is the cause. The microsecond `[O]/[O3]` null cycle creates
a multi-root implicit equation at any practical dt; BE's Newton
iterate picks the non-physical root when started from a degenerate
state (`[O] ≈ 0` with full photolysis). MICM is *not* broken — on
atom-conservative non-stiff systems it integrates correctly, and when
Newton starts from a non-degenerate state on the physical attractor it
stays there.

### Implication: Newton stability on the attractor

BE's Newton iterate linearizes around its starting guess (typically
`y_old`). With `y_old` in a degenerate neighborhood ([O] ≈ 0, full
photolysis), the Jacobian is ill-conditioned — the loss term
`k2·[O]·[O2]·[M]` is dominated by `[O]` going to zero, so there is no
restoring force toward small [O], and the far-field attractor is
within reach. With `y_old = [O]_ss`, the Jacobian has active loss
terms and Newton's linearization lands on the nearest root — the
physical one.

This means: once the system is spun up to QSS, normal dt is safe. The
only unsafe moments are when something pushes the state into a
degenerate neighborhood (cold start, sunrise after long night with
[O] not at QSS, impulsive perturbations).

### Next test — warmup strategy

Run the first N MPAS chemistry steps with `config_chem_substeps` very
high (e.g. 3000 → dt = 0.001 s, below `τ_O` at all altitudes up to
stratosphere) so Newton is forced to the physical root every step and
[O] builds up to QSS. After N steps, drop `config_chem_substeps = 1`
and continue at the full 3 s outer dt; rely on attractor stability
to keep Newton on the physical manifold.

To implement without per-step namelist churn: add
`config_chem_warmup_steps` and `config_chem_warmup_substeps` options
and switch to `config_chem_substeps` once the counter elapses.

If this works, it's a cheap production fix for the cold-start case and
a clean model for handling sunrise in longer runs (same pattern, just
triggered by cos_sza transitions rather than step count).

## 2026-04-18 late-evening: pivoting to solver-API and QSS-seed tests

Built the cross-repo MICM tolerance-setting API that the handoff plan had
assumed existed:

- `MUSICA-LLVM/include/musica/micm/state_c_interface.hpp` +
  `src/micm/state_c_interface.cpp`: new `SetRelativeTolerance(state, value, error)`
  C entry point. Uses `std::visit` to set `state.relative_tolerance_` on
  whichever `StateVariant` the solver chose (VectorState / StandardState /
  GpuState). Mass-conservative wrt. the existing State object.
- `MUSICA-LLVM/fortran/micm/state.F90`: matching Fortran binding
  `set_relative_tolerance_c` and a `state_t%set_relative_tolerance(value, error)`
  method. No API churn elsewhere.
- Rebuilt MUSICA-LLVM and installed updated `libmusica.a`,
  `libmusica-fortran.a`, `libmechanism_configuration.a`, and `*.mod`
  files into `~/software`.
- `CheMPAS/src/core_atmosphere/Registry.xml`: added
  `config_micm_relative_tolerance` (default `1e-6`, MICM's default).
- `CheMPAS/src/core_atmosphere/chemistry/mpas_atm_chemistry.F`: reads
  the namelist option and passes it through to `musica_init`.
- `CheMPAS/src/core_atmosphere/chemistry/musica/mpas_musica.F`:
  `musica_init` now accepts `relative_tolerance` and calls
  `state%set_relative_tolerance(relative_tolerance, error)` on both
  the coupled and reference states immediately after `get_state`.

The API works and logs confirm the tolerance is applied.

### Result: tightening rel_tol does NOT fix the explosion

With BE and `config_micm_relative_tolerance = 1e-9`: bit-for-bit
identical explosion (qO3 24000 → 9.4e7 ppb at 5 min). Solver stats:
`accepted=1, rejected=0` per call — the adaptive controller never
triggers.

With BE and `rel_tol = 1e-15` (near machine precision): same.

**Why rel_tol is ineffective here.** From
`micm-src/include/micm/solver/backward_euler.inl:IsConverged`:

```
|residual| > small AND |residual| > abs_tol[i] AND |residual| > rel_tol * |Yn+1|
```

All three must hold for non-convergence. At the wrong root,
`|Yn+1|` for qO3 is ≈ 0.3 mol/m³, so `rel_tol * |Yn+1|` at
`rel_tol = 1e-15` is `3e-16` — Newton's residuals drop below that
trivially once converging. Tightening rel_tol makes Newton converge
*more precisely* to the wrong root; it does not force a step-size
reduction because the `!converged → H *= time_step_reductions[...]`
branch never fires.

### Result: Rosenbrock instead of BE

Switched `solver_type = RosenbrockStandardOrder` in
`mpas_musica.F::musica_init`. Rosenbrock has true embedded error
estimation (step-doubling), not Newton convergence, so it *should*
respond to tighter rel_tol by rejecting large H steps. Tested at
`rel_tol = 1e-9` and `rel_tol = 1e-15`:

- qO3 evolution: 24000 → 9.4e7 ppb at 5 min — identical to BE.
- Solver stats: `accepted=9, rejected=0` — same 9 internal sub-steps
  Rosenbrock took in Ubuntu Claude's earlier Line A test. Not a single
  rejection at any tolerance.

**Why Rosenbrock's error estimator is also ineffective here.** The
embedded estimate compares the full-order and lower-order methods'
predictions of `y_new` at the same H. Along the wrong-attractor
trajectory, both estimates agree — the step is "accurate" in the
sense that the two methods produce consistent answers. They just
consistently go to the wrong place. No purely consistency-based
error estimator can discriminate physical from non-physical roots.

### Result: physical QSS seeding of [O]

Extended `scripts/init_chapman.py` with `--qo-mode qss` (now the
default) that writes an altitude-dependent Chapman QSS [O] profile
instead of `[O]=1e-12` uniform. Profile computed from

    [O]_ss = (2·jO2·[O2] + jO3_O·[O3]) / (k2·[O2]·[M] + k3·[O3])

using AFGL MLS T and [air] profiles, the canonical chapman_nox.yaml
rate constants, and a daytime mid-lat SZA~58° j-value climatology
extracted from this plan doc's earlier run logs. Produces
`qO = 5e-24 kg/kg` at surface → `6.7e-8 kg/kg` at the stratopause —
seven orders of magnitude dynamic range, matching the physical
dependence on altitude.

Re-init'd `chem_box_init.nc` with this profile and reran. qO3 evolution:

- t=0: 5.07e-6 (AFGL)
- t=5m: 6.62e-2 mean
- t=10m: 7.22e-2 mean

**Bit-for-bit identical to the uniform-seed runs.** Newton ignores
the QSS starting guess; it finds the wrong root anyway.

### Why none of this worked: the Jacobian analysis

For the Chapman [O]/[O3] null cycle the Jacobian of
`d[O]/dt` w.r.t. `[O]` is

    ∂(d[O]/dt)/∂[O] = -k2·[O2]·[M] - k3·[O3] ≈ -k2·[O2]·[M]

which **does not depend on [O]**. At surface, this eigenvalue is
≈ `-7×10⁴ s⁻¹` regardless of whether `[O]=0`, `[O]=1e-12`, or
`[O]=[O]_ss`. The nonlinear regime — the one in which the implicit
equation `y_new = y_old + dt·f(y_new)` admits multiple physically
distinct roots — is entered whenever

    dt · ||J|| >> 1   ⇔   dt >> 14 µs

At `dt = 3 s`, `dt·||J|| ≈ 2×10⁵`. Deep in the multi-root regime.
No starting guess, tolerance setting, or solver choice can move the
implicit equation's root structure; all that machinery affects which
root Newton or Rosenbrock lands on within the convergence neighborhood
of their starting guess, but BE and Rosenbrock at this dt have the
wrong-root attractor as a *stable* fixed point of their respective
discretizations. Once in its basin of attraction (which is large
here), Newton/Rosenbrock converge to it.

### 2026-04-19 correction: standalone column tests do not reproduce

The late-evening conclusion above was too strong. Two standalone
MUSICA column-model tests were run on macOS, outside the CheMPAS-A
coupler, to check whether daylight cold start + Chapman stiffness is
enough to reproduce the chem_box explosion.

**Test 1 — canonical MUSICA Chapman, daylight cold start.**
Temporary copy of `MUSICA-LLVM/fortran/examples/column_model.F90`
with only:

```fortran
START_UTC = 18.0_dk
```

Everything else stayed canonical: `configs/v1/chapman/config.json`,
TUV v5.4 column profiles, 15 min chemistry interval, `[O]=[O1D]=0`
initially. Result: no explosion. O3 stayed physical:

```
time_hr   O3_mean      O3_max       O_max        surface jO3(3P)
0.000     1.115e-06    6.902e-06    0.000e+00    0.000e+00
0.250     1.118e-06    6.907e-06    1.038e-08    4.852e-04
1.000     1.131e-06    6.920e-06    1.736e-08    4.913e-04
24.000    1.228e-06    6.995e-06    1.180e-07    4.815e-04
```

**Test 2 — CheMPAS-A `chapman_nox.yaml` in the standalone column
model.** Temporary column-model main loaded
`../v1/chapman_nox.yaml`, mapped TUV v5.4 photolysis channels into
`PHOTO.jO2`, `PHOTO.jO3_O`, `PHOTO.jO3_O1D`, and `PHOTO.jNO2`,
initialized NO/NO2 from the same broad profile shape as
`scripts/init_chapman.py`, and ran a chem_box-like daylight stress
case:

```fortran
DT_PHOTO = 3.0_dk
SIM_LENGTH = 600.0_dk
START_UTC = 18.0_dk
```

Result: no explosion. O3 stayed near the physical column profile:

```
step  time_s   O3_mean      O3_max       O_max        NO_mean      NO2_mean
0       0.0    1.115e-06    6.902e-06    0.000e+00    5.915e-10   1.380e-09
1       3.0    1.115e-06    6.903e-06    3.612e-09    6.247e-10   1.347e-09
2       6.0    1.115e-06    6.903e-06    5.199e-09    6.559e-10   1.316e-09
20     60.0    1.115e-06    6.906e-06    9.456e-09    9.561e-10   1.016e-09
100   300.0    1.116e-06    6.908e-06    9.813e-09    1.070e-09   9.015e-10
200   600.0    1.117e-06    6.909e-06    1.011e-08    1.071e-09   9.007e-10
```

The temporary files were:

- `/tmp/column_model_daylight.F90`
- `/tmp/column_model_daylight_run/configs/tuvx/column_model_fortran.csv`
- `/tmp/column_model_chapman_nox.F90`
- `/tmp/column_model_chapman_nox_run/configs/tuvx/column_model_fortran.csv`

These tests invalidate the claim that the mechanism, solver choice,
or daylight cold start alone explains the chem_box qO3 explosion.
`chapman_nox.yaml` itself is stable in standalone MICM/TUV-x at a 3 s
daylight cadence.

### Revised conclusion

The remaining suspect is CheMPAS-A-specific coupling or host-state
construction, not the raw MICM mechanism:

- MPAS → MICM concentration conversion or grid-cell ordering
- CheMPAS-A `state%rate_parameters` assignment
- CheMPAS-A TUV from-host profile path (`mpas_tuvx.F`) versus the
  standalone TUV v5.4 profile setup
- MPAS density, pressure, temperature, or vertical-coordinate inputs
- A mismatch between chem_box layer ordering and TUV/MICM column
  expectations

Do **not** proceed directly to QSS substitution as the next primary
fix. QSS substitution may still be useful eventually, but it would be
a scientific mechanism change and must go through human review.

### 2026-04-19 exact-input MICM discriminator

The immediate discriminator above was run on macOS with a tiny
standalone MICM program using the exact cell-1 / level-1 step-1
chem_box inputs:

```
T = 299.09 K
P = 98321 Pa
air_density = 39.2 mol/m3
O2 = 8.21 mol/m3
O = 0
O1D = 0
O3 = 1.05e-6 mol/m3
NO = 5.88e-10 mol/m3
NO2 = 1.37e-9 mol/m3
jO2 = 3.92e-38 s-1
jO3_O = 3.63e-4 s-1
jO3_O1D = 8.87e-6 s-1
jNO2 = 6.74e-3 s-1
dt = 3.0 s
solver = RosenbrockStandardOrder
relative_tolerance = 1e-15
```

Result: no explosion. MICM advanced the full 3 s in one call
(`Converged`, 9 accepted, 0 rejected) and produced:

```
before: O3 = 1.05000000e-06, O = 0,              NO = 5.88000000e-10, NO2 = 1.37000000e-09
after : O3 = 1.05000692e-06, O = 5.66545016e-15, NO = 5.94930308e-10, NO2 = 1.36306969e-09
```

O-atom and N-atom totals were conserved. A second standalone run
cloned the same exact state over 3,840 MICM cells (matching the
64-cell × 60-level chem_box count) and used the same MICM stride
formulae as the CheMPAS-A coupler:

```
after: O3 mean/range = 1.05000692e-06 / 1.05000692e-06 .. 1.05000692e-06
       O max         = 5.66545016e-15
       NO mean       = 5.94930308e-10
       NO2 mean      = 1.36306969e-09
```

The temporary files were:

- `/tmp/micm_exact_chapman_nox.F90`
- `/tmp/micm_exact_chapman_nox_3840.F90`
- `/tmp/micm_exact_run/configs/v1/chapman_nox.yaml`

This rules out MICM behavior for the logged surface cell and rules
out a generic vector-size/stride failure for a CheMPAS-A-sized MICM
state. The chem_box explosion must depend on some part of the full
CheMPAS-A host state that the single-cell exact replay did not cover:
another level/cell, a whole-column layout/profile issue, a
post-solve CheMPAS-A copy-back issue, or a difference in how the
CheMPAS-A driver calls/logs the solve.

Next discriminator: dump the full 3,840-cell MICM state immediately
before the first CheMPAS-A `micm%solve` call (conditions,
concentrations, and rate parameters), replay that exact state in a
standalone program, and compare the full-state post-solve values
against CheMPAS-A before any MPAS copy-back.

### 2026-04-19 full-state replay: MICM reproduces the failure

The full-state discriminator above was run with temporary
rank-qualified dump instrumentation around the first coupled
`micm%solve` call in `mpas_musica.F`. Because CheMPAS-A is MPI
decomposed, each rank owns a local MICM state:

```
rank 0: 2400 MICM cells  (40 local MPAS columns x 60 levels)
rank 1: 2400 MICM cells
rank 2: 2520 MICM cells  (42 local MPAS columns x 60 levels)
rank 3: 2520 MICM cells
rank 4: 2400 MICM cells
rank 5: 2520 MICM cells
rank 6: 2520 MICM cells
rank 7: 2520 MICM cells
```

A standalone replay driver loaded each rank's dumped conditions,
concentrations, and rate parameters into a fresh MICM state, ran the
same 3 s `RosenbrockStandardOrder` solve at `relative_tolerance =
1e-15`, and wrote its post-solve state. The replayed concentration
arrays matched the CheMPAS-A post-solve dumps bit-for-bit on every
rank (`max_abs_diff = 0` for all ranks).

All ranks reproduce the explosion outside MPAS:

```
rank  cells  O3_mean before  O3_mean after  O3_max after
0     2400   2.871e-06       9.507e-02      3.150e-01
1     2400   2.871e-06       9.507e-02      3.150e-01
2     2520   2.871e-06       9.507e-02      3.150e-01
3     2520   2.871e-06       9.507e-02      3.150e-01
4     2400   2.871e-06       9.507e-02      3.150e-01
5     2520   2.871e-06       9.507e-02      3.150e-01
6     2520   2.871e-06       9.507e-02      3.150e-01
7     2520   2.871e-06       9.507e-02      3.150e-01
```

This rules out MPAS copy-back and CheMPAS-A-specific solve-call
plumbing. The exact state handed to MICM is sufficient to reproduce
the first-step failure in a standalone program.

The failure was reduced further. Rank 0, local cell 1 / level 1
still stays stable as before, but rank 0, local cell 2 / level 2
explodes by itself as a one-cell standalone MICM solve. Its inputs
are nearly identical to the stable surface cell:

```
T = 296.542333817 K
P = 94417.324400994 Pa
air_density = 37.9828906717 mol/m3
O = 0
O2 = 7.95587740009 mol/m3
O3 = 1.03579990236e-6 mol/m3
O1D = 4.06074210566e-22 mol/m3
NO = 5.69633226737e-10 mol/m3
NO2 = 1.32914419572e-9 mol/m3
jNO2 = 6.91433685646e-3 s-1
jO2 = 3.54345945701e-37 s-1
jO3_O = 3.66372021585e-4 s-1
jO3_O1D = 9.25367724139e-6 s-1
```

One 3 s MICM solve gives:

```
O = 1.51774137591e-13
O2 = 7.48634752522
O3 = 3.13020686479e-1
O1D = 1.59265660751e-6
NO = 7.95534515703e-7
NO2 = 0
```

The surface-level exact replay used earlier (`T=299.09 K`, `O2=8.21`,
`jNO2=6.74e-3`, `jO3_O1D=8.87e-6`) is stable, while the immediately
adjacent level-2 state is not. The next debugging target is therefore
a minimal one-cell MICM reproducer for this level-2 state, not any
MPAS/TUV/copy-back path. Use it to bracket solver choice,
time-step length, tolerance, and mechanism variants before making any
scientific mechanism change.

### 2026-04-19 root cause: MICM rate-parameter storage order

The one-cell level-2 reproducer is now tracked:

- `test_cases/chem_box/reproducers/chapman_nox_level2_reproducer.F90`
- `test_cases/chem_box/reproducers/run_chapman_nox_level2_reproducer.sh`

It exposed the actual issue: the failure is not a physical
level-2 MICM instability. It is a CheMPAS-A rate-parameter storage-order
mismatch.

For `chapman_nox.yaml`, `state%rate_parameters_ordering%name(i)` and
`state%rate_parameters_ordering%index(name)` are not the same order.
TUV-x enumerates reactions as:

```
jO2, jO3_O1D, jO3_O, jNO2
```

but MICM stores `chapman_nox` rate parameters at:

```
PHOTO.jO2     -> 1
PHOTO.jO3_O   -> 2
PHOTO.jO3_O1D -> 3
PHOTO.jNO2    -> 4
```

Before the fix, `musica_cache_photo_indices` searched the names by
iteration and cached the loop counter `j`, not the MICM storage index.
That wrote the physically correct TUV-x rates into the wrong slots:

```
MICM PHOTO.jO2     received jNO2    = 6.914e-3 s-1
MICM PHOTO.jO3_O   received jO2     = 3.543e-37 s-1
MICM PHOTO.jO3_O1D received jO3_O   = 3.664e-4 s-1
MICM PHOTO.jNO2    received jO3_O1D = 9.254e-6 s-1
```

The tracked reproducer has modes that make this explicit:

```
# current-code pre-fix equivalent: species by MICM name, rates by raw slots
test_cases/chem_box/reproducers/run_chapman_nox_level2_reproducer.sh \
  3.0 rosenbrock 1e-15 name_species_raw_rates

# corrected physical state: species and rates by MICM name/index
test_cases/chem_box/reproducers/run_chapman_nox_level2_reproducer.sh \
  3.0 rosenbrock 1e-15 name_mapped
```

Results:

```
mode                    dt       solver       O3 after (mol/m3)
name_species_raw_rates  3.0 s    Rosenbrock   3.13020686479e-1
name_mapped             3.0 s    Rosenbrock   1.03580833021e-6
```

The raw-rate state also explodes with `BackwardEulerStandardOrder`
(`O3 = 2.982e-1 mol/m3` after 3 s), and remains strongly
timestep-sensitive under Rosenbrock:

```
dt (s)   raw-rate O3 after (mol/m3)
3.0      3.130e-1
0.1      1.098e-2
0.01     1.099e-3
0.001    1.094e-4
0.0001   1.040e-5
0.00001  1.336e-6
```

That bracket explains why the original debugging looked like a stiff
timestep/implicit-root problem: the miswired rates put the NO2
photolysis rate into the O2 photolysis slot, creating a large atomic-O
source.

### Fix and verification

`src/core_atmosphere/chemistry/musica/mpas_musica.F` now resolves
rate-parameter storage with
`state%rate_parameters_ordering%index(name, error)` in both:

- `musica_cache_photo_indices` for TUV-x photolysis rates.
- `assign_rate_parameters` for generic USER/LOSS/PHOTO defaults.

This is a chemistry coupling change and should be reviewed under the
project's human review gates.

Verification:

```
test_cases/chem_box/reproducers/run_chapman_nox_level2_reproducer.sh \
  3.0 rosenbrock 1e-15 name_species_raw_rates
```

reproduces the old bad slot assignment. The same state with
`name_mapped` is stable.

The MUSICA atmosphere build was checked with:

```bash
eval "$(scripts/check_build_env.sh --export)" && make -j8 llvm \
  CORE=atmosphere \
  PIO="$PIO" \
  NETCDF="$NETCDF" \
  PNETCDF="$PNETCDF" \
  PRECISION=double \
  MUSICA=true
```

The first sandboxed build compiled `mpas_musica.F` but failed later
when `checkout_externals` could not resolve GitHub for `MMM-physics`.
The rerun with network access completed and linked `atmosphere_model`
against MUSICA-Fortran 0.13.0.

Coupled chem_box verification with the rebuilt executable:

- 3 s run in `/tmp/chem_box_rate_index_fix_run`:
  - Cached indices in the log are now `jO2 -> 1`,
    `jO3_O1D -> 3`, `jO3_O -> 2`, `jNO2 -> 4`.
  - `qO3` max in `output.nc`: initial `3.96927497467e-5 kg/kg`,
    after 3 s `3.96024675947e-5 kg/kg`.
  - Old pre-fix first-step log for the same case had
    `global min, max scalar 9 ... 0.211200176249252E-01`.
- 5 min run in `/tmp/chem_box_rate_index_fix_5min_run`:
  - `qO3` max in `output.nc`: initial `3.96927497467e-5 kg/kg`,
    after 5 min `3.91480558608e-5 kg/kg`.
  - Final log line for scalar 9:
    `global min, max scalar 9 ... 0.391480558608163E-04`.
  - The run finished with 0 logged errors and 0 critical errors.

### Current state shipped

- `SetRelativeTolerance` API in MUSICA-LLVM (generally useful for
  other stiff chemistry, not specifically for Chapman).
- `config_micm_relative_tolerance` and `config_chem_substeps`
  namelist plumbing in CheMPAS-A.
- `scripts/init_chapman.py --qo-mode {qss,uniform,zero}` with
  altitude-dependent QSS [O] seeding as the default.
- Solver default in `mpas_musica.F` flipped to
  `RosenbrockStandardOrder`; revert to `BackwardEulerStandardOrder`
  if mass balance becomes a concern in production runs.
- Rate-parameter mapping in `mpas_musica.F` now uses MICM storage
  indices instead of ordering iteration positions.

The Chapman + NOx chem_box explosion is fixed by the rate-parameter
mapping change in the 3 s and 5 min daylight verification runs above.
