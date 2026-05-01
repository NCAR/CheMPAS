# README Reframing as ACOM Integration Pilot — Design

Date: 2026-04-19
Status: Implemented
Target file: `README.md`

## Goal

Reframe the top-level `README.md` so that CheMPAS-A reads as an ACOM
integration pilot for MUSICA/MICM-in-MPAS coupling. The audience is
MPAS / chemistry developers who may pull pieces of this work into their
own forks or `MPAS-Model-ACOM-dev` PRs. Rapid prototyping is
emphasized; the agent-assisted development workflow is de-emphasized.

## Framing Decisions

- **Pilot identity:** CheMPAS-A is an ACOM integration pilot for MUSICA /
  MICM coupling on MPAS-Atmosphere's unstructured Voronoi mesh.
- **Repo relationship:** CheMPAS-A is fully decoupled from both
  `MPAS-Dev/MPAS-Model` and `NCAR/MPAS-Model-ACOM-dev`. No sync or
  fork-tracking mechanism. Mature pieces are contributed back to
  `MPAS-Model-ACOM-dev` as deliberate, hand-crafted PRs;
  `MPAS-Model-ACOM-dev` is the staging ground for eventual upstream
  integration into `MPAS-Dev/MPAS-Model`.
- **Audience:** MPAS / chemistry developers evaluating or extracting
  pieces. Optimize for "is there something here for me, and how do I
  pull it?"
- **Structure:** Approach 1 (pilot-led). Lead with the pilot framing,
  then status, then build, then code layout, then docs, then a brief
  development-model note.
- **Agents:** De-emphasized. The development model is described via the
  repository's governance structure — not by contrasting humans and
  agents. AGENTS.md is the place for role detail.

## Section-by-Section Design

### 1. Header + opening paragraph

Names CheMPAS-A, identifies it as an ACOM integration pilot, lists the
representative working pieces inline (runtime tracer allocation,
MUSICA/MICM state transfer, TUV-x photolysis, idealized chemistry test
cases), and describes the decoupled relationship with
`MPAS-Dev/MPAS-Model` and `NCAR/MPAS-Model-ACOM-dev`. Calls
`MPAS-Model-ACOM-dev` the staging ground for upstream integration.

### 2. Upstream Integration Path

States explicitly that there is no merge or rebase relationship with
upstream. Describes contributions as focused pull requests that
reimplement a mature CheMPAS-A feature against the current
`MPAS-Model-ACOM-dev` tree. Three operational rules:

- Scoped to one capability per PR.
- Re-derived against the current upstream tree.
- Backed by prototype evidence (test cases, validation runs, design
  notes) rather than a literal port.

### 3. What's Working

Bulleted list of demonstrated integration pieces, ordered by extraction
independence. Each entry has a one-line description plus pointers to
source paths and the relevant deeper documentation:

- Runtime chemistry tracer system
  (`mpas_atm_core_interface.F`, `mpas_block_creator.F`).
- MUSICA/MICM coupler
  (`mpas_musica.F`, `mpas_atm_chemistry.F`;
  `docs/musica/MUSICA_INTEGRATION.md`).
- TUV-x clear-sky photolysis (j_NO2 via delta-Eddington, CAM 102-bin
  wavelength grid; `docs/guides/TUVX_INTEGRATION.md`).
- TUV-x cloud opacity from host
  (`tau = 3·LWC·dz / (2·r_eff·ρ_water)`, SSA = 0.999999, g = 0.85;
  `docs/guides/TUVX_INTEGRATION.md`).
- Idealized chemistry test cases (supercell with LNOx source, mountain
  wave, Jablonowski–Williamson baroclinic wave; `test_cases/`,
  `docs/results/TEST_RUNS.md`).
- Chemistry visualization tooling (`scripts/`,
  `docs/guides/VISUALIZE.md`).

### 4. Building

Documents both supported platforms: macOS (LLVM/flang) and Ubuntu
(GCC/gfortran via conda). Uses the preflight script as the canonical
entry point. Surfaces the two recurring footguns inline:

- `PKG_CONFIG_PATH` must be present in the same shell as `make`.
- Do not mix flang and gfortran `.mod` files; rebuild MUSICA-Fortran
  with the same compiler as CheMPAS-A.

Lists external dependencies: MPI, NetCDF, PnetCDF, PIO, MUSICA-Fortran.
Pushes full preflight, troubleshooting, and dependency-build notes to
`BUILD.md` and run instructions to `RUN.md`.

### 5. Code Layout

Tree view of the repository, with chemistry-relevant locations made
explicit and inherited (non-chemistry) `core_*` directories called out
as not actively maintained for the pilot. Adds `micm_configs/`,
`test_cases/`, and `docs/` to the tree (all missing from the existing
README). Names the chemistry source files inline
(`mpas_atm_chemistry.F`, `mpas_musica.F`).

### 6. Documentation

Three purpose-grouped tables, with the integration-relevant docs
listed first:

- **Architecture & integration:** `ARCHITECTURE.md`, `COMPONENTS.md`,
  `MUSICA_INTEGRATION.md`, `MUSICA_API.md`, `TUVX_INTEGRATION.md`.
- **Build, run, and validation:** `BUILD.md`, `RUN.md`,
  `TEST_RUNS.md`, `VISUALIZE.md`.
- **Project context:** `PURPOSE.md`, `AGENTS.md`.

Drops `BENCHMARKS.md` from the README (not load-bearing for the pilot
framing). Pushes the long-tail docs (user guide, plans, project/TODO)
to `docs/README.md`.

### 7. Development Model

Two sentences. Names the repository's governance structure as
supporting rapid PR turnaround when coding agent tools are employed,
and points to `AGENTS.md` and `PURPOSE.md` for detail. Does not
contrast humans and agents.

### 8. License

Pointer to `LICENSE`. Unchanged from current README.

## Out of Scope

- Editing `PURPOSE.md`, `AGENTS.md`, `docs/README.md`, or any other
  documents to match the new framing. Internal-consistency edits will
  be tracked separately if needed.
- Changing build flags, dependency versions, or platform support.
- Adding new content beyond what is already documented elsewhere in
  the repo.

## Implementation Notes

- File to modify: `README.md` (current length ~87 lines; expected new
  length roughly 130–160 lines given expanded sections).
- The seven content sections above are already drafted in the
  brainstorming session and approved by the user.
- After implementation, sanity-check that all relative links resolve
  to existing files in the tree.
