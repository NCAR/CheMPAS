# Idealized Test Cases

Reference namelists and streams configurations for MPAS idealized test cases.
These files are tracked in the repo; the actual run data lives in `~/Data/CheMPAS/`.

## Data Download

Download and extract the three test cases from NCAR:

```bash
mkdir -p ~/Data/CheMPAS && cd ~/Data/CheMPAS
curl -LO https://www2.mmm.ucar.edu/projects/mpas/test_cases/v7.0/supercell.tar.gz
curl -LO https://www2.mmm.ucar.edu/projects/mpas/test_cases/v7.0/mountain_wave.tar.gz
curl -LO https://www2.mmm.ucar.edu/projects/mpas/test_cases/v7.0/jw_baroclinic_wave.tar.gz
for f in *.tar.gz; do tar xzf "$f"; done
rm *.tar.gz
```

## Test Cases

| Case | Init Case | Mesh | Cells | Levels | dt (s) | Duration |
|------|-----------|------|-------|--------|--------|----------|
| `supercell/` | 5 | ~500 m | ~40k | 60 (stretched 0–50 km) | 3 | 2 hours |
| `mountain_wave/` | 6 | ~577 m | ~2k | 70 | 6 | 5 hours |
| `jw_baroclinic_wave/` | 2 | 120 km | 40,962 | 26 | 450 | 16 days |
| `chem_box/` | 5 | 500 m periodic 8×8 | 64 | 60 (stretched 0–50 km) | 3 | 1 hour |
| `chapman_nox_global/` | (reuses JW init, see below) | 120 km | 40,962 | 26 | 450 | 24 hours |

The supercell vertical grid is read from `test_cases/supercell/supercell_zeta_levels.txt`
(61 edge heights in metres) via the `config_specified_zeta_levels` namelist option.
Regenerate with `scripts/gen_zeta_levels.py --top 50000 --nlevels 60 --stretch 1.25`.

The chem_box case is a chemistry-focused 64-cell periodic box that
reuses the supercell sounding and zeta profile. There is no NCAR
tarball — build the mesh and partitions locally with `planar_hex`
+ `MpasMeshConverter.x` + `gpmetis` (all in the `mpas` conda env).
See `docs/chempas/plans/2026-04-18-chapman-nox-chem-box-issue.md` for the
exact reproduction steps and the chemistry configs it pairs with.

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

## Setup and Initialization

After downloading, copy the tracked configs and initialize each case:

```bash
# Copy reference configs (with io_type="netcdf") to run directories.
# For the supercell case this also copies supercell_zeta_levels.txt, which
# the init step reads when building the 60-level stretched grid.
for case in supercell mountain_wave jw_baroclinic_wave; do
  cp test_cases/$case/* ~/Data/CheMPAS/$case/
  ln -sf ~/EarthSystem/CheMPAS-A/init_atmosphere_model ~/Data/CheMPAS/$case/
  ln -sf ~/EarthSystem/CheMPAS-A/atmosphere_model ~/Data/CheMPAS/$case/
done

# Initialize each case
for case in supercell mountain_wave jw_baroclinic_wave; do
  cd ~/Data/CheMPAS/$case
  mpiexec -n 4 ./init_atmosphere_model
  cd -
done
```

## Available Partition Files (MPI ranks)

| Case | Partitions |
|------|-----------|
| supercell | 2, 4, 8, 12, 16, 24, 32 |
| mountain_wave | 2, 4, 6, 8 |
| jw_baroclinic_wave | 2, 4, 6, 8, 12, 16, 24 |

## Running

See [RUN.md](../RUN.md) for run instructions and verification steps.

## Files Tracked Here

For each test case:
- `namelist.init_atmosphere` — initialization namelist
- `streams.init_atmosphere` — initialization I/O streams
- `namelist.atmosphere` — model run namelist
- `streams.atmosphere` — model run I/O streams (with `io_type="netcdf"`)
- `stream_list.atmosphere.output` — output variable list

## Data Source

All test case data from [NCAR MPAS idealized test cases (v7.0)](https://www2.mmm.ucar.edu/projects/mpas/site/access_code/idealized.html).
