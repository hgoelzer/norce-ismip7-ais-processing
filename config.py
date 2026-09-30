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
# Path to the CISM model output (ensemble_v1 run directory)
# ----------------------------------------------------------------------
PATH_EXP = '/nird/datapeak/NS11016K/users/heig/CISM/AIS/ais_08km_ismip7/AIS_08km_v03_geo01_ghf01_smb03_bas01_otf01_mel02_tun01_pow/ensemble_v1'

# ----------------------------------------------------------------------
# Base path for the ISMIP7 output data
# ----------------------------------------------------------------------
DST_PATH = '/nird/datalake/NS11016K/users/heig/ISMIP7/data_processing'

# ----------------------------------------------------------------------
# ISM model ID used in the output directory tree and file names
# ({DST_PATH}/AIS/NORCE/{ISM_ID}/CORE/{C001..C011}/) and as the `model`
# global attribute in the output files.
# ----------------------------------------------------------------------
ISM_ID = 'CISM'

# ----------------------------------------------------------------------
# Metadata written as global attributes in the output files
# ----------------------------------------------------------------------
DOMAIN_ID = 'AIS'    # Ice sheet
SOURCE_ID = 'NORCE'  # Modelling group (also global attribute `group`)
SET_ID = 'CORE'      # Experiment set
CONTACT_NAME = 'Maria Paz Lira, Heiko Goelzer'
CONTACT_EMAIL = 'mali@norceresearch.no, heig@norceresearch.no'

# Directory containing this config file (repo root)
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
