#!/usr/bin/env python3
"""Quick-look plots for the global Chapman+NOx test run.

Produces four figures, saved as PNG and PDF, using the NCAR brand
styling from scripts/style.py:

  - jNO2_terminator   : jNO2 maps at t=0, 6, 12, 18 UTC (terminator sweep)
  - tracers_t0_t24    : O3 and NO2 snapshots at t=0 and t=24 h
  - nox_partition     : NO2 / (NO + NO2) molar fraction at t=0 and t=24 h
  - o3_profile        : global-mean O3 profile vs z with zonal-mean
                        d(O3)/dt over the 24-hour window

Usage:
    python scripts/plot_chapman_nox_global.py -i output.nc -o ./plots
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from netCDF4 import Dataset
import cartopy.crs as ccrs

sys.path.insert(0, str(Path(__file__).resolve().parent))
import style

LEVEL = 17  # ~25 km on x1.40962 vertical grid (ozone-peak level)
M_NO = 30.01
M_NO2 = 46.00


def xtime_str(ds, t):
    return b"".join(ds.variables["xtime"][t, :]).decode().strip()


def save_figure(out_dir, stem, dpi=300):
    png = out_dir / f"{stem}.png"
    pdf = out_dir / f"{stem}.pdf"
    plt.savefig(png, dpi=dpi, bbox_inches="tight")
    plt.savefig(pdf, bbox_inches="tight")
    print(f"  wrote {png} and {pdf}")


def scatter_global(ax, lon, lat, vals, title, cbar_label, cmap, vmin, vmax):
    sc = ax.scatter(
        lon, lat, c=vals, s=2.5, cmap=cmap,
        vmin=vmin, vmax=vmax, transform=ccrs.PlateCarree(),
        rasterized=True,
    )
    ax.set_global()
    ax.coastlines(linewidth=0.4, color=style.NCAR_COLORS["gray"])
    ax.gridlines(draw_labels=False, linewidth=0.3,
                 color=style.NCAR_COLORS["gray"], alpha=0.4)
    ax.set_title(style.format_title(title))
    cb = plt.colorbar(sc, ax=ax, shrink=0.7, pad=0.03)
    cb.set_label(cbar_label)
    cb.solids.set_rasterized(True)


def fig_jno2_terminator(ds, lon, lat, out_dir):
    times = [0, 6, 12, 18]
    fig, axes = plt.subplots(
        2, 2, figsize=(13, 7),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )
    j = ds.variables["j_jNO2"]
    vmax = float(j[:, :, LEVEL].max())
    for ax, t in zip(axes.flat, times):
        scatter_global(
            ax, lon, lat, j[t, :, LEVEL],
            f"j(NO2) @ ~25 km, {xtime_str(ds, t)}",
            r"j(NO$_2$) [s$^{-1}$]",
            cmap="ncar_sunset", vmin=0.0, vmax=vmax,
        )
    fig.suptitle(style.format_title(
        "Chapman+NOx global: NO2 photolysis rate, terminator sweep"))
    fig.tight_layout()
    save_figure(out_dir, "jNO2_terminator")
    plt.close(fig)


def fig_tracers_t0_t24(ds, lon, lat, out_dir):
    fig, axes = plt.subplots(
        2, 2, figsize=(13, 7),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )
    qo3 = ds.variables["qO3"][:, :, LEVEL] * 1e6
    qno2 = ds.variables["qNO2"][:, :, LEVEL] * 1e9
    o3_max = float(qo3.max())
    no2_max = float(qno2.max())

    o3_label = f"{style.species_label('qO3')} [ppm-mass]"
    no2_label = f"{style.species_label('qNO2')} [ppb-mass]"

    scatter_global(axes[0, 0], lon, lat, qo3[0],
                   f"O3 @ ~25 km, {xtime_str(ds, 0)}",
                   o3_label, cmap="ncar_sunset", vmin=0.0, vmax=o3_max)
    scatter_global(axes[0, 1], lon, lat, qo3[24],
                   f"O3 @ ~25 km, {xtime_str(ds, 24)}",
                   o3_label, cmap="ncar_sunset", vmin=0.0, vmax=o3_max)
    scatter_global(axes[1, 0], lon, lat, qno2[0],
                   f"NO2 @ ~25 km, {xtime_str(ds, 0)}",
                   no2_label, cmap="ncar_sunset", vmin=0.0, vmax=no2_max)
    scatter_global(axes[1, 1], lon, lat, qno2[24],
                   f"NO2 @ ~25 km, {xtime_str(ds, 24)}",
                   no2_label, cmap="ncar_sunset", vmin=0.0, vmax=no2_max)
    fig.suptitle(style.format_title(
        "Chapman+NOx global: O3 and NO2 at t=0 vs t=24 h"))
    fig.tight_layout()
    save_figure(out_dir, "tracers_t0_t24")
    plt.close(fig)


def fig_nox_partition(ds, lon, lat, out_dir):
    qno = ds.variables["qNO"][:, :, LEVEL] / M_NO
    qno2 = ds.variables["qNO2"][:, :, LEVEL] / M_NO2
    f_no2 = qno2 / np.maximum(qno + qno2, 1e-30)

    fig, axes = plt.subplots(
        1, 2, figsize=(14, 4.6),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )
    cbar_label = r"NO$_2$ / (NO + NO$_2$) molar"
    scatter_global(axes[0], lon, lat, f_no2[0],
                   f"NOx partition @ ~25 km, {xtime_str(ds, 0)}",
                   cbar_label, cmap="ncar_sunset", vmin=0.0, vmax=1.0)
    scatter_global(axes[1], lon, lat, f_no2[24],
                   f"NOx partition @ ~25 km, {xtime_str(ds, 24)}",
                   cbar_label, cmap="ncar_sunset", vmin=0.0, vmax=1.0)
    fig.suptitle(style.format_title(
        "Chapman+NOx global: NOx partitioning shifts toward NO2 in daylight"))
    fig.tight_layout()
    save_figure(out_dir, "nox_partition")
    plt.close(fig)


def fig_o3_profile(ds, lat, out_dir):
    qo3 = ds.variables["qO3"][:]
    zg = ds.variables["zgrid"][:]
    zc_km = 0.5 * (zg[:, :-1] + zg[:, 1:]) * 1e-3
    z_mean = zc_km.mean(axis=0)

    times = [0, 6, 12, 18, 24]
    cycle = style.get_palette(len(times))

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    ax = axes[0]
    for t, color in zip(times, cycle):
        prof_ppm = qo3[t].mean(axis=0) * 1e6
        ax.plot(prof_ppm, z_mean, color=color, lw=1.8,
                label=xtime_str(ds, t))
    ax.set_xlabel(f"{style.species_label('qO3')} [ppm-mass]")
    ax.set_ylabel("z [km]")
    ax.set_title(style.format_title("Global-mean O3 profile"))
    ax.set_ylim(0, z_mean.max())
    ax.legend(title="UTC", loc="lower right")

    ax = axes[1]
    diff = (qo3[24] - qo3[0]) * 1e6
    n_lat = 36
    lat_edges = np.linspace(-90, 90, n_lat + 1)
    lat_mid = 0.5 * (lat_edges[:-1] + lat_edges[1:])
    zonal = np.full((n_lat, z_mean.size), np.nan)
    for j in range(n_lat):
        m = (lat >= lat_edges[j]) & (lat < lat_edges[j + 1])
        if m.any():
            zonal[j] = diff[m].mean(axis=0)
    vmax = float(np.nanmax(np.abs(zonal)))
    pc = ax.pcolormesh(lat_mid, z_mean, zonal.T, cmap=style.get_bias_cmap(),
                       vmin=-vmax, vmax=vmax, shading="auto",
                       rasterized=True)
    ax.set_xlabel("latitude [deg]")
    ax.set_ylabel("z [km]")
    ax.set_title(style.format_title("Zonal-mean d(O3)/dt over 24 h"))
    cb = plt.colorbar(pc, ax=ax)
    cb.set_label(f"{style.species_label('qO3')}(24h) - {style.species_label('qO3')}(0) [ppm-mass]")
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

    fig_jno2_terminator(ds, lon, lat, out_dir)
    fig_tracers_t0_t24(ds, lon, lat, out_dir)
    fig_nox_partition(ds, lon, lat, out_dir)
    fig_o3_profile(ds, lat, out_dir)


if __name__ == "__main__":
    main()
