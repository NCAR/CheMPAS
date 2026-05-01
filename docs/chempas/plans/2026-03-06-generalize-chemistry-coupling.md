# Plan: Generalize Chemistry Coupling — Remove Hardcoded ABBA

## Document Status

- `Historical Context:` Implementation plan and execution log for Phase 1
  (generic MICM species coupling) and Phase 2 (runtime chemistry tracer
  allocation).
- `Current State:` Complete and merged to `main` (as of March 6, 2026).
- `Use This As:` Historical record and rationale, not active implementation
  instructions.

Key commits:
- `2dee808` — Core refactoring: dynamic species table, generic coupling loops
- `dd7824f` — Documentation: MUSICA build pitfalls in BUILD.md, testing notes in CLAUDE.md
- `88fa2a0` — Bugfix: gradient check scans all tracers before seeding

## Context

All chemistry tracer coupling in CheMPAS-A was hardcoded for the 3-species ABBA mechanism (AB, A, B). Species names appeared as string literals in 7+ places each, molar masses were Fortran `parameter` constants, and tracer indices were fetched individually by name. This made it impossible to switch chemistry mechanisms without editing Fortran source code.

Phase 1 generalized the coupling layer to loop over species dynamically using MICM's runtime API. Phase 2 then removed chemistry tracers from `Registry.xml` entirely, discovering them at runtime from the MICM config.

## Files Modified (Phase 1)

| File | Changes |
|------|---------|
| `src/core_atmosphere/chemistry/musica/mpas_musica.F` | Dynamic `species_entry_t` table, generic coupling loops |
| `src/core_atmosphere/chemistry/mpas_atm_chemistry.F` | Removed per-species index args, renamed `chemistry_seed_chem`, fixed gradient check |
| `src/core_atmosphere/mpas_atm_core.F` | Updated call sites: `chemistry_seed_chem`, `chem_seed_after_stream` |
| `src/core_atmosphere/Registry.xml` | Phase 1 interim wrapped qAB/qA/qB; Phase 2 removed chemistry tracers entirely |
| `BUILD.md` | MUSICA build pitfalls documentation |
| `CLAUDE.md` | Testing notes (8 MPI ranks requirement) |
| `~/Data/MPAS/supercell/abba.yaml` | Added `__molar mass`, corrected scaling factors to 2.0e-3 / 1.0e-3 |

## What Was Done (Phase 1)

### Step 1: Add `__molar mass` to `abba.yaml` — DONE

Added `__molar mass` property (kg/mol) to each species in the MICM config:
- A: 0.029, B: 0.029, AB: 0.058

### Step 2: Add species table to `mpas_musica.F` — DONE

Replaced hardcoded `parameter` block (M_AB, M_A, M_B) with module-level derived type and allocatable array:

```fortran
type :: species_entry_t
    character(len=64) :: micm_name    ! e.g. 'AB'
    character(len=64) :: mpas_name    ! e.g. 'qAB'
    integer           :: micm_index   ! from state%species_ordering%index(name)
    integer           :: mpas_index   ! from MPAS pool dimension
    real(kind=8)      :: molar_mass   ! kg/mol from MICM config
end type
```

### Step 3: Populate species table in `musica_init` — DONE

Generic loop over `state%species_ordering`:
- Builds `mpas_name` via `'q' // trim(micm_name)` convention
- Reads `molar_mass` via `micm%get_species_property_double` (scalar return)
- Uses `state%species_ordering%index(name)` for correct stride-based `micm_index`
- Seeds both `state` and `state_ref` with initial concentrations

### Step 4: Add `resolve_mpas_indices` subroutine — DONE

Looks up MPAS pool dimensions (`index_qAB`, etc.) and fills `chem_species(i)%mpas_index`. Called from `chemistry_init` after `musica_init`.

### Step 5–6: Rewrite `MICM_from/to_chemistry` — DONE

Generic species loops replace explicit per-species blocks. No more index arguments in signatures.

### Step 7: Rename `micm_to_mpas_abba` → `micm_to_mpas_chem` — DONE

Generic seeding loop over `chem_species(:)`.

### Step 8: Generalize `log_column_comparison` — DONE

Dynamic loop prints each species name and coupled/reference concentrations.

### Step 9: Update `mpas_atm_chemistry.F` — DONE

Removed per-species index declarations and pool lookups. Simplified call signatures. Renamed public interface. Fixed gradient check to scan all tracers.

### Step 10: Update `mpas_atm_core.F` — DONE

All call sites updated: `chemistry_seed_abba` → `chemistry_seed_chem`, `abba_seed_after_stream` → `chem_seed_after_stream`.

### Step 11 (Phase 1 interim): Wrap Registry.xml tracers — SUPERSEDED

This was an intermediate Phase 1 step. In Phase 2, chemistry tracers were
removed from `Registry.xml` and are now injected at runtime.

## Bugs Found and Fixed

1. **Gradient check only examined first species** — The seeding skip logic checked `chem_species(1)` (species A) for spatial gradients, missing sine wave patterns on qAB. Fixed to loop over all chemistry tracers.

2. **Scaling factors too fast** — `abba.yaml` had scaling factors 2.0 / 1.0 (instant equilibrium). Corrected to 2.0e-3 / 1.0e-3 for gradual chemistry evolution visible over 15-minute runs.

## Verification Results

1. **Build:** MUSICA=true build succeeds (MUSICA-Fortran 0.13.0)
2. **Run:** Supercell test passes with 8 MPI ranks, 15-minute run, 0 errors/warnings
3. **Log check:** Dynamic species discovery confirmed:
   - `[MUSICA] Species A molar_mass=0.029 kg/mol`
   - `[MUSICA] Species AB molar_mass=0.058 kg/mol`
   - `[MUSICA] Species B molar_mass=0.029 kg/mol`
   - `[MUSICA] Resolved A -> MPAS index 5`
   - `[MUSICA] Resolved AB -> MPAS index 4`
   - `[MUSICA] Resolved B -> MPAS index 6`
4. **Chemistry correctness:** Mass conservation holds (qA + qB + qAB ≈ 1.0), smooth exponential decay
5. **Sine wave init:** Gradient check correctly detects spatial variation, preserves init file patterns
6. **Plots:** All visualization types generated successfully (temporal, multispecies, diff, single-cell, vertical)

## Lessons Learned

- `state%species_ordering%index(name)` returns the stride-based index needed for concentration array access; the iteration counter from `species_ordering%name(i)` is NOT the same thing
- `micm%get_species_property_double` returns a scalar `real(8)`, not an array
- MPAS logging `realArgs` must use `kind=RKIND` (not `kind=4`) when `-fdefault-real-8` is active
- Running with wrong MPI rank count (e.g., 1 rank on 8-partition mesh) causes segfaults in RK3 dynamics — always test with 8 ranks
- Gradient detection must check ALL chemistry tracers, not just the first in iteration order
- ABBA scaling factors: use 2.0e-3 / 1.0e-3 for visible chemistry evolution; 2.0 / 1.0 equilibrates in one timestep

## Design Notes

- **`state_ref` keeps uniform initial concentrations** even when init file has spatial gradients. This is intentional — `state_ref` is a debugging device for comparing MICM's standalone ODE solution against the coupled run.
- **MICM state gets real values from MPAS** at the first coupling step via `MICM_from_chemistry`, so the uniform MICM initial state is harmlessly overwritten.

## Phase 2: Runtime Chemistry Tracer Allocation — COMPLETE

### Goal

Remove chemistry tracers from `Registry.xml`. Discover species from MICM config at startup and inject them into the `scalars` and `scalars_tend` var_arrays dynamically. Switching chemistry mechanisms requires zero Fortran or registry changes.

### Design Decisions

1. **Only chemistry tracers are dynamic** — Core met tracers (qv, qc, qi, etc.) stay in Registry.xml. Chemistry tracers from MICM are appended at runtime. Other modules (physics, different chemistry packages) can still define tracers in the registry.

2. **Two-phase initialization (A2)** — A lightweight early scan of the MICM config gets species names/count during `atm_setup_block`. The full MICM solver initialization still happens later in `chemistry_init`.

3. **Temporary MICM instance for early scan** — Create a throwaway `micm_t` to query `species_ordering`, extract names/count, then destroy it. Keeps MICM config as the single source of truth — no sidecar files, no YAML parsing.

4. **Extend both `scalars` and `scalars_tend` together** — Following the `atm_allocate_scalars` (CAM dycore) precedent. Both arrays grow by the same chemistry species count.

5. **I/O works automatically** — The MPAS stream system writes all constituents of a var_array. Since dynamic tracers are added to `constituentNames`, they appear in `output.nc` with no extra I/O registration needed.

### Architecture

```
atm_setup_block
  |-> atm_generate_structs()           # Registry tracers allocated (qv, qc, qi...)
  |-> atm_extend_scalars_for_chemistry()  # NEW
  |     |-> Read MICM config path from namelist
  |     |-> Create temporary micm_t, query species_ordering
  |     |-> For each species: extend scalars 1st dim, add index_qXX dimension
  |     |-> Same for scalars_tend
  |     |-> Destroy temporary micm_t
  |
  ... later ...
  |
chemistry_init
  |-> musica_init()                    # Full MICM solver (unchanged)
  |-> resolve_mpas_indices()           # Finds index_qXX injected by step above (unchanged)
  |-> chemistry_seed_chem()            # Seeds MPAS tracers from MICM state (unchanged)
```

### Files to Modify

| File | Changes |
|------|---------|
| `Registry.xml` | Remove `#ifdef MPAS_USE_MUSICA` tracer block (qAB/qA/qB + tendencies) |
| `mpas_atm_core_interface.F` | Add `atm_extend_scalars_for_chemistry`; call from `atm_setup_block` |
| `mpas_musica.F` | Add `musica_query_species(config_path, names, count)` lightweight query |
| `mpas_atm_chemistry.F` | Minor adjustments if needed for new init sequence |

### Key Technical Detail

At `atm_setup_block` time, field arrays are **not yet allocated** — only metadata exists. The extension modifies metadata only:
- Update `num_scalars` dimension in-place via pointer (`mpas_pool_add_dimension` silently ignores duplicate keys)
- Extend `constituentNames` and `attLists` arrays for each time level
- Add `index_qXX` dimensions for each new species
- Repeat for `scalars_tend` in the tend pool
- The framework (`mpas_block_creator.F`) later allocates correctly-sized arrays using the updated `num_scalars`

### Regression Test — PASSED

- Reference output: `~/Data/MPAS/supercell/reference_phase1_output.nc`
- Build: MUSICA=true, run supercell 15 min / 8 ranks
- Chemistry tracers (qA, qAB, qB): **bitwise identical** to Phase 1 reference
- Met fields unaffected

### Codex Review — All Issues Fixed

Codex reviewed commits `195452e`–`46c180d` and found three issues, all resolved:

1. **High: LBC incompatibility** — Runtime tracers extend `num_scalars` beyond `lbc_scalars` bounds. Fixed with `MPAS_LOG_CRIT` guard when `config_apply_lbcs=true`.
2. **Medium: `scalars_tend` naming** — Constituent names used `q*` instead of `tend_q*`. Fixed by adding `tend_` prefix in `extend_field_metadata`.
3. **Low: Memory leak on error** — `musica_query_species` leaked `tmp_micm`/`tmp_state` on error paths. Fixed with `goto`-based cleanup and null-initialized pointers.

### Future Work (Post Phase 2)

- **LBC support for dynamic tracers** — Extend `lbc_scalars` metadata at runtime (currently guarded with hard-fail)
- **`__do advect` filtering** — Support non-advected species
- **Fallback molar mass table** — For configs lacking `__molar mass`
- **Generic visualization** — `plot_chemistry.py` discovers species dynamically
- **Non-MUSICA build verification** — Clean compilation without MUSICA flag
