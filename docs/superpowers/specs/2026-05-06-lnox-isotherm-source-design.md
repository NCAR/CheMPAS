# LNOx isotherm-gated source design

**Date:** 2026-05-06
**Status:** Proposed
**Scope:** Add an isotherm-based gating mode to the existing CheMPAS-A
lightning-NOx source, faithful to the LNOx.md description, while preserving
the current altitude-based behavior bit-for-bit.

## Background

`LNOx.md` describes a constant lightning-generated NO source applied between
the 262.15 K and 233.15 K isotherms (the mixed-phase layer where charge
separation drives lightning), calibrated to produce ~1 ppbv NOx at cloud
top in DC3-like supercells.

The existing module `src/core_atmosphere/chemistry/mpas_lightning_nox.F`
already provides a lightning-NOx source, but with a different formulation:
altitude-window gating (`z_min`–`z_max`) and a source rate that scales
linearly with updraft excess `(w − w_threshold)/w_ref`. That formulation
was inherited from DAVINCI-MPAS and is useful, but it is not what the
DC3 literature reflected in LNOx.md uses.

## Goal

Add the LNOx.md formulation as a selectable mode while keeping the existing
altitude-mode behavior available and unchanged. Run an end-to-end test of
the new isotherm mode in the supercell test case and verify the NOx
enhancement is spatially confined to the mixed-phase layer with peak NOx
of order 1 ppbv.

## Non-goals

- No change to the MICM mechanism (`micm_configs/lnox_o3.yaml`).
- No change to TUV-x photolysis configuration.
- No change to MPAS dynamics, microphysics, or advection.
- No new test framework — testing follows the existing build + run +
  visualize pattern in `RUN.md` and `docs/chempas/guides/VISUALIZE.md`.
- Source-rate auto-calibration is out of scope; calibration is a manual
  retune-and-rerun loop.

## Design

### Gating-mode switch

`mpas_lightning_nox.F` gains a single integer mode flag, parsed once at
init time from a new namelist option:

```
config_lnox_gating_mode = 'altitude'   ! default — current behavior
                       | 'isotherm'    ! LNOx.md formulation
```

Internally the module stores `mode = MODE_ALTITUDE | MODE_ISOTHERM` so
the per-cell loop branches on an integer, not a string.

### Behavior per mode

| Mode | Gate | Rate |
|---|---|---|
| `altitude` (default) | `z_min ≤ z ≤ z_max` AND `w > w_threshold` | `S = source_rate · (w − w_threshold) / w_ref` |
| `isotherm` (new) | `T_min ≤ T ≤ T_max` AND `w > w_threshold` | `S = source_rate` (constant) |

The `w > w_threshold` requirement in isotherm mode is a hard on/off gate
(no rate scaling), so emission is still tied to active convection but
the magnitude is flat — faithful to LNOx.md's "constant" framing.

### New namelist options

Added to `Registry.xml` under the `musica` group:

```
config_lnox_gating_mode  string  default = 'altitude'
config_lnox_T_min        real    default = 233.15  ! K, cold isotherm
config_lnox_T_max        real    default = 262.15  ! K, warm isotherm
```

Existing options (`config_lnox_source_rate`, `config_lnox_w_threshold`,
`config_lnox_w_ref`, `config_lnox_z_min`, `config_lnox_z_max`,
`config_lnox_j_no2`, `config_lnox_nox_tau`) are retained. `w_ref`,
`z_min`, `z_max` are unused in isotherm mode but keep their meaning in
altitude mode.

### Threading temperature through

The current `lightning_nox_inject` signature is

```
subroutine lightning_nox_inject(dt, scalars, w, zgrid, &
                                nVertLevels, nCells, time_lev)
```

We add an **optional** `temperature(:,:)` argument:

```
subroutine lightning_nox_inject(dt, scalars, w, zgrid, &
                                nVertLevels, nCells, time_lev, &
                                temperature)
    real(kind=RKIND), intent(in), optional :: temperature(:,:)
```

The call site in `mpas_atm_chemistry.F` computes T from
`theta_m / (1 + rvord*qv) * exner` (the same formula already used in
`chemistry_from_MPAS` and `chemistry_to_MPAS`) into a local
`(nVertLevels, nCells)` array, and passes it down. The computation is
gated on `lnox_active .and. mode == MODE_ISOTHERM` so altitude-mode runs
do no extra work.

In altitude mode the optional argument is omitted (or ignored), and the
inner loop is bit-identical to today's code.

### Module boundaries

- `mpas_lightning_nox` does not touch pools — it operates on plain Fortran
  arrays. Easy to reason about, single-purpose.
- `mpas_atm_chemistry` is the only place that pulls T out of the
  diag/state pools; the LNOx module receives a pre-computed `temperature`
  array.
- T is computed once per chemistry step and passed by reference; no
  module-level temperature state.

## Test plan

### Test case

Supercell (`test_cases/supercell/`, 2 h, ~300 m surface → ~1 km top, 60
stretched levels to 50 km, Kessler microphysics, Oklahoma coordinates
35.86 N / −97.93 W). Already has the LNOx + MICM + TUV-x scaffolding
commented in.

### Calibration starting point

LNOx.md target: ~1 ppbv NOx at cloud top. With a constant source and
~1000 s for an air parcel to traverse the 262–233 K mixed-phase layer
in a strong updraft, a starting rate of

```
config_lnox_source_rate = 1.0e-3   ! ppbv/s
```

gives an order-of-magnitude-correct first run. Refinement is a manual
retune-and-rerun loop, not part of this design.

### Verification steps

1. **Build:** `eval "$(scripts/check_build_env.sh --export)" && make -j8 llvm
   CORE=atmosphere MUSICA=true PRECISION=double` — clean build, no new
   warnings in `mpas_lightning_nox.F` or `mpas_atm_chemistry.F`.
2. **Regression (altitude mode):** rerun the supercell with the existing
   altitude-mode `&musica` block uncommented; LNOx output (qNO field)
   matches a pre-change baseline within numerical noise (~1e-12 relative).
3. **New behavior (isotherm mode):** rerun the supercell with the new
   isotherm-mode `&musica` block uncommented and `source_rate = 1.0e-3
   ppbv/s`. Visually verify with `scripts/plot_lnox_o3.py`:
   - NOx enhancement confined to the 262–233 K layer (~5–9 km in this
     setup);
   - peak NOx in the convective core of order 1 ppbv (within a factor
     of a few — retuning is OK);
   - O₃ shows the expected small tropospheric-NOx response;
   - no NaN, no negative tracer values.

If the regression check fails, that's a refactor bug — fix before
continuing. If the calibration is off by an order of magnitude, retune
`source_rate` and rerun; that is not a code bug.

### Test-case namelist additions

Add a second commented-out `&musica` block to
`test_cases/supercell/namelist.atmosphere` (next to the existing altitude
block) titled "LNOx tropospheric development setup (isotherm gating,
LNOx.md formulation)" and including the new options.

## Error handling & edge cases

- **Unknown gating mode:** if `config_lnox_gating_mode` is neither
  `"altitude"` nor `"isotherm"`, `lightning_nox_init` logs a critical
  message and sets `lnox_active = .false.` (same fall-through pattern
  as the existing `source_rate <= 0` guard).
- **Isotherm-mode parameter validation:** require `T_min > 0` and
  `T_min < T_max`; otherwise log and disable.
- **Missing temperature in isotherm mode:** the call site already guards
  the inject call on `associated(scalars) .and. associated(w) .and.
  associated(zgrid)`; extend that guard to cover `theta_m`, `exner`, and
  `index_qv` so a bad pool state degrades to a no-op rather than a crash.
- **Altitude mode unchanged:** the new `temperature` argument is optional;
  altitude-mode callers do not need to compute T, and existing
  altitude-mode runs stay bit-identical.

## Files touched

| File | Change |
|---|---|
| `src/core_atmosphere/Registry.xml` | Add `config_lnox_gating_mode`, `config_lnox_T_min`, `config_lnox_T_max` to the `musica` nml group |
| `src/core_atmosphere/chemistry/mpas_lightning_nox.F` | Add mode flag, isotherm branch in inject loop, optional `temperature` arg, init-time mode validation and logging |
| `src/core_atmosphere/chemistry/mpas_atm_chemistry.F` | Compute `temperature(nVertLevels,nCells)` from `theta_m / exner / qv` when LNOx is active in isotherm mode; pass to `lightning_nox_inject` |
| `test_cases/supercell/namelist.atmosphere` | Add a second commented-out `&musica` block for the isotherm-mode setup |

No deletions. No changes to MICM YAML, TUV-x JSON, or any plotting script.

## Open questions

None blocking. Calibration of the source rate is expected to need one or
two retunes after the first end-to-end run; that is not a design
question.
