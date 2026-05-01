# Claude Code Project Configuration

## Project Overview

CheMPAS-A (Chemistry for MPAS - Atmosphere) is a standalone project derived from [NCAR/MPAS-Model-ACOM-dev](https://github.com/NCAR/MPAS-Model-ACOM-dev), itself a fork of [MPAS-Dev/MPAS-Model](https://github.com/MPAS-Dev/MPAS-Model). It extends the Model for Prediction Across Scales (MPAS) with integrated MUSICA/MICM atmospheric chemistry, enabling coupled atmospheric-chemistry modeling on MPAS's unstructured mesh. CheMPAS-A is an independent project and is not intended to sync with the upstream repositories.

## Key Documentation

- `docs/chempas/architecture/ARCHITECTURE.md` - High-level system architecture
- `BUILD.md` - Build system documentation (includes LLVM/macOS instructions)
- `RUN.md` - Test case execution instructions
- `docs/chempas/guides/VISUALIZE.md` - Chemistry visualization tools and workflows
- `docs/chempas/architecture/COMPONENTS.md` - Detailed component descriptions
- `docs/chempas/musica/MUSICA_INTEGRATION.md` - MUSICA/MICM coupling details
- `docs/chempas/musica/MUSICA_API.md` - MUSICA Fortran API reference
- `docs/chempas/results/TEST_RUNS.md` - Test run documentation

## Sister Project Reference

- `~/EarthSystem/DAVINCI-MPAS/` - Sister project with prior lightning-NOx/O3
  implementation work.
- Start with:
  - `PLAN.md` (Phase 6 LNOx-O3 details)
  - `SCIENCE.md` (physics assumptions and validation framing)
  - `DC3.md` (observational context and targets)

## Build Configuration

CheMPAS-A builds on two platforms. The preflight script auto-detects the
compiler toolchain (flang or gfortran) and sets paths accordingly:

```bash
scripts/check_build_env.sh          # report mode — shows what it found
eval "$(scripts/check_build_env.sh --export)"   # export mode — sets env vars
```

`PKG_CONFIG_PATH` must be present in the same shell invocation as `make`.
The Makefile uses `$(shell pkg-config ...)` during parse, so exporting it
in a separate shell and then invoking `make` later is not sufficient.

### macOS (LLVM/flang)

Resolved environment:
- `NETCDF=/opt/homebrew`
- `PNETCDF=/Users/fillmore/software`
- `PIO=/Users/fillmore/software`
- `PKG_CONFIG_PATH=/Users/fillmore/software/lib/pkgconfig`
- Make target: `llvm`

```bash
eval "$(scripts/check_build_env.sh --export)" && make -j8 llvm \
  CORE=atmosphere PIO="$PIO" NETCDF="$NETCDF" PNETCDF="$PNETCDF" \
  PRECISION=double MUSICA=true

eval "$(scripts/check_build_env.sh --export)" && make -j8 llvm \
  CORE=init_atmosphere PIO="$PIO" NETCDF="$NETCDF" PNETCDF="$PNETCDF" \
  PRECISION=double
```

### Ubuntu (GCC/gfortran via conda)

Requires the `mpas` conda environment (`conda activate mpas`).

Resolved environment:
- `NETCDF=$CONDA_PREFIX` (miniconda3/envs/mpas)
- `PNETCDF=$CONDA_PREFIX`
- `PIO=$HOME/software`
- `PKG_CONFIG_PATH=$HOME/software/lib/pkgconfig`
- Make target: `gfortran`

```bash
eval "$(scripts/check_build_env.sh --export)" && make -j8 gfortran \
  CORE=atmosphere PIO="$PIO" NETCDF="$NETCDF" PNETCDF="$PNETCDF" \
  PRECISION=double MUSICA=true

eval "$(scripts/check_build_env.sh --export)" && make -j8 gfortran \
  CORE=init_atmosphere PIO="$PIO" NETCDF="$NETCDF" PNETCDF="$PNETCDF" \
  PRECISION=double
```

Dependencies installed via conda-forge: `gcc gxx gfortran cmake openmpi
libnetcdf netcdf-fortran libpnetcdf libblas liblapack pkg-config make`.
PIO and MUSICA built from source into `~/software`.

### Important (both platforms)

- Always use `-j8` for parallel compilation.
- MUSICA-Fortran must be built with the same Fortran compiler as CheMPAS-A.
  Mixing flang and gfortran `.mod` files causes link failures.
- `PNETCDF` is required for the normal top-level build.
- A full atmosphere build may still stop later if `src/core_atmosphere/physics/physics_mmm`
  tries to `git fetch` `MMM-physics` and network access is unavailable.

## Key Source Locations

| Component | Path |
|-----------|------|
| Framework | `src/framework/` |
| Operators | `src/operators/` |
| Atmosphere Core | `src/core_atmosphere/` |
| Init Atmosphere | `src/core_init_atmosphere/` |
| Dynamics | `src/core_atmosphere/dynamics/` |
| Physics | `src/core_atmosphere/physics/` |
| Chemistry | `src/core_atmosphere/chemistry/` |
| MUSICA Integration | `src/core_atmosphere/chemistry/musica/` |
| Registry (metadata) | `src/core_atmosphere/Registry.xml` |

## MUSICA Integration Files

| File | Purpose |
|------|---------|
| `mpas_atm_chemistry.F` | Generic chemistry interface |
| `mpas_musica.F` | MUSICA/MICM coupler implementation |

## Build Artifacts

| File | Description |
|------|-------------|
| `atmosphere_model` | Main atmosphere executable |
| `init_atmosphere_model` | Initialization/preprocessing tool |
| `build_tables` | Physics lookup table generator |

## Available Skills

Skills are defined in `.claude/commands/` and can be invoked with `/skillname`:

| Skill | Command | Description |
|-------|---------|-------------|
| Build MPAS | `/build-mpas` | Build atmosphere or init_atmosphere |
| Test MPAS | `/test-mpas` | Run a test case and verify output |
| Plot Chemistry | `/plot-chemistry` | Generate and open chemistry visualization plots |
| MUSICA Dev | `/musica-dev` | Work on MUSICA/MICM chemistry integration |

## Development Approach

CheMPAS-A uses a coding-agent-assisted development model. Agents are used for implementation, review support, and verification; scientific judgment and final technical direction remain with project maintainers.

## Multi-Agent Workflow

CheMPAS-A uses three agents from three vendors. Codex reviews Claude's work and may push doc edits or review findings directly to the repo, but that review remains part of a maintainer-directed workflow rather than a fully automated merge path.

**Convention for cross-agent communication:**
- Codex writes review findings to `CODEX_REVIEW.md` and pushes to `develop`
- When the user says "check the review", pull and read `CODEX_REVIEW.md`
- Implement fixes, then remove `CODEX_REVIEW.md` (it's a transient artifact, not a permanent doc)
- Codex may also edit `.md` documentation files directly — always `git pull` before committing if Codex has been active
- Before merging to main, ensure no concurrent Codex edits are in flight

## Notes for AI Assistants

1. **Fortran Standards**: This is a Fortran 2008 codebase using MPI for parallelism
2. **Build System**: Uses legacy Makefile (not CMake) with `make llvm` (macOS) or `make gfortran` (Ubuntu)
3. **Module Files**: flang and gfortran `.mod` files are incompatible - don't mix compilers
4. **MPI**: macOS/LLVM uses `include 'mpif.h'` via `NOMPIMOD` flag; Ubuntu/gfortran uses `mpi_f08` module natively
5. **Registry System**: Most variable definitions are in `Registry.xml` (build-time), but MUSICA chemistry tracers are injected at runtime from the MICM config
6. **Physics**: Many physics schemes from WRF, NoahMP, and other sources
7. **MUSICA**: Use `scripts/check_build_env.sh` before MUSICA builds. The working pkg-config file is `~/software/lib/pkgconfig/musica-fortran.pc` on both platforms.
8. **Build Environment**: `PKG_CONFIG_PATH` must be present in the same shell invocation as `make`; otherwise the Makefile's parse-time `pkg-config` checks fail.
9. **Testing**: Always run with 8 MPI ranks (`mpiexec -n 8`). A mismatched rank count with no matching partition file causes segfaults in the dynamics solver. See `RUN.md` for details.

## Common Tasks

### Full Rebuild

The preflight script auto-detects the make target (`llvm` or `gfortran`):

```bash
make clean CORE=atmosphere
find . -name "*.mod" -delete
find . -name "*.o" -delete
eval "$(scripts/check_build_env.sh --export)" && make -j8 TARGET CORE=atmosphere PIO="$PIO" NETCDF="$NETCDF" PNETCDF="$PNETCDF" PRECISION=double
```

Replace `TARGET` with `llvm` (macOS) or `gfortran` (Ubuntu), or read it from
the preflight output.

### Build with MUSICA
```bash
eval "$(scripts/check_build_env.sh --export)" && make -j8 TARGET \
  CORE=atmosphere \
  PIO="$PIO" \
  NETCDF="$NETCDF" \
  PNETCDF="$PNETCDF" \
  PRECISION=double \
  MUSICA=true
```

**Notes:**
- Keep the `eval ... && make ...` in a single shell command.
- If the build fails after chemistry compiles, check whether `physics_mmm` attempted a network fetch.

### Check Build Status
```bash
ls -la atmosphere_model init_atmosphere_model build_tables
```

## Python Environment and Scripts

### Conda Environment
A conda environment `mpas` is available for visualization and analysis:
```bash
~/miniconda3/envs/mpas/bin/python  # Direct path
# Or activate: conda activate mpas
```

Core packages: `numpy`, `xarray`, `matplotlib`, `netCDF4`.

Standalone MUSICA-Python tutorial extras
(`scripts/musica_python/{abba_box,lnox_box,chapman_nox_column}.py`,
documented in tutorial §§2.10 / 2.11 / 3.10):

```bash
~/miniconda3/envs/mpas/bin/pip install musica ussa1976 ephem
```

- `musica` — MICM solver, TUV-x calculator, mechanism config parser.
- `ussa1976` — US Standard Atmosphere 1976 T/p profiles.
- `ephem` — solar position from latitude / longitude / UTC time.

Branding-asset extras (`scripts/generate_logo_chempas.py` writes a 2048-px
PNG companion next to each SVG when cairosvg is available; the script
falls back to SVG-only without it):

```bash
~/miniconda3/envs/mpas/bin/pip install cairosvg
```

### Visualization Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `plot_chemistry.py` | Visualize chemistry tracer output (qA, qB, qAB) |
| `init_tracer_sine.py` | Initialize tracers with sine wave patterns |

**plot_chemistry.py usage:**
```bash
cd ~/Data/CheMPAS/supercell
~/miniconda3/envs/mpas/bin/python plot_chemistry.py -o output.png
~/miniconda3/envs/mpas/bin/python plot_chemistry.py --time-series  # Spatial evolution
~/miniconda3/envs/mpas/bin/python plot_chemistry.py --diff          # Difference from t=0
```

**init_tracer_sine.py usage:**
```bash
# Apply horizontal sine wave to qAB (for advection studies)
python init_tracer_sine.py -i supercell_init.nc -t qAB --waves-x 2 --amplitude 0.4 --offset 0.6
```

## Test Run Directory

Idealized test cases are in `~/Data/CheMPAS/`:

| Case | Directory | Duration | Mesh |
|------|-----------|----------|------|
| Supercell | `~/Data/CheMPAS/supercell/` | 2 hours | 60 stretched levels to 50 km (~300 m surface → ~1 km top) |
| Mountain wave | `~/Data/CheMPAS/mountain_wave/` | 5 hours | ~577 m, 70 levels |
| Baroclinic wave | `~/Data/CheMPAS/jw_baroclinic_wave/` | 16 days | 120 km, 26 levels |

Reference namelists and streams files are tracked in `test_cases/` in the repo.
See `RUN.md` for execution instructions and `test_cases/README.md` for data
download and setup.

**Important:** All streams files use `io_type="netcdf"` to avoid PnetCDF
compatibility issues.
