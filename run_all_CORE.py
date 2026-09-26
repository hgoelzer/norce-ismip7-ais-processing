#!/usr/bin/env python
"""
Wrapper script: run all 4 ISMIP7 NORCE processing scripts for the
11 CORE experiments in the ensemble_v1 run directory.

Experiments (set_counter):
    historical m01 -> C001   (1970-2014)
    historical m02 -> C002   (1970-2014)
    ssp370     m01 -> C003   (2015-2100)
    ssp370     m02 -> C004   (2015-2100)
    ssp126     m01 -> C005   (2015-2300)
    ssp126     m02 -> C006   (2015-2300)
    ssp585     m01 -> C007   (2015-2300)
    ssp585     m02 -> C008   (2015-2300)
    ctrl2015   m01 -> C009   (2015-2300)
    ctrl2015   m02 -> C010   (2015-2300)
    ocx        r01 -> C011   (1979-2025)

Usage:
    python run_all_CORE.py                 # run everything
    python run_all_CORE.py --exp ssp126    # run only one experiment (all members)
    python run_all_CORE.py --dryrun        # only print what would be run
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime

# Top-level configuration (paths, interpreter)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import PYTHON, PATH_EXP

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS = [
    'ISMIP7_scalar_processing.py',
    'ISMIP7_variable_HgridST_processing.py',
    'ISMIP7_variable_HgridFL_processing.py',
    'ISMIP7_variable_VelogridST_processing.py',
]

# (exp, ESM_num, RCM_num) for the 11 CORE runs.
# The ocx run has no ESM member; it is identified by RCM_num only.
RUNS = [
    ('historical', 'm01', 'r01'),
    ('historical', 'm02', 'r01'),
    ('ssp370',     'm01', 'r01'),
    ('ssp370',     'm02', 'r01'),
    ('ssp126',     'm01', 'r01'),
    ('ssp126',     'm02', 'r01'),
    ('ssp585',     'm01', 'r01'),
    ('ssp585',     'm02', 'r01'),
    ('ctrl2015',   'm01', 'r01'),
    ('ctrl2015',   'm02', 'r01'),
    ('ocx',        None,  'r01'),
]

# Python interpreter used to run the processing scripts: see PYTHON in config.py

path_exp = PATH_EXP


def run_dir(exp, ESM_num, RCM_num):
    """Input run directory for a given experiment."""
    if exp == 'ocx':
        return f"{path_exp}/ocx_{RCM_num}"
    return f"{path_exp}/{exp}_{ESM_num}_{RCM_num}"


def main():
    parser = argparse.ArgumentParser(description='Run ISMIP7 NORCE processing for all CORE experiments')
    parser.add_argument('--exp', default=None,
                        help='Only run this experiment (e.g. ssp126). Default: all 11 runs')
    parser.add_argument('--dryrun', action='store_true',
                        help='Only print what would be run, without executing')
    args = parser.parse_args()

    runs = RUNS
    if args.exp is not None:
        runs = [r for r in RUNS if r[0] == args.exp]
        if not runs:
            sys.exit(f'Error: unknown experiment {args.exp}')

    results = []

    for exp, ESM_num, RCM_num in runs:
        rdir = run_dir(exp, ESM_num, RCM_num)
        label = f"{exp}_{ESM_num or 'ocx'}_{RCM_num}"

        if not os.path.isdir(rdir):
            print(f"\n===== {label}: input directory missing, skipping =====")
            print(f"    {rdir}")
            results.append((label, 'SKIPPED (no input dir)'))
            continue

        if not os.path.isfile(f"{rdir}/output.nc"):
            print(f"\n===== {label}: output.nc missing, skipping =====")
            print(f"    {rdir}")
            results.append((label, 'SKIPPED (no output.nc)'))
            continue

        print(f"\n===== {label} =====")
        print(f"    {rdir}")

        status = 'OK'
        for script in SCRIPTS:
            cmd = [PYTHON, os.path.join(SCRIPT_DIR, script),
                   '--exp', exp, '--ESM_num', ESM_num or 'm01', '--RCM_num', RCM_num]
            if args.dryrun:
                print('    [dryrun]', ' '.join(cmd))
                continue

            print(f"    running {script} ...")
            proc = subprocess.run(cmd)
            if proc.returncode != 0:
                print(f"    ERROR: {script} failed with return code {proc.returncode}")
                status = f'FAILED ({script})'
                break

        if not args.dryrun:
            results.append((label, status))

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    if not args.dryrun:
        print('\n===== Summary =====')
        for label, status in results:
            print(f"  {label:20s}  {status}")
        n_fail = sum(1 for _, s in results if s.startswith('FAILED'))
        print(f"\nFinished at {datetime.now():%Y-%m-%d %H:%M:%S}: "
              f"{len(results)} runs, {n_fail} failed")


if __name__ == '__main__':
    main()
