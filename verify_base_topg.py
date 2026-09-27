#!/usr/bin/env python
"""
Offline verification: replicate the isschecker consistency tests for
base/topg/sftgrf/sftflf and orog/base/lithk on the regenerated output files.

Vectorized version: each file is read once (all time steps at once), so this
runs in seconds instead of hours. All variables are ST on the same grid with
aligned time axes, so no per-year matching is needed.

Checks per set_counter directory (ELEVATION_TOLERANCE = 1e-2 m):
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


def read_all(path):
    """Read the full (time, y, x) array with auto-masking disabled."""
    var = os.path.basename(path).split('_')[0]
    with Dataset(path) as nc:
        nc.set_auto_mask(False)
        return np.asarray(nc.variables[var][:], dtype='f8')


def known(a):
    """Cells that hold real data (not the f4 fill value, not NaN)."""
    return np.isfinite(a) & (np.abs(a) < FILL / 2)


def main():
    counters = sorted(glob.glob(f'{DST}/C*'))
    total_err = 0
    for d in counters:
        sc = os.path.basename(d)
        paths = {}
        ok = True
        for v in ('base', 'topg', 'sftgrf', 'sftflf', 'orog', 'lithk'):
            f = glob.glob(f'{d}/{v}_*.nc')
            if len(f) != 1:
                print(f'{sc}: expected exactly one {v} file, found {len(f)} -- skipping')
                ok = False
                break
            paths[v] = f[0]
        if not ok:
            total_err += 1
            continue

        base, topg = read_all(paths['base']), read_all(paths['topg'])
        grf, flf = read_all(paths['sftgrf']), read_all(paths['sftflf'])
        orog, lithk = read_all(paths['orog']), read_all(paths['lithk'])

        if not (base.shape == topg.shape == grf.shape == flf.shape
                == orog.shape == lithk.shape):
            print(f'{sc}: shape mismatch across files -- skipping')
            total_err += 1
            continue

        k = known(base) & known(topg)
        above = base - topg

        n3 = int((k & (above < -TOL)).sum())                       # below bed
        g = k & known(grf) & (grf == 1.0)
        n1 = int((g & (np.abs(above) > TOL)).sum())                # grounded afloat
        f = k & known(flf) & (flf == 1.0)
        n2 = int((f & (above <= TOL)).sum())                       # floating aground
        k4 = k & known(orog) & known(lithk)
        n4 = int((k4 & (np.abs(base + lithk - orog) > TOL)).sum()) # orog identity

        errs = n1 + n2 + n3 + n4
        total_err += errs
        status = 'OK' if errs == 0 else f'{errs} VIOLATION(S)'
        print(f'{sc}: grounded-afloat={n1}, floating-aground={n2}, '
              f'below-bed={n3}, orog-identity={n4}  -> {status}')

    print(f'\nTotal violations: {total_err}')
    sys.exit(1 if total_err else 0)


if __name__ == '__main__':
    main()
