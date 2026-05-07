#!/usr/bin/env python3
"""
Visualize CheMPAS-A LNOx-O3 output from the MPAS supercell test case.

Plots NO, NO2, O3, and NOx diagnostics: vertical cross-sections through the
updraft, time evolution of peak/mean concentrations, horizontal slices,
and the NO2/(NO+NO2) partitioning ratio.

Adapted from DAVINCI-MPAS/scripts/plot_lightning_nox.py with O3 added as
a prognostic species.

Usage:
    python plot_lnox_o3.py                        # All plots, default paths
    python plot_lnox_o3.py -i output.nc --all     # Explicit input
    python plot_lnox_o3.py --vertical --time 30   # Single plot type
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation
from netCDF4 import Dataset

# Add scripts dir to path for style module
sys.path.insert(0, str(Path(__file__).parent))
import style


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Molar masses [kg/mol] for ppbv conversion
M_NO = 0.030
M_NO2 = 0.046
M_O3 = 0.048
M_AIR = 0.029


# ---------------------------------------------------------------------------
# I/O helpers (shared with plot_passive.py patterns)
# ---------------------------------------------------------------------------

def rasterize_contours(cf):
    """Rasterize contourf fills for clean PDF output."""
    if hasattr(cf, 'collections'):
        for c in cf.collections:
            c.set_rasterized(True)
    else:
        cf.set_rasterized(True)


def add_colorbar(cf, ax, label=''):
    """Add a colorbar with rasterized fill."""
    from matplotlib.collections import Collection
    from matplotlib.image import AxesImage
    cb = plt.colorbar(cf, ax=ax, label=label)
    for artist in cb.ax.get_children():
        if isinstance(artist, (Collection, AxesImage)):
            artist.set_rasterized(True)
    return cb


def save_figure(output_file, dpi=300):
    """Save figure to both PNG and PDF."""
    png_file = output_file if output_file.endswith('.png') else output_file + '.png'
    pdf_file = png_file.replace('.png', '.pdf')
    plt.savefig(png_file, dpi=dpi, bbox_inches='tight')
    plt.savefig(pdf_file, bbox_inches='tight')
    print(f"  saved {png_file} and {pdf_file}")


def smart_levels(data_min, data_max, n=51):
    """Choose contour levels that reveal structure in the data."""
    span = data_max - data_min
    if span < 1e-12:
        return np.linspace(0, max(data_max, 1e-6), n)
    # Round to clean boundaries
    nice = 10 ** np.floor(np.log10(span))
    lo = np.floor(data_min / nice) * nice
    hi = np.ceil(data_max / nice) * nice
    if hi <= lo:
        hi = lo + nice
    return np.linspace(lo, hi, n)


def load_data(filename):
    """Load MPAS output data for lightning NOx analysis."""
    ds = Dataset(filename, 'r')
    # Parse xtime strings to get elapsed simulation minutes
    nT = len(ds.dimensions['Time'])
    xt = ds['xtime'][:]

    def _xtime_to_minutes(chars):
        s = ''.join([c.decode() if isinstance(c, bytes) else c for c in chars]).strip()
        # Format: YYYY-DD-MM_HH:MM:SS  (MPAS uses 0000-01-01 epoch)
        parts = s.split('_')
        dparts = parts[0].split('-')
        hms = parts[-1].split(':')
        days = (int(dparts[0]) * 365 + (int(dparts[1]) - 1) * 30 + int(dparts[2]) - 1)
        return days * 1440 + int(hms[0]) * 60 + int(hms[1]) + int(hms[2]) / 60.0

    # Use the init file start time (18:00) as t=0 reference if available,
    # otherwise use the first output frame
    t0_minutes = _xtime_to_minutes(xt[0])
    init_file = Path(filename).parent / 'supercell_init.nc'
    if init_file.exists():
        ds_init = Dataset(str(init_file), 'r')
        t0_minutes = _xtime_to_minutes(ds_init['xtime'][0])
        ds_init.close()

    time_minutes = np.array([_xtime_to_minutes(xt[t]) - t0_minutes
                             for t in range(nT)])

    data = {
        'xCell': ds['xCell'][:] / 1000,       # km
        'yCell': ds['yCell'][:] / 1000,
        'areaCell': ds['areaCell'][:],
        'qNO': ds['qNO'][:],                  # (Time, nCells, nVertLevels)
        'qNO2': ds['qNO2'][:],
        'qO3': ds['qO3'][:],
        'nCells': len(ds.dimensions['nCells']),
        'nVertLevels': len(ds.dimensions['nVertLevels']),
        'nTimes': nT,
        'times': np.arange(nT),
        'time_minutes': time_minutes,          # actual simulation minutes
    }
    if 'zgrid' in ds.variables:
        data['zgrid'] = ds['zgrid'][:] / 1000  # km (nCells, nVertLevelsP1)
    if 'w' in ds.variables:
        data['w'] = ds['w'][:, :, :-1]         # trim interface -> nVertLevels
    if 'uReconstructZonal' in ds.variables:
        data['uZonal'] = ds['uReconstructZonal'][:]
        data['uMeridional'] = ds['uReconstructMeridional'][:]
    if 'j_no2' in ds.variables:
        data['j_no2'] = ds['j_no2'][:]              # (Time, nCells, nVertLevels)
    ds.close()
    return data


def get_level_height(data, level):
    """Approximate height in km for a vertical level."""
    if data.get('zgrid') is not None:
        return float(0.5 * (data['zgrid'][:, level] + data['zgrid'][:, level + 1]).mean())
    return level * 20.0 / data['nVertLevels']


def level_label(data, level):
    return f"{get_level_height(data, level):.1f} km"


def to_ppbv(q_kgkg, M_species):
    """Convert mass mixing ratio (kg/kg) to ppbv."""
    return q_kgkg * (M_AIR / M_species) * 1.0e9


def select_cell_row(data, y_slice):
    """Select a row of cells for vertical cross-section."""
    x, y = data['xCell'], data['yCell']
    dx = (x.max() - x.min()) / 200
    x_bins = np.arange(x.min(), x.max() + dx, dx)
    bin_idx = np.digitize(x, x_bins)
    selected = []
    for b in range(1, len(x_bins)):
        in_bin = np.where(bin_idx == b)[0]
        if len(in_bin) == 0:
            continue
        best = in_bin[np.argmin(np.abs(y[in_bin] - y_slice))]
        selected.append(best)
    selected = np.array(selected)
    order = np.argsort(x[selected])
    return selected[order]


def add_wind_barbs(ax, data, time_idx, level, skip=200, length=4.5):
    """Overlay wind barbs on a horizontal plot, subsampled for clarity.

    Parameters
    ----------
    skip : int
        Plot every *skip*-th cell (default 200 for ~140 barbs on 28k cells).
    length : float
        Barb length in points.
    """
    if 'uZonal' not in data:
        return
    idx = np.arange(0, data['nCells'], skip)
    x = data['xCell'][idx]
    y = data['yCell'][idx]
    u = data['uZonal'][time_idx, idx, level]
    v = data['uMeridional'][time_idx, idx, level]
    ax.barbs(x, y, u, v, length=length, linewidth=0.4,
             barbcolor='0.3', flagcolor='0.3', zorder=3)


def find_updraft_y(data, time_idx):
    """Find y-coordinate of the maximum updraft at mid-level."""
    nLev = data['nVertLevels']
    if 'w' not in data:
        return (data['yCell'].min() + data['yCell'].max()) / 2
    w_mid = data['w'][time_idx, :, nLev // 4]
    return data['yCell'][np.argmax(w_mid)]


# ---------------------------------------------------------------------------
# Plot 1: Vertical cross-section (4-panel)
# ---------------------------------------------------------------------------

def plot_vertical_cross_section(data, time_idx, output_file, y_slice=None,
                                 dt_seconds=60.0, w_threshold=0.3,
                                 w_ref=10.0, z_min_m=1000.0, z_max_m=12000.0,
                                 source_rate_ppbv=0.1):
    """4-panel vertical cross-section: NO, NO2, O3, NO2/(NO+NO2)."""
    if y_slice is None:
        y_slice = find_updraft_y(data, time_idx)

    selected = select_cell_row(data, y_slice)
    if len(selected) < 3:
        print(f"  Not enough cells near y={y_slice:.1f} km")
        return

    x_s = data['xCell'][selected]
    nLev = data['nVertLevels']
    z = np.array([get_level_height(data, k) for k in range(nLev)])
    X, Z = np.meshgrid(x_s, z)

    t_min = data['time_minutes'][time_idx]

    # Compute wind vectors for the cross-section (u_zonal, w)
    quiver_kw = None
    if 'w' in data and 'uZonal' in data:
        u_slice = data['uZonal'][time_idx, selected, :]   # (nSel, nLev)
        w_slice = data['w'][time_idx, selected, :]
        # Subsample for clarity (~15 x 12 arrows)
        x_skip = max(1, len(selected) // 15)
        z_skip = max(1, nLev // 12)
        xi = np.arange(0, len(selected), x_skip)
        zi = np.arange(0, nLev, z_skip)
        Xq = X[np.ix_(zi, xi)]
        Zq = Z[np.ix_(zi, xi)]
        Uq = u_slice[np.ix_(xi, zi)].T
        Wq = w_slice[np.ix_(xi, zi)].T
        # Scale w to match visual aspect ratio (both axes in km)
        z_range = z.max() - z.min()
        x_range = x_s.max() - x_s.min()
        quiver_kw = dict(X=Xq, Z=Zq, U=Uq, W=Wq * (x_range / z_range))

    def overlay_wind(ax):
        if quiver_kw is not None:
            ax.quiver(quiver_kw['X'], quiver_kw['Z'],
                      quiver_kw['U'], quiver_kw['W'],
                      color='0.2', alpha=0.5, scale=600,
                      width=0.0025, headwidth=3.5, headlength=4, zorder=3)

    # Compute source field on the cross-section
    z_center_m = z * 1000  # km -> m
    w_xsec = data['w'][time_idx, selected, :] if 'w' in data else None

    # Compute all slices first for shared scaling
    o3_slice = to_ppbv(data['qO3'][time_idx, selected, :], M_O3)
    no_slice = to_ppbv(data['qNO'][time_idx, selected, :], M_NO)
    no2_slice = to_ppbv(data['qNO2'][time_idx, selected, :], M_NO2)

    # Use a shared NOx scale so NO and NO2 are visually comparable
    nox_vmax = max(no_slice.max(), no2_slice.max(), 1.0)
    nox_levels = smart_levels(0, nox_vmax)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # (a) O3 in ppbv — anchor at field min/max so the LNOx-driven loss
    # near background is visible. With background ~50 ppbv and a few-ppbv
    # loss in the source region, anchoring at 0 hides all the structure.
    ax = axes[0, 0]
    o3_levels = smart_levels(o3_slice.min(), o3_slice.max())
    cf = ax.contourf(X, Z, o3_slice.T, levels=o3_levels, cmap='ncar_sunset')
    rasterize_contours(cf)
    add_colorbar(cf, ax, label='ppbv')
    overlay_wind(ax)
    ax.set_title(style.format_title('(a) O3'))
    ax.set_ylabel('Height (km)')

    # (b) NO in ppbv — same scale as NO2
    ax = axes[0, 1]
    cf = ax.contourf(X, Z, no_slice.T, levels=nox_levels, cmap='ncar_sunset',
                     extend='max')
    rasterize_contours(cf)
    add_colorbar(cf, ax, label='ppbv')
    overlay_wind(ax)
    ax.set_title('(b) NO')

    # (c) NO2 in ppbv — same scale as NO
    ax = axes[1, 0]
    cf = ax.contourf(X, Z, no2_slice.T, levels=nox_levels, cmap='ncar_sunset',
                     extend='max')
    rasterize_contours(cf)
    add_colorbar(cf, ax, label='ppbv')
    overlay_wind(ax)
    ax.set_title(style.format_title('(c) NO2'))
    ax.set_xlabel('X (km)')
    ax.set_ylabel('Height (km)')

    # (d) NO2/(NO+NO2) ratio
    ax = axes[1, 1]
    nox_slice = no_slice + no2_slice
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = np.where(nox_slice > 0.1, no2_slice / nox_slice, np.nan)
    cf = ax.contourf(X, Z, ratio.T, levels=np.linspace(0, 1, 21),
                     cmap='coolwarm')
    rasterize_contours(cf)
    cb = add_colorbar(cf, ax, label='fraction')
    cb.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.1f}'))
    overlay_wind(ax)
    ax.set_title(style.format_title('(d) NO2 / NOx'))
    ax.set_xlabel('X (km)')

    plt.suptitle(style.format_title(
        f'Lightning NOx Cross-Section at y = {y_slice:.0f} km, t = {t_min:.0f} min'),
        fontsize=style.SUPTITLE_SIZE)
    plt.tight_layout()
    save_figure(output_file)
    plt.close()


# ---------------------------------------------------------------------------
# Plot 2: Time evolution of peak and mean
# ---------------------------------------------------------------------------

def plot_time_evolution(data, output_file, dt_seconds=60.0):
    """3-panel time series: peak and domain-mean of NO, NO2, O3."""
    t_min = data['time_minutes']

    no_ppbv = to_ppbv(data['qNO'], M_NO)      # (Time, nCells, nLev)
    no2_ppbv = to_ppbv(data['qNO2'], M_NO2)
    o3_ppbv = to_ppbv(data['qO3'], M_O3)

    no_peak = np.array([no_ppbv[t].max() for t in range(data['nTimes'])])
    no2_peak = np.array([no2_ppbv[t].max() for t in range(data['nTimes'])])
    o3_peak = np.array([o3_ppbv[t].max() for t in range(data['nTimes'])])
    no_mean = np.array([no_ppbv[t].mean() for t in range(data['nTimes'])])
    no2_mean = np.array([no2_ppbv[t].mean() for t in range(data['nTimes'])])
    o3_mean = np.array([o3_ppbv[t].mean() for t in range(data['nTimes'])])

    c_no = style.species_color('qNO')
    c_no2 = style.species_color('qNO2')
    c_o3 = style.species_color('qO3')

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(17, 5))

    # Peak values (NOx)
    ax1.plot(t_min, no_peak, color=c_no, lw=2, label='NO')
    ax1.plot(t_min, no2_peak, color=c_no2, lw=2, label=style.species_label('NO2'))
    ax1.plot(t_min, no_peak + no2_peak, color=style.NCAR_COLORS['gray'],
             lw=2, ls='--', label=style.species_label('NOx'))
    ax1.set_xlabel('Time (min)')
    ax1.set_ylabel('Mixing ratio (ppbv)')
    ax1.set_title(style.format_title('Domain peak (NOx)'))
    ax1.legend()

    # Domain mean (NOx)
    ax2.plot(t_min, no_mean, color=c_no, lw=2, label='NO')
    ax2.plot(t_min, no2_mean, color=c_no2, lw=2, label=style.species_label('NO2'))
    ax2.plot(t_min, no_mean + no2_mean, color=style.NCAR_COLORS['gray'],
             lw=2, ls='--', label=style.species_label('NOx'))
    ax2.set_xlabel('Time (min)')
    ax2.set_ylabel('Mixing ratio (ppbv)')
    ax2.set_title(style.format_title('Domain mean (NOx)'))
    ax2.legend()

    # O3: show peak, mean, and min (min shows titration)
    o3_min = np.array([o3_ppbv[t].min() for t in range(data['nTimes'])])
    ax3.plot(t_min, o3_peak, color=c_o3, lw=2, label=style.species_label('O3') + ' peak')
    ax3.plot(t_min, o3_mean, color=c_o3, lw=2, ls='--', label=style.species_label('O3') + ' mean')
    ax3.plot(t_min, o3_min, color=c_o3, lw=2, ls=':', label=style.species_label('O3') + ' min')
    ax3.set_xlabel('Time (min)')
    ax3.set_ylabel('Mixing ratio (ppbv)')
    ax3.set_title(style.format_title('O3'))
    ax3.set_ylim(bottom=0)
    ax3.yaxis.get_major_formatter().set_useOffset(False)
    ax3.legend()

    plt.suptitle(style.format_title('LNOx-O3 Time Evolution'),
                 fontsize=style.SUPTITLE_SIZE)
    plt.tight_layout()
    save_figure(output_file)
    plt.close()


# ---------------------------------------------------------------------------
# Plot 3: Horizontal slices at multiple times
# ---------------------------------------------------------------------------

def plot_horizontal_evolution(data, level, output_file, n_times=6,
                               dt_seconds=60.0, wind=False, wind_skip=300):
    """6-panel horizontal slices of NO at selected times."""
    x, y = data['xCell'], data['yCell']
    tri = Triangulation(x, y)

    nT = data['nTimes']
    if nT <= n_times:
        tidx = list(range(nT))
    else:
        tidx = [int(i * (nT - 1) / (n_times - 1)) for i in range(n_times)]

    # Global color scale: use final-time max across all panels
    no_all = to_ppbv(data['qNO'][:], M_NO)
    vmax = max(no_all[tidx[-1], :, level].max(), 1.0)
    shared_levels = smart_levels(0, vmax)

    n_cols = min(3, len(tidx))
    n_rows = (len(tidx) + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
    axes = np.atleast_2d(axes)

    for idx, t in enumerate(tidx):
        row, col = divmod(idx, n_cols)
        ax = axes[row, col]
        vals = no_all[t, :, level]
        cf = ax.tricontourf(tri, vals, levels=shared_levels, cmap='ncar_sunset',
                            vmin=0, vmax=vmax, extend='max')
        rasterize_contours(cf)
        ax.set_xlabel('X (km)')
        ax.set_ylabel('Y (km)')
        ax.set_aspect('equal')
        if wind:
            add_wind_barbs(ax, data, t, level, skip=wind_skip)
        t_min = data['time_minutes'][t]
        ax.set_title(f't = {t_min:.0f} min')
        add_colorbar(cf, ax, label='ppbv')

    # Hide unused
    for idx in range(len(tidx), n_rows * n_cols):
        row, col = divmod(idx, n_cols)
        axes[row, col].set_visible(False)

    plt.suptitle(style.format_title(
        f'NO at {level_label(data, level)}'),
        fontsize=style.SUPTITLE_SIZE)
    plt.tight_layout()
    save_figure(output_file)
    plt.close()


# ---------------------------------------------------------------------------
# Plot 4: NO vs NO2 side-by-side horizontal slices
# ---------------------------------------------------------------------------

def plot_species_comparison(data, level, time_idx, output_file,
                             dt_seconds=60.0, wind=False,
                             w_threshold=0.3, w_ref=10.0,
                             z_min_m=1000.0, z_max_m=12000.0,
                             source_rate_ppbv=0.1):
    """3-panel: NO, NO2, and NO source at a single time and level."""
    x, y = data['xCell'], data['yCell']
    tri = Triangulation(x, y)
    t_min = data['time_minutes'][time_idx]

    no_ppbv = to_ppbv(data['qNO'][time_idx, :, level], M_NO)
    no2_ppbv = to_ppbv(data['qNO2'][time_idx, :, level], M_NO2)

    # Shared NOx scale
    nox_vmax = max(no_ppbv.max(), no2_ppbv.max(), 1.0)
    nox_levels = smart_levels(0, nox_vmax)

    fig, axes = plt.subplots(1, 3, figsize=(17, 5))

    # NO
    ax = axes[0]
    cf = ax.tricontourf(tri, no_ppbv, levels=nox_levels, cmap='ncar_sunset',
                        extend='max')
    rasterize_contours(cf)
    add_colorbar(cf, ax, label='ppbv')
    if wind:
        add_wind_barbs(ax, data, time_idx, level)
    ax.set_title('NO')
    ax.set_xlabel('X (km)')
    ax.set_ylabel('Y (km)')
    ax.set_aspect('equal')

    # NO2
    ax = axes[1]
    cf = ax.tricontourf(tri, no2_ppbv, levels=nox_levels, cmap='ncar_sunset',
                        extend='max')
    rasterize_contours(cf)
    add_colorbar(cf, ax, label='ppbv')
    if wind:
        add_wind_barbs(ax, data, time_idx, level)
    ax.set_title(style.species_label('NO2'))
    ax.set_xlabel('X (km)')
    ax.set_aspect('equal')

    # NO source
    ax = axes[2]
    if 'w' in data and data.get('zgrid') is not None:
        w_vals = data['w'][time_idx, :, level]
        z_center_m = 0.5 * (data['zgrid'][:, level] + data['zgrid'][:, level + 1]) * 1000
        active = ((w_vals > w_threshold) &
                  (z_center_m >= z_min_m) &
                  (z_center_m <= z_max_m))
        source = np.where(active,
                          source_rate_ppbv * np.maximum(0, w_vals - w_threshold) / w_ref,
                          0.0)
        src_max = max(source.max(), 1e-6)
        cf = ax.tricontourf(tri, source, levels=50,
                            cmap='ncar_sunset', vmin=0, vmax=src_max)
        rasterize_contours(cf)
        add_colorbar(cf, ax, label=r'ppbv s$^{-1}$')
    if wind:
        add_wind_barbs(ax, data, time_idx, level)
    ax.set_title('NO source')
    ax.set_xlabel('X (km)')
    ax.set_aspect('equal')

    plt.suptitle(style.format_title(
        f'NO and NO2 at {level_label(data, level)}, t = {t_min:.0f} min'),
        fontsize=style.SUPTITLE_SIZE)
    plt.tight_layout()
    save_figure(output_file)
    plt.close()


# ---------------------------------------------------------------------------
# Plot 5: Vertical profiles at updraft location
# ---------------------------------------------------------------------------

def plot_updraft_profiles(data, time_idx, output_file, dt_seconds=60.0):
    """Vertical profiles of NO, NO2, ratio, and w at the updraft core cell."""
    nLev = data['nVertLevels']
    z = np.array([get_level_height(data, k) for k in range(nLev)])

    # Find the cell nearest the updraft y-slice (consistent with cross-sections)
    y_slice = find_updraft_y(data, time_idx)
    # Among cells near that y, pick the one with strongest mid-level w
    dy = np.abs(data['yCell'] - y_slice)
    near = dy < 2.0  # within 2 km
    if 'w' in data and near.any():
        w_mid = data['w'][time_idx, :, nLev // 4]
        w_near = np.where(near, w_mid, -999)
        iCell = np.argmax(w_near)
    else:
        iCell = data['nCells'] // 2

    t_min = data['time_minutes'][time_idx]

    no_prof = to_ppbv(data['qNO'][time_idx, iCell, :], M_NO)
    no2_prof = to_ppbv(data['qNO2'][time_idx, iCell, :], M_NO2)
    o3_prof = to_ppbv(data['qO3'][time_idx, iCell, :], M_O3)
    nox_prof = no_prof + no2_prof

    c_no = style.species_color('qNO')
    c_no2 = style.species_color('qNO2')
    c_o3 = style.species_color('qO3')

    fig, axes = plt.subplots(1, 4, figsize=(18, 6))

    # NOx concentrations
    ax = axes[0]
    ax.plot(no_prof, z, color=c_no, lw=2, label='NO')
    ax.plot(no2_prof, z, color=c_no2, lw=2, label=style.species_label('NO2'))
    ax.plot(nox_prof, z, color=style.NCAR_COLORS['gray'], lw=2, ls='--',
            label=style.species_label('NOx'))
    ax.set_xlabel('Mixing ratio (ppbv)')
    ax.set_ylabel('Height (km)')
    ax.set_title(style.format_title('NOx profiles'))
    ax.legend()

    # O3 concentration
    ax = axes[1]
    ax.plot(o3_prof, z, color=c_o3, lw=2, label=style.species_label('O3'))
    ax.set_xlabel('Mixing ratio (ppbv)')
    ax.set_ylabel('Height (km)')
    ax.set_title(style.format_title('O3 profile'))
    ax.legend()

    # NO2/NOx ratio
    ax = axes[2]
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = np.where(nox_prof > 0.01, no2_prof / nox_prof, np.nan)
    ax.plot(ratio, z, color='black', lw=2)
    ax.set_xlabel(style.format_title('NO2 / NOx'))
    ax.set_ylabel('Height (km)')
    ax.set_title(style.format_title('NO2/NOx partitioning'))
    ax.set_xlim(-0.05, 1.05)
    ax.axvline(0.5, color='gray', ls=':', alpha=0.5)

    # Vertical velocity
    ax = axes[3]
    if 'w' in data:
        w_prof = data['w'][time_idx, iCell, :]
        ax.plot(w_prof, z, color='black', lw=2)
        ax.axvline(0, color='gray', ls=':', alpha=0.5)
    ax.set_xlabel('w (m/s)')
    ax.set_ylabel('Height (km)')
    ax.set_title('Vertical velocity')

    cell_x = data['xCell'][iCell]
    cell_y = data['yCell'][iCell]
    plt.suptitle(style.format_title(
        f'Updraft Core Profiles (x={cell_x:.0f}, y={cell_y:.0f} km, '
        f't = {t_min:.0f} min)'),
        fontsize=style.SUPTITLE_SIZE)
    plt.tight_layout()
    save_figure(output_file)
    plt.close()


# ---------------------------------------------------------------------------
# Plot 6: Lightning source vertical profiles at multiple times
# ---------------------------------------------------------------------------

def plot_source_profiles(data, output_file, n_times=8, dt_seconds=60.0,
                          w_threshold=0.3, w_ref=10.0,
                          z_min_m=1000.0, z_max_m=12000.0,
                          source_rate_ppbv=0.1):
    """Vertical profiles of the lightning NO source, averaged over the
    convective core, at multiple times on a single set of axes.

    The source mask is reconstructed from w and height using the same
    thresholds as the Fortran code.  For each time, the profile shows
    the mean source rate over activated cells (left) and the number of
    activated cells per level (right).
    """
    nLev = data['nVertLevels']
    nT = data['nTimes']
    z_km = np.array([get_level_height(data, k) for k in range(nLev)])

    # Cell-center heights in metres (static)
    if data.get('zgrid') is not None:
        z_center_m = 0.5 * (data['zgrid'][:, :nLev] + data['zgrid'][:, 1:nLev+1]) * 1000
    else:
        z_center_m = np.tile(z_km * 1000, (data['nCells'], 1))

    # Select times to plot
    if nT <= n_times:
        tidx = list(range(1, nT))        # skip t=0 (no updraft)
    else:
        tidx = [max(1, int(i * (nT - 1) / (n_times - 1)))
                for i in range(n_times)]
        tidx = sorted(set(tidx))          # deduplicate

    # Color map: time progression
    cmap = plt.cm.magma_r
    norm = plt.Normalize(vmin=data['time_minutes'][0],
                         vmax=data['time_minutes'][-1])

    fig, ax = plt.subplots(figsize=(7, 7))

    for t in tidx:
        w_t = data['w'][t]                # (nCells, nVertLevels)
        t_min = data['time_minutes'][t]
        color = cmap(norm(t_min))

        # Convective core: cells where w exceeds threshold at any level
        core_mask = (w_t > w_threshold).any(axis=1)   # (nCells,)
        n_core = core_mask.sum()
        if n_core == 0:
            continue

        # Source rate profile averaged over the convective core
        source_prof = np.zeros(nLev)
        for k in range(nLev):
            activated = (core_mask &
                         (w_t[:, k] > w_threshold) &
                         (z_center_m[:, k] >= z_min_m) &
                         (z_center_m[:, k] <= z_max_m))
            if activated.sum() > 0:
                w_excess = np.maximum(0, w_t[activated, k] - w_threshold)
                source_prof[k] = (source_rate_ppbv * w_excess.sum() /
                                  (w_ref * n_core))

        ax.plot(source_prof, z_km, color=color, lw=2,
                label=f'{t_min:.0f} min')

    ax.set_xlabel(style.format_title('NO source rate (ppbv s$^{-1}$)'))
    ax.set_ylabel('Height (km)')
    ax.legend(fontsize=style.FONT_SIZES_DEFAULT.legend_small,
              loc='upper right')

    plt.suptitle(style.format_title(
        f'Lightning NO Source (w > {w_threshold} m/s, '
        f'{z_min_m/1000:.0f}--{z_max_m/1000:.0f} km)'),
        fontsize=style.SUPTITLE_SIZE)
    plt.tight_layout()
    save_figure(output_file)
    plt.close()


# ---------------------------------------------------------------------------
# Plot 7: j_NO2 photolysis rate
# ---------------------------------------------------------------------------

def plot_photolysis(data, output_file, dt_seconds=60.0):
    """Vertical cross-section of j_NO2 at the final time step."""
    if 'j_no2' not in data:
        print("  j_no2 not in output — skipping photolysis plot")
        return

    j = data['j_no2']  # (Time, nCells, nVertLevels)

    # Vertical cross-section at final time
    time_idx = data['nTimes'] - 1
    y_slice = find_updraft_y(data, time_idx)
    selected = select_cell_row(data, y_slice)
    if len(selected) < 3:
        print("  too few cells in cross-section row — skipping photolysis plot")
        return

    x_s = data['xCell'][selected]
    nLev = data['nVertLevels']
    z = np.array([get_level_height(data, k) for k in range(nLev)])
    X, Z = np.meshgrid(x_s, z)
    j_slice = j[time_idx, selected, :] * 1000  # -> 1e-3 s-1
    j_levels = smart_levels(0, max(j_slice.max(), 0.001))

    fig, ax = plt.subplots(1, 1, figsize=(8, 5))
    cf = ax.contourf(X, Z, j_slice.T, levels=j_levels, cmap='magma')
    rasterize_contours(cf)
    add_colorbar(cf, ax, label=r'$\times 10^{-3}$ s$^{-1}$')
    ax.set_xlabel('X (km)')
    ax.set_ylabel('Height (km)')
    t_label = data['time_minutes'][time_idx]
    ax.set_title(style.format_title(
        f'j$_{{NO_2}}$ (TUV-x) at y = {y_slice:.0f} km, t = {t_label:.0f} min'))

    plt.tight_layout()
    save_figure(output_file)
    plt.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Visualize CheMPAS-A LNOx-O3 output')
    parser.add_argument('-i', '--input', default='output.nc',
                        help='MPAS output file')
    parser.add_argument('-o', '--output', default='lightning_nox',
                        help='Base output name (default: lightning_nox)')
    parser.add_argument('-l', '--level', type=int, default=None,
                        help='Vertical level index (default: auto ~5 km)')
    parser.add_argument('-t', '--time', type=int, default=-1,
                        help='Time index (default: -1 = last)')
    parser.add_argument('--every-min', type=float, default=None,
                        help='Generate per-snapshot plots (vertical, comparison, '
                             'profiles) at this cadence in simulation minutes. '
                             'Filenames get a _tNNNmin suffix. '
                             'Default: single snapshot at --time.')
    parser.add_argument('--dt', type=float, default=30.0,
                        help='Output interval in seconds (default: 30)')
    parser.add_argument('--y-slice', type=float, default=None,
                        help='Y for cross-section (default: max updraft)')
    parser.add_argument('--show', action='store_true',
                        help='Display plots interactively')

    parser.add_argument('--all', action='store_true', help='All plot types')
    parser.add_argument('--vertical', action='store_true',
                        help='Vertical cross-section (w, NO, NO2, ratio)')
    parser.add_argument('--evolution', action='store_true',
                        help='Time evolution of peak/mean')
    parser.add_argument('--horizontal', action='store_true',
                        help='Horizontal NO slices at multiple times')
    parser.add_argument('--comparison', action='store_true',
                        help='NO vs NO2 side-by-side at one time')
    parser.add_argument('--profiles', action='store_true',
                        help='Vertical profiles at updraft core')
    parser.add_argument('--source', action='store_true',
                        help='Lightning source profiles at multiple times')
    parser.add_argument('--photolysis', action='store_true',
                        help='j_NO2 photolysis rate time series and cross-section')
    parser.add_argument('--wind', action='store_true',
                        help='Overlay wind barbs on horizontal plots')
    parser.add_argument('--w-threshold', type=float, default=0.3,
                        help='w threshold for source mask (default: 0.3 m/s)')
    parser.add_argument('--w-ref', type=float, default=10.0,
                        help='Reference w for source scaling (default: 10.0 m/s)')
    parser.add_argument('--z-min', type=float, default=1000.0,
                        help='Min altitude for source (default: 1000 m)')
    parser.add_argument('--z-max', type=float, default=12000.0,
                        help='Max altitude for source (default: 12000 m)')
    parser.add_argument('--source-rate', type=float, default=0.1,
                        help='Source rate in ppbv/s (default: 0.1)')

    args = parser.parse_args()

    style.setup()

    print(f"Loading {args.input}...")
    data = load_data(args.input)

    time_idx = args.time if args.time >= 0 else data['nTimes'] - 1

    # Auto-select level near 5 km if not specified
    if args.level is not None:
        level = args.level
    else:
        nLev = data['nVertLevels']
        heights = [get_level_height(data, k) for k in range(nLev)]
        level = int(np.argmin([abs(h - 5.0) for h in heights]))

    print(f"  {data['nCells']} cells, {data['nVertLevels']} levels, "
          f"{data['nTimes']} times")
    print(f"  level={level} ({level_label(data, level)}), time={time_idx}")

    no_max = to_ppbv(data['qNO'][time_idx].max(), M_NO)
    no2_max = to_ppbv(data['qNO2'][time_idx].max(), M_NO2)
    o3_max = to_ppbv(data['qO3'][time_idx].max(), M_O3)
    o3_mean = to_ppbv(data['qO3'][time_idx].mean(), M_O3)
    print(f"  peak NO = {no_max:.2f} ppbv, peak NO2 = {no2_max:.2f} ppbv")
    print(f"  peak O3 = {o3_max:.2f} ppbv, mean O3 = {o3_mean:.2f} ppbv")

    base = args.output.removesuffix('.png').removesuffix('.pdf')

    if not any([args.all, args.vertical, args.evolution, args.horizontal,
                args.comparison, args.profiles, args.source, args.photolysis]):
        args.all = True

    # Snapshot-style plots (vertical, comparison, profiles) repeat per index.
    # Aggregate-style plots (evolution, horizontal, source, photolysis) run once.
    if args.every_min is not None and args.every_min > 0:
        tm = data['time_minutes']
        # Targets: multiples of every_min that fall inside the available
        # snapshot range. For each, pick the first snapshot at-or-after the
        # target so that labels approach round-number ticks even when the
        # output cadence doesn't divide every_min cleanly.
        first_target = np.ceil(tm[0] / args.every_min) * args.every_min
        targets = np.arange(first_target, tm[-1] + 1e-6, args.every_min)
        snapshot_indices = []
        for t in targets:
            after = np.where(tm >= t)[0]
            if len(after) > 0:
                snapshot_indices.append(int(after[0]))
        # Deduplicate while preserving order
        seen = set()
        snapshot_indices = [i for i in snapshot_indices
                            if not (i in seen or seen.add(i))]
        print(f"  --every-min={args.every_min}: {len(snapshot_indices)} snapshots "
              f"at t = {[round(tm[i], 1) for i in snapshot_indices]} min")
    else:
        snapshot_indices = [time_idx]

    def snap_suffix(idx):
        if args.every_min is None:
            return ''
        return f'_t{int(round(data["time_minutes"][idx])):03d}min'

    if args.vertical or args.all:
        print("Generating vertical cross-section...")
        for idx in snapshot_indices:
            plot_vertical_cross_section(data, idx,
                                        f'{base}_vertical{snap_suffix(idx)}.png',
                                        y_slice=args.y_slice, dt_seconds=args.dt,
                                        w_threshold=args.w_threshold,
                                        w_ref=args.w_ref,
                                        z_min_m=args.z_min, z_max_m=args.z_max,
                                        source_rate_ppbv=args.source_rate)

    if args.evolution or args.all:
        print("Generating time evolution...")
        plot_time_evolution(data, f'{base}_evolution.png', dt_seconds=args.dt)

    if args.horizontal or args.all:
        print("Generating horizontal slices...")
        plot_horizontal_evolution(data, level, f'{base}_horizontal.png',
                                  dt_seconds=args.dt, wind=args.wind)

    if args.comparison or args.all:
        print("Generating species comparison...")
        for idx in snapshot_indices:
            plot_species_comparison(data, level, idx,
                                    f'{base}_comparison{snap_suffix(idx)}.png',
                                    dt_seconds=args.dt,
                                    wind=args.wind, w_threshold=args.w_threshold,
                                    w_ref=args.w_ref,
                                    z_min_m=args.z_min, z_max_m=args.z_max,
                                    source_rate_ppbv=args.source_rate)

    if args.profiles or args.all:
        print("Generating updraft profiles...")
        for idx in snapshot_indices:
            plot_updraft_profiles(data, idx,
                                  f'{base}_profiles{snap_suffix(idx)}.png',
                                  dt_seconds=args.dt)

    if args.source or args.all:
        print("Generating source profiles...")
        plot_source_profiles(data, f'{base}_source.png', dt_seconds=args.dt,
                             w_threshold=args.w_threshold,
                             w_ref=args.w_ref,
                             z_min_m=args.z_min, z_max_m=args.z_max,
                             source_rate_ppbv=args.source_rate)

    if args.photolysis or args.all:
        print("Generating photolysis plot...")
        plot_photolysis(data, f'{base}_photolysis.png', dt_seconds=args.dt)

    if args.show:
        plt.show()

    print("Done.")


if __name__ == '__main__':
    main()
