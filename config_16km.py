#!/usr/bin/env python
"""
Top-level configuration for the ISMIP7 NORCE AIS processing scripts.

All processing scripts (ISMIP7_scalar_processing.py,
ISMIP7_variable_HgridST_processing.py, ISMIP7_variable_HgridFL_processing.py,
ISMIP7_variable_VelogridST_processing.py) and the wrapper (run_all_CORE.py)
import their defaults from this file. Edit the values here to change them
for all scripts at once; individual scripts can still override them on the
command line (--path_exp, --dstPath).
"""

import os

# ----------------------------------------------------------------------
# Python interpreter used by the wrapper to run the processing scripts
# (must have netCDF4, numpy and scipy installed)
# ----------------------------------------------------------------------
PYTHON = '/nird/datapeak/NS11016K/miniforge3_26/envs/nc/bin/python'

# ----------------------------------------------------------------------
# Path to the CISM model output (ensemble_v1 run directory)
# ----------------------------------------------------------------------
PATH_EXP = '/nird/datapeak/NS11016K/users/heig/CISM/AIS/ais_16km_ismip7/AIS_16km_v01_geo01_ghf01_smb03_bas01_otf01_mel02_tun01_pow/ensemble_v1'

# ----------------------------------------------------------------------
# Base path for the ISMIP7 output data
# ----------------------------------------------------------------------
DST_PATH = '/nird/datalake/NS11016K/users/heig/ISMIP7/data_processing'

# ----------------------------------------------------------------------
# ISM model ID used in the output directory tree and file names
# ({DST_PATH}/AIS/NORCE/{ISM_ID}/CORE/{C001..C011}/). This separates the
# output of different model resolutions sharing the same DST_PATH:
#   8km ensemble -> 'CISM8'   16km ensemble -> 'CISM'
# ----------------------------------------------------------------------
ISM_ID = 'CISM'

# Directory containing this config file (repo root)
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
