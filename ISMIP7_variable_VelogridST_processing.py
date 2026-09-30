#!/usr/bin/env python
"""
ISMIP7 AIS velocity-grid state variable processing (Velogrid ST)

Converted from ISMIP7_variable_VelogridST_processing.ipynb to a plain Python script.
"""

# Import packages
import numpy as np
from netCDF4 import Dataset
import sys, os
import argparse

# Top-level configuration (paths, metadata)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (PATH_EXP, DST_PATH, ISM_ID, CONTACT_NAME, CONTACT_EMAIL,
                    DOMAIN_ID, SOURCE_ID, SET_ID)
import netCDF4
from pathlib import Path

from datetime import date, datetime

from scipy.interpolate import RegularGridInterpolator


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
ism_id = ISM_ID  # from config; can be overridden with --ism_id
set_id = 'CORE'

dayPerY = 365.
sPerY = 31536000.

fill_value = netCDF4.default_fillvals['f4']

# ----------------------------------------------------------------------
# Command line arguments (defaults reproduce the previous hard-coded run)
# ----------------------------------------------------------------------
parser = argparse.ArgumentParser(description='ISMIP7 AIS velocity-grid state variable processing (Velogrid ST)')
parser.add_argument('--exp',       default='ssp585', help='Experiment name (e.g. historical, ssp126, ssp370, ssp585, ctrl2015, ocx)')
parser.add_argument('--ESM_num',   default='m01',    help='ESM ensemble member (m01, m02); ocx run uses r01 only')
parser.add_argument('--RCM_num',   default='r01',    help='RCM/ISM configuration number')
parser.add_argument('--path_exp',  default=PATH_EXP,
                    help='Path to the ensemble_v1 run directory')
parser.add_argument('--dstPath',   default=DST_PATH,
                    help='Base path for output')
parser.add_argument('--ism_id',    default=ISM_ID,
                    help='ISM model ID for the output path/file names (default from config)')
args = parser.parse_args()

exp      = args.exp
ESM_num  = args.ESM_num
RCM_num  = args.RCM_num
path_exp = args.path_exp
dstPath  = args.dstPath
ism_id   = args.ism_id

# exp is the data-request experiment name used in the output file names
# ('ctrl', not the input directory name 'ctrl2015'; see run_dir below).

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
    'ctrl':       'C009',
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

# OCX run directory has no _{ESM_num}_{RCM_num} suffix; the control run is
# selected as 'ctrl' but its input directory keeps the name ctrl2015_*.
def run_dir(exp, ESM_num, RCM_num):
    if exp == 'ocx':
        return f"{path_exp}/ocx_{RCM_num}"
    if exp == 'ctrl':
        return f"{path_exp}/ctrl2015_{ESM_num}_{RCM_num}"
    return f"{path_exp}/{exp}_{ESM_num}_{RCM_num}"


run_dir = run_dir(exp, ESM_num, RCM_num)

# NOTE: There is no separate velo.nc file in the NORCE output. The velocity
# variables uvel_mean, vvel_mean and btract are stored in output_g0.nc.
fileVar = f"{run_dir}/output.nc"
fileVarVel = f"{run_dir}/output_g0.nc"


fieldVel = ['xvelmean', 'yvelmean', 'strbasemag']


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

# Ice mask on the destination (x1/y1) grid; used to mask the output
# variables, which the data request defines only where there is ice.
ice_mask = nidsrc['ice_mask'][:, :, :]

x0_src = nidsrc['x0'][:]
y0_src = nidsrc['y0'][:]

nidsrc.close()

# The velocity variables uvel_mean, vvel_mean and btract are stored in
# output_g0.nc (on the x0/y0 grid, same time axis as output.nc).
nidvel = Dataset(fileVarVel, 'r')
uvel_mean_x0 = nidvel['uvel_mean'][:, :, :]
vvel_mean_x0 = nidvel['vvel_mean'][:, :, :]
btract_x0 = nidvel['btract'][:, :, :]
x0_src = nidvel['x0'][:]
y0_src = nidvel['y0'][:]
nidvel.close()

nt = len(time_dst)
nx = len(x_dst)
ny = len(y_dst)

nx0 = len(x0_src)
ny0 = len(y0_src)

# The time_range tag in the output filename is derived from the data:
# entry t (CISM year time_dst[t]) covers nominal year time_dst[t]-1, so the
# first/last nominal years are time_dst[0]-1 / time_dst[-1]-1. It therefore
# adjusts automatically when a run is extended by one year.
time_range = f"{int(time_dst[0])-1}-{int(time_dst[-1])-1}"
print('time_range =', time_range)


# ----------------------------------------------------------------------
# Time axis
# ----------------------------------------------------------------------
timeST = np.zeros(nt)

for t in range(nt):
    timeST[t] = days_since_1850(int(time_dst[t]), 1, 1)  # time in days

print(time_dst)


# ----------------------------------------------------------------------
# Velocity variable treatments
# We need to interpolate the velocity variables onto the ISMIP7 grid
# ----------------------------------------------------------------------
def prep_data3d_for_interp(z, y, x, var_to_interp):
    """
    This function prepares the the variable var_to_interp for interpolation by
    reordering the variable based on grid orientation.
    """
    nz = len(z)

    if x[1] < x[0]:
        x = x[::-1]
        for k in range(nz):
            var_temp = var_to_interp[k, :, :]
            var_temp = var_temp[var_temp.columns[::-1]]
            var_to_interp[k, :, :] = var_temp

    if y[1] < y[0]:
        y = y[::-1]
        for k in range(nz):
            var_to_interp[k, :, :] = np.flipud(var_to_interp[k, :, :])

    return var_to_interp


# ----------------------------------------------------------------------
# Main processing loop
# ----------------------------------------------------------------------
fieldReadyVel = ['xvelmean', 'yvelmean', 'strbasemag']
nameCISMvel = ['uvel_mean', 'vvel_mean', 'btract']

count = 0
for field in fieldVel:

    # Select the source variable for this field
    if field in ['xvelmean']:
        var_src = uvel_mean_x0
    if field in ['yvelmean']:
        var_src = vvel_mean_x0
    if field in ['strbasemag']:
        var_src = btract_x0

    # Skip fields whose source variable is not available in the NORCE output
    if var_src is None:
        print('Skipping', field, ': source variable not available in NORCE output')
        continue

    # Create the field output file.
    dstFile = f"{dstDir}{field}_{domain_id}_{source_id}_{ism_id}_{ISM_member_id}_{ESM_id}_{forcing_member_id}_{exp}_{set_counter}_{time_range}.nc"

    # Removing the output file if it already exists.
    if os.path.isfile(dstFile):
        print('yup')
        os.remove(dstFile)

    print('Created field output file', dstFile)
    ncid = Dataset(dstFile, 'w')
    ncid.createDimension('time', None)
    time    = ncid.createVariable('time', 'f4', ('time'))
    time.bounds        = 'time_bnds'
    time.units         = "days since 1850-01-01"
    time.calendar      = "standard"
    time.axis          = "T"
    time.long_name     = "time"
    time.standard_name = "time"
    time[:] = timeST[:]  # time in days since 1850

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

    var_dst = np.zeros((nt, ny, nx))

    var_src[:, :, :] = prep_data3d_for_interp(time_dst, y0_src, x0_src, var_src[:, :, :])

    interp_count = 0
    for t in range(nt):

        # Reading the file to process
        # var_src[:,:,:] = np.where(var_src==0,eps,var_src[:,:,:])
        # var_src[:,:,:] = np.where(var_src==var_src[0,0,0],fill_temp,var_src[:,:,:])

        # Logic to make sure the order on the grid is strictly ascending
        # var_src[:,:,:] = prep_data3d_for_interp(time,y0_src,x0_src,var_src[:,:,:])

        var_src_temp = np.zeros((ny0, nx0))
        var_src_temp[:, :] = var_src[t, :, :]

        # Performing the interpolation

        # Defining the interpolation functions
        myInterpFunction_var = RegularGridInterpolator((x0_src, y0_src), var_src_temp.transpose(), method='linear', bounds_error=False, fill_value=None)

        # Performing the interpolation
        for j in range(ny):
            point_y = np.zeros(nx)
            point_y[:] = y_dst[j]
            pts = (x_dst[:], point_y[:])
            var_dst[t, j, :] = myInterpFunction_var(pts)

    if field in ['xvelmean']:
        xvelmean = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        xvelmean.units         = 'm s-1'
        xvelmean.long_name     = 'mean velocity in x'
        xvelmean.standard_name = 'land_ice_vertical_mean_x_velocity'
        # The data request defines this variable only where there is ice;
        # cells without ice hold the fill value.
        xvelmean[:, :, :] = np.where(ice_mask[:, :, :] > 0,
                                     var_dst[:, :, :]/sPerY,
                                     netCDF4.default_fillvals['f4'])
        del var_dst

    if field in ['yvelmean']:
        yvelmean = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        yvelmean.units         = 'm s-1'
        yvelmean.long_name     = 'mean velocity in y'
        yvelmean.standard_name = 'land_ice_vertical_mean_y_velocity'
        # The data request defines this variable only where there is ice;
        # cells without ice hold the fill value.
        yvelmean[:, :, :] = np.where(ice_mask[:, :, :] > 0,
                                     var_dst[:, :, :]/sPerY,
                                     netCDF4.default_fillvals['f4'])
        del var_dst

    if field in ['strbasemag']:
        strbasemag = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        strbasemag.units         = 'Pa'
        strbasemag.long_name     = 'basal drag'
        strbasemag.standard_name = 'land_ice_basal_drag'
        # The data request defines this variable only where there is ice;
        # cells without ice hold the fill value.
        strbasemag[:, :, :] = np.where(ice_mask[:, :, :] > 0,
                                       var_dst[:, :, :],
                                       netCDF4.default_fillvals['f4'])
        del var_dst


    ncid.group = source_id
    ncid.model = ism_id
    ncid.contact_name = CONTACT_NAME
    ncid.contact_email = CONTACT_EMAIL
    ncid.crs = 'epsg:3031'
    ncid.close()

    count = count + 1
