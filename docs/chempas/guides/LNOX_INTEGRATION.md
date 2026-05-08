# LNOx Integration Summary

This note describes CheMPAS-A's lightning-NOx (LNOx) source scheme as
it currently stands in `src/core_atmosphere/chemistry/mpas_lightning_nox.F`.
It supersedes the historical `LNOx.md` note at the repository root,
which is preserved there as the original DC3 motivation record.

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
| `config_lnox_gating_mode` | character | `'altitude'` | both | Selects the gate; `'altitude'` or `'isotherm'`. Unknown values disable the source and emit a log message. |
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

For altitude mode, the DAVINCI-era working value `source_rate = 0.5`
(paired with the Registry defaults `w_threshold = 5.0`, `w_ref = 10.0`)
produces a visually similar enhancement on the supercell case;
calibration there is also a manual loop.

A regression-suite reference for both modes is planned but not yet
present in this branch — see
[docs/superpowers/specs/2026-04-19-regression-suite-design.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/superpowers/specs/2026-04-19-regression-suite-design.md).

## See also

- [`LNOx.md`](https://github.com/NCAR/CheMPAS-A/blob/develop/LNOx.md) — original DC3 motivation note
- [docs/superpowers/specs/2026-05-06-lnox-isotherm-source-design.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/superpowers/specs/2026-05-06-lnox-isotherm-source-design.md) — design of the isotherm-mode branch
- [docs/tutorial/02-supercell.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/tutorial/02-supercell.md) — Chapter 2 §2.6 worked examples for both modes
- [docs/chempas/musica/MUSICA_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/musica/MUSICA_INTEGRATION.md) — MUSICA / MICM coupling
- [docs/chempas/guides/TUVX_INTEGRATION.md](https://github.com/NCAR/CheMPAS-A/blob/develop/docs/chempas/guides/TUVX_INTEGRATION.md) — TUV-x photolysis (the `config_lnox_j_no2` fallback path)
