# Merge MPAS-Model v8.4.0 (non-chemistry) — Design

Date: 2026-04-19
Status: Design (awaiting user review)
Target branch: `merge-mpas-v8.4.0-non-chemistry` (new feature branch off `develop`)

## Goal

Pull in v8.4.0's non-chemistry changes from `MPAS-Dev/MPAS-Model` into CheMPAS-A, deferring all chemistry-touching files to a separate later effort. Work happens on a feature branch; final integration via `--no-ff` merge into `develop` only after macOS build + supercell smoke + Ubuntu build all pass.

## Scope

**In scope (~78 files):**
- 53 v8.4.0 files with no CheMPAS-A modifications — clean adds/applies
- ~25 v8.4.0 files in the intersection that don't touch chemistry (framework/, dynamics/ except chemistry-adjacent, init_atmosphere/, physics/ except chemistry-adjacent, core_test/, external/, build infrastructure)

**Explicitly out of scope (deferred to a separate chemistry-strategy brainstorm):**
- `src/core_atmosphere/Registry.xml` (chemistry namelist conflicts)
- `src/core_atmosphere/mpas_atm_core.F` (chemistry init/step calls)
- `src/core_atmosphere/Makefile` (chemistry/MUSICA build wiring)
- `src/core_atmosphere/chemistry/Makefile` (CheMPAS-A-side; v8.4.0 added its own)
- `src/core_atmosphere/chemistry/mpas_atm_chemistry.F` (CheMPAS-A 1039 lines vs v8.4.0's 128-line stub)
- `src/core_atmosphere/chemistry/musica/Makefile` (same situation)
- `src/core_atmosphere/chemistry/musica/mpas_musica.F` (CheMPAS-A 1036 lines vs v8.4.0's 181-line stub)

These 7 files require the chemistry-strategy decision (CheMPAS-A adopts upstream's chemistry interface? upstream adopts CheMPAS-A's? coexist?) which is its own brainstorm.

## Pre-existing Context

- v8.3.1 → v8.4.0 changeset: 236 commits; 81 files changed (71 modified, 10 added, 0 deleted); +8276/-1812 lines.
- CheMPAS-A-modified files vs v8.3.1: 29.
- Intersection (CheMPAS-A-modified ∩ v8.4.0-modified): 28 files. Of these, 3 are chemistry-adjacent (deferred); 25 are in scope.
- v8.4.0-only files: 53 (no CheMPAS-A conflict).
- See `docs/upstream/2026-04-19-vs-mpas-v8.3.1.md` for the CheMPAS-A-vs-v8.3.1 baseline comparison.

## File Categorization

| Area | Pure v8.4.0-only | Intersection (in scope) | In-scope total |
|---|---:|---:|---:|
| `src/framework/` | 3 — `mpas_halo_interface.inc`*, `mpas_ptscotch_interface.F`, `ptscotch_interface.c` | 11 — block_creator, dmpar†, field_routines, framework, halo, pool_routines, stream_inquiry, stream_list, stream_manager, timekeeping, CMakeLists.txt | 14 |
| `src/core_atmosphere/dynamics/` | 1 — `mpas_atm_dissipation_models.F` | 1 — `mpas_atm_time_integration.F`‡ | 2 |
| `src/core_atmosphere/physics/` non-chemistry | a few | 4 — `atmphys_lsm_noahmpinit`, `atmphys_todynamics`‡, WRF `module_cu_gf.mpas`, WRF `module_sf_urban` | ~6–10 |
| `src/core_atmosphere/diagnostics/` | 0 | 1 — `mpas_cloud_diagnostics.F` | 1 |
| `src/core_atmosphere/` (top, non-chemistry) | 0 | 1 — `mpas_atm_halos.F`‡ | 1 |
| `src/core_init_atmosphere/` | a few | 2 — `mpas_init_atm_cases.F`, `Registry.xml` (non-chemistry) | varies |
| `src/core_test/` | 2 — `mpas_test_core_io.F`, `mpas_test_core_stream_list.F` | 3 — `Makefile`, `mpas_test_core_streams.F`, `mpas_test_core.F` | 5 |
| Other cores (`landice`, `ocean`, `seaice`, `sw`) | a few each (Registry, Makefile bumps) | 0 | varies |
| `src/external/` | 1 — `SMIOL/smiol.c` | 0 | 1 |
| `src/driver/` | 1 — `Makefile` | 0 | 1 |
| Top-level + `cmake/` | 3 — `Makefile`, `README.md`, `cmake/Functions/MPAS_Functions.cmake` | 2 — `Makefile`, `cmake/Modules/FindPnetCDF.cmake` | 5 |

\* `mpas_halo_interface.inc` is a v8.4.0 *addition*, but CheMPAS-A already has its own version of the same file (independently created to fix the macOS LLVM/flang build — see project memory `project_halo_interface_macos_fix.md`). Convergent evolution; needs explicit reconciliation.

† `mpas_dmpar.F` carries the CheMPAS-A-side `inlist` `pointer` → `intent(in)` fix (per the v8.3.1 comparison doc). Default-to-upstream MUST re-apply this fix.

‡ `mpas_atm_time_integration.F`, `mpas_atmphys_todynamics.F`, `mpas_atm_halos.F` carry the CheMPAS-A-side halo refactor (Mac build fix). When defaulting to upstream, verify the macOS build still works — if upstream's `mpas_halo_interface.inc` isn't sufficient on its own, additional CheMPAS-A-side adjustments may need to be re-applied.

## Conflict-Resolution Policy

**Default**: take v8.4.0's version of each in-scope file.

**Re-apply intentional CheMPAS-A fixes**:
- `mpas_dmpar.F`: re-apply `inlist` `pointer` → `intent(in)` change.
- Halo files (3 above + the new `mpas_halo_interface.inc`): test macOS build first; if it breaks, treat halo subsystem as a sub-merge requiring per-line reconciliation between CheMPAS-A and v8.4.0 solutions.

If additional intentional CheMPAS-A-side fixes surface during the merge (i.e., a file's CheMPAS-A modification turns out to be a deliberate fix rather than incidental), preserve it and document in the relevant commit message.

## Merge Mechanism (kept flexible)

The plan supports two interchangeable mechanisms; the implementer chooses at execution time based on what reads cleaner once the branch is set up.

### Mechanism A — Branch merge with selective revert

```bash
git checkout -b merge-mpas-v8.4.0-non-chemistry develop
git remote add upstream https://github.com/MPAS-Dev/MPAS-Model.git  # if not already
git fetch upstream v8.4.0
git merge upstream/v8.4.0   # produces conflicts in chemistry-adjacent + intersection files

# For each out-of-scope file, discard upstream's version:
for f in src/core_atmosphere/Registry.xml \
         src/core_atmosphere/mpas_atm_core.F \
         src/core_atmosphere/Makefile \
         src/core_atmosphere/chemistry/Makefile \
         src/core_atmosphere/chemistry/mpas_atm_chemistry.F \
         src/core_atmosphere/chemistry/musica/Makefile \
         src/core_atmosphere/chemistry/musica/mpas_musica.F; do
    git checkout HEAD -- "$f"   # keep CheMPAS-A-side version
done

# Resolve remaining intersection-file conflicts per Conflict-Resolution Policy.
# Re-apply the mpas_dmpar.F intent(in) fix if upstream re-introduces the bug.
# Verify macOS build before resolving halo files.
git commit
```

Pro: preserves merge commit + upstream provenance; future v8.5.0 → `git merge upstream/v8.5.0` knows what's already in.
Con: forces dealing with chemistry-adjacent conflicts (one `git checkout` per file — minor cognitive load).

### Mechanism B — File-by-file patch application

```bash
git checkout -b merge-mpas-v8.4.0-non-chemistry develop
# Use a script that iterates over the in-scope file list and applies
# git diff v8.3.1 v8.4.0 -- <file> for each one. Skip out-of-scope files
# entirely. Group commits by area (Section 4).
```

Pro: clean scope adherence; never touches out-of-scope files.
Con: loses git provenance — future merges from v8.5.0 must redo the same dance from scratch.

### Picking between A and B at execution time

- If the upstream merge produces ≤30 conflict markers and all are in-scope intersection files: prefer A.
- If the upstream merge produces conflicts in dozens of files because the chemistry-adjacent surface is wider than expected: prefer B.

The plan will write the in-scope and out-of-scope file lists explicitly in both forms (`for f in ...` script for A, file-list array for B) so either mechanism can be invoked.

## Commit Structure on the Branch

Inside `merge-mpas-v8.4.0-non-chemistry`, group changes by area for bisect-friendly history. Target ~7–9 commits before the final merge to `develop`.

```
1. merge(framework): pull v8.4.0 changes (sans halo refactor)
   - 11 modified intersection files: mpas_block_creator.F, mpas_dmpar.F (with
     intent(in) fix re-applied), mpas_field_routines.F, mpas_framework.F,
     mpas_pool_routines.F, mpas_stream_inquiry.F, mpas_stream_list.F,
     mpas_stream_manager.F, mpas_timekeeping.F, CMakeLists.txt
   - 2 added: mpas_ptscotch_interface.F, ptscotch_interface.c
   - mpas_halo.F deferred to commit 2

2. merge(framework,halo): reconcile halo refactor with v8.4.0
   - mpas_halo.F (intersection)
   - mpas_atm_halos.F (intersection, in core_atmosphere)
   - mpas_atm_time_integration.F (intersection, in dynamics)
   - mpas_atmphys_todynamics.F (intersection, in physics)
   - mpas_halo_interface.inc (CheMPAS-A already has; reconcile with v8.4.0's
     newly added version)
   - **macOS build verification gate before this commit lands**

3. merge(dynamics): pull v8.4.0 dynamics changes
   - mpas_atm_dissipation_models.F (added)
   - any other dynamics non-halo changes

4. merge(physics): pull v8.4.0 physics non-chemistry changes
   - mpas_atmphys_lsm_noahmpinit.F (intersection)
   - WRF physics_wrf modules (intersection)
   - any other physics non-chemistry intersection files

5. merge(diagnostics): pull v8.4.0 diagnostics changes
   - mpas_cloud_diagnostics.F

6. merge(init_atmosphere): pull v8.4.0 init_atmosphere changes
   - mpas_init_atm_cases.F
   - core_init_atmosphere/Registry.xml (non-chemistry; safe)
   - any other

7. merge(core_test): pull v8.4.0 test infra
   - mpas_test_core_io.F (added), mpas_test_core_stream_list.F (added)
   - mpas_test_core_streams.F, mpas_test_core.F, Makefile (intersection)

8. merge(other_cores): pull v8.4.0 routine bumps
   - core_landice/, core_ocean/, core_seaice/, core_sw/ Registry/Makefile bumps

9. merge(build,external,driver): pull v8.4.0 build infra
   - top-level Makefile, README.md, cmake/, src/Makefile, src/external/SMIOL/smiol.c,
     src/driver/Makefile

10. (final) Merge into develop with --no-ff
```

Each branch commit should:
- Have subject `merge(area): pull v8.4.0 <area> changes`
- Body lists the specific files included with a 1-line note per change category
- Reference the spec + plan in the trailer

The final `--no-ff` merge into `develop` uses subject `Merge branch 'merge-mpas-v8.4.0-non-chemistry'` and a body summarizing the 78-file scope and out-of-scope deferral.

## Validation

**Validation gates** (full safety net):

1. **macOS build** (after commit 1, again after commit 2, final after commit 9):
   ```bash
   eval "$(scripts/check_build_env.sh --export)" && make -j8 llvm \
     CORE=atmosphere PIO="$PIO" NETCDF="$NETCDF" PNETCDF="$PNETCDF" \
     PRECISION=double MUSICA=true 2>&1 | tail -20
   ```
   Pass: `atmosphere_model` produced; no compile errors mentioning halo, framework, or dissipation symbols.

2. **Supercell smoke** (after commit 9, before merge to develop):
   ```bash
   cp atmosphere_model ~/Data/CheMPAS/supercell/
   cd ~/Data/CheMPAS/supercell/
   rm -f log.atmosphere.* output.nc
   # Override config_run_duration to '00:03:00' for the smoke
   mpiexec -n 8 ./atmosphere_model 2>&1 | tail -10
   ```
   Pass: clean run completion (`Critical error messages = 0`, no `CRITICAL ERROR` in `log.atmosphere.0000.out`); spot-check that `j_jNO2`, `qNO`, `qNO2`, `qO3` min/max at t=3 min match the `d7601e4` / `fee5a28` baseline values within rounding precision (since chemistry was untouched, this should be bit-identical).

3. **Ubuntu build** (after macOS validation passes; user-driven step):
   - Push the feature branch to `origin`.
   - User pulls on Ubuntu, runs `make -j8 gfortran ...`; reports back.

4. **Merge to develop**: only after macOS build + supercell smoke + Ubuntu build all pass.

## Files Touched Summary

- ~78 files modified or added (53 v8.4.0-only + 25 in-scope intersection)
- 7 files explicitly NOT touched (deferred chemistry-adjacent + chemistry/* additions)
- New top-level files added by upstream and brought in: `mpas_ptscotch_interface.F`, `ptscotch_interface.c`, `mpas_atm_dissipation_models.F`, `mpas_test_core_io.F`, `mpas_test_core_stream_list.F`, plus halo-include reconciliation (6 files total)

## Risks and Mitigations

- **macOS build breaks after halo reconciliation** → commit 2 has its own validation gate; abort and fall back to keeping CheMPAS-A's halo refactor unchanged if upstream's `mpas_halo_interface.inc` doesn't compile with flang.
- **Build works but supercell run regresses** → only chemistry-untouched files in scope, so a regression points to a build-system issue or framework change with side effects on output. Diff `output.nc` against the `d7601e4` / `fee5a28` baseline; bisect by commit-on-branch.
- **Ubuntu fails after macOS passes** → most likely a `gfortran`-vs-`flang` divergence in something v8.4.0 changed; treat as a separate fix, not a merge revert.
- **`mpas_dmpar.F` `intent(in)` fix gets lost** → spec calls this out explicitly in the categorization table; commit 1 message lists it as a re-application.

## Deferred / Out of Scope

- Chemistry-strategy decision (CheMPAS-A chemistry vs upstream stub) — separate brainstorm
- The 7 chemistry-touching files (Registry.xml, mpas_atm_core.F, core_atmosphere/Makefile, all chemistry/* files)
- Forward merges from v8.4.0 → v8.5.0 / v9.0.0 — establish the upstream remote and merge mechanism here so future merges are routine
- Cross-platform `init_atmosphere_model` build (the spec only validates `atmosphere_model`; the init binary likely also needs a separate verify, deferred to plan-time)
