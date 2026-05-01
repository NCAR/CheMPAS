# README ACOM-Pilot Reframe Implementation Plan

## Document Status

- `Historical Context:` Task-by-task plan used to deliver the ACOM-pilot
  README rewrite.
- `Current State:` Implemented; the live `README.md` has since received
  follow-on edits (e.g., dropping the `PURPOSE.md` / `AGENTS.md`
  references). Relative paths in this plan reflect the pre-reorg
  `docs/<topic>/` layout — the dev-notes tree was later moved under
  `docs/chempas/<topic>/`.
- `Use This As:` Implementation history, not active task instructions.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the contents of `README.md` with the ACOM-pilot-reframed version specified in `docs/superpowers/specs/2026-04-19-readme-acom-pilot-reframe-design.md`.

**Architecture:** Single-file documentation rewrite. The existing README is ~87 lines and will be replaced with a ~155-line version organized in eight sections (header/opening, upstream integration path, what's working, building, code layout, documentation, development model, license). All section content was drafted and approved during brainstorming.

**Tech Stack:** Markdown only. Verification uses standard shell tools (`ls`, `test -e`).

---

## File Structure

- Modify: `README.md` (full rewrite)

No other files are touched. Section ordering, voice, and link consistency are tightly coupled, so the rewrite is one atomic change followed by link verification and a single commit.

---

### Task 1: Rewrite README.md

**Files:**
- Modify: `README.md` (replace entire contents)

- [ ] **Step 1: Replace `README.md` with the new contents below**

Use the Write tool to overwrite `README.md` with exactly this content:

````markdown
CheMPAS-A
=======

CheMPAS-A (Chemistry for MPAS) is an ACOM integration pilot that couples
MUSICA/MICM atmospheric chemistry to MPAS-Atmosphere on its native
unstructured Voronoi mesh. The repository serves as a rapid-prototyping
ground for the chemistry coupling: runtime tracer allocation, MUSICA/MICM
state transfer, TUV-x photolysis, and idealized chemistry test cases are
developed here ahead of any upstream integration.

CheMPAS-A is decoupled from both
[MPAS-Dev/MPAS-Model](https://github.com/MPAS-Dev/MPAS-Model) and
[NCAR/MPAS-Model-ACOM-dev](https://github.com/NCAR/MPAS-Model-ACOM-dev) —
there is no sync or fork-tracking mechanism. Mature pieces are contributed
back to `MPAS-Model-ACOM-dev` as deliberate, hand-crafted pull requests,
which is the staging ground for eventual upstream integration into
`MPAS-Dev/MPAS-Model`.

## Upstream Integration Path

CheMPAS-A does not push its history to `MPAS-Model-ACOM-dev`. The two repos
share ancestry but have no merge or rebase relationship. Integration
contributions take the form of focused pull requests that reimplement a
mature CheMPAS-A feature against the current `MPAS-Model-ACOM-dev` tree.

In practice this means each upstream PR is:

- **Scoped to one capability** — e.g., runtime tracer allocation, the
  MUSICA/MICM coupler, or the TUV-x cloud radiator — rather than a bulk
  port of CheMPAS-A state.
- **Re-derived against the current upstream tree**, so the diff is clean
  against `MPAS-Model-ACOM-dev`'s `Registry.xml`, build system, and module
  layout at PR time.
- **Backed by the prototype evidence in this repo** — test cases,
  validation runs, and design notes — but not a literal port of every
  CheMPAS-A file.

This separation keeps CheMPAS-A free to iterate quickly while keeping
upstream PRs reviewable as standalone changes.

## What's Working

The pieces below are demonstrated end-to-end in this repo and are the
primary candidates for upstream integration PRs. Each entry points to the
code and the relevant deeper documentation.

- **Runtime chemistry tracer system** — chemistry tracers are removed from
  `Registry.xml` and discovered at startup from the active MICM YAML
  configuration; tracer field arrays are allocated at runtime in the block
  setup path.
  Code: `src/core_atmosphere/mpas_atm_core_interface.F`,
  `src/framework/mpas_block_creator.F`.

- **MUSICA/MICM coupler** — state transfer between MPAS and MICM in
  mol/m³, unit conversion, and external rate-parameter wiring.
  Code: `src/core_atmosphere/chemistry/musica/mpas_musica.F`,
  `src/core_atmosphere/chemistry/mpas_atm_chemistry.F`.
  See [docs/musica/MUSICA_INTEGRATION.md](docs/musica/MUSICA_INTEGRATION.md).

- **TUV-x clear-sky photolysis** — j_NO2 computed via the delta-Eddington
  solver with a from-host wavelength grid (CAM 102-bin grid).
  See [docs/guides/TUVX_INTEGRATION.md](docs/guides/TUVX_INTEGRATION.md).

- **TUV-x cloud opacity from host** — cloud radiator built from MPAS LWC
  (`tau = 3·LWC·dz / (2·r_eff·ρ_water)`, SSA = 0.999999, g = 0.85),
  attached to the TUV-x solver before construction.
  See [docs/guides/TUVX_INTEGRATION.md](docs/guides/TUVX_INTEGRATION.md).

- **Idealized chemistry test cases** — supercell (with LNOx source),
  mountain wave, and Jablonowski–Williamson baroclinic wave configurations,
  all wired for MUSICA tracer transport.
  See [test_cases/](test_cases/) and
  [docs/results/TEST_RUNS.md](docs/results/TEST_RUNS.md).

- **Chemistry visualization tooling** — Python scripts for chemistry
  tracers, LNOx/O₃ evolution, and chemistry profile plotting (frame
  selection and time-series modes).
  See [scripts/](scripts/) and
  [docs/guides/VISUALIZE.md](docs/guides/VISUALIZE.md).

## Building

CheMPAS-A builds on macOS (LLVM/flang) and Ubuntu (GCC/gfortran via conda).
Both paths use the same preflight script to detect the toolchain and
export the required environment.

External dependencies: MPI, NetCDF, PnetCDF, PIO, and (for chemistry)
MUSICA-Fortran built with the matching Fortran compiler.

```bash
scripts/check_build_env.sh                       # report mode
eval "$(scripts/check_build_env.sh --export)"    # export mode
```

macOS (LLVM/flang):

```bash
eval "$(scripts/check_build_env.sh --export)" && make -j8 llvm \
  CORE=atmosphere PIO="$PIO" NETCDF="$NETCDF" PNETCDF="$PNETCDF" \
  PRECISION=double MUSICA=true
```

Ubuntu (GCC/gfortran, requires `conda activate mpas`):

```bash
eval "$(scripts/check_build_env.sh --export)" && make -j8 gfortran \
  CORE=atmosphere PIO="$PIO" NETCDF="$NETCDF" PNETCDF="$PNETCDF" \
  PRECISION=double MUSICA=true
```

Notes:
- `PKG_CONFIG_PATH` must be present in the same shell invocation as
  `make` — the Makefile invokes `pkg-config` at parse time.
- Do not mix flang and gfortran `.mod` files; rebuild MUSICA-Fortran with
  the same compiler as CheMPAS-A.

See [BUILD.md](BUILD.md) for the full preflight, troubleshooting, and
dependency-build notes, and [RUN.md](RUN.md) for executing test cases.

## Code Layout

```
CheMPAS/
├── src/
│   ├── driver                       -- Standalone driver
│   ├── framework                    -- MPAS framework (pools, fields, I/O, MPI)
│   ├── operators                    -- Mesh operators
│   ├── external                     -- Vendored external dependencies
│   ├── tools/
│   │   ├── registry                 -- Registry.xml parser / code gen
│   │   └── input_gen                -- Stream and namelist generators
│   ├── core_atmosphere/
│   │   ├── dynamics                 -- Dynamical core
│   │   ├── physics                  -- Physics parameterizations
│   │   ├── diagnostics              -- Diagnostic outputs
│   │   └── chemistry/
│   │       ├── mpas_atm_chemistry.F -- Generic chemistry interface
│   │       └── musica/              -- MUSICA/MICM coupler (mpas_musica.F)
│   ├── core_init_atmosphere         -- Initialization / preprocessing core
│   └── core_{ocean,seaice,landice,sw,test}  -- Inherited from upstream MPAS;
│                                              not actively maintained here
├── micm_configs/                    -- MICM YAML mechanism configs
├── test_cases/                      -- Idealized test case configurations
├── default_inputs/                  -- Default streams and namelists
├── scripts/                         -- Visualization and analysis tools
└── docs/                            -- Documentation tree
```

## Documentation

The most relevant docs for evaluating or extracting pieces of this pilot:

**Architecture & integration**

| Document | Description |
|----------|-------------|
| [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) | System architecture overview |
| [docs/architecture/COMPONENTS.md](docs/architecture/COMPONENTS.md) | Component-level details |
| [docs/musica/MUSICA_INTEGRATION.md](docs/musica/MUSICA_INTEGRATION.md) | MUSICA/MICM coupling design and implementation |
| [docs/musica/MUSICA_API.md](docs/musica/MUSICA_API.md) | MUSICA-Fortran API reference |
| [docs/guides/TUVX_INTEGRATION.md](docs/guides/TUVX_INTEGRATION.md) | TUV-x photolysis integration and test case |

**Build, run, and validation**

| Document | Description |
|----------|-------------|
| [BUILD.md](BUILD.md) | Build instructions and preflight notes |
| [RUN.md](RUN.md) | Running test cases |
| [docs/results/TEST_RUNS.md](docs/results/TEST_RUNS.md) | Recorded run outcomes and validation evidence |
| [docs/guides/VISUALIZE.md](docs/guides/VISUALIZE.md) | Chemistry visualization tools |

**Project context**

| Document | Description |
|----------|-------------|
| [PURPOSE.md](PURPOSE.md) | Pilot motivation and operating approach |
| [AGENTS.md](AGENTS.md) | Development model and review gates |

The full topic-organized index lives at [docs/README.md](docs/README.md),
including the imported MPAS user guide chapters.

## Development Model

The repository's governance structure is designed to support rapid PR
turnaround when coding agent tools are employed. See [AGENTS.md](AGENTS.md)
and [PURPOSE.md](PURPOSE.md).

## License

See [LICENSE](LICENSE).
````

- [ ] **Step 2: Verify the new file contents**

Run: `wc -l README.md`
Expected: roughly 150–160 lines (the existing file was 87 lines; the new file is longer because of the expanded sections).

Run: `head -3 README.md`
Expected output (exactly):
```
CheMPAS-A
=======

```

---

### Task 2: Verify all relative links resolve

**Files:**
- Read: `README.md`

This task is a sanity check that every relative link in the new README points to a file or directory that exists in the repo. The link list was assembled from the new README contents.

- [ ] **Step 1: Run the link existence check**

Run this exact command from the repo root:

```bash
for p in \
  docs/musica/MUSICA_INTEGRATION.md \
  docs/guides/TUVX_INTEGRATION.md \
  test_cases \
  docs/results/TEST_RUNS.md \
  scripts \
  docs/guides/VISUALIZE.md \
  BUILD.md \
  RUN.md \
  docs/architecture/ARCHITECTURE.md \
  docs/architecture/COMPONENTS.md \
  docs/musica/MUSICA_API.md \
  PURPOSE.md \
  AGENTS.md \
  docs/README.md \
  LICENSE \
  ; do
    if [ -e "$p" ]; then
      echo "OK   $p"
    else
      echo "MISS $p"
    fi
  done
```

Expected: every line begins with `OK`. If any line begins with `MISS`, stop and report the missing target — the link in the README must be corrected (or the file created) before commit.

- [ ] **Step 2: Confirm the two external links are well-formed (visual inspection only)**

Read `README.md` and confirm these two URLs appear exactly as written:
- `https://github.com/MPAS-Dev/MPAS-Model`
- `https://github.com/NCAR/MPAS-Model-ACOM-dev`

No network call is required; these are well-known repo URLs.

---

### Task 3: Commit

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Inspect the diff one more time**

Run: `git diff README.md | head -80`
Expected: shows the rewrite (large deletion of old content, large addition of new content).

Run: `git status`
Expected: `README.md` listed as modified; no other working-tree changes.

- [ ] **Step 2: Stage and commit**

Run:

```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs(readme): reframe as ACOM integration pilot

Reframes README around the ACOM integration pilot identity for
MUSICA/MICM-in-MPAS coupling, with MPAS-Model-ACOM-dev positioned as the
hand-crafted-PR staging ground for upstream integration into
MPAS-Dev/MPAS-Model. Adds a "What's Working" section listing the
demonstrated, extractable integration pieces with code paths; documents
both supported build platforms (macOS LLVM/flang and Ubuntu
GCC/gfortran); reorganizes the docs index by purpose; replaces the
agent-forward "Development Workflow" with a brief governance-forward
"Development Model" note.

Design: docs/superpowers/specs/2026-04-19-readme-acom-pilot-reframe-design.md
Plan:   docs/superpowers/plans/2026-04-19-readme-acom-pilot-reframe.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 3: Verify the commit landed**

Run: `git log -1 --oneline`
Expected: shows the new commit on top with the `docs(readme):` subject.

Run: `git status`
Expected: `nothing to commit, working tree clean`.

---

## Self-Review Notes

**Spec coverage:** Each of the eight section drafts in the spec is included verbatim in Task 1's content blob (header/opening, Upstream Integration Path, What's Working, Building, Code Layout, Documentation, Development Model, License). The decoupled-from-upstream framing, the audience-B emphasis, and the agent de-emphasis are all preserved. The out-of-scope items (no edits to PURPOSE/AGENTS/docs/README, no build changes) are honored.

**Placeholder scan:** No TBD/TODO/"add appropriate" markers. Every step shows the actual command or content.

**Type consistency:** Not applicable (no code/types). File paths in Task 2's link check were assembled from the README contents in Task 1; they match exactly.

**Note on `core_init_atmosphere`:** The README tree shows `core_init_atmosphere` as an "Initialization / preprocessing core" — not a "not actively maintained" inherited core. This is intentional and matches the spec.
