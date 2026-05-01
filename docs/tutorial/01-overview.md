# Chapter 1: Overview

```{admonition} Work in progress
:class: warning

This chapter is being actively written. Commands and cross-references
are provisional and may change.
```

The CheMPAS-A Tutorial walks through CheMPAS-A's idealized chemistry test
cases. Where the [User's Guide](../users-guide/index.rst)
is reference-style — a verbatim port of the upstream MPAS-Atmosphere
documentation — this tutorial is narrative: run the case, look at the
output, understand what the chemistry is doing.

## What this tutorial assumes

- `atmosphere_model` is built. See `BUILD.md` in the repository root
  and [Chapter 3 of the User's Guide](../users-guide/03-building.md).
- `~/Data/CheMPAS/<case>/` is set up with the namelist, streams, graph
  partition, and (where needed) initial-condition files. See `RUN.md`
  in the repository root and `test_cases/README.md`.
- The conda environment `mpas` is available for plotting:
  `conda activate mpas`.

## Python environment for standalone examples

The MPAS-coupled runs in §§2.5, 2.6, and 3.6 only need the base
`mpas` conda environment (`numpy`, `xarray`, `matplotlib`, `netCDF4`)
for plotting. The standalone MUSICA-Python examples in §§2.10, 2.11,
and 3.10 need three additional packages:

```bash
conda activate mpas
pip install musica ussa1976 ephem
```

- `musica` — MUSICA-Python bindings: MICM solver, TUV-x calculator,
  mechanism-configuration parser.
- `ussa1976` — US Standard Atmosphere 1976 temperature / pressure
  profiles, used by the column model to set per-cell environmental
  conditions.
- `ephem` — solar position (zenith angle) from latitude / longitude
  / UTC time, used by the column model to drive TUV-x photolysis
  through the diurnal cycle.

The standalone-example sections each link back here for the install;
no need to re-run `pip` between sections.

## Chapters

- [Chapter 2: Supercell with ABBA and LNOx](02-supercell.md) — idealized
  deep convection, run with two MUSICA/MICM mechanisms, with a
  side-by-side comparison.
- [Chapter 3: Chapman + NOx Photostationary State](03-chapman-nox.md) —
  small-domain Chapman cycle plus NOx, where the analytical PSS solution
  is a clean numerical sanity check.

## Verifying numerically

The tutorial focuses on what each run looks like. For numerical match
against tracked reference values, use the regression suite once it is
implemented. Its design is captured in
`docs/superpowers/specs/2026-04-19-regression-suite-design.md`; the
`scripts/regression.py` entry point and reference YAML files are not
present in this branch yet.

Until that lands, use the explicit log checks and plotting commands in
Chapters 2 and 3.
