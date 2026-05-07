! Copyright (c) 2025 The University Corporation for Atmospheric Research (UCAR).
!
! Unless noted otherwise source code is licensed under the BSD license.
! Additional copyright and license information can be found in the LICENSE file
! distributed with this code, or at https://mpas-dev.github.io/license.html .
!
!-----------------------------------------------------------------------
!  mpas_atm_chemistry
!
!> \brief Manages interactions with chemistry packages
!> \author CheMPAS-A Developers
!> \date   20 August 2025
!> \details
!>  This module manages the interactions with chemistry packages,
!>  including initialization, time-stepping, and finalization.
!>  It provides a framework for integrating various chemistry models
!>  into the CheMPAS-A system.
!
!-------------------------------------------------------------------------
module mpas_atm_chemistry

    use mpas_kind_types, only : StrKIND, RKIND
    use mpas_timer, only : mpas_timer_start, mpas_timer_stop

    implicit none

    private

    public :: chemistry_init, chemistry_step, chemistry_finalize, chemistry_seed_chem
    public :: chemistry_from_MPAS, chemistry_to_MPAS
    public :: chemistry_query_species

    ! Lightning NOx source (no-op if qNO not in mechanism)
    public :: chemistry_lightning_nox_init

    ! Solar geometry config values (cached at init, used per-step)
    real(kind=RKIND), save :: chem_lat = 0.0_RKIND
    real(kind=RKIND), save :: chem_lon = 0.0_RKIND
    real(kind=RKIND), save :: chem_j_no2_max = 0.0_RKIND
    logical, save :: chem_use_grid_coords = .false.

    ! TUV-x update interval state (set in chemistry_init, accumulated in chemistry_step)
    real(kind=RKIND), save :: tuvx_update_interval = 0.0_RKIND
    real(kind=RKIND), save :: tuvx_time_since_last = huge(1.0_RKIND)

        ! Reference solve (doubles chemistry cost; off by default)
        logical, save :: use_ref_solve = .false.

        ! Number of MICM sub-steps per MPAS dt (1 = no sub-stepping)
        integer, save :: chem_substeps_val = 1

        ! MICM state relative tolerance (MICM default is 1e-6)
        real(kind=RKIND), save :: micm_relative_tolerance_val = 1.0e-6_RKIND

        ! TUV-x state
        logical, save :: use_tuvx = .false.
        integer, save :: idx_qO3 = -1
        integer, save :: idx_qc  = -1
        integer, save :: idx_qr  = -1

    contains

    !------------------------------------------------------------------------
    !  routine chemistry_init
    !
    !> \brief Initializes the chemistry packages
    !> \author CheMPAS-A Developers
    !> \date   20 August 2025
    !> \details
    !>  This routine initializes the chemistry packages, setting up
    !>  necessary parameters and data structures for the simulation.
    !------------------------------------------------------------------------
    subroutine chemistry_init(configs, dimensions, structs)

#ifdef MPAS_USE_MUSICA
        use mpas_musica, only: musica_init, resolve_mpas_indices, &
                               musica_cache_photo_indices
        use mpas_tuvx, only: tuvx_init, tuvx_is_enabled, &
                             tuvx_n_rates, tuvx_rate_names
#endif
        use mpas_log, only : mpas_log_write
        use mpas_derived_types, only: mpas_pool_type, MPAS_LOG_CRIT
        use mpas_pool_routines, only: mpas_pool_get_config, mpas_pool_get_dimension, &
                                      mpas_pool_get_subpool

        type (mpas_pool_type), intent(in) :: configs
        type (mpas_pool_type), intent(in) :: dimensions
        type (mpas_pool_type), intent(inout) :: structs

#ifdef MPAS_USE_MUSICA
        character(len=StrKIND), pointer :: filepath_ptr
        integer                         :: error_code
        character(len=:), allocatable   :: error_message
        integer                         :: nCells
        integer                         :: nVertLevels
        integer, pointer                :: nCells_ptr
        integer, pointer                :: nVertLevels_ptr
        type (mpas_pool_type), pointer  :: statePool
        type (mpas_pool_type), pointer  :: diagPool
        real(kind=RKIND), pointer       :: j_no2_ptr, nox_tau_ptr
        real(kind=RKIND)                :: j_no2_val, nox_tau_val
        real(kind=RKIND), pointer       :: lat_ptr, lon_ptr
        logical, pointer                :: use_grid_coords_ptr
        character(len=StrKIND), pointer :: tuvx_filepath_ptr
        logical, pointer                :: tuvx_top_extension_ptr
        character(len=StrKIND), pointer :: tuvx_extension_file_ptr
        logical                         :: tuvx_top_extension
        character(len=StrKIND)          :: tuvx_extension_file
        integer, pointer                :: idx_qO3_ptr
        integer, pointer                :: idx_qc_ptr, idx_qr_ptr
#endif

        call mpas_log_write('Initializing chemistry packages...')

#ifdef MPAS_USE_MUSICA
        call mpas_pool_get_dimension(dimensions, 'nVertLevels', nVertLevels_ptr)
        nVertLevels = nVertLevels_ptr

        call mpas_pool_get_dimension(dimensions, 'nCells', nCells_ptr)
        if (associated(nCells_ptr)) then
            nCells = nCells_ptr
        else
            nCells = 0
        end if

        call mpas_pool_get_config(configs, 'config_micm_file', filepath_ptr)

        ! Read prescribed photolysis and sink parameters
        j_no2_val = 0.0_RKIND
        nox_tau_val = 0.0_RKIND
        nullify(j_no2_ptr)
        nullify(nox_tau_ptr)
        call mpas_pool_get_config(configs, 'config_lnox_j_no2', j_no2_ptr)
        if (associated(j_no2_ptr)) j_no2_val = j_no2_ptr
        call mpas_pool_get_config(configs, 'config_lnox_nox_tau', nox_tau_ptr)
        if (associated(nox_tau_ptr)) nox_tau_val = nox_tau_ptr

        ! Read reference solve flag
        block
            logical, pointer :: ref_solve_ptr
            nullify(ref_solve_ptr)
            call mpas_pool_get_config(configs, 'config_chemistry_ref_solve', ref_solve_ptr)
            if (associated(ref_solve_ptr)) use_ref_solve = ref_solve_ptr
        end block

        ! Read chemistry sub-step count (split MICM dt for stiff mechanisms)
        block
            integer, pointer :: chem_substeps_ptr
            nullify(chem_substeps_ptr)
            call mpas_pool_get_config(configs, 'config_chem_substeps', chem_substeps_ptr)
            if (associated(chem_substeps_ptr)) chem_substeps_val = chem_substeps_ptr
            if (chem_substeps_val < 1) chem_substeps_val = 1
        end block

        ! Read MICM relative tolerance (tighten from default 1e-6 for stiff mechanisms)
        block
            real(kind=RKIND), pointer :: reltol_ptr
            nullify(reltol_ptr)
            call mpas_pool_get_config(configs, 'config_micm_relative_tolerance', reltol_ptr)
            if (associated(reltol_ptr)) micm_relative_tolerance_val = reltol_ptr
        end block

        ! Cache solar geometry config values for per-step SZA computation
        chem_j_no2_max = j_no2_val
        nullify(lat_ptr)
        nullify(lon_ptr)
        call mpas_pool_get_config(configs, 'config_chemistry_latitude', lat_ptr)
        if (associated(lat_ptr)) chem_lat = lat_ptr
        call mpas_pool_get_config(configs, 'config_chemistry_longitude', lon_ptr)
        if (associated(lon_ptr)) chem_lon = lon_ptr
        nullify(use_grid_coords_ptr)
        call mpas_pool_get_config(configs, 'config_chemistry_use_grid_coords', use_grid_coords_ptr)
        if (associated(use_grid_coords_ptr)) chem_use_grid_coords = use_grid_coords_ptr

        block
            real(kind=RKIND), pointer :: tuvx_update_interval_ptr
            nullify(tuvx_update_interval_ptr)
            call mpas_pool_get_config(configs, 'config_tuvx_update_interval', tuvx_update_interval_ptr)
            if (associated(tuvx_update_interval_ptr)) tuvx_update_interval = tuvx_update_interval_ptr
        end block

        ! Initialize MICM (species already injected into scalars by atm_setup_block)
        call musica_init(filepath_ptr, nCells * nVertLevels, &
                         nox_tau_val, &
                         real(micm_relative_tolerance_val, kind(1.0d0)), &
                         error_code, error_message)

        if (error_code /= 0) then
            call mpas_log_write(error_message, messageType=MPAS_LOG_CRIT)
        end if

        ! Resolve MPAS tracer indices for all chemistry species
        nullify(statePool)
        call mpas_pool_get_subpool(structs, 'state', statePool)
        if (associated(statePool)) then
            call resolve_mpas_indices(statePool, error_code, error_message)
            if (error_code /= 0) then
                call mpas_log_write(error_message, messageType=MPAS_LOG_CRIT)
            end if
        end if

        ! Seed MPAS tracers from MICM initial state (both time levels)
        call chemistry_seed_chem(dimensions, structs)

        ! Initialize photolysis diagnostics before any initial history write.
        ! We zero every j_<reaction> diag var that the Registry declares, by
        ! scanning candidate names and clearing those that exist.
        nullify(diagPool)
        call mpas_pool_get_subpool(structs, 'diag', diagPool)
        if (associated(diagPool)) then
            call zero_photolysis_diag(diagPool, ['j_jNO2   ', 'j_jO2    ', &
                                                  'j_jO3_O  ', 'j_jO3_O1D'])
        end if

        ! Initialize lightning NOx source (no-op if qNO not in mechanism)
        call chemistry_lightning_nox_init(configs, statePool)

        ! Initialize TUV-x if config file is specified
        nullify(tuvx_filepath_ptr)
        call mpas_pool_get_config(configs, 'config_tuvx_config_file', tuvx_filepath_ptr)
        if (associated(tuvx_filepath_ptr) .and. len_trim(tuvx_filepath_ptr) > 0) then
            nullify(tuvx_top_extension_ptr)
            nullify(tuvx_extension_file_ptr)
            call mpas_pool_get_config(configs, 'config_tuvx_top_extension', tuvx_top_extension_ptr)
            call mpas_pool_get_config(configs, 'config_tuvx_extension_file', tuvx_extension_file_ptr)
            tuvx_top_extension = .false.
            tuvx_extension_file = ''
            if (associated(tuvx_top_extension_ptr)) tuvx_top_extension = tuvx_top_extension_ptr
            if (associated(tuvx_extension_file_ptr)) tuvx_extension_file = tuvx_extension_file_ptr

            call tuvx_init(tuvx_filepath_ptr, nVertLevels, tuvx_top_extension, &
                           tuvx_extension_file, error_code, error_message)
            if (error_code /= 0) then
                call mpas_log_write(error_message, messageType=MPAS_LOG_CRIT)
            end if
            use_tuvx = tuvx_is_enabled()

            ! Resolve qO3 index (required for TUV-x)
            if (use_tuvx .and. associated(statePool)) then
                nullify(idx_qO3_ptr)
                call mpas_pool_get_dimension(statePool, 'index_qO3', idx_qO3_ptr)
                if (associated(idx_qO3_ptr) .and. idx_qO3_ptr > 0) then
                    idx_qO3 = idx_qO3_ptr
                    call mpas_log_write('[Chemistry] Resolved index_qO3 = $i for TUV-x', &
                        intArgs=[idx_qO3])
                else
                    use_tuvx = .false.
                    idx_qO3 = -1
                    call mpas_log_write('[Chemistry] qO3 tracer not found; TUV-x requires O3 and cannot continue.', &
                        messageType=MPAS_LOG_CRIT)
                    return
                end if
                ! Resolve cloud water index (required for Phase 3 cloud opacity)
                nullify(idx_qc_ptr)
                call mpas_pool_get_dimension(statePool, 'index_qc', idx_qc_ptr)
                if (associated(idx_qc_ptr) .and. idx_qc_ptr > 0) then
                    idx_qc = idx_qc_ptr
                    call mpas_log_write('[Chemistry] Resolved index_qc = $i for TUV-x cloud opacity', &
                        intArgs=[idx_qc])
                else
                    idx_qc = -1
                    call mpas_log_write('[Chemistry] qc tracer not found; TUV-x will use clear-sky only.')
                end if

                ! Resolve rain water index (optional — zero fallback if absent)
                nullify(idx_qr_ptr)
                call mpas_pool_get_dimension(statePool, 'index_qr', idx_qr_ptr)
                if (associated(idx_qr_ptr) .and. idx_qr_ptr > 0) then
                    idx_qr = idx_qr_ptr
                    call mpas_log_write('[Chemistry] Resolved index_qr = $i for TUV-x cloud opacity', &
                        intArgs=[idx_qr])
                else
                    idx_qr = -1
                    call mpas_log_write('[Chemistry] qr tracer not found; rain opacity will be zero.')
                end if
            else if (use_tuvx) then
                use_tuvx = .false.
                idx_qO3 = -1
                call mpas_log_write('[Chemistry] State pool unavailable; cannot resolve qO3 for TUV-x.', &
                    messageType=MPAS_LOG_CRIT)
                return
            end if
        else
            call mpas_log_write('[Chemistry] TUV-x disabled (no config_tuvx_config_file); using Phase 1 fallback.')
        end if

        ! Cache MICM rate-parameter indices for every photolysis rate we plan
        ! to write. When TUV-x is active, names come from its photolysis
        ! ordering. When TUV-x is disabled, we fall back to a single rate
        ! ('jNO2') driven by cos(SZA) * j_max.
        block
            character(len=64), allocatable :: photo_names(:)
            integer                        :: n_rates
            if (use_tuvx) then
                n_rates = tuvx_n_rates()
                if (n_rates < 1) then
                    call mpas_log_write('[Chemistry] TUV-x reported zero photolysis rates.', &
                        messageType=MPAS_LOG_CRIT)
                    return
                end if
                allocate(photo_names(n_rates))
                call tuvx_rate_names(photo_names)
            else
                n_rates = 1
                allocate(photo_names(1))
                photo_names(1) = 'jNO2'
            end if
            call musica_cache_photo_indices(photo_names, error_code, error_message)
            if (error_code /= 0) then
                call mpas_log_write(error_message, messageType=MPAS_LOG_CRIT)
            end if
            deallocate(photo_names)
        end block
#endif

    end subroutine chemistry_init


    !------------------------------------------------------------------------
    !  routine chemistry_step
    !
    !> \brief Steps the chemistry packages
    !> \author CheMPAS-A Developers
    !> \date   20 August 2025
    !> \details
    !>  This routine steps the chemistry packages, updating their state
    !>  based on the current simulation time and conditions.
    !>  Now includes bidirectional coupling: MPAS -> MICM -> MPAS
    !------------------------------------------------------------------------
    subroutine chemistry_step(dt, currTime, mesh, state, diag, dimensions, time_lev)

#ifdef MPAS_USE_MUSICA
        use iso_fortran_env, only: real64
        use mpas_musica, only: musica_step, musica_step_ref, log_column_comparison, &
                               copy_state_to_ref, musica_set_photolysis_rates, &
                               n_photo_rp
        use mpas_lightning_nox, only: lightning_nox_inject
        use mpas_solar_geometry, only: solar_cos_sza
        use mpas_tuvx, only: tuvx_compute_photolysis, tuvx_rate_names
#endif
        use mpas_log, only : mpas_log_write
        use mpas_derived_types, only: mpas_pool_type, MPAS_LOG_CRIT
        use mpas_pool_routines, only: mpas_pool_get_dimension, mpas_pool_get_array
        use mpas_timekeeping, only: mpas_get_time, MPAS_Time_type

        real (kind=RKIND), intent(in) :: dt
        type (MPAS_Time_type), intent(in) :: currTime
        type (mpas_pool_type), intent(in) :: mesh
        type (mpas_pool_type), intent(inout) :: state
        type (mpas_pool_type), intent(inout) :: diag
        type (mpas_pool_type), intent(in) :: dimensions
        integer, intent(in) :: time_lev

#ifdef MPAS_USE_MUSICA
        real(real64)                  :: time_step
        integer                       :: error_code
        character(len=:), allocatable :: error_message
        integer                       :: nCells, nVertLevels
        integer, pointer              :: nCells_ptr, nVertLevels_ptr
        integer                       :: probe_cell
        logical, save                 :: first_call = .true.

        ! Solar geometry variables
        integer :: DoY, hour, minute, second
        real(kind=RKIND) :: hour_utc
        real(kind=RKIND), allocatable :: cos_sza_cell(:)
        real(kind=RKIND), parameter   :: RAD2DEG = 57.29577951308232_RKIND
        real(kind=RKIND), dimension(:), pointer :: latCell, lonCell

        ! Lightning NOx injection arrays
        real(kind=RKIND), dimension(:,:,:), pointer :: scalars
        real(kind=RKIND), dimension(:,:), pointer :: w, zgrid

        ! Photolysis variables
        real(kind=RKIND), allocatable :: photo_rates(:,:,:)  ! (n_rates, nVertLevels, nCells)
        real(kind=RKIND), dimension(:,:), pointer :: rho_zz, theta_m, zz, exner
        integer, pointer :: index_qv
        real(kind=RKIND), allocatable :: rho_air_col(:), temperature_col(:)
        real(kind=RKIND), allocatable :: qc_col(:), qr_col(:)
        real(kind=RKIND), parameter :: rvord = 461.5_RKIND / 287.0_RKIND
        integer :: iCell, k, ir

        time_step = dt

        ! Get dimensions
        call mpas_pool_get_dimension(dimensions, 'nCells', nCells_ptr)
        call mpas_pool_get_dimension(dimensions, 'nVertLevels', nVertLevels_ptr)
        nCells = nCells_ptr
        nVertLevels = nVertLevels_ptr

        ! Probe cell near center of domain for advection diagnostics
        probe_cell = nCells / 2

        ! Update photolysis rates. Unified multi-rate path: TUV-x fills
        ! photo_rates(ir,k,iCell) for every reaction it reports; when TUV-x
        ! is disabled, the fallback fills a single 'jNO2' slot with
        ! j_max * max(0, cos_sza). The whole block is gated by
        ! tuvx_update_interval; on skip steps the accumulator just ticks
        ! forward and MICM keeps using the last-set rate parameters.
        if (n_photo_rp < 1) then
            call mpas_log_write('[Chemistry] photolysis rate indices not cached.', &
                messageType=MPAS_LOG_CRIT)
            return
        end if

        if (tuvx_time_since_last >= tuvx_update_interval) then
            ! Compute the time-of-day inputs (only needed when an update fires).
            call mpas_get_time(currTime, DoY=DoY, H=hour, M=minute, S=second)
            hour_utc = real(hour, RKIND) + real(minute, RKIND) / 60.0_RKIND &
                     + real(second, RKIND) / 3600.0_RKIND

            ! Per-cell solar zenith angle. Filled per cell when the grid-coords
            ! switch is enabled, broadcast from the namelist scalars otherwise.
            allocate(cos_sza_cell(nCells))
            if (chem_use_grid_coords) then
                call mpas_pool_get_array(mesh, 'latCell', latCell)
                call mpas_pool_get_array(mesh, 'lonCell', lonCell)
                do iCell = 1, nCells
                    cos_sza_cell(iCell) = solar_cos_sza(DoY, hour_utc, &
                                                        latCell(iCell) * RAD2DEG, &
                                                        lonCell(iCell) * RAD2DEG)
                end do
            else
                cos_sza_cell(:) = solar_cos_sza(DoY, hour_utc, chem_lat, chem_lon)
            end if

            allocate(photo_rates(n_photo_rp, nVertLevels, nCells))
            photo_rates = 0.0_RKIND

            if (use_tuvx) then
                if (idx_qO3 < 1) then
                    call mpas_log_write('[Chemistry] TUV-x enabled but index_qO3 is unresolved.', &
                        messageType=MPAS_LOG_CRIT)
                    deallocate(photo_rates, cos_sza_cell)
                    return
                end if

                allocate(rho_air_col(nVertLevels))
                allocate(temperature_col(nVertLevels))
                allocate(qc_col(nVertLevels))
                allocate(qr_col(nVertLevels))

                call mpas_pool_get_array(state, 'scalars', scalars, time_lev)
                call mpas_pool_get_array(state, 'rho_zz', rho_zz, time_lev)
                call mpas_pool_get_array(state, 'theta_m', theta_m, time_lev)
                call mpas_pool_get_array(mesh, 'zz', zz)
                call mpas_pool_get_array(mesh, 'zgrid', zgrid)
                call mpas_pool_get_array(diag, 'exner', exner)
                call mpas_pool_get_dimension(state, 'index_qv', index_qv)

                do iCell = 1, nCells
                    do k = 1, nVertLevels
                        rho_air_col(k) = zz(k, iCell) * rho_zz(k, iCell) * &
                                         (1.0_RKIND + scalars(index_qv, k, iCell))
                        temperature_col(k) = (theta_m(k, iCell) / &
                            (1.0_RKIND + rvord * scalars(index_qv, k, iCell))) * exner(k, iCell)
                    end do

                    if (idx_qc > 0) then
                        qc_col(:) = scalars(idx_qc, :, iCell)
                    else
                        qc_col(:) = 0.0_RKIND
                    end if
                    if (idx_qr > 0) then
                        qr_col(:) = scalars(idx_qr, :, iCell)
                    else
                        qr_col(:) = 0.0_RKIND
                    end if

                    call tuvx_compute_photolysis(cos_sza_cell(iCell), zgrid(:, iCell), &
                                                 rho_air_col, temperature_col, &
                                                 scalars(idx_qO3, :, iCell), &
                                                 qc_col, qr_col, &
                                                 nVertLevels, &
                                                 photo_rates(:, :, iCell), &
                                                 error_code, error_message)
                    if (error_code /= 0) then
                        call mpas_log_write(error_message, messageType=MPAS_LOG_CRIT)
                        deallocate(photo_rates, rho_air_col, temperature_col, qc_col, qr_col, cos_sza_cell)
                        return
                    end if
                end do

                deallocate(rho_air_col, temperature_col, qc_col, qr_col)
            else
                ! Phase-1 fallback: single rate 'jNO2' = j_max * max(0, cos_sza).
                ! Assumes n_photo_rp == 1 and the cached rate name is 'jNO2' —
                ! musica_cache_photo_indices was called with that name at init.
                do iCell = 1, nCells
                    photo_rates(1, :, iCell) = chem_j_no2_max * &
                                                max(0.0_RKIND, cos_sza_cell(iCell))
                end do
            end if

            call musica_set_photolysis_rates(photo_rates, nCells, nVertLevels, &
                                             n_photo_rp, error_code, error_message)
            if (error_code /= 0) then
                call mpas_log_write(error_message, messageType=MPAS_LOG_CRIT)
                deallocate(photo_rates, cos_sza_cell)
                return
            end if

            call chemistry_set_photolysis_diag(diag, photo_rates, nCells, nVertLevels)

            deallocate(photo_rates, cos_sza_cell)

            tuvx_time_since_last = 0.0_RKIND
        else
            tuvx_time_since_last = tuvx_time_since_last + dt
        end if

        call mpas_log_write('Stepping chemistry packages...')
        call mpas_timer_start('chemistry')

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

        ! Step 1: Copy MPAS state to MICM (MPAS -> MICM)
        call mpas_timer_start('chem MPAS->MICM')
        call chemistry_from_MPAS(mesh, state, diag, dimensions, time_lev, &
                                  nCells, nVertLevels, error_code, error_message)
        call mpas_timer_stop('chem MPAS->MICM')
        if (error_code /= 0) then
            call mpas_log_write(error_message, messageType=MPAS_LOG_CRIT)
            return
        end if

        ! On first call, copy coupled state to reference so both start with
        ! identical initial conditions from MPAS. Any subsequent divergence
        ! will indicate advection effects.
        if (first_call .and. use_ref_solve) then
            call copy_state_to_ref()
            call mpas_log_write('[Chemistry] Copied coupled state to reference state (first timestep).')
            first_call = .false.
        end if

        ! Step 2: Solve chemistry (coupled state). Split the MPAS dt into
        ! config_chem_substeps MICM calls. TUV-x photolysis rates were set
        ! once above and stay frozen across sub-steps. Sub-stepping is needed
        ! for stiff mechanisms where Backward Euler at the full dt lands on
        ! a non-physical implicit fixed point (see
        ! docs/plans/2026-04-18-chapman-nox-chem-box-issue.md).
        block
            real(kind=RKIND) :: sub_dt
            integer          :: i_sub
            sub_dt = time_step / real(chem_substeps_val, RKIND)
            call mpas_timer_start('chem MICM solve')
            do i_sub = 1, chem_substeps_val
                call musica_step(real(sub_dt, kind(time_step)), error_code, error_message)
                if (error_code /= 0) then
                    call mpas_timer_stop('chem MICM solve')
                    call mpas_log_write(error_message, messageType=MPAS_LOG_CRIT)
                    return
                end if
            end do
            call mpas_timer_stop('chem MICM solve')

            ! Step 2b: Reference state (uncoupled, for advection diagnostics)
            if (use_ref_solve) then
                call mpas_timer_start('chem MICM ref solve')
                do i_sub = 1, chem_substeps_val
                    call musica_step_ref(real(sub_dt, kind(time_step)), error_code, error_message)
                    if (error_code /= 0) then
                        call mpas_log_write(error_message, messageType=MPAS_LOG_CRIT)
                        exit
                    end if
                end do
                call mpas_timer_stop('chem MICM ref solve')

                call log_column_comparison(probe_cell, nVertLevels)
            end if
        end block

        ! Step 3: Copy MICM state back to MPAS (MICM -> MPAS)
        call mpas_timer_start('chem MICM->MPAS')
        call chemistry_to_MPAS(mesh, state, diag, dimensions, time_lev, &
                                nCells, nVertLevels, error_code, error_message)
        call mpas_timer_stop('chem MICM->MPAS')
        if (error_code /= 0) then
            call mpas_log_write(error_message, messageType=MPAS_LOG_CRIT)
        end if
        call mpas_timer_stop('chemistry')
#endif

    end subroutine chemistry_step


    !------------------------------------------------------------------------
    !  routine chemistry_finalize
    !
    !> \brief Finalizes the chemistry packages
    !> \author CheMPAS-A Developers
    !> \date   20 August 2025
    !> \details
    !>  This routine finalizes the chemistry packages, cleaning up
    !>  any resources and data structures used during the simulation.
    !------------------------------------------------------------------------
    subroutine chemistry_finalize()

#ifdef MPAS_USE_MUSICA
        use mpas_musica, only: musica_finalize
        use mpas_tuvx, only: tuvx_finalize_sub => tuvx_finalize
#endif
        use mpas_log, only : mpas_log_write

#ifdef MPAS_USE_MUSICA
        call mpas_log_write('Finalizing chemistry packages...')
        call tuvx_finalize_sub()
        call musica_finalize()
#endif

    end subroutine chemistry_finalize


    !------------------------------------------------------------------------
    !  routine chemistry_set_photolysis_diag
    !
    !> \brief Write per-cell/level photolysis rates into diagnostic pool
    !> \details
    !>  For every cached photolysis rate name (j_<name>), look up the
    !>  matching diag array and copy the corresponding slice from
    !>  photo_rates. Silently skips rates whose diag variable is not in
    !>  the Registry (so the chemistry driver stays agnostic about which
    !>  mechanism is loaded).
    !------------------------------------------------------------------------
    subroutine chemistry_set_photolysis_diag(diag, photo_rates, nCells, nVertLevels)

#ifdef MPAS_USE_MUSICA
        use mpas_musica, only: photo_rp_names, n_photo_rp
#endif
        use mpas_pool_routines, only: mpas_pool_get_array
        use mpas_derived_types, only: mpas_pool_type

        type(mpas_pool_type), intent(inout) :: diag
        real(kind=RKIND), intent(in) :: photo_rates(:,:,:)  ! (n_rates, nVertLevels, nCells)
        integer, intent(in) :: nCells, nVertLevels

#ifdef MPAS_USE_MUSICA
        real(kind=RKIND), dimension(:,:), pointer :: diag_field
        integer :: ir, k, iCell

        do ir = 1, n_photo_rp
            nullify(diag_field)
            call mpas_pool_get_array(diag, 'j_' // trim(photo_rp_names(ir)), diag_field)
            if (.not. associated(diag_field)) cycle

            do iCell = 1, min(nCells, size(diag_field, 2))
                do k = 1, min(nVertLevels, size(diag_field, 1))
                    diag_field(k, iCell) = photo_rates(ir, k, iCell)
                end do
            end do
        end do
#endif

    end subroutine chemistry_set_photolysis_diag


    !------------------------------------------------------------------------
    !  routine zero_photolysis_diag
    !
    !> \brief Zero a set of photolysis diagnostic fields at init time
    !> \details
    !>  Given a caller-provided list of candidate diag variable names
    !>  (padded to equal length), clear each one that exists in the diag
    !>  pool. Names not present in the Registry are silently skipped.
    !------------------------------------------------------------------------
    subroutine zero_photolysis_diag(diag, names)

        use mpas_pool_routines, only: mpas_pool_get_array
        use mpas_derived_types, only: mpas_pool_type

        type(mpas_pool_type), intent(inout) :: diag
        character(len=*), intent(in)        :: names(:)

        real(kind=RKIND), dimension(:,:), pointer :: diag_field
        integer :: i

        do i = 1, size(names)
            nullify(diag_field)
            call mpas_pool_get_array(diag, trim(names(i)), diag_field)
            if (associated(diag_field)) diag_field = 0.0_RKIND
        end do

    end subroutine zero_photolysis_diag


    !------------------------------------------------------------------------
    !  routine chemistry_from_MPAS
    !
    !> \brief Extracts MPAS state for chemistry processing
    !> \author CheMPAS-A Developers
    !> \date   January 2026
    !> \details
    !>  This routine extracts MPAS state variables (scalars, thermodynamic
    !>  fields) and passes them to the chemistry package (MICM) for processing.
    !>  Following the physics interface pattern from mpas_atmphys_interface.F
    !------------------------------------------------------------------------
    subroutine chemistry_from_MPAS(mesh, state, diag, dimensions, time_lev, &
                                    nCells, nVertLevels, error_code, error_message)

#ifdef MPAS_USE_MUSICA
        use mpas_musica, only: MICM_from_chemistry
#endif
        use mpas_log, only : mpas_log_write
        use mpas_derived_types, only: mpas_pool_type, MPAS_LOG_CRIT
        use mpas_pool_routines, only: mpas_pool_get_array, mpas_pool_get_dimension

        type (mpas_pool_type), intent(in) :: mesh
        type (mpas_pool_type), intent(in) :: state
        type (mpas_pool_type), intent(in) :: diag
        type (mpas_pool_type), intent(in) :: dimensions
        integer, intent(in) :: time_lev
        integer, intent(in) :: nCells
        integer, intent(in) :: nVertLevels
        integer, intent(out) :: error_code
        character(len=:), allocatable, intent(out) :: error_message

#ifdef MPAS_USE_MUSICA
        ! MPAS state arrays
        real (kind=RKIND), dimension(:,:,:), pointer :: scalars
        real (kind=RKIND), dimension(:,:), pointer :: rho_zz, theta_m
        real (kind=RKIND), dimension(:,:), pointer :: zz, exner
        real (kind=RKIND), dimension(:,:), pointer :: pressure_p, pressure_b
        integer, pointer :: index_qv

        ! Local work arrays
        real (kind=RKIND), allocatable :: rho_air(:,:)
        real (kind=RKIND), allocatable :: temperature(:,:)
        real (kind=RKIND), allocatable :: pressure(:,:)

        real (kind=RKIND), parameter :: rvord = 461.5_RKIND / 287.0_RKIND  ! Rv/Rd

        integer :: k, iCell

        error_code = 0
        error_message = ''

        ! Get MPAS arrays from pools
        call mpas_pool_get_array(state, 'scalars', scalars, time_lev)
        call mpas_pool_get_array(state, 'rho_zz', rho_zz, time_lev)
        call mpas_pool_get_array(state, 'theta_m', theta_m, time_lev)
        call mpas_pool_get_array(mesh, 'zz', zz)
        call mpas_pool_get_array(diag, 'exner', exner)
        call mpas_pool_get_array(diag, 'pressure_p', pressure_p)
        call mpas_pool_get_array(diag, 'pressure_base', pressure_b)

        ! Get water vapor index (needed for thermodynamic calculations)
        call mpas_pool_get_dimension(state, 'index_qv', index_qv)

        ! Validate pointers
        if (.not. associated(scalars) .or. .not. associated(rho_zz) .or. &
            .not. associated(theta_m) .or. .not. associated(zz) .or. &
            .not. associated(exner)) then
            error_code = 1
            error_message = '[Chemistry] Required MPAS arrays not available in chemistry_from_MPAS.'
            return
        end if

        ! Allocate work arrays
        allocate(rho_air(nVertLevels, nCells))
        allocate(temperature(nVertLevels, nCells))
        allocate(pressure(nVertLevels, nCells))

        ! Calculate derived quantities following physics interface pattern
        do iCell = 1, nCells
            do k = 1, nVertLevels
                ! Moist air density [kg/m³]: rho = zz * rho_zz * (1 + qv)
                rho_air(k, iCell) = zz(k, iCell) * rho_zz(k, iCell) * &
                                    (1.0_RKIND + scalars(index_qv, k, iCell))

                ! Temperature [K]: T = theta * exner, where theta = theta_m / (1 + Rv/Rd * qv)
                temperature(k, iCell) = (theta_m(k, iCell) / &
                    (1.0_RKIND + rvord * scalars(index_qv, k, iCell))) * exner(k, iCell)

                ! Total pressure [Pa]
                if (associated(pressure_p) .and. associated(pressure_b)) then
                    pressure(k, iCell) = pressure_p(k, iCell) + pressure_b(k, iCell)
                else
                    ! Fallback: estimate from ideal gas law
                    pressure(k, iCell) = rho_air(k, iCell) * 287.0_RKIND * temperature(k, iCell)
                end if
            end do
        end do

        ! Call MICM-specific coupling routine (uses chem_species table internally)
        call MICM_from_chemistry(scalars, rho_air, temperature, pressure, &
                                  nCells, nVertLevels, &
                                  error_code, error_message)

        deallocate(rho_air)
        deallocate(temperature)
        deallocate(pressure)
#else
        error_code = 0
        error_message = ''
#endif

    end subroutine chemistry_from_MPAS


    !------------------------------------------------------------------------
    !  routine chemistry_to_MPAS
    !
    !> \brief Updates MPAS state from chemistry results
    !> \author CheMPAS-A Developers
    !> \date   January 2026
    !> \details
    !>  This routine copies the updated chemistry state back to MPAS scalars
    !>  after the chemistry solver has completed.
    !------------------------------------------------------------------------
    subroutine chemistry_to_MPAS(mesh, state, diag, dimensions, time_lev, &
                                  nCells, nVertLevels, error_code, error_message)

#ifdef MPAS_USE_MUSICA
        use mpas_musica, only: MICM_to_chemistry
#endif
        use mpas_log, only : mpas_log_write
        use mpas_derived_types, only: mpas_pool_type, MPAS_LOG_CRIT
        use mpas_pool_routines, only: mpas_pool_get_array, mpas_pool_get_dimension

        type (mpas_pool_type), intent(in) :: mesh
        type (mpas_pool_type), intent(inout) :: state
        type (mpas_pool_type), intent(in) :: diag
        type (mpas_pool_type), intent(in) :: dimensions
        integer, intent(in) :: time_lev
        integer, intent(in) :: nCells
        integer, intent(in) :: nVertLevels
        integer, intent(out) :: error_code
        character(len=:), allocatable, intent(out) :: error_message

#ifdef MPAS_USE_MUSICA
        ! MPAS state arrays
        real (kind=RKIND), dimension(:,:,:), pointer :: scalars
        real (kind=RKIND), dimension(:,:), pointer :: rho_zz, zz
        integer, pointer :: index_qv

        ! Local work arrays
        real (kind=RKIND), allocatable :: rho_air(:,:)

        integer :: k, iCell

        error_code = 0
        error_message = ''

        ! Get MPAS arrays from pools
        call mpas_pool_get_array(state, 'scalars', scalars, time_lev)
        call mpas_pool_get_array(state, 'rho_zz', rho_zz, time_lev)
        call mpas_pool_get_array(mesh, 'zz', zz)

        ! Get water vapor index
        call mpas_pool_get_dimension(state, 'index_qv', index_qv)

        ! Validate pointers
        if (.not. associated(scalars) .or. .not. associated(rho_zz) .or. &
            .not. associated(zz)) then
            error_code = 1
            error_message = '[Chemistry] Required MPAS arrays not available in chemistry_to_MPAS.'
            return
        end if

        ! Allocate work arrays
        allocate(rho_air(nVertLevels, nCells))

        ! Calculate air density for unit conversion
        do iCell = 1, nCells
            do k = 1, nVertLevels
                rho_air(k, iCell) = zz(k, iCell) * rho_zz(k, iCell) * &
                                    (1.0_RKIND + scalars(index_qv, k, iCell))
            end do
        end do

        ! Call MICM-specific coupling routine (uses chem_species table internally)
        call MICM_to_chemistry(scalars, rho_air, nCells, nVertLevels, &
                                error_code, error_message)

        deallocate(rho_air)
#else
        error_code = 0
        error_message = ''
#endif

    end subroutine chemistry_to_MPAS


    !------------------------------------------------------------------------
    !  routine chemistry_seed_chem
    !
    !> \brief One-time (or repeated) MICM -> MPAS chemistry tracer seed
    !------------------------------------------------------------------------
    subroutine chemistry_seed_chem(dimensions, structs)

#ifdef MPAS_USE_MUSICA
        use mpas_musica, only: micm_to_mpas_chem, n_chem_species, chem_species
#endif
        use mpas_log, only : mpas_log_write
        use mpas_derived_types, only: mpas_pool_type, MPAS_LOG_CRIT, field3dReal
        use mpas_pool_routines, only: mpas_pool_get_dimension, mpas_pool_get_subpool, &
                                      mpas_pool_get_field, mpas_pool_get_array

        type (mpas_pool_type), intent(in) :: dimensions
        type (mpas_pool_type), intent(in) :: structs

#ifdef MPAS_USE_MUSICA
        integer                         :: nCells
        integer                         :: nVertLevels
        integer, pointer                :: nCells_ptr
        integer, pointer                :: nVertLevels_ptr
        type (mpas_pool_type), pointer  :: statePool
        type (field3dReal), pointer     :: scalarsField
        real (kind=RKIND), dimension(:,:,:), pointer :: scalars_time1
        real (kind=RKIND), dimension(:,:,:), pointer :: scalars_time2
        integer                         :: error_code, i_sp, mpas_idx
        character(len=:), allocatable   :: error_message

        call mpas_log_write('[MUSICA] Seeding chemistry tracers from MICM into MPAS scalars (both time levels).')

        if (n_chem_species == 0) then
            call mpas_log_write('[MUSICA] No chemistry species to seed.')
            return
        end if

        call mpas_pool_get_dimension(dimensions, 'nVertLevels', nVertLevels_ptr)
        nVertLevels = nVertLevels_ptr

        call mpas_pool_get_dimension(dimensions, 'nCells', nCells_ptr)
        if (associated(nCells_ptr)) then
            nCells = nCells_ptr
        else
            nCells = 0
        end if

        nullify(statePool)
        nullify(scalarsField)
        nullify(scalars_time1)
        nullify(scalars_time2)

        call mpas_pool_get_subpool(structs, 'state', statePool)
        if (associated(statePool)) then
            call mpas_pool_get_field(statePool, 'scalars', scalarsField, 1)
            call mpas_pool_get_array(statePool, 'scalars', scalars_time1, 1)
            call mpas_pool_get_array(statePool, 'scalars', scalars_time2, 2)
        end if

        if (.not. associated(scalars_time1)) then
            call mpas_log_write('[MUSICA] Skipping MICM->MPAS seed: scalars time level 1 not available.')
            return
        else if (.not. associated(scalars_time2)) then
            call mpas_log_write('[MUSICA] Skipping MICM->MPAS seed: scalars time level 2 not available.')
            return
        end if

        ! Check if any chemistry tracer has MPAS index not yet resolved
        do i_sp = 1, n_chem_species
            if (chem_species(i_sp)%mpas_index < 1) then
                call mpas_log_write('[MUSICA] Skipping MICM->MPAS seed: MPAS indices not resolved.')
                return
            end if
        end do

        ! Skip seeding if any chemistry tracer already has spatial gradients (initialized from file)
        do i_sp = 1, n_chem_species
            mpas_idx = chem_species(i_sp)%mpas_index
            if (maxval(scalars_time1(mpas_idx,:,:)) - minval(scalars_time1(mpas_idx,:,:)) > 1.0e-10_RKIND) then
                call mpas_log_write('[MUSICA] Tracer ' // trim(chem_species(i_sp)%mpas_name) // &
                    ' has spatial gradients, skipping MICM seed.')
                return
            end if
        end do

        error_code = 0
        call micm_to_mpas_chem(scalars_time1, nCells, nVertLevels, error_code, error_message)
        if (error_code /= 0) then
            call mpas_log_write(error_message, messageType=MPAS_LOG_CRIT)
        end if

        error_code = 0
        call micm_to_mpas_chem(scalars_time2, nCells, nVertLevels, error_code, error_message)
        if (error_code /= 0) then
            call mpas_log_write(error_message, messageType=MPAS_LOG_CRIT)
        end if
#endif

    end subroutine chemistry_seed_chem


    !------------------------------------------------------------------------
    !  subroutine chemistry_query_species
    !
    !> \brief Wrapper to query MICM config for chemistry species names
    !> \details
    !>  Delegates to musica_query_species. Provides a clean interface
    !>  for mpas_atm_core_interface without requiring direct musica access.
    !------------------------------------------------------------------------
    subroutine chemistry_query_species(config_path, num_species, species_names, error_code, error_message)

#ifdef MPAS_USE_MUSICA
        use mpas_musica, only: musica_query_species
#endif

        character(len=*), intent(in)                :: config_path
        integer, intent(out)                        :: num_species
        character(len=64), allocatable, intent(out)  :: species_names(:)
        integer, intent(out)                        :: error_code
        character(len=:), allocatable, intent(out)   :: error_message

        error_code = 0
        error_message = ''
        num_species = 0

#ifdef MPAS_USE_MUSICA
        call musica_query_species(config_path, num_species, species_names, error_code, error_message)
#endif

    end subroutine chemistry_query_species


    !------------------------------------------------------------------------
    !  subroutine chemistry_lightning_nox_init
    !
    !> \brief Initialize lightning NOx source from namelist + tracer pool
    !------------------------------------------------------------------------
    subroutine chemistry_lightning_nox_init(configs, statePool)

        use mpas_lightning_nox, only: lightning_nox_init
        use mpas_derived_types, only: mpas_pool_type

        type(mpas_pool_type), intent(in) :: configs
        type(mpas_pool_type), intent(in) :: statePool

        call lightning_nox_init(configs, statePool)

    end subroutine chemistry_lightning_nox_init

end module mpas_atm_chemistry
