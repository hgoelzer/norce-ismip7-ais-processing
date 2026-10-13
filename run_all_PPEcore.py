#!/usr/bin/env python
"""
Wrapper script: run all 4 ISMIP7 NORCE processing scripts for the
11 CORE experiments of the 16km ensemble, written to the PPE
experiment tree.

The same 11 runs (historical/ssp370/ssp126/ssp585/ctrl m01,m02 + ocx)
as run_all_CORE.py are processed and submitted as the second model
configuration:
    - output tree:  AIS/NORCE/{ISM_ID}/{SET_ID}/{counter}/  (PPE/P001..P011)
    - the ISM member ID is fixed for all runs (m002 for PPEcore; ESM_id
      alone distinguishes the CESM2-WACCM / MRI-ESM2-0 / ERA forcing)
    - all settings (input path, set ID, ISM member ID) come from the
      configuration module selected with --config and are passed to the
      child scripts via --path_exp / --set_id / --ism_member_id

For the 16km PPEcore runs use:
    python run_all_PPEcore.py --config config_16km.py
or copy config_16km.py over config.py and run without --config.

Experiments (set_counter, PPE tree):
    historical m01 -> P001   (1970-2014)
    historical m02 -> P002   (1970-2014)
    ssp370     m01 -> P003   (2015-2100)
    ssp370     m02 -> P004   (2015-2100)
    ssp126     m01 -> P005   (2015-2300)
    ssp126     m02 -> P006   (2015-2300)
    ssp585     m01 -> P007   (2015-2300)
    ssp585     m02 -> P008   (2015-2300)
    ctrl       m01 -> P009   (2015-2300)
    ctrl       m02 -> P010   (2015-2300)
    ocx        r01 -> P011   (1990-2025)
The time_range tag in the output filenames is derived from the actual time
axis of the model output, so it adjusts automatically when a run is
extended (e.g. historical 1970-2013 -> 1970-2014 with the new output).
Usage:
    python run_all_PPEcore.py --config config_16km.py   # 16km PPEcore run
    python run_all_PPEcore.py                 # run everything (config.py)
    python run_all_PPEcore.py --exp ssp126    # run only one experiment (all members)
    python run_all_PPEcore.py --exp P004      # run one case by PPE counter id
    python run_all_PPEcore.py --exp C004      # CORE counter ids also accepted
    python run_all_PPEcore.py --exp P003 P004 ctrl   # several cases at once
    python run_all_PPEcore.py --dryrun        # only print what would be run

The child scripts are launched with the same interpreter that runs this
wrapper (sys.executable); choose the environment by activating it before
invoking the wrapper.
"""

import argparse
import importlib
import os
import subprocess
import sys
from datetime import datetime

# The configuration module is selected with --config (default: config.py).
# It provides PATH_EXP, SET_ID and ISM_MEMBER_ID for the run.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

# (exp, ESM_num, RCM_num) for the 11 runs (same table as run_all_CORE.py).
# The ocx run has no ESM member; it is identified by RCM_num only.
# exp is the data-request experiment name used in the output file names
# ('ctrl', not the input directory name 'ctrl2015'; see run_dir below).
RUNS = [
    ('historical', 'm01', 'r01'),
    ('historical', 'm02', 'r01'),
    ('ssp370',     'm01', 'r01'),
    ('ssp370',     'm02', 'r01'),
    ('ssp126',     'm01', 'r01'),
    ('ssp126',     'm02', 'r01'),
    ('ssp585',     'm01', 'r01'),
    ('ssp585',     'm02', 'r01'),
    ('ctrl',       'm01', 'r01'),
    ('ctrl',       'm02', 'r01'),
    ('ocx',        None,  'r01'),
]

# Input path, set ID and ISM member ID are set in main() from the
# configuration module selected with --config.
path_exp = None


def run_dir(exp, ESM_num, RCM_num):
    """Input run directory for a given experiment.

    The control run is selected as 'ctrl' (data-request name); its input
    directory on disk keeps the historical name ctrl2015_{ESM_num}_{RCM_num}.
    """
    if exp == 'ocx':
        return f"{path_exp}/ocx_{RCM_num}"
    if exp == 'ctrl':
        return f"{path_exp}/ctrl2015_{ESM_num}_{RCM_num}"
    return f"{path_exp}/{exp}_{ESM_num}_{RCM_num}"


def runs_for_exp(exp):
    """Return the RUNS entries matching an experiment name or counter id.

    Accepts experiment names (historical, ssp370, ssp126, ssp585, ctrl, ocx)
    or counter ids P001..P011 (case-insensitive); CORE counter ids
    C001..C011 are also accepted (same runs).
    """
    key = exp.lower()
    if key[0] in ('c', 'p') and key[1:].isdigit():
        idx = int(key[1:]) - 1
        if 0 <= idx < len(RUNS):
            return [RUNS[idx]]
        sys.exit(f'Error: unknown counter {exp} (valid: P001..P011)')
    runs = [r for r in RUNS if r[0] == exp]
    if not runs:
        sys.exit(f'Error: unknown experiment {exp}')
    return runs


def main():
    parser = argparse.ArgumentParser(
        description='Run ISMIP7 NORCE processing for the 16km ensemble, '
                    'written to the PPE experiment tree')
    parser.add_argument('--exp', default=None, nargs='+',
                        help='Only run these experiments or counter ids '
                             '(e.g. ssp126, P004, P003 P004 ctrl). '
                             'Default: all 11 runs')
    parser.add_argument('--config', default='config.py',
                        help='Configuration module to use (default: '
                             'config.py; config_16km.py for the 16km '
                             'PPEcore runs)')
    parser.add_argument('--dryrun', action='store_true',
                        help='Only print what would be run, without executing')
    args = parser.parse_args()

    # Load the selected configuration module: PATH_EXP, SET_ID, ISM_MEMBER_ID
    cfg = importlib.import_module(args.config.removesuffix('.py'))
    global path_exp
    path_exp = cfg.PATH_EXP
    set_id = cfg.SET_ID
    ism_member_id = cfg.ISM_MEMBER_ID
    print(f"Config: {args.config}"
          f"  (SET_ID={set_id}, ISM_MEMBER_ID={ism_member_id})")
    print(f"Input:  {path_exp}")

    runs = RUNS
    if args.exp is not None:
        runs = []
        for exp in args.exp:
            runs.extend(runs_for_exp(exp))

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
            cmd = [sys.executable, os.path.join(SCRIPT_DIR, script),
                   '--exp', exp, '--ESM_num', ESM_num or 'm01',
                   '--RCM_num', RCM_num,
                   '--path_exp', path_exp,
                   '--set_id', set_id,
                   '--ism_member_id', ism_member_id]
            if args.dryrun:
                print('    [dryrun]', ' '.join(cmd))
                continue

            print(f"    running {script} ...")
            proc = subprocess.run(cmd)
            if proc.returncode != 0:
                print(f"    ERROR: {script} failed with return code "
                      f"{proc.returncode}")
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

