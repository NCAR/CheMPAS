# CheMPAS-A Architecture

This document describes the high-level architecture of CheMPAS-A: the MPAS
(Model for Prediction Across Scales) framework plus the chemistry extensions in
this repository.

## Overview

MPAS is a modular, unstructured mesh framework for Earth system modeling. It supports multiple specialized "cores" for different physical domains:

- **core_atmosphere** - Atmospheric modeling (primary focus of this branch)
- **core_init_atmosphere** - Initialization preprocessing
- **core_ocean** - Ocean modeling
- **core_seaice** - Sea ice modeling
- **core_landice** - Land ice/glacier modeling
- **core_sw** - Shallow water test cases
- **core_test** - Framework testing suite

## Architecture Diagram

```
                        MPAS Main Driver
                         (src/driver/)
                              |
                +-------------+-------------+
                |                           |
          Atmosphere Core             Ocean/Other Core
                |
    +-----------+-----------+
    |           |           |
 Dynamics    Physics    Chemistry
  (SRK3)  (Convection,  (MPAS driver +
           Radiation,   MUSICA/MICM +
           Microphysics, TUV-x)
           LSM)               |
                       Runtime tracer
                       discovery from
                       MICM config

   ====================================================
        MPAS Framework (Shared)
        Pools, I/O, DMpar, Logging, Halo, Block Creator
   ====================================================
```

### Chemistry Tracer Flow

Chemistry tracers are **not** defined in `Registry.xml`. They are discovered
at runtime from the MICM configuration file:

```
atm_setup_block
  |-> atm_generate_structs()                  # Registry tracers (qv, qc, qr...)
  |-> atm_extend_scalars_for_chemistry()      # Queries MICM config
  |     |-> musica_query_species()            #   Creates temp micm_t, reads species
  |     |-> Update num_scalars in-place       #   Extends pool dimension via pointer
  |     |-> Extend constituentNames/attLists  #   Metadata only (arrays not yet allocated)
  |     |-> Add index_qXX dimensions          #   Per-species index dimensions
  |
  |-> mpas_block_creator allocates arrays     # Uses updated num_scalars for sizing
  |
  ... later ...
  |
chemistry_init
  |-> musica_init()                           # Full MICM solver instance
  |-> resolve_mpas_indices()                  # Finds index_qXX from pool
  |-> chemistry_seed_chem()                   # Seeds MPAS scalars from MICM state
```

Switching chemistry mechanisms requires only changing the MICM config file —
no Fortran source or registry edits.

### Chemistry Timestep Flow

Once initialized, chemistry is stepped through the MPAS chemistry driver:

```
chemistry_step
  |-> solar_cos_sza() or TUV-x input preparation
  |-> tuvx_compute_photolysis() / fallback j = j_max * max(0, cos_sza)
  |-> lightning_nox_inject()                  # Operator-split NO source
  |-> chemistry_from_MPAS()                   # MPAS state -> MICM state
  |-> musica_step()                           # MICM chemistry solve
  |-> chemistry_to_MPAS()                     # MICM state -> MPAS state
```

Current chemistry-specific modules under `src/core_atmosphere/chemistry/` are:

- `mpas_atm_chemistry.F` - top-level chemistry manager and MPAS coupling
- `musica/mpas_musica.F` - MUSICA/MICM coupler and state/rate-parameter updates
- `mpas_lightning_nox.F` - operator-split lightning NOx source
- `mpas_solar_geometry.F` - fallback solar zenith-angle calculation
- `mpas_tuvx.F` - TUV-x photolysis wrapper, including cloud-radiator support

## Directory Structure

```
CheMPAS-A/
├── CMakeLists.txt          # Main CMake build configuration
├── Makefile                # Legacy Makefile build system
├── cmake/                  # CMake modules and functions
├── docs/                   # Sphinx documentation source
│   ├── chempas/            # CheMPAS-A-specific developer notes
│   ├── tutorial/           # CheMPAS-A tutorial chapters
│   ├── users-guide/        # Imported MPAS-Atmosphere user's guide
│   └── technical-description/
├── micm_configs/           # MICM and TUV-x chemistry configuration files
├── scripts/                # Analysis, plotting, and helper scripts
├── src/                    # Main source code
│   ├── driver/             # Main execution entry points
│   ├── framework/          # Shared infrastructure
│   ├── operators/          # Mathematical operations
│   ├── tools/              # Code generation tools
│   ├── external/           # External libraries (ezxml, SMIOL, ESMF)
│   ├── core_atmosphere/    # Atmosphere modeling
│   ├── core_init_atmosphere/
│   ├── core_ocean/
│   ├── core_seaice/
│   ├── core_landice/
│   ├── core_sw/
│   └── core_test/
├── test_cases/             # Tracked runtime test cases and namelists
└── testing_and_setup/      # Upstream/legacy test configuration support
```

## Core Components

### 1. Framework (`src/framework/`)

The framework provides shared infrastructure used by all cores:

| File | Size | Purpose |
|------|------|---------|
| `mpas_dmpar.F` | 415KB | Distributed memory parallel communication |
| `mpas_io_streams.F` | 180KB | I/O streaming infrastructure |
| `mpas_io.F` | 268KB | Core I/O routines |
| `mpas_pool_routines.F` | 235KB | Data pool management |
| `mpas_stream_manager.F` | 280KB | Stream handling |
| `mpas_field_routines.F` | 118KB | Field manipulation |
| `mpas_block_creator.F` | 94KB | Block decomposition |

Additional services: logging, timekeeping, halo exchanges, forcing, bootstrapping, hash tables.

### 2. Operators (`src/operators/`)

Specialized mathematical kernels:

- `mpas_rbf_interpolation.F` - Radial basis function interpolation
- `mpas_geometry_utils.F` - Geometric calculations
- `mpas_tensor_operations.F` - Tensor computations
- `mpas_vector_operations.F` - Vector routines
- Tracer advection schemes (monotonic, standard)
- Matrix and spline operations

### 3. Driver (`src/driver/`)

Main execution entry points:

- `mpas.F` - Main program
- `mpas_subdriver.F` - Common subdriver for all cores

### 4. External Libraries (`src/external/`)

- `ezxml/` - XML parsing library
- `SMIOL/` - Scalable Modeling I/O Library
- `esmf_time_f90/` - ESMF time management (internal copy)

## Registry System

The `Registry.xml` files define model metadata:

- **Dimensions**: Mesh sizes (nCells, nEdges, nVertices, nVertLevels)
- **Variables**: State variables, diagnostics, tracers
- **Namelists**: Configuration parameters
- **Streams**: I/O definitions (input, output, restart files)

The registry is processed by tools in `src/tools/registry/` to generate Fortran code.

## Data Flow

1. **Initialization**: Driver reads configuration, initializes framework
2. **Domain Decomposition**: Mesh partitioned across MPI ranks
3. **Time Integration**: Core-specific dynamics, physics, and chemistry stepping
4. **Halo Exchange**: Framework handles inter-processor communication
5. **I/O**: Stream manager handles checkpointing and output

## Dependencies

### Required
- MPI (Fortran bindings)
- PnetCDF (Fortran bindings)

### Optional
- PIO (Parallel I/O library)
- NetCDF
- GPTL (profiling)
- ESMF
- MUSICA/MICM (chemistry, this branch)

## Selected Source Counts

Approximate source/config counts in the current tree:

| Component | Files | Description |
|-----------|-------|-------------|
| Framework | 61 | Core infrastructure |
| Operators | 10 | Mathematical kernels |
| Atmosphere | 297 | Dynamics, physics, and chemistry |
| Init Atmosphere | 35 | Preprocessing |
| Chemistry | 5 | Driver, source, solar geometry, TUV-x, MUSICA coupler |
| Ocean | 308 | Ocean modeling |

These counts include Fortran/C source, include files, and XML configuration
under each component. They are for orientation, not architectural limits.

## Related Documentation

- `BUILD.md` - Build system documentation
- [COMPONENTS.md](COMPONENTS.md) - Detailed component documentation
- [MUSICA_INTEGRATION.md](../musica/MUSICA_INTEGRATION.md) - Chemistry integration details
- [TEST_RUNS.md](../results/TEST_RUNS.md) - Recorded runtime validation results
- `PLAN.md` - Current focus and active plan index

## External Resources

- MPAS-Atmosphere User Guide: http://mpas-dev.github.io/atmosphere/
- MPAS GitHub: https://github.com/MPAS-Dev
