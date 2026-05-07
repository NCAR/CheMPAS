! Copyright (c) 2025 The University Corporation for Atmospheric Research (UCAR).
!
! Unless noted otherwise source code is licensed under the BSD license.
! Additional copyright and license information can be found in the LICENSE file
! distributed with this code, or at https://mpas-dev.github.io/license.html .
!
!-----------------------------------------------------------------------
!  mpas_lightning_nox
!
!> \brief Lightning NOx source parameterization
!> \author CheMPAS-A Developers
!> \date   March 2026
!> \details
!>  Injects NO into MPAS scalars where vertical velocity exceeds a
!>  threshold and altitude is within a prescribed range. This is a
!>  source-only module; the chemistry (NO + O3 -> NO2, NO2 + hv -> NO + O3)
!>  is handled by MICM.
!>
!>  The source rate scales linearly with updraft strength:
!>    S = source_rate * max(0, w - w_threshold) / w_ref  [ppbv/s]
!>  The configured source_rate is reached when (w - w_threshold) = w_ref.
!>
!>  At init time the module looks up index_qNO in the scalars pool.
!>  If qNO is not present (mechanism doesn't use it), the module is a no-op.
!>
!>  Adapted from DAVINCI-MPAS mpas_davinci_lightning_nox.F
!
!-----------------------------------------------------------------------
module mpas_lightning_nox

    use mpas_kind_types, only: RKIND, StrKIND

    implicit none
    private

    public :: lightning_nox_init
    public :: lightning_nox_inject

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

    ! Constants for unit conversion (ppbv -> kg/kg mass mixing ratio)
    real(kind=RKIND), parameter :: M_NO  = 0.030_RKIND   ! kg/mol (NO molar mass)
    real(kind=RKIND), parameter :: M_AIR = 0.029_RKIND   ! kg/mol (dry air molar mass)

contains

    !-----------------------------------------------------------------------
    !  routine lightning_nox_init
    !
    !> \brief Initialize lightning NOx source; no-op if qNO not present
    !-----------------------------------------------------------------------
    subroutine lightning_nox_init(configs, state)

        use mpas_derived_types, only: mpas_pool_type
        use mpas_pool_routines, only: mpas_pool_get_config, mpas_pool_get_dimension
        use mpas_log, only: mpas_log_write

        type(mpas_pool_type), intent(in) :: configs
        type(mpas_pool_type), intent(in) :: state

        integer, pointer :: index_qNO_ptr
        real(kind=RKIND), pointer :: cfg_ptr

        ! Look for qNO in the scalars pool
        nullify(index_qNO_ptr)
        call mpas_pool_get_dimension(state, 'index_qNO', index_qNO_ptr)

        if (.not. associated(index_qNO_ptr)) then
            call mpas_log_write('[LNOx] qNO not found in scalars; lightning source disabled.')
            lnox_active = .false.
            return
        end if

        if (index_qNO_ptr < 1) then
            call mpas_log_write('[LNOx] qNO index invalid; lightning source disabled.')
            lnox_active = .false.
            return
        end if

        idx_qNO = index_qNO_ptr

        ! Read namelist parameters
        nullify(cfg_ptr)
        call mpas_pool_get_config(configs, 'config_lnox_source_rate', cfg_ptr)
        if (associated(cfg_ptr)) source_rate_ppbv = cfg_ptr

        nullify(cfg_ptr)
        call mpas_pool_get_config(configs, 'config_lnox_w_threshold', cfg_ptr)
        if (associated(cfg_ptr)) w_threshold = cfg_ptr

        nullify(cfg_ptr)
        call mpas_pool_get_config(configs, 'config_lnox_w_ref', cfg_ptr)
        if (associated(cfg_ptr)) w_ref = cfg_ptr

        nullify(cfg_ptr)
        call mpas_pool_get_config(configs, 'config_lnox_z_min', cfg_ptr)
        if (associated(cfg_ptr)) z_min = cfg_ptr

        nullify(cfg_ptr)
        call mpas_pool_get_config(configs, 'config_lnox_z_max', cfg_ptr)
        if (associated(cfg_ptr)) z_max = cfg_ptr

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

        if (source_rate_ppbv <= 0.0_RKIND) then
            call mpas_log_write('[LNOx] source_rate <= 0; lightning source disabled.')
            lnox_active = .false.
            return
        end if

        if (w_ref <= 0.0_RKIND) then
            call mpas_log_write('[LNOx] w_ref <= 0; lightning source disabled (would cause divide-by-zero).')
            lnox_active = .false.
            return
        end if

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

    end subroutine lightning_nox_init


    !-----------------------------------------------------------------------
    !  routine lightning_nox_inject
    !
    !> \brief Inject NO source into scalars where w > threshold
    !> \details
    !>  Modifies scalars(index_qNO, k, iCell) in place. Called before
    !>  MICM solves the chemistry. The source is converted from ppbv/s to
    !>  mass mixing ratio tendency [kg/kg] before it is added to qNO.
    !>
    !>  Uses layer-midpoint height from zgrid for altitude gating and
    !>  w interpolated to layer midpoints from interface values.
    !-----------------------------------------------------------------------
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

        integer :: iCell, k, n_activated
        real(kind=RKIND) :: w_mid, z_mid, delta_q
        logical, save :: first_call = .true.

        if (.not. lnox_active) return

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

        if (first_call) then
            call mpas_log_write('[LNOx] First injection: $i cell-levels activated', &
                                intArgs=(/n_activated/))
            first_call = .false.
        end if

    end subroutine lightning_nox_inject

end module mpas_lightning_nox
