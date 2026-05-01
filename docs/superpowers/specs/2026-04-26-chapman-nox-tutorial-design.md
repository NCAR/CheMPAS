# CheMPAS-A Tutorial Chapter 3 — Design

Date: 2026-04-26
Status: Implemented

Target file (modified, not new):
- `docs/tutorial/03-chapman-nox.md`

## Goal

Replace the Chapter 3 placeholder (`docs/tutorial/03-chapman-nox.md`,
nine stub sections from the 2026-04-26 tutorial-scaffold pass) with a
fleshed-out chapter covering the small-domain Chapman + NOx
photostationary-state (PSS) tutorial *and* the TUV-x extended
atmosphere column that Chapman requires.

The chapter is one combined unit — the column extension is a
prerequisite for Chapman (without it, photolysis above the model lid
is wrong and the Chapman steady state never establishes), so the
extension concept and how-to are integrated into the chapter's
reading flow rather than living in a separate chapter or guide.

The chapter reuses `~/Data/CheMPAS/supercell/` as the run directory:
same mesh, partition, namelist files, and `supercell_init.nc` —
swapping in the Chapman `&musica` block and re-initializing tracers
via `init_chapman.py`. This mirrors Chapter 2's ABBA → LNOx swap and
matches how `init_chapman.py` is wired (default input:
`supercell_init.nc`).

Every visible subsection wears the orange "Work in progress" banner
(consistent with Chapter 2's draft-pass convention). Figures are
textual placeholders.

## Scope

**In scope:**

- Replace the existing nine-stub placeholder in
  `docs/tutorial/03-chapman-nox.md` with fleshed prose, command
  blocks, and figure placeholders.
- Cover the Chapman + NOx mechanism via `chapman_nox.yaml` paired
  with `tuvx_chapman_nox.json`; single run, single mechanism.
- Cover the TUV-x column extension as the conceptual section 3.3 and
  the operational section 3.4.
- Reuse the existing tutorial conventions: MyST `{admonition}` WIP
  banners (backtick-fenced), figure placeholders in the form
  `**[Figure 3.N: caption. To be added.]**`, inline-code form for
  repo-root files (`BUILD.md`, `RUN.md`, etc.), markdown-link form
  for in-tree docs (`../chempas/guides/TUVX_INTEGRATION.md`,
  `../chempas/musica/MUSICA_INTEGRATION.md`, etc.).

**Out of scope:**

- New chapters beyond Chapter 3. The tutorial scaffold remains at
  three chapters: Overview (1) / Supercell (2) / Chapman + NOx (3).
- Implementing the regression-suite reference for the Chapman case
  (the YAML file the tutorial points at). The forward reference to
  `scripts/regression.py` parallels Chapter 2's reference and is
  understood to land separately.
- Writing or updating `scripts/gen_tuvx_upper_atm.py`,
  `scripts/init_chapman.py`, `scripts/plot_extension_profiles.py`, or
  `scripts/plot_chemistry_profiles.py`. These exist already; the
  chapter documents them as-is.
- Adding a new run directory under `~/Data/CheMPAS/`. The existing
  `~/Data/CheMPAS/chapman/` directory is essentially empty
  (vestigial Registry files only); the tutorial uses
  `~/Data/CheMPAS/supercell/` instead.
- Generating real PNG plots. Placeholders this pass.
- Modifying any other tutorial chapter, the User's Guide, the
  Technical Description, or the project root toctree.

## Section Layout

Nine sections, matching Chapter 2's count, tuned to the case:

1. **3.1 What you'll learn** — bullets framing the chapter (run
   Chapman + NOx with TUV-x photolysis on an extended atmosphere
   column; verify the photostationary state).
2. **3.2 The Chapman + NOx case** — case description: the four
   classic Chapman reactions, NOx as a catalytic ozone-cycle modifier,
   the analytical Leighton PSS as the chapter's diagnostic target.
   One paragraph also explains *why the supercell mesh works as a
   testbed* even though Chapman is global-stratospheric in spirit
   (1-D AFGL profile seeded uniformly; chemistry has no feedback on
   dynamics; the small mesh is acting as a column-like sandbox).
   Figure 3.1 placeholder: AFGL O₃ profile interpolated to the
   supercell vertical grid.
3. **3.3 The TUV-x column extension *(concept)*** — *why* this
   exists. The MPAS lid is at 50 km but TUV-x photolysis depends on
   UV that has been attenuated by the entire column above. Without
   an extension, TUV-x sees vacuum above 50 km, jO₃ and jNO₂ are
   wrong by a non-trivial factor at high altitudes, and the Chapman
   steady state never establishes. The fix: a tracked CSV
   (`micm_configs/tuvx_upper_atm.csv`) carrying T, n_air, n_O₃ from
   USSA76 + AFGL O₃ on a 5-km grid from 50 to 100 km. At runtime,
   `mpas_tuvx.F::load_extension_csv` stitches MPAS midpoint values
   (lower slice) and CSV midpoint values (upper slice) into a single
   radiator column for TUV-x. Source-of-truth: cross-link to
   `src/core_atmosphere/chemistry/mpas_tuvx.F` and to
   `docs/chempas/guides/TUVX_INTEGRATION.md` for the broader
   integration story. Prose-only; no figure (figures live in 3.4
   where the reader actually generates them).
4. **3.4 Generating and verifying the extension CSV *(how-to)*** —
   two concrete commands:

   - `python scripts/gen_tuvx_upper_atm.py` — emits
     `micm_configs/tuvx_upper_atm.csv` covering 50–100 km at 5 km
     spacing.
   - `python scripts/plot_extension_profiles.py -i ~/Data/CheMPAS/supercell/output.nc`
     — three panels (T, n_air log, n_O₃ log) showing MPAS values
     below the lid and extension-CSV values above, boundary visibly
     continuous.

   Note in prose: the verification step references `output.nc` that
   doesn't yet exist at this point in the chapter; the section
   explicitly tells the reader they will run the plotter twice — once
   here against the previous LNOx run from Chapter 2 (or any prior
   supercell run) to inspect the column shape, and again after the
   Chapman run lands in section 3.6. Figure 3.2 placeholder: stitched
   T / n_air / n_O₃ vertical profiles, MPAS region vs. extension.
5. **3.5 Initializing the Chapman tracers** — `init_chapman.py`
   invocation against `supercell_init.nc`. Documents the six tracers
   it seeds: qO2 (uniform 0.2313 kg/kg), qO3 (AFGL profile,
   continuous with the column extension at the lid), qO and qO1D
   (zero, fast radicals spin up), qNO and qNO2 (total-NOx profile
   with daytime ~30/70 partitioning). Single-command invocation
   plus a parenthetical note: this rewrites tracers in
   `supercell_init.nc`, so a reader who is mid-LNOx-experiments may
   want to keep a copy first or re-generate the supercell init from
   scratch when switching back.
6. **3.6 Run with the Chapman + NOx mechanism** — `&musica` block
   replacement (six fields: `config_micm_file`,
   `config_tuvx_config_file`, `config_tuvx_top_extension`,
   `config_tuvx_extension_file`, `config_chemistry_latitude`,
   `config_chemistry_longitude`); archive-and-rerun pattern matching
   Chapter 2's; plotting via `scripts/plot_chemistry_profiles.py`.
   Figure 3.3 placeholder: vertical profiles of qO3, qNO, qNO2, and
   the NO/NO₂ ratio at t = 2 h, mid-domain column.

   Pairing note: the chapter pairs `chapman_nox.yaml` (mechanism)
   with `tuvx_chapman_nox.json` (photolysis). This pairing must be
   verified during implementation against the actual file contents
   in `micm_configs/`; if the existing `tuvx_chapman_nox.json` does
   not in fact match the species in `chapman_nox.yaml`, the spec is
   wrong and the implementation must use the correct pairing.
7. **3.7 The photostationary-state diagnostic** — prose-only
   conceptual section. The Leighton expression
   `[NO]/[NO₂] = jNO₂ / (k_{NO+O₃} · [O₃])`, where it should hold
   (stratospheric NOx peak layer ~25–35 km where photolysis is
   strong, [O₃] is high, and partitioning relaxes within seconds),
   and where it shouldn't (lowest layers, surface shadow, anywhere
   the photolysis driver is weak). Spin-up note: 10–15 minutes of
   model time is plenty for partitioning to settle.
8. **3.8 Verifying numerically** — two complementary checks:

   - **Regression suite:** `python scripts/regression.py run --case supercell`
     (same forward-reference caveat as Chapter 2 — the design exists
     in `docs/superpowers/specs/2026-04-19-regression-suite-design.md`,
     the implementation lands separately).
   - **Analytical PSS check:** a short inline Python snippet
     (~10 lines using `netCDF4` + `numpy`) that pulls jNO₂, [O₃],
     [NO], [NO₂] from `output.nc` at the final timestep, computes
     the Leighton ratio, and compares to the simulated ratio. Pass
     criterion: agreement to within ~5 % in the stratospheric layer.
     Figure 3.4 placeholder: simulated vs. analytical [NO]/[NO₂] vs.
     height at the final timestep.
9. **3.9 Next steps** — forward links: MUSICA / MICM / TUV-x upstream
   docs, in-tree `TUVX_INTEGRATION.md` and `MUSICA_INTEGRATION.md`,
   one-bullet note that future tutorial chapters will cover other
   idealized cases (mountain wave, baroclinic wave, chem box) when
   they're written.

## Conventions (mirroring Chapter 2)

- **WIP banner** on every numbered subsection (3.1–3.9), MyST
  backtick-fenced ``` ```{admonition} Work in progress :class: warning ``` ```
  with body "Section content coming." This signals draft state per
  the user's explicit guidance for this pass.
- **Figure placeholders** in the technical-description style:
  `**[Figure 3.N: caption. To be added.]**`. Used in sections 3.2,
  3.4, 3.6, 3.8 (Figures 3.1–3.4). When real PNGs land, they go in
  `docs/_static/tutorial/` and replace these placeholders.
- **References to repo-root files** (`BUILD.md`, `RUN.md`,
  `test_cases/...`) use inline-code form (backticks); markdown links
  produce `myst.xref_missing` warnings since those files live
  outside the Sphinx source tree.
- **References to in-tree docs** (`../chempas/guides/TUVX_INTEGRATION.md`,
  `../chempas/musica/MUSICA_INTEGRATION.md`,
  `../tutorial/02-supercell.md`, etc.) use markdown-link form.

## Build verification

After the Chapter 3 rewrite lands:

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && make html
```

Acceptable: existing pre-`develop` warnings carry over. **Not
acceptable:** any new warning whose path contains `tutorial/`. The
chapter's cross-links — to `02-supercell.md`,
`../chempas/guides/TUVX_INTEGRATION.md`,
`../chempas/musica/MUSICA_INTEGRATION.md`, `../index.rst`, and any
others added in 3.9 — must all resolve.

`docs/_build/html/tutorial/03-chapman-nox.html` should render with
nine numbered subsections, each carrying a WIP banner; four figure
placeholders (Figures 3.1–3.4); commands rendered as bash code blocks
with syntax highlighting; the Fortran `&musica` namelist block in
section 3.6 rendered with Fortran highlighting; the inline Python
snippet in section 3.8 rendered with Python highlighting; the
Leighton expression in section 3.7 rendered as a code block (or a
math block — the implementer can choose; MyST `dollarmath` is
enabled).

## Non-goals (explicit)

- This spec does not produce real PNG plots; placeholders only.
- This spec does not add tutorial chapters for mountain wave, JW
  baroclinic wave, or chem box.
- This spec does not modify the regression suite or its YAML
  references.
- This spec does not change the Sphinx theme, search index, or
  navigation behavior.
- This spec does not edit any CheMPAS-A source code or scripts.
