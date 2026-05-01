# Standalone MUSICA-Python Tutorials Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three standalone MUSICA-Python example scripts under `scripts/musica_python/` (one box model per CheMPAS-A tutorial mechanism, plus one column model for Chapman + NOx) along with three matching tutorial sections (§§2.10, 2.11 in Chapter 2; §3.10 in Chapter 3).

**Architecture:** Three Python scripts each load a CheMPAS-A `micm_configs/*.yaml` mechanism via `musica.MICM`, set initial conditions and rate parameters, step the solver, and emit `<case>.nc` and `<case>.png`. The column script reuses MUSICA's bundled `vTS1` TUV-x calculator with a custom alias map for our reaction names. Plotting follows `scripts/style.py` (NCAR palette + project label/title rules). Tutorial sections wear the project draft-pass WIP banner and figure-placeholder convention.

**Tech Stack:** `musica` (MICM + TUV-x Python bindings), `numpy`, `xarray`, `matplotlib`, `pvlib`, `ussa1976`. The `mpas` conda env already has the first four; `pip install musica ussa1976 pvlib` covers the new deps.

**Spec:** `docs/superpowers/specs/2026-04-26-musica-python-tutorials-design.md`

---

## File Structure

New directory and files:

```
scripts/musica_python/
├── README.md                   # one-page overview + install pointer
├── abba_box.py                 # ABBA box model
├── lnox_box.py                 # LNOx + O3 box model
└── chapman_nox_column.py       # Chapman + NOx column model
```

Modified files:

- `docs/tutorial/02-supercell.md` — append §§2.10 and 2.11 at chapter end (after existing §2.9).
- `docs/tutorial/03-chapman-nox.md` — append §3.10 at chapter end (after existing §3.9).

No conf.py changes. No edits to existing tutorial sections, mechanisms, or CheMPAS-A source.

**Note on script smoke-testing.** Each implementation step ends with a build/spot-check; running the new scripts requires `musica`, `pvlib`, `ussa1976` in the conda env, which may or may not be installed. The hard acceptance gate for each task is the **clean Sphinx build** (zero new tutorial-pathed warnings) and the file existing on disk with the expected content. If the conda env has the packages, the implementer also runs each script as a sanity check; if not, that step is a no-op with a brief note in the report.

---

## Task 1: Create `scripts/musica_python/` with README and `abba_box.py`

**Files:**
- Create: `scripts/musica_python/README.md`
- Create: `scripts/musica_python/abba_box.py`

This task creates the new directory, writes a one-page README, and lands the smallest of the three scripts (ABBA box, no photolysis, no TUV-x).

- [ ] **Step 1.1: Create `scripts/musica_python/README.md`**

````markdown
# Standalone MUSICA-Python Examples

Pedagogical scripts that exercise the same MICM mechanism configs the
CheMPAS-A tutorial chapters use, *without* MPAS in the loop. Each
script mirrors a section of the tutorial:

| Script                  | Tutorial section            | Mechanism             |
| ----------------------- | --------------------------- | --------------------- |
| `abba_box.py`           | §2.10 (Chapter 2 supercell) | `abba.yaml`           |
| `lnox_box.py`           | §2.11 (Chapter 2 supercell) | `lnox_o3.yaml`        |
| `chapman_nox_column.py` | §3.10 (Chapter 3 Chapman)   | `chapman_nox.yaml`    |

Each script writes `<case>.nc` (xarray Dataset) and `<case>.png`
into this directory.

## Dependencies

`numpy`, `xarray`, `matplotlib`, `netCDF4` are already in the `mpas`
conda environment. Two extra installs:

```bash
~/miniconda3/envs/mpas/bin/pip install musica ussa1976 pvlib
```

(Equivalent: `pip install 'musica[tutorial]'` per MUSICA's README.)

## Running

```bash
~/miniconda3/envs/mpas/bin/python scripts/musica_python/abba_box.py
~/miniconda3/envs/mpas/bin/python scripts/musica_python/lnox_box.py
~/miniconda3/envs/mpas/bin/python scripts/musica_python/chapman_nox_column.py
```

## Plot style

All three scripts import `scripts/style.py` (via a `sys.path` shim)
and call `style.apply_ncar_style()`. Axis labels and titles use
`style.species_label()` and `style.format_title()` for consistent
NCAR formatting.
````

- [ ] **Step 1.2: Create `scripts/musica_python/abba_box.py`**

Use the Write tool. The full file content:

```python
#!/usr/bin/env python3
"""Standalone MUSICA-Python box model for the ABBA toy mechanism.

Mirrors section 2.5 of the CheMPAS-A tutorial (the supercell + ABBA
run) without MPAS in the loop. Single grid cell, slow two-way reaction
qAB <-> qA + qB, 2 h integration. Output: abba_box.nc, abba_box.png.

Run:
    ~/miniconda3/envs/mpas/bin/python scripts/musica_python/abba_box.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# scripts/style.py lives one level up.
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

import musica
from musica.mechanism_configuration import Parser
from musica.micm.solver_result import SolverState

import style

REPO_ROOT = Path(__file__).parent.parent.parent
ABBA_YAML = REPO_ROOT / "micm_configs" / "abba.yaml"
OUT_DIR = Path(__file__).parent

# Reference conditions for the box.
T_REF = 273.0     # K
P_REF = 101325.0  # Pa


def main() -> None:
    style.apply_ncar_style()

    parser = Parser()
    mechanism = parser.parse(str(ABBA_YAML))
    solver = musica.MICM(
        mechanism=mechanism,
        solver_type=musica.SolverType.rosenbrock_standard_order,
    )
    state = solver.create_state(num_grid_cells=1)
    state.set_conditions(temperatures=T_REF, pressures=P_REF)
    state.set_concentrations({"A": [0.0], "B": [0.0], "AB": [1.0]})

    # USER_DEFINED reaction rates (scaling factors from abba.yaml).
    user = state.get_user_defined_rate_parameters()
    user["USER.forward_AB_to_A_B"] = [2.0e-3]
    user["USER.reverse_A_B_to_AB"] = [1.0e-3]
    state.set_user_defined_rate_parameters(user)

    dt_out = 60.0       # output cadence (s)
    t_end  = 7200.0     # 2 h
    times = [0.0]
    history = [{k: float(v[0]) for k, v in state.get_concentrations().items()}]

    while times[-1] < t_end:
        elapsed = 0.0
        while elapsed < dt_out:
            r = solver.solve(state, dt_out - elapsed)
            elapsed += r.stats.final_time
            if r.state != SolverState.Converged:
                print(f"  solver state: {r.state} at t={times[-1] + elapsed:.1f}")
        times.append(times[-1] + dt_out)
        history.append({k: float(v[0]) for k, v in state.get_concentrations().items()})

    minutes = np.array(times) / 60.0
    ds = xr.Dataset(
        {sp: ("time", np.array([h[sp] for h in history])) for sp in ("A", "B", "AB")},
        coords={"time": minutes},
        attrs={"mechanism": "abba.yaml", "T_K": T_REF, "P_Pa": P_REF},
    )
    ds["time"].attrs["units"] = "minutes"
    for sp in ("A", "B", "AB"):
        ds[sp].attrs["units"] = "mol m-3"
    ds.to_netcdf(OUT_DIR / "abba_box.nc", engine="scipy")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    palette = style.get_palette(3)
    for sp, color in zip(("AB", "A", "B"), palette):
        ax.plot(minutes, ds[sp].values, color=color, label=style.species_label(sp))
    ax.set_xlabel("Time [min]")
    ax.set_ylabel("Concentration [mol m$^{-3}$]")
    ax.set_title(style.format_title("Standalone ABBA box model"))
    ax.legend()
    ax.grid(True, alpha=0.4)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "abba_box.png", dpi=150)
    print(f"Wrote {OUT_DIR / 'abba_box.nc'} and {OUT_DIR / 'abba_box.png'}.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 1.3: Smoke-test (optional)**

```bash
~/miniconda3/envs/mpas/bin/python /Users/fillmore/EarthSystem/CheMPAS-A/scripts/musica_python/abba_box.py
```

If `musica` is installed in the env: expected output is "Wrote .../abba_box.nc and .../abba_box.png." plus the two output files.

If `musica` is not installed: the script raises `ModuleNotFoundError: No module named 'musica'`. That is acceptable for this step; just note it in the task report. The hard gate is that the file exists on disk and is syntactically valid Python (Python at least imports — verify with `python -c "import ast; ast.parse(open('scripts/musica_python/abba_box.py').read())"`).

- [ ] **Step 1.4: Commit**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A
git add scripts/musica_python/
git commit -m "$(cat <<'EOF'
feat(scripts): standalone MUSICA-Python ABBA box model + README

Adds scripts/musica_python/ with a one-page README documenting the
three planned standalone-Python examples (ABBA box, LNOx box,
Chapman+NOx column) and the first script: abba_box.py.

abba_box.py is a ~80-line single-cell box model that loads
micm_configs/abba.yaml, seeds qAB = 1.0 mol/m^3 with qA = qB = 0,
runs the slow two-way reaction for 2 hours at 60-second output
cadence, and writes abba_box.nc + abba_box.png. Plotting uses
scripts/style.py (NCAR palette + project label/title conventions).

Spec: docs/superpowers/specs/2026-04-26-musica-python-tutorials-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Implement `lnox_box.py`

**Files:**
- Create: `scripts/musica_python/lnox_box.py`

LNOx + O₃ box model: same skeleton as `abba_box.py` plus a `ppb_to_mol_m3` helper, mid-troposphere conditions, and a hardcoded `PHOTO.jNO2` rate.

- [ ] **Step 2.1: Create `scripts/musica_python/lnox_box.py`**

Full file content:

```python
#!/usr/bin/env python3
"""Standalone MUSICA-Python box model for LNOx + O3 photochemistry.

Mirrors section 2.6 of the CheMPAS-A tutorial without MPAS and without
the lightning-NOx source (which is a CheMPAS-A-side operator-split
injection in mpas_lightning_nox.F, not part of the MICM mechanism).
Single grid cell at mid-tropospheric conditions, hardcoded
jNO2 = 0.01 s^-1 (matches CheMPAS-A's config_lnox_j_no2), 2 h
integration. Output: lnox_box.nc, lnox_box.png.

Run:
    ~/miniconda3/envs/mpas/bin/python scripts/musica_python/lnox_box.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

import musica
from musica.constants import GAS_CONSTANT
from musica.mechanism_configuration import Parser
from musica.micm.solver_result import SolverState

import style

REPO_ROOT = Path(__file__).parent.parent.parent
LNOX_YAML = REPO_ROOT / "micm_configs" / "lnox_o3.yaml"
OUT_DIR = Path(__file__).parent

# Mid-troposphere conditions (~5-8 km), where the CheMPAS-A LNOx source
# is active.
T_REF = 240.0   # K
P_REF = 5e4     # Pa

# Photolysis rate matches CheMPAS-A's config_lnox_j_no2 setting.
J_NO2 = 0.01    # s^-1


def ppb_to_mol_m3(ppb: float, T: float, P: float) -> float:
    """Volume mixing ratio in ppb to concentration in mol m^-3."""
    return ppb * 1e-9 * P / (GAS_CONSTANT * T)


def main() -> None:
    style.apply_ncar_style()

    parser = Parser()
    mechanism = parser.parse(str(LNOX_YAML))
    solver = musica.MICM(
        mechanism=mechanism,
        solver_type=musica.SolverType.rosenbrock_standard_order,
    )
    state = solver.create_state(num_grid_cells=1)
    state.set_conditions(temperatures=T_REF, pressures=P_REF)

    # 1 ppb total NOx, 50/50 NO/NO2; 50 ppb O3 background.
    nox_each = ppb_to_mol_m3(0.5, T_REF, P_REF)
    o3 = ppb_to_mol_m3(50.0, T_REF, P_REF)
    state.set_concentrations({
        "NO":  [nox_each],
        "NO2": [nox_each],
        "O3":  [o3],
    })

    # PHOTOLYSIS reaction rate (constant for the whole run).
    user = state.get_user_defined_rate_parameters()
    user["PHOTO.jNO2"] = [J_NO2]
    state.set_user_defined_rate_parameters(user)

    dt_out = 60.0
    t_end = 7200.0
    times = [0.0]
    history = [{k: float(v[0]) for k, v in state.get_concentrations().items()}]

    while times[-1] < t_end:
        elapsed = 0.0
        while elapsed < dt_out:
            r = solver.solve(state, dt_out - elapsed)
            elapsed += r.stats.final_time
            if r.state != SolverState.Converged:
                print(f"  solver state: {r.state} at t={times[-1] + elapsed:.1f}")
        times.append(times[-1] + dt_out)
        history.append({k: float(v[0]) for k, v in state.get_concentrations().items()})

    minutes = np.array(times) / 60.0
    ds = xr.Dataset(
        {sp: ("time", np.array([h[sp] for h in history])) for sp in ("NO", "NO2", "O3")},
        coords={"time": minutes},
        attrs={
            "mechanism": "lnox_o3.yaml",
            "T_K": T_REF,
            "P_Pa": P_REF,
            "jNO2_s-1": J_NO2,
            "note": "Lightning-NOx source omitted (CheMPAS-A operator-split, not in MICM).",
        },
    )
    ds["time"].attrs["units"] = "minutes"
    for sp in ("NO", "NO2", "O3"):
        ds[sp].attrs["units"] = "mol m-3"
    ds.to_netcdf(OUT_DIR / "lnox_box.nc", engine="scipy")

    fig, axes = plt.subplots(3, 1, figsize=(7, 9), sharex=True)
    palette = style.get_palette(3)
    for ax, sp, color in zip(axes, ("NO", "NO2", "O3"), palette):
        ax.plot(minutes, ds[sp].values, color=color)
        ax.set_ylabel(f"[{style.species_label(sp)}] [mol m$^{{-3}}$]")
        ax.grid(True, alpha=0.4)
    axes[-1].set_xlabel("Time [min]")
    axes[0].set_title(style.format_title("Standalone LNOx + O3 box model"))
    fig.tight_layout()
    fig.savefig(OUT_DIR / "lnox_box.png", dpi=150)
    print(f"Wrote {OUT_DIR / 'lnox_box.nc'} and {OUT_DIR / 'lnox_box.png'}.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2.2: Smoke-test (optional)**

```bash
~/miniconda3/envs/mpas/bin/python /Users/fillmore/EarthSystem/CheMPAS-A/scripts/musica_python/lnox_box.py
```

Same gating as Task 1 Step 1.3: if `musica` is unavailable, just verify the file parses (`python -c "import ast; ast.parse(open('scripts/musica_python/lnox_box.py').read())"`).

- [ ] **Step 2.3: Commit**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A
git add scripts/musica_python/lnox_box.py
git commit -m "$(cat <<'EOF'
feat(scripts): standalone MUSICA-Python LNOx + O3 box model

Adds scripts/musica_python/lnox_box.py — single-cell box model
loading micm_configs/lnox_o3.yaml at mid-tropospheric conditions
(T = 240 K, P = 50 kPa). Initial state: 1 ppb total NOx (50/50
NO/NO2) and 50 ppb O3 background. Photolysis hardcoded as
PHOTO.jNO2 = 0.01 s^-1, matching CheMPAS-A's config_lnox_j_no2.

The lightning-NOx source is intentionally omitted — it is a
CheMPAS-A operator-split injection (mpas_lightning_nox.F), not part
of the MICM mechanism. The standalone box exercises only the
photochemistry: NO/NO2 partitioning relaxes to Leighton PSS
within ~1 minute, with slow O3 titration over the 2 h run.

Output: lnox_box.nc + lnox_box.png. Plotting uses scripts/style.py.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Implement `chapman_nox_column.py`

**Files:**
- Create: `scripts/musica_python/chapman_nox_column.py`

The largest script (~220 lines). Adapts MUSICA's bundled `chapman.py` example with our `chapman_nox.yaml` mechanism. Reuses MUSICA's `vTS1` TUV-x calculator with a custom alias map for our reaction names; documented inline why we don't load `tuvx_chapman_nox.json` directly. Reuses `init_chapman.py`'s `afgl_qo3_profile` and `nox_vmr_profile` for initial conditions.

- [ ] **Step 3.1: Create `scripts/musica_python/chapman_nox_column.py`**

Full file content:

```python
#!/usr/bin/env python3
"""Standalone MUSICA-Python column model for Chapman + NOx PSS.

Mirrors Chapter 3 of the CheMPAS-A tutorial without MPAS in the loop.
Same chapman_nox.yaml MICM mechanism; the column grid is independent
of the MPAS mesh (TUV-x dictates it via the bundled vTS1 calculator).

TUV-x photolysis sourcing
-------------------------
The CheMPAS-A project ships micm_configs/tuvx_chapman_nox.json paired
with chapman_nox.yaml. Loading that JSON directly via the
musica.tuvx.TUVX path-driven constructor would require also building
GridMap / ProfileMap / RadiatorMap (the constructor takes those as
arguments alongside the config path) — essentially reimplementing
mpas_tuvx.F's profile-construction with USSA76 + AFGL data. For
pedagogical simplicity, this script instead reuses MUSICA's bundled
vTS1 calculator (which already provides jO2, jO3->O(3P), jO3->O(1D),
jNO2) and translates TS1's reaction labels to chapman_nox.yaml's
PHOTO.* parameter names via the TS1_LABEL_MAP table below. The
Leighton PSS demonstration is unchanged.

Output: chapman_nox_column.nc, chapman_nox_column.png.

Run:
    ~/miniconda3/envs/mpas/bin/python scripts/musica_python/chapman_nox_column.py
"""
from __future__ import annotations

import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# scripts/ lives one level up; both style.py and init_chapman.py live there.
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import pvlib
import ussa1976

import musica
from musica.constants import GAS_CONSTANT
from musica.mechanism_configuration import Parser
from musica.micm.solver_result import SolverState
from musica.tuvx import vTS1

import style
from init_chapman import afgl_qo3_profile, nox_vmr_profile

REPO_ROOT = Path(__file__).parent.parent.parent
MECH_YAML = REPO_ROOT / "micm_configs" / "chapman_nox.yaml"
OUT_DIR = Path(__file__).parent

# Match the supercell case's nominal location.
LAT, LON = 35.86, -97.93
TZ = ZoneInfo("America/Chicago")  # Norman, OK

# JPL kinetics for NO + O3 -> NO2 + O2 (matches §3.7's Leighton expression).
A_NO_O3, EA_R_NO_O3 = 1.7e-12, 1310.0  # cm^3 molec^-1 s^-1, K

# vTS1 reaction labels matching chapman_nox.yaml's photolysis reactions.
# Run `print(list(vTS1.get_tuvx_calculator().photolysis_rate_names.keys()))`
# to inspect what TS1 actually exposes if these labels need adjusting.
TS1_LABEL_MAP = {
    "jO2":     "O2+hv->O+O",
    "jO3_O":   "O3+hv->O2+O(3P)",
    "jO3_O1D": "O3+hv->O2+O(1D)",
    "jNO2":    "NO2+hv->NO+O",
}

# Molar masses (match scripts/init_chapman.py).
M_AIR = 0.02897
M_O3 = 0.048

# Daytime NOx partitioning (matches scripts/init_chapman.py).
NO_FRACTION = 0.30


def vmr_to_mol_m3(vmr: np.ndarray, T: np.ndarray, P: np.ndarray) -> np.ndarray:
    """Volume mixing ratio (mol/mol) -> concentration (mol/m^3)."""
    return vmr * P / (GAS_CONSTANT * T)


def kgkg_to_mol_m3(kgkg: np.ndarray, M_species: float,
                   T: np.ndarray, P: np.ndarray) -> np.ndarray:
    """Mass mixing ratio (kg/kg) -> mol/m^3 at given T (K), P (Pa)."""
    return (kgkg * P / (GAS_CONSTANT * T)) / (M_species / M_AIR)


def get_photolysis(tuvx, utc_time, n_cells, start_idx):
    """Compute jO2, jO3_O, jO3_O1D, jNO2 at each column level."""
    solpos = pvlib.solarposition.get_solarposition(
        time=utc_time, latitude=LAT, longitude=LON,
    )
    sza_deg = float(solpos["zenith"].iloc[0])
    rates = tuvx.run(sza=np.deg2rad(sza_deg), earth_sun_distance=1.0)
    end = start_idx + n_cells
    out = {}
    for our_name, ts1_label in TS1_LABEL_MAP.items():
        out[f"PHOTO.{our_name}"] = (
            rates.sel(reaction=ts1_label).photolysis_rate_constants.values[start_idx:end]
        )
    return out, sza_deg


def main():
    style.apply_ncar_style()

    # 1. TUV-x: vTS1 dictates the column grid.
    tuvx = vTS1.get_tuvx_calculator()
    grids = tuvx.get_grid_map()
    z_edges_km = grids["height", "km"].edge_values

    # Use a slice of the TS1 grid: skip the surface cell (start=1), span 0-60 km.
    start = 1
    n_cells = 0
    for i in range(start, len(z_edges_km) - 1):
        if z_edges_km[i] >= 60.0:
            break
        n_cells += 1
    z_mids_km = 0.5 * (z_edges_km[start:start + n_cells]
                       + z_edges_km[start + 1:start + n_cells + 1])

    # 2. USSA76 T, P at column midpoints.
    env = ussa1976.compute(z=z_mids_km * 1000.0, variables=["t", "p"])
    T_K = env["t"].values
    P_Pa = env["p"].values

    # 3. Initial profile from scripts/init_chapman.py helpers.
    qo3_kgkg = afgl_qo3_profile(z_mids_km)
    nox_vmr = nox_vmr_profile(z_mids_km)
    initial_concs = {
        "O2":  vmr_to_mol_m3(np.full(n_cells, 0.20946), T_K, P_Pa),
        "O":   np.zeros(n_cells),
        "O1D": np.zeros(n_cells),
        "O3":  kgkg_to_mol_m3(qo3_kgkg, M_O3, T_K, P_Pa),
        "NO":  vmr_to_mol_m3(NO_FRACTION * nox_vmr, T_K, P_Pa),
        "NO2": vmr_to_mol_m3((1.0 - NO_FRACTION) * nox_vmr, T_K, P_Pa),
    }

    # 4. MICM solver setup.
    parser = Parser()
    mechanism = parser.parse(str(MECH_YAML))
    solver = musica.MICM(
        mechanism=mechanism,
        solver_type=musica.SolverType.rosenbrock_standard_order,
    )
    state = solver.create_state(num_grid_cells=n_cells)
    state.set_conditions(T_K, P_Pa)
    state.set_concentrations({sp: list(v) for sp, v in initial_concs.items()})

    # 5. 12-hour run starting at 06:00 local, 30-min cadence.
    today = datetime.now(TZ).date()
    sim_time = datetime.combine(today, time(6, 0), tzinfo=TZ).astimezone(ZoneInfo("UTC"))
    dt_out = 30 * 60
    n_steps = 12 * 2  # 12 hours, 30-min cadence

    photo, sza = get_photolysis(tuvx, sim_time, n_cells, start)
    user = state.get_user_defined_rate_parameters()
    for k, v in photo.items():
        user[k] = list(v)
    state.set_user_defined_rate_parameters(user)

    times = [sim_time]
    species_hist = [state.get_concentrations()]
    photo_hist = [photo]
    sza_hist = [sza]

    for _ in range(n_steps):
        elapsed = 0.0
        while elapsed < dt_out:
            r = solver.solve(state, dt_out - elapsed)
            elapsed += r.stats.final_time
            if r.state != SolverState.Converged:
                print(f"  solver state: {r.state} at sim_time={sim_time}")
        sim_time += timedelta(seconds=dt_out)
        photo, sza = get_photolysis(tuvx, sim_time, n_cells, start)
        user = state.get_user_defined_rate_parameters()
        for k, v in photo.items():
            user[k] = list(v)
        state.set_user_defined_rate_parameters(user)
        times.append(sim_time)
        species_hist.append(state.get_concentrations())
        photo_hist.append(photo)
        sza_hist.append(sza)

    # 6. Build xarray Dataset.
    species_names = ("O2", "O", "O1D", "O3", "NO", "NO2")
    photo_names = ("jO2", "jO3_O", "jO3_O1D", "jNO2")
    species_arr = {
        sp: np.array([[h[sp][i] for i in range(n_cells)] for h in species_hist])
        for sp in species_names
    }
    photo_arr = {
        pn: np.array([p[f"PHOTO.{pn}"] for p in photo_hist])
        for pn in photo_names
    }
    data_vars = {
        sp: (["time", "height"], species_arr[sp], {"units": "mol m-3"})
        for sp in species_names
    }
    for pn in photo_names:
        data_vars[pn] = (["time", "height"], photo_arr[pn], {"units": "s-1"})
    data_vars["sza_deg"] = (["time"], np.array(sza_hist), {"units": "degrees"})

    ds = xr.Dataset(
        data_vars,
        coords={
            "time": np.array(times, dtype="datetime64[ns]"),
            "height": z_mids_km,
        },
        attrs={
            "mechanism": "chapman_nox.yaml",
            "tuvx": "vTS1 (custom alias map for chapman_nox.yaml reactions)",
            "lat_deg": LAT, "lon_deg": LON, "tz": str(TZ),
        },
    )
    ds["height"].attrs["units"] = "km"
    ds.to_netcdf(OUT_DIR / "chapman_nox_column.nc", engine="scipy")

    # 7. 2x2 plot (uses scripts/style.py).
    palette = style.get_palette(4)
    fig = plt.figure(figsize=(11, 8.5))
    gs = fig.add_gridspec(2, 2)

    # Solar noon = min SZA in the run.
    noon_idx = int(np.argmin(sza_hist))

    # Top-left: O3 profile at noon (ppb).
    ax_o3 = fig.add_subplot(gs[0, 0])
    o3_ppb_noon = ds["O3"].isel(time=noon_idx).values * GAS_CONSTANT * T_K / P_Pa * 1e9
    ax_o3.plot(o3_ppb_noon, z_mids_km, color=palette[0])
    ax_o3.set_xlabel(f"[{style.species_label('O3')}] [ppb]")
    ax_o3.set_ylabel("Height [km]")
    ax_o3.set_title(style.format_title("Solar-noon O3 profile"))
    ax_o3.grid(True, alpha=0.4)

    # Top-right: NO and NO2 profiles at noon.
    ax_no = fig.add_subplot(gs[0, 1])
    no_ppb = ds["NO"].isel(time=noon_idx).values * GAS_CONSTANT * T_K / P_Pa * 1e9
    no2_ppb = ds["NO2"].isel(time=noon_idx).values * GAS_CONSTANT * T_K / P_Pa * 1e9
    ax_no.plot(no_ppb, z_mids_km, color=palette[1], label=style.species_label("NO"))
    ax_no.plot(no2_ppb, z_mids_km, color=palette[2], label=style.species_label("NO2"))
    ax_no.set_xlabel("Concentration [ppb]")
    ax_no.set_ylabel("Height [km]")
    ax_no.set_title(style.format_title("Solar-noon NOx profile"))
    ax_no.legend()
    ax_no.grid(True, alpha=0.4)

    # Bottom-left: simulated vs analytical Leighton ratio at noon.
    ax_lt = fig.add_subplot(gs[1, 0])
    sim_ratio = (ds["NO"].isel(time=noon_idx).values
                 / np.maximum(ds["NO2"].isel(time=noon_idx).values, 1e-30))
    k_NO_O3 = A_NO_O3 * np.exp(-EA_R_NO_O3 / T_K)
    leighton = (ds["jNO2"].isel(time=noon_idx).values
                / np.maximum(k_NO_O3 * ds["O3"].isel(time=noon_idx).values, 1e-30))
    ax_lt.plot(sim_ratio, z_mids_km, color=palette[0], label="Simulated")
    ax_lt.plot(leighton, z_mids_km, color=palette[2], linestyle="--", label="Leighton")
    ax_lt.set_xlabel(f"[{style.species_label('NO')}]/[{style.species_label('NO2')}]")
    ax_lt.set_ylabel("Height [km]")
    ax_lt.set_title(style.format_title("Solar-noon Leighton check"))
    ax_lt.set_xscale("log")
    ax_lt.legend()
    ax_lt.grid(True, alpha=0.4)

    # Bottom-right: O3 time series at three altitudes.
    ax_ts = fig.add_subplot(gs[1, 1])
    target_alts_km = [10.0, 30.0, 45.0]
    times_arr = ds["time"].values
    hours_since_start = ((times_arr - times_arr[0]).astype("timedelta64[s]")
                         .astype(float)) / 3600.0
    for alt, color in zip(target_alts_km, palette):
        idx = int(np.argmin(np.abs(z_mids_km - alt)))
        o3_at_alt_ppb = (ds["O3"].isel(height=idx).values
                         * GAS_CONSTANT * T_K[idx] / P_Pa[idx] * 1e9)
        ax_ts.plot(hours_since_start, o3_at_alt_ppb,
                   color=color, label=f"{z_mids_km[idx]:.1f} km")
    ax_ts.set_xlabel("Hours since start")
    ax_ts.set_ylabel(f"[{style.species_label('O3')}] [ppb]")
    ax_ts.set_title(style.format_title("O3 time series"))
    ax_ts.legend()
    ax_ts.grid(True, alpha=0.4)

    fig.suptitle(style.format_title("Standalone Chapman + NOx column model"))
    fig.tight_layout()
    fig.savefig(OUT_DIR / "chapman_nox_column.png", dpi=150)
    print(f"Wrote {OUT_DIR / 'chapman_nox_column.nc'} and "
          f"{OUT_DIR / 'chapman_nox_column.png'}.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3.2: Smoke-test (optional)**

```bash
~/miniconda3/envs/mpas/bin/python /Users/fillmore/EarthSystem/CheMPAS-A/scripts/musica_python/chapman_nox_column.py
```

If `musica` is unavailable, just verify Python parses the file:

```bash
~/miniconda3/envs/mpas/bin/python -c "import ast; ast.parse(open('/Users/fillmore/EarthSystem/CheMPAS-A/scripts/musica_python/chapman_nox_column.py').read())"
```

Expected: no output (clean parse).

If `musica` IS installed but a TS1 reaction label fails to resolve (e.g., `KeyError: 'O2+hv->O+O'`), update the offending entry in `TS1_LABEL_MAP`. Diagnose with:

```python
from musica.tuvx import vTS1
print(list(vTS1.get_tuvx_calculator().photolysis_rate_names.keys()))
```

This is the documented procedure (the script docstring tells the reader the same thing).

- [ ] **Step 3.3: Commit**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A
git add scripts/musica_python/chapman_nox_column.py
git commit -m "$(cat <<'EOF'
feat(scripts): standalone MUSICA-Python Chapman + NOx column model

Adds scripts/musica_python/chapman_nox_column.py — column model
that loads micm_configs/chapman_nox.yaml MICM mechanism and uses
MUSICA's bundled vTS1 TUV-x calculator for photolysis. The
column grid is independent of the MPAS mesh (TS1 dictates it);
USSA76 supplies T/P; init_chapman.py supplies AFGL O3 and NOx
profiles.

The script could load micm_configs/tuvx_chapman_nox.json directly
through musica.tuvx.TUVX, but that constructor also requires
GridMap / ProfileMap / RadiatorMap construction — essentially
reimplementing mpas_tuvx.F's profile setup. The vTS1+alias-map
approach is pedagogically equivalent for the Leighton PSS
demonstration; the docstring documents the trade-off.

Plot is a 2x2 grid: O3 profile, NO/NO2 profile, simulated vs.
analytical Leighton ratio (matching §3.7), and O3 time series at
three altitudes. Output: chapman_nox_column.nc + .png.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Append §§2.10 and 2.11 to Chapter 2

**Files:**
- Modify: `docs/tutorial/02-supercell.md`

Append two new sections at the end of the chapter (after the existing §2.9 "Next steps" closing). Both wear the WIP banner; §2.10 has Figure 2.5 and §2.11 has Figure 2.6.

- [ ] **Step 4.1: Append §§2.10 and 2.11**

The current chapter ends at §2.9 "Next steps" with its 4-bullet list and then a trailing newline. Use the Edit tool to insert the new sections AFTER the last bullet (which currently reads `*(Not yet scheduled.)*`). Specifically: locate the closing `*(Not yet scheduled.)*` line in §2.9 and append the following content immediately after it.

The content to append (paste verbatim):

````markdown

## 2.10 Standalone ABBA box model

```{admonition} Work in progress
:class: warning

Section content coming.
```

The same chemistry as §2.5, exercised in pure Python with no MPAS in
the loop. `scripts/musica_python/abba_box.py` loads
`micm_configs/abba.yaml` into a single-cell MICM solver, seeds qAB at
1 mol m⁻³, runs the slow two-way reaction for 2 hours, and writes
`abba_box.nc` plus `abba_box.png` next to the script. Useful for
poking at initial conditions or temperatures without rebuilding MPAS.

Pre-req:

```bash
~/miniconda3/envs/mpas/bin/pip install musica
```

Run:

```bash
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/musica_python/abba_box.py
```

**[Figure 2.5: A, B, AB concentrations from the standalone ABBA box
model over a 2 h integration. To be added.]**

What to look for: AB starts at 1 mol m⁻³ and decays slowly toward
equilibrium with A and B; on the 2 h run duration only a small
fraction reacts, mirroring the "advection-dominated" framing of §2.5.

## 2.11 Standalone LNOx + O₃ box model

```{admonition} Work in progress
:class: warning

Section content coming.
```

The standalone counterpart of §2.6, *minus* the lightning-NOx source
(which is a CheMPAS-A operator-split injection in
`mpas_lightning_nox.F`, not part of the MICM mechanism).
`scripts/musica_python/lnox_box.py` loads `micm_configs/lnox_o3.yaml`
into a single-cell MICM solver at mid-tropospheric conditions
(T = 240 K, P = 5×10⁴ Pa), seeds 1 ppb total NOx (50/50 NO/NO₂) and
50 ppb O₃, hardcodes `PHOTO.jNO2 = 0.01 s⁻¹` (matching CheMPAS-A's
`config_lnox_j_no2`), and runs for 2 hours.

Pre-req: same `pip install musica` as §2.10. Run:

```bash
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/musica_python/lnox_box.py
```

**[Figure 2.6: NO, NO₂, O₃ from the standalone LNOx + O₃ box model.
The first ~minute shows NO/NO₂ relaxing to the Leighton PSS; over
2 h, slow O₃ titration is visible. To be added.]**

What to look for: NO and NO₂ partitioning settles within ~1 minute
to the Leighton ratio (jNO₂ / k_{NO+O₃}·[O₃]); after that, the slow
titration depresses O₃ over the 2 h run while keeping NO/NO₂ near
steady state. A direct independent check of the analytical PSS
computation referenced in §2.7.
````

(The leading blank line is intentional — separates the new material from §2.9's last bullet.)

- [ ] **Step 4.2: Build and verify**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && make html 2>&1 | grep -iE "warning|error" | grep -i "tutorial/" || echo "no tutorial warnings"
```

Expected: `no tutorial warnings`. The two new sections render with WIP banners and figure placeholders.

- [ ] **Step 4.3: Commit**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A
git add docs/tutorial/02-supercell.md
git commit -m "$(cat <<'EOF'
docs(tutorial): add Chapter 2 standalone-Python sections (2.10, 2.11)

Appends two new sections at the end of Chapter 2:

- 2.10 Standalone ABBA box model — points at
  scripts/musica_python/abba_box.py, parallels §2.5 without MPAS.
- 2.11 Standalone LNOx + O3 box model — points at
  scripts/musica_python/lnox_box.py, parallels §2.6 without MPAS
  and without the lightning-NOx source (which is a CheMPAS-A-side
  operator-split injection, not in the MICM mechanism).

Both sections wear the WIP banner per the project draft-pass
convention. Figures 2.5 and 2.6 are placeholders.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Append §3.10 to Chapter 3

**Files:**
- Modify: `docs/tutorial/03-chapman-nox.md`

Append one new section at the end of Chapter 3 (after the existing §3.9 "Next steps" closing). Wears the WIP banner; has Figure 3.5.

- [ ] **Step 5.1: Append §3.10**

The current chapter ends at §3.9 "Next steps" — last bullet ends in `*(Not yet scheduled.)*`. Append the following content immediately after that bullet:

````markdown

## 3.10 Standalone Chapman + NOx column model

```{admonition} Work in progress
:class: warning

Section content coming.
```

The standalone counterpart of this whole chapter — same
`chapman_nox.yaml` MICM mechanism, TUV-x photolysis on a vertical
column, no MPAS in the loop. `scripts/musica_python/chapman_nox_column.py`
loads MUSICA's bundled `vTS1` TUV-x calculator (which provides jO₂,
jO₃→O, jO₃→O¹D, jNO₂), maps its TS1 reaction labels to
`chapman_nox.yaml`'s `PHOTO.*` parameter names via a small alias table
in the script, and runs a 12-hour diurnal cycle starting at 06:00
local at the supercell case's nominal lat/lon (Norman, OK). The
column grid is whatever vTS1 dictates — independent of the MPAS mesh
and of the upper-atmosphere extension introduced in §3.3.

Initial profiles come from `scripts/init_chapman.py`'s helpers (AFGL
mid-latitude-summer O₃, total NOx with daytime 30/70 NO/NO₂
partitioning), so the standalone column starts from the same vertical
distribution the CheMPAS-A run does.

Pre-req:

```bash
~/miniconda3/envs/mpas/bin/pip install musica ussa1976 pvlib
```

Run:

```bash
~/miniconda3/envs/mpas/bin/python \
    ~/EarthSystem/CheMPAS-A/scripts/musica_python/chapman_nox_column.py
```

**[Figure 3.5: Standalone Chapman + NOx column model — solar-noon O₃
profile, solar-noon NO and NO₂ profiles, simulated vs. analytical
Leighton ratio with height, and O₃ time series at 10 / 30 / 45 km. To
be added.]**

What to look for: simulated NO/NO₂ ratio tracks the analytical
Leighton expression (the same one §3.7 motivates) closely in the
stratospheric column where photolysis is strong; O₃ peak settles
near 25–30 km; daytime PSS visibly breaks down at sunset in the
time-series panel. An independent numerical check on the same
chemistry the chapter's MPAS-coupled run exercises.
````

- [ ] **Step 5.2: Build and verify**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && make html 2>&1 | grep -iE "warning|error" | grep -i "tutorial/" || echo "no tutorial warnings"
```

Expected: `no tutorial warnings`.

- [ ] **Step 5.3: Commit**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A
git add docs/tutorial/03-chapman-nox.md
git commit -m "$(cat <<'EOF'
docs(tutorial): add Chapter 3 standalone-Python section (3.10)

Appends §3.10 "Standalone Chapman + NOx column model" at the end
of Chapter 3 — points at scripts/musica_python/chapman_nox_column.py
and frames it as the no-MPAS counterpart of the whole chapter
(same chapman_nox.yaml mechanism, TUV-x photolysis on an
independent column grid, init_chapman.py-style initial profile,
12-hour diurnal cycle).

Wears the WIP banner. Figure 3.5 is a placeholder. Pre-reqs note
musica + ussa1976 + pvlib.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Final clean build + Chrome verify

**Files:** none modified.

- [ ] **Step 6.1: Clean rebuild**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs && rm -rf _build && make html
```

Expected: build succeeds, warnings carry the develop baseline, zero new warnings under `tutorial/`.

- [ ] **Step 6.2: Confirm zero tutorial-pathed warnings**

```bash
cd /Users/fillmore/EarthSystem/CheMPAS-A/docs
make html 2>&1 | grep -iE "warning|error" | grep -i "tutorial/" | tee /tmp/musica_py_warnings.txt
wc -l /tmp/musica_py_warnings.txt
```

Confirm line count is 0.

- [ ] **Step 6.3: Browser walk-through**

```bash
open -a "Google Chrome" /Users/fillmore/EarthSystem/CheMPAS-A/docs/_build/html/tutorial/02-supercell.html
```

Verify in the rendered Chapter 2 page:
- §§2.10 and 2.11 appear at the bottom of the page after §2.9.
- Each new subsection carries an orange WIP banner.
- Figure 2.5 and Figure 2.6 placeholders are present in bold bracketed text.
- Bash code blocks (run commands) are syntax-highlighted.

```bash
open -a "Google Chrome" /Users/fillmore/EarthSystem/CheMPAS-A/docs/_build/html/tutorial/03-chapman-nox.html
```

Verify in the rendered Chapter 3 page:
- §3.10 appears at the bottom of the page after §3.9.
- WIP banner present.
- Figure 3.5 placeholder present.
- Bash code blocks render.

- [ ] **Step 6.4: Optional polish commit**

If a rendering issue surfaces in Step 6.3 (broken admonition fence, code-block language tag wrong, etc.), fix inline and commit:

```bash
git add docs/tutorial/
git commit -m "$(cat <<'EOF'
docs(tutorial): polish standalone-Python section render issues

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

If everything renders cleanly, no commit is needed.

---

## Self-Review Notes

- Spec coverage:
  - `scripts/musica_python/` directory with README → Task 1 (README.md + abba_box.py)
  - `abba_box.py` (~60 lines, no photolysis) → Task 1
  - `lnox_box.py` (~80 lines, hardcoded `jNO2 = 0.01`) → Task 2
  - `chapman_nox_column.py` (~200 lines, vTS1 + alias map) → Task 3 (with documented deviation from spec's "target A" — see Task 3 docstring + commit message)
  - §2.10 and §2.11 in Chapter 2 → Task 4
  - §3.10 in Chapter 3 → Task 5
  - Build verification → Task 6
- Placeholder scan: every step contains either an exact file path, exact code/markdown, or an exact command. The only "Section content coming." token is the WIP-banner body, which is the explicit project convention. No "TBD" / "implement later" / "similar to Task N" tokens.
- Type / name consistency:
  - Script paths consistent (`scripts/musica_python/abba_box.py` etc.) across all references.
  - Section numbers (2.10, 2.11, 3.10) consistent across plan, prose, and commit messages.
  - Figure numbers (2.5, 2.6, 3.5) consistent.
  - `style.apply_ncar_style()`, `style.species_label()`, `style.format_title()`, `style.get_palette()` used consistently across the three scripts.
  - `init_chapman.py` imports (`afgl_qo3_profile`, `nox_vmr_profile`) match what that script actually exports (verified during planning by `grep '^def ' scripts/init_chapman.py`).
  - `PHOTO.*` vs `USER.*` parameter prefixes match each YAML's reaction `type` (USER_DEFINED → `USER.*`, PHOTOLYSIS → `PHOTO.*`).

- Documented spec deviations:
  - Spec said the "target" TUV-x sourcing for `chapman_nox_column.py` is path-driven loading of our `tuvx_chapman_nox.json`. After API inspection, that constructor (`musica.tuvx.TUVX(config_path=..., grid_map=..., profile_map=..., radiator_map=...)`) requires also building GridMap/ProfileMap/RadiatorMap, which is essentially reimplementing `mpas_tuvx.F`'s profile-construction. The plan uses the spec's "fallback" (vTS1 + custom alias map) as primary. The script docstring and commit message document the trade-off.
