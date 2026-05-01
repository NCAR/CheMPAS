# CheMPAS-A Tutorial Section — Design

Date: 2026-04-26
Status: Implemented

Target files (new):
- `docs/tutorial/index.rst`
- `docs/tutorial/01-overview.md`
- `docs/tutorial/02-supercell.md`
- `docs/tutorial/03-chapman-nox.md`

Target files (modified):
- `docs/index.rst` (add `tutorial/index` to the root toctree)

## Goal

Add a new top-level **CheMPAS-A Tutorial** section to the Sphinx docs that
walks readers hands-on through CheMPAS-A's idealized chemistry test cases.
This pass scaffolds the full tutorial structure and fleshes out the first
chapter — the supercell test case run with both the ABBA and LNOx + O3
mechanisms. The second chapter (small-domain Chapman + NOx
photostationary state) is added as a structural placeholder so the
toctree announces the tutorial arc from day one.

The tutorial is grounded in the existing regression-test runs
(`scripts/regression.py`, `~/Data/CheMPAS/<case>/`) but its tone is
pedagogical — narrative walkthrough, expected plots, comparison
between mechanisms — rather than the snapshot-comparison framing of
the regression suite itself.

Every section in this pass carries an orange "Work in progress" banner
and uses figure placeholders rather than embedded PNGs.

## Scope

**In scope:**

- New `docs/tutorial/` directory, parallel to `users-guide/` and
  `technical-description/` in `docs/index.rst`'s root toctree.
- Markdown content files (matching the `users-guide/` `.md` + `index.rst`
  pattern), so the existing `myst_parser` configuration works without
  changes to `conf.py`.
- `01-overview.md` orienting the reader: what cases the tutorial covers,
  what's assumed (model built per `BUILD.md`, conda env `mpas` available,
  `~/Data/CheMPAS/<case>/` set up per `RUN.md`), with cross-links.
- `02-supercell.md` fleshed out: one chapter, two mechanisms (ABBA and
  LNOx + O3) as parallel sections, ending with a comparison.
- `03-chapman-nox.md` as a structural placeholder: same section headings
  as `02-supercell.md`, each marked `**[To be added.]**`.
- WIP admonition banner at the top of each subsection across the
  tutorial. The whole tutorial is a draft in this pass, so every
  subsection of `02-supercell.md` and `03-chapman-nox.md` carries the
  banner, and `01-overview.md` carries a single page-level banner.
- Figure placeholders in the technical-description style:
  `**[Figure N.M: caption. To be added.]**`.

**Out of scope:**

- Generating real PNG plots and embedding them — placeholders only.
- Mountain wave, JW baroclinic wave, and chem-box tutorial chapters
  — not added in this pass; these may be added later as separate work
  and are not implied by the placeholder structure.
- Changes to `users-guide/` or `technical-description/`.
- Numerical verification tables embedded in tutorial prose — readers
  are pointed at `scripts/regression.py` as the source of truth, not
  given hand-copied min/max/mean values that would drift.
- Sphinx theme or extension changes (no `conf.py` edits beyond what
  may be required to make the new toctree render).

## File Layout

```
docs/tutorial/
├── index.rst              # toctree, landing page
├── 01-overview.md         # purpose, prereqs, how to use
├── 02-supercell.md        # fleshed-out: ABBA + LNOx + comparison
└── 03-chapman-nox.md      # placeholder: same headings, "To be added."
```

`docs/tutorial/index.rst` follows the structure of
`docs/users-guide/index.rst`: a brief landing page header plus a
`toctree` listing the chapter files in numeric order.

`docs/index.rst` gains a single line in its existing toctree:

```rst
.. toctree::
   :titlesonly:

   users-guide/index
   tutorial/index
   technical-description/index
```

(Tutorial sits between User's Guide and Technical Description: a reader
typically reads about the model, runs the tutorial, then reaches for
the dynamical-core reference material.)

## Chapter 1 — Overview (`01-overview.md`)

Page-level WIP banner at the top. Then short prose covering:

- What the CheMPAS-A Tutorial is (a hands-on walkthrough of CheMPAS-A's
  idealized chemistry cases, complementary to the verbatim-upstream
  User's Guide).
- What this tutorial assumes the reader has done already:
  `atmosphere_model` built (cross-link to `BUILD.md` / Chapter 3),
  `~/Data/CheMPAS/<case>/` populated (cross-link to `RUN.md` and
  `test_cases/README.md`), conda env `mpas` available for plotting.
- A two-line description of each chapter currently in scope, with
  internal cross-references.
- A pointer to `scripts/regression.py` as the way to numerically
  verify a run.

## Chapter 2 — Supercell with ABBA and LNOx (`02-supercell.md`)

One chapter, top-to-bottom flow. Section headings:

1. **What you'll learn** — bullet list framing the chapter.
2. **The supercell case** — one paragraph on the idealized convection
   setup (60 stretched levels to 50 km, ~300 m surface to ~1 km top,
   2 h run) and why it's a useful chemistry testbed (strong vertical
   transport, well-defined updraft); placeholder for an initial-state
   figure.
3. **Setup checklist** — concrete commands to confirm the build, the
   run dir, and the conda env.
4. **Initialization** — invocation of `init_atmosphere_model`, what it
   produces (`supercell_init.nc`), pointer to `RUN.md` for the
   rank/partition rules.
5. **Run with the ABBA mechanism** — namelist line selecting
   `abba.yaml`, brief description of ABBA (toy reaction set, link to
   `micm_configs/abba.yaml`), `mpiexec -n 8 ./atmosphere_model`
   invocation, expected log-tail signature, figure placeholder for the
   qA / qB / qAB final state.
6. **Run with the LNOx + O3 mechanism** — switch `config_micm_file`
   to `lnox_o3.yaml`, note `init_lnox_o3.py` if a re-init is needed,
   run again, figure placeholder for NO / NO₂ / O₃ final state, brief
   note on the lightning-NOx source term with a pointer to the MUSICA
   integration doc.
7. **Comparing the two runs** — short prose calling out what to look
   for (shared transport pattern, divergent chemistry), side-by-side
   figure placeholder.
8. **Verifying numerically** — one paragraph pointing at
   `scripts/regression.py` and the exact invocation; explicitly notes
   that the regression YAML — not the tutorial — is the source of
   truth for expected min/max/mean values.
9. **Next steps** — pointer to Chapter 3 (Chapman + NOx) and to MUSICA
   / MICM upstream docs.

## Chapter 3 — Chapman + NOx Photostationary State (`03-chapman-nox.md`)

Skeleton-only. Page-level WIP banner at the top, then one short stub
describing intent (small-domain Chapman cycle plus NOx for
photostationary-state diagnostics; short integration where the
analytical PSS solution is a clean sanity check). The same nine
section headings as `02-supercell.md` follow, each containing only
`**[To be added.]**` so the chapter is structurally complete the
moment real content lands.

## Conventions

### WIP banner

Reuses the existing `index.rst` orange `Under construction` admonition
pattern, transcribed to MyST for the `.md` files:

````markdown
```{admonition} Work in progress
:class: warning

This section is still being written. Commands and expected output are
provisional and may change.
```
````

Applied at the top of every numbered subsection of `02-supercell.md`
and `03-chapman-nox.md`, and once at the top of `01-overview.md` as a
page-level banner.

### Figure placeholder

Follows the technical-description convention:

```markdown
**[Figure 2.3: qA, qB, qAB at t = 2 h, ABBA mechanism. To be added.]**
```

Chapter number matches the file's `0N` prefix. When real PNGs land,
they go in `docs/_static/tutorial/` and replace these placeholders
one at a time without touching the surrounding prose.

## Build verification

After the new files are written, the docs must build cleanly:

```bash
cd docs && make html
```

No new Sphinx warnings beyond those already present on `develop`.
`docs/_build/html/index.html` should show **CheMPAS-A Tutorial** as
a top-level section in the sidebar with three child entries
(Overview, Supercell with ABBA and LNOx, Chapman + NOx
Photostationary State).

## Non-goals (explicit)

- This spec does not produce real plots; that's a separate follow-up.
- This spec does not add tutorial chapters for mountain wave, JW
  baroclinic wave, or chem-box.
- This spec does not modify the regression suite or its YAML
  references.
- This spec does not change the Sphinx theme, search index, or
  navigation behavior.
