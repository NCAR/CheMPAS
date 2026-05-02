#!/usr/bin/env python3
"""Quick-look plots for the global Chapman+NOx test run.

Produces four figures, saved as PNG and PDF, using the NCAR brand
styling from scripts/style.py:

  - jNO2_terminator   : jNO2 maps at t=0, 6, 12, 18 UTC (terminator sweep)
  - tracers_evolution : O3 at ~36 km and NO2 at ~25 km, t=12 vs t=24 h
  - nox_partition     : NO2 / (NO + NO2) molar fraction at t=12 and t=24 h
  - o3_profile        : global-mean O3 profile vs z and zonal-mean
                        ΔO3 over the 24-hour window (symlog so both the
                        upper-stratosphere production and lower-altitude
                        NOx-driven loss are visible)

Map fields are rendered with a triangulated mesh (matplotlib.tri) and
antimeridian-spanning triangles masked, so the limb is clean.

Usage:
    python scripts/plot_chapman_nox_global.py -i output.nc -o ./plots
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.colors import SymLogNorm
from netCDF4 import Dataset
import cartopy.crs as ccrs

sys.path.insert(0, str(Path(__file__).resolve().parent))
import style

LEVEL_NO2 = 17  # ~25 km on x1.40962 vertical grid (NO2 seed peak)
LEVEL_O3 = 22   # ~36 km on x1.40962 vertical grid (O3 chemistry active)

# Molar masses in kg/mol; matches scripts/init_chapman_nox.py and the
# convention in scripts/plot_lnox_o3.py.
M_AIR = 28.97e-3
M_O3 = 48.00e-3
M_NO = 30.01e-3
M_NO2 = 46.00e-3


def to_ppmv(q_kgkg, M_species):
    """Mass mixing ratio (kg/kg) -> volume/molar mixing ratio in ppmv."""
    return q_kgkg * (M_AIR / M_species) * 1.0e6


def to_ppbv(q_kgkg, M_species):
    """Mass mixing ratio (kg/kg) -> volume/molar mixing ratio in ppbv."""
    return q_kgkg * (M_AIR / M_species) * 1.0e9


def xtime_str(ds, t):
    return b"".join(ds.variables["xtime"][t, :]).decode().strip()


def hh_mm(ds, t):
    s = xtime_str(ds, t).split("_")[-1]
    return s[:5]


def percentile_range(arr, lo=2.0, hi=98.0):
    """Return (vmin, vmax) at the given percentiles of the masked array."""
    a = np.asarray(arr).ravel()
    a = a[np.isfinite(a)]
    return float(np.percentile(a, lo)), float(np.percentile(a, hi))


def save_figure(out_dir, stem, dpi=300):
    png = out_dir / f"{stem}.png"
    pdf = out_dir / f"{stem}.pdf"
    plt.savefig(png, dpi=dpi, bbox_inches="tight")
    plt.savefig(pdf, bbox_inches="tight")
    print(f"  wrote {png} and {pdf}")


def make_global_triangulation(lon, lat, max_lon_span=180.0):
    """Triangulate (lon, lat) and mask triangles spanning the antimeridian."""
    triang = mtri.Triangulation(lon, lat)
    lon_at_tri = lon[triang.triangles]
    span = lon_at_tri.max(axis=1) - lon_at_tri.min(axis=1)
    triang.set_mask(span > max_lon_span)
    return triang


def map_global(ax, triang, vals, title, cbar_label, cmap, vmin, vmax,
               norm=None):
    pc = ax.tripcolor(
        triang, vals, cmap=cmap,
        vmin=vmin, vmax=vmax, norm=norm,
        shading="gouraud",
        transform=ccrs.PlateCarree(),
        rasterized=True,
    )
    ax.set_global()
    ax.coastlines(linewidth=0.4, color=style.NCAR_COLORS["gray"])
    ax.gridlines(draw_labels=False, linewidth=0.3,
                 color=style.NCAR_COLORS["gray"], alpha=0.4)
    ax.set_title(style.format_title(title))
    cb = plt.colorbar(pc, ax=ax, shrink=0.7, pad=0.03)
    cb.set_label(cbar_label)
    cb.solids.set_rasterized(True)
    return pc


def fig_jno2_terminator(ds, triang, out_dir):
    # Skip t=0 (TUV-x has not run yet at the initial output frame; field is
    # all zero). Sample the diurnal cycle every 6 h post-first-fire so the
    # subsolar point sweeps 135E -> 45E -> 45W -> 135W.
    times = [3, 9, 15, 21]
    fig, axes = plt.subplots(
        2, 2, figsize=(13, 7),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )
    j = ds.variables["j_jNO2"]
    # Common range over the four sampled times, clipped to suppress
    # the tiny minority of cells right at the subsolar point.
    sample = np.stack([j[t, :, LEVEL_NO2] for t in times])
    vmin, vmax = percentile_range(sample[sample > 0], lo=2.0, hi=98.0)
    for ax, t in zip(axes.flat, times):
        map_global(
            ax, triang, j[t, :, LEVEL_NO2],
            f"j(NO2) @ ~25 km, {hh_mm(ds, t)} UTC",
            r"j(NO$_2$) [s$^{-1}$]",
            cmap="ncar_sunset", vmin=0.0, vmax=vmax,
        )
    fig.suptitle(style.format_title(
        "Chapman+NOx global: NO2 photolysis rate, terminator sweep"))
    fig.tight_layout()
    save_figure(out_dir, "jNO2_terminator")
    plt.close(fig)


def fig_tracers_evolution(ds, triang, out_dir):
    fig, axes = plt.subplots(
        2, 2, figsize=(13, 7),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )
    qo3 = to_ppmv(ds.variables["qO3"][:, :, LEVEL_O3], M_O3)
    qno2 = to_ppbv(ds.variables["qNO2"][:, :, LEVEL_NO2], M_NO2)

    # Use 2-98 percentile bounds across both shown frames so the bulk
    # variability fills the colormap instead of a few outliers.
    o3_min, o3_max = percentile_range(qo3[[12, 24]])
    no2_min, no2_max = percentile_range(qno2[[12, 24]])

    o3_label = f"{style.species_label('qO3')} [ppm]"
    no2_label = f"{style.species_label('qNO2')} [ppb]"

    map_global(axes[0, 0], triang, qo3[12],
               f"O3 @ ~36 km, {hh_mm(ds, 12)} UTC",
               o3_label, cmap="ncar_sunset", vmin=o3_min, vmax=o3_max)
    map_global(axes[0, 1], triang, qo3[24],
               f"O3 @ ~36 km, {hh_mm(ds, 24)} UTC (+24 h)",
               o3_label, cmap="ncar_sunset", vmin=o3_min, vmax=o3_max)
    map_global(axes[1, 0], triang, qno2[12],
               f"NO2 @ ~25 km, {hh_mm(ds, 12)} UTC",
               no2_label, cmap="ncar_sunset", vmin=no2_min, vmax=no2_max)
    map_global(axes[1, 1], triang, qno2[24],
               f"NO2 @ ~25 km, {hh_mm(ds, 24)} UTC (+24 h)",
               no2_label, cmap="ncar_sunset", vmin=no2_min, vmax=no2_max)
    fig.suptitle(style.format_title(
        "Chapman+NOx global: O3 (~36 km) and NO2 (~25 km), t=12 vs t=24 h"))
    fig.tight_layout()
    save_figure(out_dir, "tracers_evolution")
    plt.close(fig)


def fig_nox_partition(ds, triang, out_dir):
    qno = ds.variables["qNO"][:, :, LEVEL_NO2] / M_NO
    qno2 = ds.variables["qNO2"][:, :, LEVEL_NO2] / M_NO2
    f_no2 = qno2 / np.maximum(qno + qno2, 1e-30)

    # The mechanism has no NOx removal, so all cells trend NO2-rich
    # within hours; the realised range is ~0.72-1.0 even though the
    # quantity is bounded by [0, 1]. Use percentile clamping so the
    # day/night contrast within the realised range fills the cmap.
    vmin, vmax = percentile_range(f_no2[[12, 24]])

    fig, axes = plt.subplots(
        1, 2, figsize=(14, 4.6),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )
    cbar_label = r"NO$_2$ / (NO + NO$_2$)"
    map_global(axes[0], triang, f_no2[12],
               f"NOx partition @ ~25 km, {hh_mm(ds, 12)} UTC",
               cbar_label, cmap="ncar_sunset", vmin=vmin, vmax=vmax)
    map_global(axes[1], triang, f_no2[24],
               f"NOx partition @ ~25 km, {hh_mm(ds, 24)} UTC",
               cbar_label, cmap="ncar_sunset", vmin=vmin, vmax=vmax)
    fig.suptitle(style.format_title(
        "Chapman+NOx global: NOx partitioning shifts toward NO2 in daylight"))
    fig.tight_layout()
    save_figure(out_dir, "nox_partition")
    plt.close(fig)


def fig_o3_profile(ds, lat, out_dir):
    qo3 = to_ppmv(ds.variables["qO3"][:], M_O3)
    zg = ds.variables["zgrid"][:]
    zc_km = 0.5 * (zg[:, :-1] + zg[:, 1:]) * 1e-3
    z_mean = zc_km.mean(axis=0)

    times = [0, 6, 12, 18, 24]
    # Sequential colors for time progression: light -> deep blue
    cmap_seq = plt.colormaps["ncar_blue"]
    colors = [cmap_seq(x) for x in np.linspace(0.20, 0.95, len(times))]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    ax = axes[0]
    for t, color in zip(times, colors):
        prof_ppm = qo3[t].mean(axis=0)
        ax.plot(prof_ppm, z_mean, color=color, lw=1.8,
                label=f"+{t:02d} h")
    ax.set_xlabel(f"{style.species_label('qO3')} [ppm]")
    ax.set_ylabel("z [km]")
    ax.set_title(style.format_title("Global-mean O3 profile"))
    ax.set_ylim(0, z_mean.max())
    ax.legend(title="elapsed", loc="lower right")

    ax = axes[1]
    diff = qo3[24] - qo3[0]  # (nCells, nLev), ppmv
    n_lat = 36
    lat_edges = np.linspace(-90, 90, n_lat + 1)
    lat_mid = 0.5 * (lat_edges[:-1] + lat_edges[1:])
    zonal = np.full((n_lat, z_mean.size), np.nan)
    for j in range(n_lat):
        m = (lat >= lat_edges[j]) & (lat < lat_edges[j + 1])
        if m.any():
            zonal[j] = diff[m].mean(axis=0)
    vmax = float(np.nanmax(np.abs(zonal)))
    # Symlog so the small NOx-driven loss below ~25 km is visible alongside
    # the large upper-stratosphere production. linthresh chosen ~1% of vmax
    # so the linear region covers values that are essentially noise.
    linthresh = max(vmax * 0.01, 1.0e-3)
    norm = SymLogNorm(linthresh=linthresh, linscale=1.0,
                      vmin=-vmax, vmax=vmax, base=10)
    pc = ax.pcolormesh(lat_mid, z_mean, zonal.T, cmap=style.get_bias_cmap(),
                       norm=norm, shading="auto", rasterized=True)
    ax.set_xlabel("latitude [deg]")
    ax.set_ylabel("z [km]")
    ax.set_title(style.format_title("Zonal-mean ΔO3, 0 → 24 h (symlog)"))
    cb = plt.colorbar(pc, ax=ax)
    cb.set_label(f"{style.species_label('qO3')}(24 h) - {style.species_label('qO3')}(0) [ppm]")
    cb.solids.set_rasterized(True)

    fig.suptitle(style.format_title(
        "Chapman+NOx global: O3 builds the upper stratosphere from the 25-km seed"))
    fig.tight_layout()
    save_figure(out_dir, "o3_profile")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-i", "--input", default="output.nc",
                    help="Path to MPAS output NetCDF (default: ./output.nc)")
    ap.add_argument("-o", "--output-dir", default=".",
                    help="Directory for figure files (default: cwd)")
    args = ap.parse_args()

    style.setup()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ds = Dataset(args.input, "r")
    lat = np.degrees(ds.variables["latCell"][:])
    lon = np.degrees(ds.variables["lonCell"][:])
    lon = np.where(lon > 180.0, lon - 360.0, lon)
    triang = make_global_triangulation(lon, lat)

    fig_jno2_terminator(ds, triang, out_dir)
    fig_tracers_evolution(ds, triang, out_dir)
    fig_nox_partition(ds, triang, out_dir)
    fig_o3_profile(ds, lat, out_dir)


if __name__ == "__main__":
    main()
