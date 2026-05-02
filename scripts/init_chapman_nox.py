#!/usr/bin/env python3
"""Inject Chapman+NOx chemistry tracers into an MPAS init NetCDF.

Reads an existing init file (e.g. x1.40962.init.nc) and writes a new
file with qO2, qO3, qO, qNO, qNO2 added as functions of altitude only,
preserving every other variable. Mass mixing ratios in kg kg^{-1}.

  qO2 : 0.21 mole fraction       -> ~0.232 kg/kg uniform
  qO3 : Gaussian peak 10 ppmm at 25 km, sigma 7 km
  qO  : 1e-12 floor (photolysis seeds it on the first sunlit step)
  qNO : 1 ppbv background        -> ~1.04e-9 kg/kg
  qNO2: 1 ppbv background        -> ~1.59e-9 kg/kg

Usage:
    python scripts/init_chapman_nox.py -i x1.40962.init.nc \\
                                       -o x1.40962.chapman_nox_init.nc
"""

import argparse
import shutil

import numpy as np
import netCDF4 as nc

M_AIR = 28.97e-3
M_O2 = 32.00e-3
M_NO = 30.01e-3
M_NO2 = 46.00e-3


def ozone_mmr(z_m, peak=1.0e-5, z_peak_km=25.0, sigma_km=7.0):
    z_km = z_m * 1.0e-3
    return peak * np.exp(-((z_km - z_peak_km) ** 2) / (2.0 * sigma_km ** 2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-i", "--input", required=True,
                    help="Path to source MPAS init NetCDF")
    ap.add_argument("-o", "--output", required=True,
                    help="Path for the chemistry-augmented init NetCDF")
    args = ap.parse_args()

    shutil.copy(args.input, args.output)
    f = nc.Dataset(args.output, "a")

    nCells = f.dimensions["nCells"].size
    nLev = f.dimensions["nVertLevels"].size

    zg = f.variables["zgrid"][:]
    zc = 0.5 * (zg[:, :-1] + zg[:, 1:])

    qO2_val = 0.21 * M_O2 / M_AIR
    qO_val = 1.0e-12
    qNO_val = 1.0e-9 * M_NO / M_AIR
    qNO2_val = 1.0e-9 * M_NO2 / M_AIR

    profiles = {
        "qO2":  np.full((1, nCells, nLev), qO2_val, dtype="f8"),
        "qO3":  ozone_mmr(zc).astype("f8")[np.newaxis, ...],
        "qO":   np.full((1, nCells, nLev), qO_val, dtype="f8"),
        "qNO":  np.full((1, nCells, nLev), qNO_val, dtype="f8"),
        "qNO2": np.full((1, nCells, nLev), qNO2_val, dtype="f8"),
    }

    for name, arr in profiles.items():
        if name in f.variables:
            v = f.variables[name]
        else:
            v = f.createVariable(name, "f8", ("Time", "nCells", "nVertLevels"))
            v.units = "kg kg^{-1}"
            v.long_name = name
        v[:] = arr
        print(f"{name:5s} min={arr.min():.4g} max={arr.max():.4g} "
              f"mean={arr.mean():.4g}")

    f.close()


if __name__ == "__main__":
    main()
