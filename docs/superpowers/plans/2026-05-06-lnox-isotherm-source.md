# LNOx isotherm-gated source — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an isotherm-based gating mode (262.15 K → 233.15 K, constant rate) to the existing CheMPAS-A lightning-NOx source while preserving altitude-mode behavior bit-for-bit, then run an end-to-end test in the supercell case.

**Architecture:** A single integer mode flag in `mpas_lightning_nox.F` selects altitude-vs-isotherm gating; the inner loop branches on mode. Temperature is computed once per chemistry step in `mpas_atm_chemistry.F` and passed into `lightning_nox_inject` as a new optional argument. Altitude mode ignores T and runs unchanged.

**Tech Stack:** Fortran 2008, MPAS atmosphere core, MUSICA/MICM (linked via pkg-config), MPI (8 ranks), legacy Makefile build (no CMake), conda `mpas` Python env for plotting.

**Spec:** `docs/superpowers/specs/2026-05-06-lnox-isotherm-source-design.md`

---

## File Structure

| File | Role | Status |
|---|---|---|
| `src/core_atmosphere/Registry.xml` | Adds three new namelist options under `<nml_record name="musica">` | modify |
| `src/core_atmosphere/chemistry/mpas_lightning_nox.F` | Adds mode flag, isotherm branch, optional `temperature` arg, init-time validation/logging | modify |
| `src/core_atmosphere/chemistry/mpas_atm_chemistry.F` | Computes `temperature(nVertLevels,nCells)` from `theta_m / (1+rvord*qv) * exner` and passes it to `lightning_nox_inject` | modify |
| `test_cases/supercell/namelist.atmosphere` | Adds a second commented-out `&musica` block with isotherm-mode settings | modify |

No new files. No deletions.

---

## Build / Test commands (referenced repeatedly)

These commands appear in many tasks; collected here so the steps can stay short.

**Build (macOS / llvm — adjust target if on Ubuntu):**
```bash
eval "$(scripts/check_build_env.sh --export)" && make -j8 llvm \
  CORE=atmosphere PIO="$PIO" NETCDF="$NETCDF" PNETCDF="$PNETCDF" \
  PRECISION=double MUSICA=true
```

**Verify executable rebuilt:**
```bash
ls -la atmosphere_model && stat -f '%Sm' atmosphere_model
```

**Run supercell (after enabling the appropriate `&musica` block in the rundir's namelist.atmosphere):**
```bash
cd ~/Data/CheMPAS/supercell
timestamp=$(date +%Y%m%d_%H%M%S)
[ -f output.nc ] && mv output.nc output.${timestamp}.nc
[ -f log.atmosphere.0000.out ] && mv log.atmosphere.0000.out log.atmosphere.0000.${timestamp}.out
mpiexec -n 8 ~/EarthSystem/CheMPAS-A/atmosphere_model 2>&1 | tee run.out
```

**Plot the result:**
```bash
~/miniconda3/envs/mpas/bin/python ~/EarthSystem/CheMPAS-A/scripts/plot_lnox_o3.py
```

---

## Task 1: Add namelist options to Registry.xml

**Files:**
- Modify: `src/core_atmosphere/Registry.xml` (insert three `<nml_option>` entries inside `<nml_record name="musica">`, after the existing `config_lnox_nox_tau` entry around line 430)

- [ ] **Step 1: Edit Registry.xml**

Open `src/core_atmosphere/Registry.xml`. Locate the block that ends with the `config_lnox_nox_tau` option (currently around lines 427–430):

```xml
                <nml_option name="config_lnox_nox_tau" type="real" default_value="0.0"
                     units="s"
                     description="NOx sink timescale in seconds (0 = no sink). Rate = 1/tau."
                     possible_values="Any non-negative real"/>
```

Immediately after it (still inside `<nml_record name="musica">`), insert these three new options:

```xml
                <nml_option name="config_lnox_gating_mode" type="character" default_value="altitude"
                     units="-"
                     description="Lightning NOx gating mode: 'altitude' uses z_min/z_max + linear w-scaling (current behavior); 'isotherm' uses t_min/t_max + constant rate (LNOx.md formulation)"
                     possible_values="altitude, isotherm"/>
                <nml_option name="config_lnox_t_min" type="real" default_value="233.15"
                     units="K"
                     description="Lower (cold) temperature bound for isotherm-mode lightning NOx injection"
                     possible_values="Any positive real less than config_lnox_t_max"/>
                <nml_option name="config_lnox_t_max" type="real" default_value="262.15"
                     units="K"
                     description="Upper (warm) temperature bound for isotherm-mode lightning NOx injection"
                     possible_values="Any positive real greater than config_lnox_t_min"/>
```

- [ ] **Step 2: Build and verify config_declare.inc picked up the new options**

Run the build command (see top of plan).

Then check the generated declaration file:

```bash
grep "config_lnox_gating_mode\|config_lnox_t_min\|config_lnox_t_max" \
     src/core_atmosphere/inc/config_declare.inc
```

Expected output: three `pointer` declaration lines, e.g.

```
      character (len=StrKIND), pointer :: config_lnox_gating_mode
      real (kind=RKIND), pointer :: config_lnox_t_min
      real (kind=RKIND), pointer :: config_lnox_t_max
```

If grep returns nothing, the Registry preprocessor didn't pick up the change — re-check the XML for typos.

- [ ] **Step 3: Commit**

```bash
git add src/core_atmosphere/Registry.xml
git commit -m "$(cat <<'EOF'
feat(registry): add LNOx isotherm-mode namelist options

Adds config_lnox_gating_mode, config_lnox_t_min, config_lnox_t_max to
the musica nml group. Default gating_mode = 'altitude' preserves
existing behavior.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Add mode-flag plumbing in `mpas_lightning_nox.F`

Adds module-level mode constants, mode state, isotherm parameter state, and init-time parsing / validation / logging. Does **not** yet touch the inject loop — that's Task 3.

**Files:**
- Modify: `src/core_atmosphere/chemistry/mpas_lightning_nox.F`

- [ ] **Step 1: Add mode constants and module state**

Locate the module-state block (currently lines 39–48):

```fortran
    ! Module state
    logical, save :: lnox_active = .false.
    integer, save :: idx_qNO = -1

    ! Parameters (set from namelist at init)
    real(kind=RKIND), save :: source_rate_ppbv = 0.0_RKIND   ! rate [ppbv/s] when (w - w_threshold) = w_ref
    real(kind=RKIND), save :: w_threshold      = 5.0_RKIND   ! [m/s]
    real(kind=RKIND), save :: w_ref            = 10.0_RKIND  ! excess updraft scale [m/s]
    real(kind=RKIND), save :: z_min            = 5000.0_RKIND ! [m]
    real(kind=RKIND), save :: z_max            = 12000.0_RKIND ! [m]
```

Immediately after the `lnox_active` / `idx_qNO` lines, add the mode constants and mode state. Then add t_min / t_max parameters at the end of the parameter block. The result should look like:

```fortran
    ! Module state
    logical, save :: lnox_active = .false.
    integer, save :: idx_qNO = -1

    ! Gating mode constants
    integer, parameter :: MODE_ALTITUDE = 1
    integer, parameter :: MODE_ISOTHERM = 2
    integer, save :: mode = MODE_ALTITUDE

    ! Parameters (set from namelist at init)
    real(kind=RKIND), save :: source_rate_ppbv = 0.0_RKIND   ! rate [ppbv/s] when (w - w_threshold) = w_ref (altitude mode); constant rate [ppbv/s] in isotherm mode
    real(kind=RKIND), save :: w_threshold      = 5.0_RKIND   ! [m/s] (used as hard on/off gate in both modes)
    real(kind=RKIND), save :: w_ref            = 10.0_RKIND  ! excess updraft scale [m/s] (altitude mode only)
    real(kind=RKIND), save :: z_min            = 5000.0_RKIND ! [m] (altitude mode only)
    real(kind=RKIND), save :: z_max            = 12000.0_RKIND ! [m] (altitude mode only)
    real(kind=RKIND), save :: t_min            = 233.15_RKIND ! [K] cold isotherm (isotherm mode only)
    real(kind=RKIND), save :: t_max            = 262.15_RKIND ! [K] warm isotherm (isotherm mode only)
```

- [ ] **Step 2: Add mode parsing + validation + isotherm-bound parsing in `lightning_nox_init`**

In the same file, locate the body of `lightning_nox_init`, specifically the existing namelist-reads block (currently around lines 91–110) that reads `config_lnox_source_rate`, `config_lnox_w_threshold`, `config_lnox_w_ref`, `config_lnox_z_min`, `config_lnox_z_max`. Right after that block, before the `if (source_rate_ppbv <= 0.0_RKIND) then` guard (currently around line 112), add:

```fortran
        ! Read isotherm-mode bounds
        nullify(cfg_ptr)
        call mpas_pool_get_config(configs, 'config_lnox_t_min', cfg_ptr)
        if (associated(cfg_ptr)) t_min = cfg_ptr

        nullify(cfg_ptr)
        call mpas_pool_get_config(configs, 'config_lnox_t_max', cfg_ptr)
        if (associated(cfg_ptr)) t_max = cfg_ptr

        ! Read gating mode (string -> integer flag)
        block
            character(len=StrKIND), pointer :: mode_str
            nullify(mode_str)
            call mpas_pool_get_config(configs, 'config_lnox_gating_mode', mode_str)
            if (associated(mode_str)) then
                select case (trim(adjustl(mode_str)))
                case ('altitude')
                    mode = MODE_ALTITUDE
                case ('isotherm')
                    mode = MODE_ISOTHERM
                case default
                    call mpas_log_write('[LNOx] Unknown config_lnox_gating_mode "' &
                        // trim(adjustl(mode_str)) // '"; lightning source disabled.')
                    lnox_active = .false.
                    return
                end select
            end if
        end block
```

- [ ] **Step 3: Add isotherm-mode validation and update logging**

Still inside `lightning_nox_init`, find the existing `lnox_active = .true.` line (currently line 124) and the logging block immediately after it (currently lines 126–132). Replace the logging block so it logs the active mode and only the parameters relevant to that mode. The replacement should look like:

```fortran
        ! Mode-specific validation
        if (mode == MODE_ISOTHERM) then
            if (t_min <= 0.0_RKIND .or. t_max <= 0.0_RKIND .or. t_min >= t_max) then
                call mpas_log_write('[LNOx] Invalid isotherm bounds (require 0 < t_min < t_max); lightning source disabled.')
                lnox_active = .false.
                return
            end if
        end if

        lnox_active = .true.

        call mpas_log_write('[LNOx] Lightning NOx source enabled:')
        call mpas_log_write('[LNOx]   qNO index    = $i', intArgs=(/idx_qNO/))
        call mpas_log_write('[LNOx]   source_rate  = $r ppbv/s', realArgs=(/source_rate_ppbv/))
        call mpas_log_write('[LNOx]   w_threshold  = $r m/s', realArgs=(/w_threshold/))
        if (mode == MODE_ALTITUDE) then
            call mpas_log_write('[LNOx]   gating_mode  = altitude')
            call mpas_log_write('[LNOx]   w_ref        = $r m/s', realArgs=(/w_ref/))
            call mpas_log_write('[LNOx]   z_min        = $r m', realArgs=(/z_min/))
            call mpas_log_write('[LNOx]   z_max        = $r m', realArgs=(/z_max/))
        else
            call mpas_log_write('[LNOx]   gating_mode  = isotherm')
            call mpas_log_write('[LNOx]   t_min        = $r K (cold)', realArgs=(/t_min/))
            call mpas_log_write('[LNOx]   t_max        = $r K (warm)', realArgs=(/t_max/))
        end if
```

- [ ] **Step 4: Build and confirm clean compile**

Run the build command. Expected: `mpas_lightning_nox.F` recompiles, no warnings, link succeeds.

```bash
ls -la atmosphere_model
```

Expected: `atmosphere_model` mtime is fresh.

- [ ] **Step 5: Commit**

```bash
git add src/core_atmosphere/chemistry/mpas_lightning_nox.F
git commit -m "$(cat <<'EOF'
feat(lnox): add gating-mode flag and isotherm bounds plumbing

Adds MODE_ALTITUDE / MODE_ISOTHERM constants, t_min / t_max parameter
state, init-time parsing of config_lnox_gating_mode and isotherm
bounds with validation. Inject loop unchanged in this commit; mode
flag still affects only the init-time log output.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Refactor `lightning_nox_inject` — add optional T arg and isotherm branch

**Files:**
- Modify: `src/core_atmosphere/chemistry/mpas_lightning_nox.F`

- [ ] **Step 1: Update subroutine signature to take optional `temperature`**

Locate the `lightning_nox_inject` subroutine (currently starting around line 149). Change its signature and its argument-declaration block.

The current signature is:

```fortran
    subroutine lightning_nox_inject(dt, scalars, w, zgrid, &
                                    nVertLevels, nCells, time_lev)

        use mpas_log, only: mpas_log_write

        real(kind=RKIND), intent(in) :: dt
        real(kind=RKIND), intent(inout) :: scalars(:,:,:)
        real(kind=RKIND), intent(in) :: w(:,:)             ! (nVertLevelsP1, nCells)
        real(kind=RKIND), intent(in) :: zgrid(:,:)         ! (nVertLevelsP1, nCells)
        integer, intent(in) :: nVertLevels
        integer, intent(in) :: nCells
        integer, intent(in) :: time_lev
```

Replace it with:

```fortran
    subroutine lightning_nox_inject(dt, scalars, w, zgrid, &
                                    nVertLevels, nCells, time_lev, &
                                    temperature)

        use mpas_log, only: mpas_log_write

        real(kind=RKIND), intent(in) :: dt
        real(kind=RKIND), intent(inout) :: scalars(:,:,:)
        real(kind=RKIND), intent(in) :: w(:,:)             ! (nVertLevelsP1, nCells)
        real(kind=RKIND), intent(in) :: zgrid(:,:)         ! (nVertLevelsP1, nCells)
        integer, intent(in) :: nVertLevels
        integer, intent(in) :: nCells
        integer, intent(in) :: time_lev
        real(kind=RKIND), intent(in), optional :: temperature(:,:)  ! (nVertLevels, nCells); required for isotherm mode
```

- [ ] **Step 2: Add isotherm-mode argument check and branch the inner loop**

Locate the existing inner double-loop body (currently lines 168–194):

```fortran
        n_activated = 0

        do iCell = 1, nCells
            do k = 1, nVertLevels

                ! Layer-midpoint vertical velocity (average of interfaces)
                w_mid = 0.5_RKIND * (w(k, iCell) + w(k+1, iCell))

                ! Layer-midpoint height
                z_mid = 0.5_RKIND * (zgrid(k, iCell) + zgrid(k+1, iCell))

                if (w_mid > w_threshold .and. &
                    z_mid >= z_min .and. z_mid <= z_max) then

                    ! Source in mass mixing ratio [kg/kg]:
                    !   rate [ppbv/s] * scale * dt * 1e-9 * (M_NO / M_AIR)
                    ! The 1e-9 converts ppbv to mole fraction; M_NO/M_AIR
                    ! converts volume mixing ratio to mass mixing ratio.
                    delta_q = source_rate_ppbv * (w_mid - w_threshold) / w_ref &
                              * dt * 1.0e-9_RKIND * (M_NO / M_AIR)

                    scalars(idx_qNO, k, iCell) = scalars(idx_qNO, k, iCell) + delta_q
                    n_activated = n_activated + 1
                end if

            end do
        end do
```

Replace with a mode-branching version. The altitude branch is **bit-identical** to the current code; the isotherm branch is new:

```fortran
        if (mode == MODE_ISOTHERM .and. .not. present(temperature)) then
            call mpas_log_write('[LNOx] Isotherm mode requires temperature; skipping injection this step.')
            return
        end if

        n_activated = 0

        if (mode == MODE_ALTITUDE) then
            do iCell = 1, nCells
                do k = 1, nVertLevels

                    ! Layer-midpoint vertical velocity (average of interfaces)
                    w_mid = 0.5_RKIND * (w(k, iCell) + w(k+1, iCell))

                    ! Layer-midpoint height
                    z_mid = 0.5_RKIND * (zgrid(k, iCell) + zgrid(k+1, iCell))

                    if (w_mid > w_threshold .and. &
                        z_mid >= z_min .and. z_mid <= z_max) then

                        ! Source in mass mixing ratio [kg/kg]:
                        !   rate [ppbv/s] * scale * dt * 1e-9 * (M_NO / M_AIR)
                        ! The 1e-9 converts ppbv to mole fraction; M_NO/M_AIR
                        ! converts volume mixing ratio to mass mixing ratio.
                        delta_q = source_rate_ppbv * (w_mid - w_threshold) / w_ref &
                                  * dt * 1.0e-9_RKIND * (M_NO / M_AIR)

                        scalars(idx_qNO, k, iCell) = scalars(idx_qNO, k, iCell) + delta_q
                        n_activated = n_activated + 1
                    end if

                end do
            end do
        else  ! MODE_ISOTHERM
            do iCell = 1, nCells
                do k = 1, nVertLevels

                    w_mid = 0.5_RKIND * (w(k, iCell) + w(k+1, iCell))

                    if (w_mid > w_threshold .and. &
                        temperature(k, iCell) >= t_min .and. &
                        temperature(k, iCell) <= t_max) then

                        ! Constant source (LNOx.md formulation): no w-scaling.
                        delta_q = source_rate_ppbv &
                                  * dt * 1.0e-9_RKIND * (M_NO / M_AIR)

                        scalars(idx_qNO, k, iCell) = scalars(idx_qNO, k, iCell) + delta_q
                        n_activated = n_activated + 1
                    end if

                end do
            end do
        end if
```

Note: in isotherm mode the local `z_mid` variable is unused. That's fine — it's a stack local and keeps the altitude branch unchanged.

- [ ] **Step 3: Build and confirm clean compile**

Run the build command. Expected: `mpas_lightning_nox.F` recompiles, no warnings, link succeeds.

If you get an "unused variable" warning on `z_mid` in isotherm mode under strict flags, that's harmless — the compiler can't tell that the variable is conditionally used. Don't add `-Wno-unused` just for this.

- [ ] **Step 4: Commit**

```bash
git add src/core_atmosphere/chemistry/mpas_lightning_nox.F
git commit -m "$(cat <<'EOF'
feat(lnox): add isotherm-mode inject branch

Adds optional temperature(:,:) argument to lightning_nox_inject and
branches the inner loop on the gating mode. Altitude branch is
bit-identical to the previous code; isotherm branch gates on
t_min <= T <= t_max plus the same w_threshold hard gate, with a
constant source rate (no w-scaling).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Compute T at the chemistry call site and pass it through

**Files:**
- Modify: `src/core_atmosphere/chemistry/mpas_atm_chemistry.F`

- [ ] **Step 1: Add the temperature-array allocation and computation block**

Locate the "Step 0: Inject lightning NOx source" block (currently lines 515–521):

```fortran
        ! Step 0: Inject lightning NOx source (pre-MICM, operator split)
        call mpas_pool_get_array(state, 'scalars', scalars, time_lev)
        call mpas_pool_get_array(state, 'w', w, time_lev)
        call mpas_pool_get_array(mesh, 'zgrid', zgrid)
        if (associated(scalars) .and. associated(w) .and. associated(zgrid)) then
            call lightning_nox_inject(dt, scalars, w, zgrid, nVertLevels, nCells, time_lev)
        end if
```

Replace it with a version that computes a temperature array and passes it down. Note that `theta_m`, `exner`, `index_qv`, and `rvord` are already declared at the top of `chemistry_step` (lines 376–380).

```fortran
        ! Step 0: Inject lightning NOx source (pre-MICM, operator split)
        call mpas_pool_get_array(state, 'scalars', scalars, time_lev)
        call mpas_pool_get_array(state, 'w', w, time_lev)
        call mpas_pool_get_array(mesh, 'zgrid', zgrid)
        call mpas_pool_get_array(state, 'theta_m', theta_m, time_lev)
        call mpas_pool_get_array(diag, 'exner', exner)
        call mpas_pool_get_dimension(state, 'index_qv', index_qv)

        if (associated(scalars) .and. associated(w) .and. associated(zgrid)) then
            if (associated(theta_m) .and. associated(exner) .and. &
                associated(index_qv)) then
                ! Compute T = theta_m / (1 + rvord * qv) * exner.
                ! Same formula used by chemistry_from_MPAS / chemistry_to_MPAS.
                block
                    real(kind=RKIND), allocatable :: temperature(:,:)
                    integer :: kk, ii
                    allocate(temperature(nVertLevels, nCells))
                    do ii = 1, nCells
                        do kk = 1, nVertLevels
                            temperature(kk, ii) = (theta_m(kk, ii) / &
                                (1.0_RKIND + rvord * scalars(index_qv, kk, ii))) &
                                * exner(kk, ii)
                        end do
                    end do
                    call lightning_nox_inject(dt, scalars, w, zgrid, &
                                              nVertLevels, nCells, time_lev, &
                                              temperature=temperature)
                    deallocate(temperature)
                end block
            else
                ! Temperature inputs unavailable — call without T (altitude mode safe).
                call lightning_nox_inject(dt, scalars, w, zgrid, &
                                          nVertLevels, nCells, time_lev)
            end if
        end if
```

- [ ] **Step 2: Build and confirm clean compile**

Run the build command. Expected: `mpas_atm_chemistry.F` recompiles, no warnings, link succeeds.

```bash
ls -la atmosphere_model
```

If the build fails with "index_qv not declared", that's because `index_qv` is already declared at line 377 — verify with `grep -n 'index_qv' src/core_atmosphere/chemistry/mpas_atm_chemistry.F | head -5`. If it's missing, you're editing the wrong file.

- [ ] **Step 3: Commit**

```bash
git add src/core_atmosphere/chemistry/mpas_atm_chemistry.F
git commit -m "$(cat <<'EOF'
feat(chemistry): compute T and pass to lightning_nox_inject

When LNOx is active and theta_m/exner/index_qv are all available,
compute temperature(nVertLevels,nCells) from
theta_m / (1 + rvord*qv) * exner and pass it to lightning_nox_inject
as the new optional temperature argument. Falls back to the
no-temperature call (altitude mode) when any input is missing.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Add isotherm-mode block to supercell namelist

**Files:**
- Modify: `test_cases/supercell/namelist.atmosphere`

- [ ] **Step 1: Add the second commented-out `&musica` block**

Open `test_cases/supercell/namelist.atmosphere`. Locate the existing "LNOx tropospheric development setup" comment block (currently lines 74–89):

```
! LNOx tropospheric development setup:
! &musica
!     config_micm_file = 'lnox_o3.yaml'
!     config_tuvx_config_file = 'tuvx_no2.json'
!     config_tuvx_top_extension = .true.
!     config_tuvx_extension_file = 'tuvx_upper_atm.csv'
!     config_lnox_source_rate = 0.5
!     config_lnox_w_threshold = 5.0
!     config_lnox_w_ref = 10.0
!     config_lnox_z_min = 5000.0
!     config_lnox_z_max = 12000.0
!     config_lnox_j_no2 = 0.01
!     config_lnox_nox_tau = 0.0
!     config_chemistry_latitude = 35.86
!     config_chemistry_longitude = -97.93
! /
!
```

Immediately after the closing `! /` and the blank `!` separator line of that block (and before the "Chapman stratospheric-ozone setup" block), insert:

```
! LNOx tropospheric development setup (isotherm gating, LNOx.md formulation):
! &musica
!     config_micm_file = 'lnox_o3.yaml'
!     config_tuvx_config_file = 'tuvx_no2.json'
!     config_tuvx_top_extension = .true.
!     config_tuvx_extension_file = 'tuvx_upper_atm.csv'
!     config_lnox_gating_mode = 'isotherm'
!     config_lnox_source_rate = 1.0e-3
!     config_lnox_w_threshold = 5.0
!     config_lnox_t_min = 233.15
!     config_lnox_t_max = 262.15
!     config_lnox_j_no2 = 0.01
!     config_lnox_nox_tau = 0.0
!     config_chemistry_latitude = 35.86
!     config_chemistry_longitude = -97.93
! /
!
```

- [ ] **Step 2: Sanity-check the file is syntactically intact**

The edits are inside Fortran-namelist comments (`!` prefix), so they don't change runtime behavior. Confirm the file ends as expected:

```bash
tail -20 test_cases/supercell/namelist.atmosphere
```

There should be no merge markers, no half-pasted lines, and the comment lines should all start with `!`.

- [ ] **Step 3: Commit**

```bash
git add test_cases/supercell/namelist.atmosphere
git commit -m "$(cat <<'EOF'
docs(supercell): add commented isotherm-mode LNOx setup

Adds a second commented &musica block alongside the existing
altitude-mode example. Source rate 1.0e-3 ppbv/s is a calibration
starting point for the LNOx.md "1 ppbv at cloud top" target;
expect to retune after the first run.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Final clean rebuild

A safety rebuild after all source changes are in. Catches any incremental-build oddities.

- [ ] **Step 1: Clean rebuild**

```bash
make clean CORE=atmosphere
find . -name "*.mod" -delete
find . -name "*.o" -delete
eval "$(scripts/check_build_env.sh --export)" && make -j8 llvm \
  CORE=atmosphere PIO="$PIO" NETCDF="$NETCDF" PNETCDF="$PNETCDF" \
  PRECISION=double MUSICA=true
```

Expected: clean build to `atmosphere_model`, no errors, no new warnings on `mpas_lightning_nox.F` or `mpas_atm_chemistry.F`. (Existing physics-package warnings from upstream MPAS are not new and not introduced by this work.)

- [ ] **Step 2: Verify executable**

```bash
ls -la atmosphere_model
```

Expected: file present, mtime fresh.

(No commit — nothing changed in tree.)

---

## Task 7: Altitude-mode regression test (recommended, ~2 h wall time)

Verifies the refactor did not change altitude-mode behavior. **Skip only if you're confident in the diff** — the mode-flag plumbing branches before the altitude loop, and the altitude loop body was preserved character-for-character, so a bit-identical altitude run is the expected outcome.

**Files in run dir** (`~/Data/CheMPAS/supercell/`, not in repo):
- Modify: `~/Data/CheMPAS/supercell/namelist.atmosphere` — uncomment the **altitude** `&musica` block
- Read: `~/Data/CheMPAS/supercell/output.nc`
- Read: `~/Data/CheMPAS/supercell/lightning_nox_*.png` (existing baseline plots)

- [ ] **Step 1: Stage the rundir for an altitude-mode run**

```bash
cd ~/Data/CheMPAS/supercell
```

Open `namelist.atmosphere` in the rundir and uncomment **only** the original altitude-mode `&musica` block (the one with `config_lnox_z_min` / `config_lnox_z_max`, no `gating_mode` line). Leave the new isotherm block commented.

- [ ] **Step 2: Archive previous outputs and run**

```bash
cd ~/Data/CheMPAS/supercell
timestamp=$(date +%Y%m%d_%H%M%S)
[ -f output.nc ] && mv output.nc output.${timestamp}.nc
[ -f log.atmosphere.0000.out ] && mv log.atmosphere.0000.out log.atmosphere.0000.${timestamp}.out
mpiexec -n 8 ~/EarthSystem/CheMPAS-A/atmosphere_model 2>&1 | tee run.out
```

Expected: run completes, `output.nc` is fresh.

- [ ] **Step 3: Verify the log reports altitude mode**

```bash
grep -A 1 "Lightning NOx source enabled" log.atmosphere.0000.out
grep "gating_mode" log.atmosphere.0000.out
```

Expected: log shows `gating_mode = altitude` and the four altitude params (`source_rate`, `w_threshold`, `w_ref`, `z_min`, `z_max`). t_min / t_max should NOT be logged.

- [ ] **Step 4: Verify qNO is non-trivial and finite**

```bash
~/miniconda3/envs/mpas/bin/python -c "
import xarray as xr, numpy as np
ds = xr.open_dataset('output.nc')
q = ds['qNO'].values
print('qNO shape:', q.shape)
print('qNO min/max:', np.nanmin(q), np.nanmax(q))
print('qNO any nan:', np.isnan(q).any())
print('qNO any neg:', (q < 0).any())
"
```

Expected: shape matches the supercell mesh, `max > 0`, no NaN, no negatives.

- [ ] **Step 5: Plot and eyeball-compare to existing baseline**

```bash
~/miniconda3/envs/mpas/bin/python ~/EarthSystem/CheMPAS-A/scripts/plot_lnox_o3.py
```

Open the freshly-written `lightning_nox_*.png` and compare to the previously committed (or prior-run) PNGs in the same directory. Vertical structure, plume shape, peak ppbv should all be visually indistinguishable. Small numerical drift in lightly-affected regions is OK.

If they don't match: something in the refactor changed altitude-mode behavior. **Stop here and debug** — do not proceed to Task 8. Likely culprits: accidental edit inside the altitude branch, or `mode` not defaulting to `MODE_ALTITUDE` somewhere.

(No commit — only rundir changes, which are not tracked.)

---

## Task 8: Isotherm-mode end-to-end test

The actual test of the new code path.

**Files in run dir** (`~/Data/CheMPAS/supercell/`, not in repo):
- Modify: `~/Data/CheMPAS/supercell/namelist.atmosphere` — re-comment the altitude `&musica` block, uncomment the isotherm `&musica` block

- [ ] **Step 1: Re-stage the rundir for isotherm mode**

```bash
cd ~/Data/CheMPAS/supercell
```

Open `namelist.atmosphere` in the rundir. Re-comment the altitude `&musica` block (add `!` back to its lines). Uncomment the isotherm `&musica` block (the one with `config_lnox_gating_mode = 'isotherm'`).

- [ ] **Step 2: Archive previous outputs and run**

```bash
cd ~/Data/CheMPAS/supercell
timestamp=$(date +%Y%m%d_%H%M%S)
[ -f output.nc ] && mv output.nc output.${timestamp}.nc
[ -f log.atmosphere.0000.out ] && mv log.atmosphere.0000.out log.atmosphere.0000.${timestamp}.out
mpiexec -n 8 ~/EarthSystem/CheMPAS-A/atmosphere_model 2>&1 | tee run.out
```

Expected: run completes, `output.nc` is fresh.

- [ ] **Step 3: Verify the log reports isotherm mode**

```bash
grep -A 1 "Lightning NOx source enabled" log.atmosphere.0000.out
grep "gating_mode\|t_min\|t_max" log.atmosphere.0000.out
```

Expected: log shows `gating_mode = isotherm`, `t_min = 233.15 K (cold)`, `t_max = 262.15 K (warm)`. `z_min` / `z_max` / `w_ref` should NOT be logged.

- [ ] **Step 4: Verify qNO is non-trivial, finite, and confined to the mixed-phase layer**

```bash
~/miniconda3/envs/mpas/bin/python <<'EOF'
import xarray as xr, numpy as np
ds = xr.open_dataset('output.nc')
q = ds['qNO'].values  # (Time, nCells, nVertLevels) or similar
print('qNO shape:', q.shape)
print('qNO min/max:', float(np.nanmin(q)), float(np.nanmax(q)))
print('qNO any nan:', bool(np.isnan(q).any()))
print('qNO any neg:', bool((q < 0).any()))

# The supercell uses Kessler (no ice) so air temperatures in the cloud
# core do dip into the 233-262 K range; the LNOx source should be
# confined to those levels. We don't have T in output.nc by default,
# so just check that the source is roughly between 5-9 km, the height
# range where the 233-262 K isotherm typically sits in this case.
zedges = ds['zgrid'].values  # (nVertLevelsP1, nCells)
zmid = 0.5 * (zedges[:-1, :] + zedges[1:, :])
mean_z_per_level = zmid.mean(axis=1)
print('Mean z per level (m), surface to top:')
for k, z in enumerate(mean_z_per_level):
    print(f'  k={k:2d}  z={z:7.0f} m')
EOF
```

Expected: max > 0, no NaN, no negatives. Print of mean-z-per-level should let you correlate the LNOx-source levels with the 5–9 km band.

- [ ] **Step 5: Plot and verify mixed-phase confinement**

```bash
~/miniconda3/envs/mpas/bin/python ~/EarthSystem/CheMPAS-A/scripts/plot_lnox_o3.py
```

Open the new `lightning_nox_profiles.png` (or `lightning_nox_horizontal.png`, whichever the script produces). Verify visually:
- Vertical NO/NO₂ profile peaks in the mid-troposphere band where T is between 233–262 K (~5–9 km in this case);
- Peak NOx of order 1 ppbv (within a factor of a few — expect to retune `source_rate` after this run);
- O₃ shows a small tropospheric-NOx response (no dramatic stratospheric-style loss);
- No NaN, no negatives in the rendered fields.

- [ ] **Step 6: Decide on follow-up**

If peak NOx is far from 1 ppbv (factor >5 either way), edit `config_lnox_source_rate` in the rundir namelist and rerun (Task 8 Step 2). This is configuration-tuning, not a code bug.

If peak NOx is near 1 ppbv and confinement looks right: the implementation works end-to-end. Optionally write a short note (e.g., to `REPORT.md` or a new `docs/chempas/results/LNOX_ISOTHERM_RUN.md`) summarizing the run and decide whether to commit a calibrated `source_rate` default.

(No commit yet — calibration is iterative; commit once the user is happy with the rate.)

---

## Self-Review

Skimming the spec against this plan:

- **§ Gating-mode switch** → Task 1 (Registry) + Task 2 (mode flag plumbing). ✓
- **§ Behavior per mode** → Task 3 (inject branching). ✓
- **§ New namelist options** → Task 1. ✓
- **§ Threading temperature through** → Task 4. ✓
- **§ Module boundaries** → Tasks 2/3/4 each keep responsibility scoped (no pool access in lnox module; T computed only in chemistry stepper). ✓
- **§ Test-case namelist additions** → Task 5. ✓
- **§ Calibration starting point (1.0e-3 ppbv/s)** → Task 5 namelist value. ✓
- **§ Verification: build, regression, new behavior** → Task 6 (clean build) + Task 7 (altitude regression) + Task 8 (isotherm e2e). ✓
- **§ Error handling: unknown mode, t_min/t_max validation, missing T** → Task 2 Step 2 (unknown mode), Task 2 Step 3 (validation), Task 3 Step 2 (missing T inside inject), Task 4 Step 1 (missing inputs at call site). ✓

**Placeholder scan:** no TBDs, no TODOs, no "implement later." Calibration is left as a follow-up but with a concrete starting value and a clear retune procedure.

**Type / signature consistency:** subroutine signature in Task 3 matches the call in Task 4 (`temperature=temperature`, `(:,:)` shape, `nVertLevels × nCells` ordering). Mode constants `MODE_ALTITUDE = 1` / `MODE_ISOTHERM = 2` defined once in Task 2 and used in Task 3 only.

Plan complete.
