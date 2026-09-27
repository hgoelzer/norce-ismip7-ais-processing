#!/usr/bin/env python
"""
Offline verification: replicate the isschecker consistency tests for
base/topg/sftgrf/sftflf and orog/base/lithk on the regenerated output files.

Checks per set_counter directory:
  1. |base - topg| <= 0.01  where sftgrf == 1.0   (grounded)
  2.  base - topg  >  0.01  where sftflf == 1.0   (floating)
  3.  base - topg  >= -0.01 everywhere known      (base not below bed)
  4. |base + lithk - orog| <= 0.01 everywhere known
"""
import glob
import os
import sys

import numpy as np
from netCDF4 import Dataset

DST = '/nird/datalake/NS11016K/users/heig/ISMIP7/data_processing/AIS/NORCE/CISM/CORE'
TOL = 1.0e-2
FILL = 9.96921e+36


def read(path):
    with Dataset(path) as nc:
        nc.set_auto_mask(False)
        return nc.variables['time'][:], nc.variables[os.path.basename(path).split('_')[0]][:]


def nominal_years(path):
    """Nominal year per time step (ST convention: Jan 1 of year+1)."""
    with Dataset(path) as nc:
        nc.set_auto_mask(False)
        t = nc.variables['time'][:]
    return np.array([1850 + int(round(d / 365.0)) for d in t])


def slice_at(path, year):
    t, v = read(path)
    yrs = nominal_years(path)
    idx = np.where(yrs == year)[0]
    if len(idx) == 0:
        return None
    return v[idx[0]]


def known(a):
    return np.isfinite(a) & (np.abs(a) < FILL / 2)


def main():
    counters = sorted(glob.glob(f'{DST}/C*'))
    total_err = 0
    for d in counters:
        sc = os.path.basename(d)
        base_f = glob.glob(f'{d}/base_*.nc')
        if not base_f:
            print(f'{sc}: no base file, skipping')
            continue
        topg_f = glob.glob(f'{d}/topg_*.nc')[0]
        grf_f = glob.glob(f'{d}/sftgrf_*.nc')[0]
        flf_f = glob.glob(f'{d}/sftflf_*.nc')[0]
        orog_f = glob.glob(f'{d}/orog_*.nc')[0]
        lithk_f = glob.glob(f'{d}/lithk_*.nc')[0]

        errs = 0
        for bf in base_f:
            years = nominal_years(bf)
            for i, yr in enumerate(years):
                base = slice_at(bf, yr)
                topg = slice_at(topg_f, yr)
                grf = slice_at(grf_f, yr)
                flf = slice_at(flf_f, yr)
                orog = slice_at(orog_f, yr)
                lithk = slice_at(lithk_f, yr)
                if base is None or topg is None:
                    print(f'{sc}: year {yr} missing in base/topg, skipping')
                    continue

                ok = known(base) & known(topg)
                above = base - topg

                # 3. base below bed
                n = int((ok & (above < -TOL)).sum())
                if n:
                    errs += n
                    print(f'{sc} yr {yr}: base below topg in {n} cell(s)')

                # 1. grounded
                if grf is not None:
                    g = ok & known(grf) & (grf == 1.0)
                    n = int((g & (np.abs(above) > TOL)).sum())
                    if n:
                        errs += n
                        print(f'{sc} yr {yr}: grounded base!=topg in {n} cell(s)')

                # 2. floating
                if flf is not None:
                    f = ok & known(flf) & (flf == 1.0)
                    n = int((f & (above <= TOL)).sum())
                    if n:
                        errs += n
                        print(f'{sc} yr {yr}: floating base<=topg+tol in {n} cell(s)')

                # 4. orog identity
                if orog is not None and lithk is not None:
                    k4 = ok & known(orog) & known(lithk)
                    n = int((k4 & (np.abs(base + lithk - orog) > TOL)).sum())
                    if n:
                        errs += n
                        print(f'{sc} yr {yr}: orog != base+lithk in {n} cell(s)')

        status = 'OK' if errs == 0 else f'{errs} VIOLATION(S)'
        total_err += errs
        print(f'{sc}: {status}')

    print(f'\nTotal violations: {total_err}')
    sys.exit(1 if total_err else 0)


if __name__ == '__main__':
    main()
