# LNOx isotherm-mode and Chapman + NOx global docs — design

**Date:** 2026-05-07
**Status:** Proposed

## Goal

Document two recently landed CheMPAS-A capabilities so they are discoverable
and usable from the existing docs:

1. The new **isotherm-mode** branch of the lightning-NOx (LNOx) source in
   `mpas_lightning_nox.F`, added by the 2026-05-06 LNOx isotherm-source
   work (commits `1eaedc9`, `2295ffd`, `e9e02ff`, `2dbcdc6`, `72fa2cf`,
   `16403d9`). The implementation spec lives at
   `docs/superpowers/specs/2026-05-06-lnox-isotherm-source-design.md`.
2. The new **`test_cases/chapman_nox_global/`** idealized case (commit
   `37ba8d5` and its plotting follow-ups), which runs Chapman + NOx
   chemistry on the global `x1.40962` mesh for 24 hours.

This is a docs-only change — no source, registry, or namelist edits.
Run scripts and namelists referenced here already exist and are
documented as-is.

## Non-goals

- No source-code changes (the LNOx scheme itself is implemented; the
  global Chapman + NOx case already runs).
- No new MICM YAML, TUV-x JSON, or plotting scripts.
- No regression-suite reference values for either case (still tracked
  separately by `2026-04-19-regression-suite-design.md`).
- No real PNG figures generated this pass — all figure slots use the
  `**[Figure X.N: caption. To be added.]**` placeholder convention
  established by Chapter 2 and Chapter 3.
- No upstream-MPAS docs (User's Guide, Technical Description) touched.

## Files touched

### New

| File | Purpose |
|---|---|
| `docs/chempas/guides/LNOX_INTEGRATION.md` | Scheme guide, parallel to `TUVX_INTEGRATION.md`. Both gating modes, namelist options, code paths, calibration notes. |
| `docs/tutorial/04-chapman-nox-global.md` | Tutorial Chapter 4 — Chapman + NOx on the global `x1.40962` mesh. |

### Modified

| File | Change |
|---|---|
| `docs/tutorial/02-supercell.md` | Restructure §2.6 into three subsections: §2.6.1 altitude-mode walkthrough (current content, lightly rewritten), §2.6.2 isotherm-mode walkthrough (new), §2.6.3 comparison subsection (new). Update §2.7 / §2.9 cross-refs. |
| `docs/tutorial/03-chapman-nox.md` | §3.9 *Next steps*: replace "Future tutorial chapters … not yet scheduled" with a link to Chapter 4. |
| `docs/tutorial/index.rst` | Add `04-chapman-nox-global` to the toctree. |
| `test_cases/README.md` | Add `chapman_nox_global/` row to the cases table and a setup note explaining the JW-init reuse and `init_chapman_nox.py` step. |
| `CLAUDE.md` | Add a `chapman_nox_global` row to the *Test Run Directory* table. |
| `LNOx.md` | Trim to a one-paragraph pointer to `LNOX_INTEGRATION.md` (preserve the original DC3 quote at the top so the historical motivation is not lost; keep file at repo root for backward compatibility). |

No deletions other than the partial trim of `LNOx.md`. No source code,
Registry.xml, MICM/TUV-x configs, plotting scripts, or User's Guide
changes.

## Section layout

### 1. `LNOX_INTEGRATION.md`

Six sections following the `TUVX_INTEGRATION.md` shape (overview →
configuration → code → calibration → references):

1. **Overview** — Operator-split LNOx injection model: what the scheme
   does, where it runs in the chemistry timestep, and its relationship
   to the MICM solver and TUV-x photolysis. One-paragraph history note
   (inherited from DAVINCI-MPAS, extended for DC3-style storms).
2. **Gating modes — altitude vs. isotherm** — Table comparing the two
   modes (lifted from the 2026-05-06 design spec):

   | Mode | Gate | Rate |
   |---|---|---|
   | `altitude` (default) | `z_min ≤ z ≤ z_max` AND `w > w_threshold` | `S = source_rate · (w − w_threshold) / w_ref` |
   | `isotherm` (new) | `t_min ≤ T ≤ t_max` AND `w > w_threshold` | `S = source_rate` (constant) |

   Cite the LNOx.md DC3 motivation for the 233.15–262.15 K mixed-phase
   isotherm window. Note that altitude mode is the inherited
   formulation and isotherm mode is the literature-faithful one.
3. **Namelist options** — Full list of `config_lnox_*` options with
   defaults, units, and which mode each applies to:
   `config_lnox_gating_mode`, `config_lnox_source_rate`,
   `config_lnox_w_threshold`, `config_lnox_w_ref`, `config_lnox_z_min`,
   `config_lnox_z_max`, `config_lnox_t_min`, `config_lnox_t_max`,
   `config_lnox_j_no2`, `config_lnox_nox_tau`. Cross-reference the
   Registry.xml `musica` group.
4. **Code paths** — File:line pointers (not full excerpts) into
   `src/core_atmosphere/chemistry/mpas_lightning_nox.F` for
   `lightning_nox_init`, `lightning_nox_inject`, the mode-flag dispatch,
   and the optional `temperature(:,:)` argument; into
   `src/core_atmosphere/chemistry/mpas_atm_chemistry.F` for the
   T-from-`theta_m`/`exner` computation when the isotherm gate is
   active.
5. **Calibration notes** — LNOx.md target (~1 ppbv NOx at cloud top in
   DC3-like supercells), the 1.0e-3 ppbv/s starting rate for isotherm
   mode, the manual retune-and-rerun loop, and a forward-pointer to
   the regression-suite design.
6. **See also** — Links to the 2026-05-06 design spec, Tutorial Ch. 2
   §2.6, `MUSICA_INTEGRATION.md`, the original `LNOx.md` note (now a
   pointer file), and the regression-suite design.

### 2. Tutorial Ch. 2 — restructured §2.6

Current §2.6 documents one LNOx run (altitude mode). Restructure into:

- **§2.6 Run with the LNOx + O3 mechanism** — short framing paragraph
  introducing the scheme and noting that two gating modes are available;
  forward-link to `LNOX_INTEGRATION.md`.
- **§2.6.1 LNOx with altitude-mode gating** — current §2.6 content
  (init, namelist block, run, plot, "What to look for"). Light prose
  edit only; the namelist block and commands are unchanged.
- **§2.6.2 LNOx with isotherm-mode gating** — parallel walkthrough:
  - Same `init_lnox_o3.py` step (no change).
  - Replace `&musica` block with the isotherm version (lifted from
    `test_cases/supercell/namelist.atmosphere`'s commented isotherm
    block: `gating_mode='isotherm'`, `source_rate=1.0e-3`, `t_min=233.15`,
    `t_max=262.15`, drop `w_ref`, `z_min`, `z_max`).
  - Same archive-and-rerun pattern, same `plot_lnox_o3.py`.
  - "What to look for": NOx confined to the 233–262 K mixed-phase layer
    (~5–9 km in the supercell setup), constant source magnitude (no
    updraft scaling), peak NOx of order 1 ppbv. Calibration may need a
    retune; that is expected.
- **§2.6.3 Comparing the gating modes** — short paragraph + figure
  placeholder for side-by-side qNO / qNO2 / qO3 final-state cross-
  sections from the two runs. Discuss the spatial-confinement
  difference (altitude window is fixed in z; isotherm window moves with
  the cloud) and the rate-magnitude difference (altitude scales with
  updraft excess; isotherm is flat).

§2.7 (Comparing the two runs — ABBA vs. LNOx) is unchanged in scope but
gets a one-line note that "LNOx + O3" in this section refers to either
gating mode (the reader picks one for the comparison).

§2.9 *Next steps* gets a `LNOX_INTEGRATION.md` link added under "MUSICA
internals".

WIP banners and `**[Figure 2.N: ... To be added.]**` placeholders
consistent with Chapter 2's existing convention.

**Figure renumbering:** Inserting two new figures inside §2.6 forces a
renumber so figures still follow content order. Final mapping:

| Slot | Caption (abbreviated) | Status |
|---|---|---|
| 2.1 | Supercell initial state | unchanged |
| 2.2 | qA, qB, qAB at t = 2 h, ABBA | unchanged |
| 2.3 | NO, NO₂, O₃ at t = 2 h, LNOx altitude mode | unchanged content; was Fig 2.3 |
| **2.4** | **NO, NO₂, O₃ at t = 2 h, LNOx isotherm mode** | **new (§2.6.2)** |
| **2.5** | **Side-by-side LNOx altitude vs. isotherm at t = 2 h** | **new (§2.6.3)** |
| 2.6 | Side-by-side ABBA vs. LNOx at t = 2 h (was 2.4) | renumbered, unchanged caption |
| 2.7 | Standalone ABBA box-model time series (was 2.5) | renumbered |
| 2.8 | Standalone LNOx box-model time series (was 2.6) | renumbered |

Cross-references to figure numbers in surrounding prose (§2.7 / §2.10 /
§2.11) get updated to match.

### 3. Tutorial Ch. 4 — `04-chapman-nox-global.md` (new)

Eight sections mirroring Chapter 3's shape:

1. **4.1 What you'll learn** — Run the global Chapman + NOx case on
   `x1.40962`; observe the day–night photolysis terminator in the jNO₂
   field; verify NOx partitioning flips across day/night; inspect the
   24-hour zonal-mean ozone response.
2. **4.2 The Chapman + NOx global case** — Global mesh (40 962 cells,
   nominal 120 km), 26 levels (the JW baroclinic-wave init mesh),
   24-hour integration, 450 s dynamics timestep, 3600 s TUV-x update
   interval, `config_chemistry_use_grid_coords = .true.` so every cell
   uses its own (lat, lon) for the SZA calculation. Contrast with
   Chapter 3's small-domain column-like sandbox: this case is what
   "global Chapman + NOx" actually looks like in CheMPAS-A — terminator
   visible, NOx photochemistry running diurnally across the mesh.
   Note: this reuses the JW baroclinic-wave horizontal mesh as a
   convenient global init; this is *not* a baroclinic-wave dynamics
   demonstration.
3. **4.3 Setup** — Checklist parallel to §2.3 / §3.3: model executable,
   run directory at `~/Data/CheMPAS/chapman_nox_global/`, partition
   files, conda env. Note the JW baroclinic-wave init step is a
   prerequisite (the global init NetCDF, `x1.40962.init.nc`, comes from
   the standard JW init pipeline documented in `test_cases/README.md`).
4. **4.4 Initializing Chapman + NOx tracers globally** — What
   `init_chapman_nox.py` writes into `x1.40962.chapman_nox_init.nc`:
   uniform qO2 (~0.232 kg/kg), Gaussian qO3 (10 ppmm peak at 25 km,
   σ = 7 km), qO floor (1e-12), uniform 1 ppbv qNO and qNO2 backgrounds.
   Mass mixing ratios in kg/kg. The init is a function of altitude
   only — no horizontal structure is imposed; the chemistry generates
   any horizontal pattern through the diurnal photolysis cycle.
5. **4.5 Running** — Reference the tracked
   `test_cases/chapman_nox_global/namelist.atmosphere` and
   `streams.atmosphere`. The `&musica` block uses
   `config_micm_file = 'chapman_nox.yaml'`,
   `config_tuvx_config_file = 'tuvx_chapman_nox.json'`, the upper-atm
   extension CSV (same one introduced in Ch. 3 §3.3), and a 3600 s
   TUV-x update interval. Run with 8 MPI ranks; archive-and-rerun
   pattern matching Chapter 2 / Chapter 3.
6. **4.6 Plotting the global response** —
   `scripts/plot_chapman_nox_global.py` produces four figures:
   - **`jNO2_terminator.png`** — jNO₂ maps at t = 0 / 6 / 12 / 18 UTC,
     showing the day-night terminator sweeping the globe.
   - **`tracers_evolution.png`** — O₃ at level 22 (~36 km) and NO₂ at
     level 17 (~25 km), at t = 12 h and t = 24 h; shows the NOx-driven
     ozone modulation in the upper stratosphere.
   - **`nox_partition.png`** — NO₂ / (NO + NO₂) molar fraction at t = 12 h
     and t = 24 h: dayside drops toward Leighton, nightside relaxes
     toward NO₂.
   - **`o3_profile.png`** — global-mean O₃ vertical profile and the
     zonal-mean ΔO₃ over the 24-hour window (symlog so production above
     and NOx-driven loss below are both visible).
   Figure placeholders (`**[Figure 4.1: ... To be added.]**` … 4.4) for
   each.
7. **4.7 What to look for** — Specific things readers should see in
   their plots: terminator-aligned jNO₂ gradients, NOx partition flip
   across the terminator, ~10–20 % O₃ swing at 36 km between dayside
   and the previous night, fast-radical species (qO, qO¹D) staying
   small. Note the 24-hour run is too short for the O₃ column to fully
   relax; longer runs are out of scope here.
8. **4.8 Next steps / See also** — Links to Chapter 3 (analytical PSS
   check on a small domain), `MUSICA_INTEGRATION.md`,
   `TUVX_INTEGRATION.md`, and `LNOX_INTEGRATION.md` (the global case
   has no LNOx source, but readers exploring chemistry-coupled cases
   should see the LNOx scheme too).

WIP banners on every visible subsection, matching the Chapter 2 / 3
convention.

### 4. `test_cases/README.md` — table + setup note

Add a row to the cases table:

| Case | Init Case | Mesh | Cells | Levels | dt (s) | Duration |
|---|---|---|---|---|---|---|
| `chapman_nox_global/` | (reuses JW init) | 120 km | 40 962 | 26 | 450 | 24 hours |

Add a short paragraph after the existing `chem_box` note explaining:
- The case reuses the JW baroclinic-wave init mesh
  (`x1.40962.init.nc`) as the dynamics initial state.
- Tracers are injected via `scripts/init_chapman_nox.py` to produce
  `x1.40962.chapman_nox_init.nc` (the file the streams config reads).
- This is *not* a baroclinic-wave dynamics demonstration — it just
  borrows the global mesh.

Document the per-case sequence explicitly (a short numbered list, not
just a comment in the shell block):

1. The standard `init_atmosphere_model` step from the *Setup and
   Initialization* loop already produces `x1.40962.init.nc` under the
   `jw_baroclinic_wave/` run directory.
2. Copy that file (or symlink it) into
   `~/Data/CheMPAS/chapman_nox_global/` as `x1.40962.init.nc`.
3. Run `scripts/init_chapman_nox.py -i x1.40962.init.nc -o
   x1.40962.chapman_nox_init.nc` from the `chapman_nox_global/` run
   directory to produce the tracer-injected init NetCDF the
   `streams.atmosphere` config reads.
4. Copy the tracked `test_cases/chapman_nox_global/` configs
   (`namelist.atmosphere`, `streams.atmosphere`,
   `stream_list.atmosphere.output`) and the partition file
   (`x1.40962.graph.info.part.8`) into the run directory.

This sequence is the single non-obvious step in the case setup; calling
it out explicitly avoids the trap of running the standard JW init loop
and then having no `x1.40962.chapman_nox_init.nc` to feed the run.

### 5. `CLAUDE.md` — test-run table

Add row to the "Test Run Directory" table:

| Case | Directory | Duration | Mesh |
|---|---|---|---|
| Chapman + NOx (global) | `~/Data/CheMPAS/chapman_nox_global/` | 24 hours | 120 km, 40 962 cells, 26 levels |

No other CLAUDE.md edits.

### 6. `LNOx.md` — pointer trim

Keep the four-line DC3 quote at the top (it is the canonical motivation
for the isotherm formulation and is cited by both the design spec and
the new guide). Append:

> See [docs/chempas/guides/LNOX_INTEGRATION.md](docs/chempas/guides/LNOX_INTEGRATION.md)
> for the full scheme description, namelist options, and calibration
> notes.

This preserves the historical reference and inbound links while
delegating the comprehensive description to the guide.

## Conventions enforced across the new prose

- **MyST admonitions** for WIP banners (backtick-fenced
  `{admonition} ... :class: warning`), matching Chapter 2 / 3.
- **Inline-code form** for repo-root files (`BUILD.md`, `RUN.md`,
  `LNOx.md`).
- **Markdown-link form** for in-tree docs
  (`docs/chempas/guides/LNOX_INTEGRATION.md`,
  `docs/chempas/musica/MUSICA_INTEGRATION.md`).
- **Figure placeholders** as `**[Figure X.N: caption. To be added.]**`.
- Lat/lon, file paths, and namelist values match the tracked
  `test_cases/chapman_nox_global/` and `test_cases/supercell/` files —
  the docs do not introduce different default values.

## Verification steps

1. **Sphinx build** — `sphinx-build` (or the existing docs build script)
   completes without warnings on the new and modified files. Toctree
   resolves Chapter 4 cleanly.
2. **Cross-link check** — every markdown link in new/modified files
   resolves to an existing file in the repo (manual `ls` of each
   target).
3. **Table parity** — the LNOx namelist options listed in the new guide
   match the `Registry.xml` `musica` group entries (`grep config_lnox_
   src/core_atmosphere/Registry.xml`).
4. **Tutorial run-through** — read Chapter 2 (with restructured §2.6)
   and Chapter 4 end-to-end; confirm commands, paths, and namelist
   blocks are internally consistent and consistent with each other and
   with the tracked test-case files.
5. **No source code touched** — `git status` shows changes only under
   `docs/`, `test_cases/README.md`, `CLAUDE.md`, and `LNOx.md`.

## Open questions

None blocking. Two minor follow-ups, neither in scope here:

- Real PNG figures for both new sections will land separately when the
  associated runs are archived (matches the pattern set in Chapter 2 /
  Chapter 3).
- Whether to add a `LNOX_INTEGRATION.md` link to `docs/chempas/README.md`
  alongside the existing TUV-x and MUSICA pointers can be decided when
  the guide is in place; for this pass, the in-tutorial cross-links are
  sufficient.
