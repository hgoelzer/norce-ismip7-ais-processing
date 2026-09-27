#!/usr/bin/env python
"""
ISMIP7 AIS flux variables processing (Hgrid FL)

Converted from ISMIP7_variable_HgridFL_processing.ipynb to a plain Python script.
"""

# Import packages
import numpy as np
from netCDF4 import Dataset
import sys, os
import argparse

# Top-level configuration (paths, interpreter)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import PATH_EXP, DST_PATH
import netCDF4
from pathlib import Path

from datetime import date, datetime


# ----------------------------------------------------------------------
# Time conversion helper
# ----------------------------------------------------------------------
EPOCH = date(1850, 1, 1)

def days_since_1850(year, month, day):
    """Whole days from 1850-01-01 (which is day 0) to the given Gregorian date."""
    return (date(year, month, day) - EPOCH).days


# ----------------------------------------------------------------------
# Strings for file naming convention:
# ----------------------------------------------------------------------
domain_id = 'AIS'  # Ice Sheet name
source_id = 'NORCE'
ism_id = 'CISM'
set_id = 'CORE'

dayPerY = 365.
sPerY = 31536000.
rhoi = 917

fill_value = netCDF4.default_fillvals['f4']

# ----------------------------------------------------------------------
# Command line arguments (defaults reproduce the previous hard-coded run)
# ----------------------------------------------------------------------
parser = argparse.ArgumentParser(description='ISMIP7 AIS flux variables processing (Hgrid FL)')
parser.add_argument('--exp',       default='ssp585', help='Experiment name (e.g. historical, ssp126, ssp370, ssp585, ctrl2015, ocx)')
parser.add_argument('--ESM_num',   default='m01',    help='ESM ensemble member (m01, m02); ocx run uses r01 only')
parser.add_argument('--RCM_num',   default='r01',    help='RCM/ISM configuration number')
parser.add_argument('--path_exp',  default=PATH_EXP,
                    help='Path to the ensemble_v1 run directory')
parser.add_argument('--dstPath',   default=DST_PATH,
                    help='Base path for output')
args = parser.parse_args()

exp      = args.exp
ESM_num  = args.ESM_num
RCM_num  = args.RCM_num
path_exp = args.path_exp
dstPath  = args.dstPath

# Output experiment name: the data request (and compliance checker) uses
# 'ctrl' for the control run, while the input directory is named ctrl2015.
exp_out = 'ctrl' if exp == 'ctrl2015' else exp

# ----------------------------------------------------------------------
# Derive ESM_id / ISM_member_id from the ESM ensemble member
# ----------------------------------------------------------------------
ESM_map = {
    'm01': ('CESM2-WACCM', 'm001'),
    'm02': ('MRI-ESM2-0',  'm002'),
}
if exp == 'ocx':
    # OCX doesn't have an ESM; use ERA
    ESM_id, ISM_member_id = 'ERA', 'm001'
elif ESM_num in ESM_map:
    ESM_id, ISM_member_id = ESM_map[ESM_num]
else:
    sys.exit(f'Error: unknown ESM_num {ESM_num}')

forcing_member_id = 'f001'

# ----------------------------------------------------------------------
# Experiment lookup: set_counter for the 11 CORE runs
# (m01/m02 pairs share the same set_counter; ocx is C011)
# The time_range tag in the output filename is derived from the data below.
# ----------------------------------------------------------------------
exp_map = {
    'historical': 'C001',
    'ssp370':     'C003',
    'ssp126':     'C005',
    'ssp585':     'C007',
    'ctrl2015':   'C009',
    'ocx':        'C011',
}
if exp in exp_map:
    set_counter_base = exp_map[exp]
else:
    sys.exit(f'Error: unknown experiment {exp}')

# m01/m02 runs get consecutive set_counters (e.g. ssp126 -> C005/C006)
if exp == 'ocx':
    set_counter = set_counter_base
elif ESM_num == 'm01':
    set_counter = set_counter_base
elif ESM_num == 'm02':
    set_counter = 'C%03d' % (int(set_counter_base[1:]) + 1)
else:
    sys.exit(f'Error: unknown ESM_num {ESM_num}')

# OCX run directory has no _{ESM_num}_{RCM_num} suffix
if exp == 'ocx':
    run_dir = f"{path_exp}/ocx_{RCM_num}"
else:
    run_dir = f"{path_exp}/{exp}_{ESM_num}_{RCM_num}"

fileVar = f"{run_dir}/output.nc"
fileVarVel = f"{run_dir}/output.nc"


fieldFL = ['acabf', 'libmassbfgr', 'libmassbffl', 'dlithkdt',
           'licalvf', 'ligroundf', 'lifmassbf']
# nameCISM_FL = ['acab_applied_tavg','basal_mbal_flux_tavg*f_ground','basal_mbal_flux_tavg*f_float',
#           'dthck_dt','calving_flux_tavg', 'gl_flux_tavg','latmelt_flux_tavg']


# List of variable that needs to be read from previous experiment
readListPrevExptString = ['ligroundf', 'licalvf', 'dlithkdt', 'libmassbfgr', 'libmassbffl', 'acabf']

fieldReady = ['acabf', 'dlithkdt', 'licalvf', 'ligroundf', 'lifmassbf']
nameCISM = ['acab_applied_tavg', 'dthck_dt', 'calving_flux_tavg', 'gl_flux_tavg', 'latmelt_flux_tavg']

fieldException = ['libmassbfgr', 'libmassbffl']
nameCISM = ['basal_mbal_flux_tavg*f_ground', 'basal_mbal_flux_tavg*f_float']


# ----------------------------------------------------------------------
# Output directory
# ----------------------------------------------------------------------
dstDir = f"{dstPath}/{domain_id}/{source_id}/{ism_id}/{set_id}/{set_counter}/"

if os.path.isdir(dstDir):
    print("The output directory already exists")
else:
    print("Creating output directory")
    os.makedirs(dstDir, exist_ok=True)


# ----------------------------------------------------------------------
# Read source data
# ----------------------------------------------------------------------
try:
    nidsrc = Dataset(fileVar, 'r')
    print('fileVar =', fileVar)
except Exception:
    print('Error: Unable to open CISM file for expt ', exp)
    sys.exit('exiting program now')

# Keep all time entries: the first CISM output is the end of the first
# simulation year (e.g. 1970 for historical), so nothing is dropped.
time_dst = nidsrc['time'][:]
x_dst = nidsrc['x1'][:]
y_dst = nidsrc['y1'][:]

ice_mask = nidsrc['ice_mask'][:, :, :]
f_ground = nidsrc['f_ground_cell'][:, :, :]*ice_mask
f_float = (1-f_ground)*ice_mask


# acab_dst         = nidsrc['acab_applied_tavg'][:, :, :]  # not available in NORCE output
acab_dst         = nidsrc['acab_applied'][:, :, :]
dthckdt_dst      = nidsrc['dthck_dt'][:, :, :]
# latmelt_dst      = nidsrc['latmelt_flux_tavg'][:, :, :]  # not available in NORCE output
latmelt_dst      = np.zeros_like(nidsrc['dthck_dt'][:, :, :])

nidsrc.close()

# The time-mean flux variables are written to a separate output_tavg.nc file
nidtavg = Dataset(f"{run_dir}/output_tavg.nc", 'r')
basal_flux_dst   = nidtavg['basal_mbal_flux_tavg'][:, :, :]
calving_flux_dst = nidtavg['calving_flux_tavg'][:, :, :]
nidtavg.close()

nt = len(time_dst)
nx = len(x_dst)
ny = len(y_dst)


print(f"nt={nt}, ny={ny}, nx={nx}")

# The time_range tag in the output filename is derived from the data:
# entry t (CISM year time_dst[t]) covers nominal year time_dst[t]-1, so the
# first/last nominal years are time_dst[0]-1 / time_dst[-1]-1. It therefore
# adjusts automatically when a run is extended by one year.
time_range = f"{int(time_dst[0])-1}-{int(time_dst[-1])-1}"
print('time_range =', time_range)


# readListPrevExptString = [ 'licalvf', 'dlithkdt',  'acabf']
if exp in ['historical']:
    # Need to read in the last time slice of the spin-up
    filePrev = f"{path_exp}/ctrl2015_{ESM_num}_{RCM_num}/restart_in.nc"

elif exp == 'ocx':
    # OCX is a standalone run with no historical predecessor;
    # use its own spin-up restart like the historical run does
    filePrev = f"{path_exp}/ocx_{RCM_num}/restart_in.nc"

else:
    # Need to read the last time slice of the historical
    filePrev = f"{path_exp}/historical_{ESM_num}_{RCM_num}/output.nc"

try:
    nidprev = Dataset(filePrev, 'r')
    print('filePrev =', filePrev)
except Exception:
    print('Error: Unable to open CISM previous file ', filePrev)
    sys.exit('exiting program now')

# basal_flux_dst[0,:,:] = nidprev['acab_applied_tavg'][-1,:,:]
nidprev.close()


# ----------------------------------------------------------------------
# Time axes
# ----------------------------------------------------------------------
# CISM writes the first output at the end of the first simulation year:
# entry t (time_dst[t]) is the state / year-mean of nominal year time_dst[t]-1.
# FL fields (year-means) are assigned to the middle of the nominal year,
# Jul 1 of time_dst[t]-1; the bounds span that nominal year.
timeST = np.zeros(nt)
timeFL = np.zeros(nt)

for t in range(nt):
    timeST[t] = days_since_1850(int(time_dst[t]), 1, 1)      # time in days

for t in range(nt):
    timeFL[t] = days_since_1850(int(time_dst[t])-1, 7, 1)    # time in days

print(time_dst)


# ----------------------------------------------------------------------
# Main processing loop
# ----------------------------------------------------------------------
for field in fieldFL:

    # Create the field output file.
    dstFile = f"{dstDir}{field}_{domain_id}_{source_id}_{ism_id}_{ISM_member_id}_{ESM_id}_{forcing_member_id}_{exp_out}_{set_counter}_{time_range}.nc"

    # Removing the output file if it already exists.
    if os.path.isfile(dstFile):
        print('yup')
        os.remove(dstFile)

    print('Created field output file', dstFile)
    ncid = Dataset(dstFile, 'w')
    ncid.createDimension('time', None)
    ncid.createDimension('bnds', 2)

    time    = ncid.createVariable('time', 'f4', ('time'))
    time.bounds        = 'time_bnds'
    time.units         = "days since 1850-01-01"
    time.calendar      = "standard"
    time.axis          = "T"
    time.long_name     = "time"
    time.standard_name = "time"
    time[:] = timeFL[:]  # time in days since 1850

    # CF bounds variable: must be named 'time_bnds' to match time:bounds
    time_bnds = ncid.createVariable('time_bnds', 'f4', ('time', 'bnds',))
    time_bnds[:, 0] = np.array([days_since_1850(int(time_dst[t])-1, 1, 1) for t in range(nt)])
    time_bnds[:, 1] = timeST[:]

    ncid.createDimension('x', size=nx)
    x    = ncid.createVariable('x', 'f4', ('x'))
    x.long_name = "Cartesian centered thickness x-coordinate"
    x.units     = "m"
    x[:] = x_dst[:]

    ncid.createDimension('y', size=ny)
    y    = ncid.createVariable('y', 'f4', ('y'))
    y.long_name = "Cartesian centered thickness y-coordinate"
    y.units     = "m"
    y[:] = y_dst[:]


    if field in ['acabf']:
        acabf = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        acabf.units         = 'kg m-2 s-1'
        acabf.long_name     = 'surface mass balance flux'
        acabf.standard_name = 'land_ice_surface_specific_mass_balance_flux'
        acabf[:, :, :] = acab_dst[:, :, :]*rhoi/sPerY

    if field in ['libmassbfgr']:
        libmassbfgr = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        libmassbfgr.units         = 'kg m-2 s-1'
        libmassbfgr.long_name     = 'basal mass balance flux beneath grounded ice'
        libmassbfgr.standard_name = 'land_ice_basal_specific_mass_balance_flux'
        # The data request defines this variable only where there is grounded
        # ice; cells without grounded ice hold the fill value.
        libmassbfgr[:, :, :] = np.where(f_ground[:, :, :] > 0,
                                        basal_flux_dst[:, :, :]*f_ground[:, :, :],
                                        netCDF4.default_fillvals['f4'])

    if field in ['libmassbffl']:
        libmassbffl = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        libmassbffl.units         = 'kg m-2 s-1'
        libmassbffl.long_name     = 'basal mass balance flux beneath floating ice'
        libmassbffl.standard_name = 'land_ice_basal_specific_mass_balance_flux'
        # The data request defines this variable only where there is floating
        # ice; cells without floating ice hold the fill value.
        libmassbffl[:, :, :] = np.where(f_float[:, :, :] > 0,
                                        basal_flux_dst[:, :, :]*f_float[:, :, :],
                                        netCDF4.default_fillvals['f4'])

    if field in ['dlithkdt']:
        dlithkdt = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        dlithkdt.units         = 'm s-1'
        dlithkdt.long_name     = 'ice thickness imbalance'
        dlithkdt.standard_name = 'tendency_of_land_ice_thickness'
        # The data request does not permit missing values in this variable:
        # any masked/fill cells (e.g. where there is no ice) are set to 0.
        dlithkdt[:, :, :] = np.ma.filled(dthckdt_dst[:, :, :]/sPerY, 0.0)

    if field in ['licalvf']:
        licalvf = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        licalvf.units         = 'kg m-2 s-1'
        licalvf.long_name     = 'calving flux'
        licalvf.standard_name = 'land_ice_specific_mass_flux_due_to_calving'
        # Temporary fix for positive values
        licalvf[:, :, :] = np.where(calving_flux_dst[:, :, :] > 0, 0, calving_flux_dst[:, :, :])

    if field in ['lifmassbf']:
        lifmassbf = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        lifmassbf.units         = 'kg m-2 s-1'
        lifmassbf.long_name     = 'loss of ice mass resulting from ice front melting'
        lifmassbf.standard_name = 'land_ice_specific_mass_flux_due_to_ice_front_melting'
        # The data request does not permit missing values in this variable:
        # any masked/fill cells (e.g. where there is no ice) are set to 0.
        lifmassbf[:, :, :] = np.ma.filled(latmelt_dst[:, :, :], 0.0)  # zeros - latmelt not available in NORCE output


    if field in ['ligroundf']:
        ligroundf = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        ligroundf.units         = 'kg m-2 s-1'
        ligroundf.long_name     = 'Flux of ice mass across the grounding line'
        ligroundf.standard_name = 'land_ice_specific_grounding_line_flux'
        ligroundf[:, :, :] = 0

    ncid.group = 'NORCE'
    ncid.model = 'CISM3'
    ncid.contact_name = 'Heiko Goelzer'
    ncid.contact_email = 'heig@norceresearch.no'
    ncid.crs = 'epsg:3031'
    ncid.close()
