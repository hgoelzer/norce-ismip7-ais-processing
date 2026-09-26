#!/usr/bin/env python
"""
ISMIP7 AIS velocity-grid state variable processing (Velogrid ST)

Converted from ISMIP7_variable_VelogridST_processing.ipynb to a plain Python script.
"""

# Import packages
import numpy as np
from netCDF4 import Dataset
import sys, os
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
ism_id = 'CISM'
set_id = 'CORE'

dayPerY = 365.
sPerY = 31536000.

fill_value = netCDF4.default_fillvals['f4']

ESM_id = 'CESM2-WACCM'
ESM_num = 'm01'
RCM_num = 'r01'
ISM_member_id = 'm001'
forcing_member_id = 'f001'
# exp = 'historical'
exp = 'ssp585'
res = '8000'

res_km_str = str(int(int(res)/1000))

path_exp = '/nird/datapeak/NS11016K/users/heig/CISM/AIS/ais_16km_ismip7/AIS_16km_v01_geo01_ghf01_smb03_bas01_otf01_mel02_tun01_pow/ensemble_v1'

# NOTE: There is no separate velo.nc file in the NORCE output. All
# variables are stored in the single output.nc file. However, output.nc
# does not contain uvel_mean, vvel_mean and btract (see below).
fileVar = f"{path_exp}/{exp}_{ESM_num}_{RCM_num}/output.nc"


fieldVel = ['xvelmean', 'yvelmean', 'strbasemag']


if exp in ['historical']:
    set_counter = 'C001'
    time_range = '2000-2014'

if exp in ['ssp585']:
    set_counter = 'C007'
    time_range = '2015-2300'


# ----------------------------------------------------------------------
# Output directory
# ----------------------------------------------------------------------
dstPath = f"/nird/datalake/NS11016K/users/heig/ISMIP7/data_processing"
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

time_dst = nidsrc['time'][1::]
x_dst = nidsrc['x1'][:]
y_dst = nidsrc['y1'][:]

x0_src = nidsrc['x0'][:]
y0_src = nidsrc['y0'][:]

# NOTE: The NORCE output (output.nc) does not contain the velocity
# variables uvel_mean, vvel_mean and btract of the NCAR velo.nc file.
# The reads are therefore commented out and the corresponding fields
# are skipped in the processing loop below.
# uvel_mean_x0 = nidsrc['uvel_mean'][1::, :, :]
# vvel_mean_x0 = nidsrc['vvel_mean'][1::, :, :]
# btract_x0 = nidsrc['btract'][1::, :, :]
uvel_mean_x0 = None
vvel_mean_x0 = None
btract_x0 = None

nt = len(time_dst)
nx = len(x_dst)
ny = len(y_dst)

nx0 = len(x0_src)
ny0 = len(y0_src)


nidsrc.close()


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
        xvelmean[:, :, :] = var_dst[:, :, :]/sPerY
        del var_dst

    if field in ['yvelmean']:
        yvelmean = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        yvelmean.units         = 'm s-1'
        yvelmean.long_name     = 'mean velocity in y'
        yvelmean.standard_name = 'land_ice_vertical_mean_y_velocity'
        yvelmean[:, :, :] = var_dst[:, :, :]/sPerY
        del var_dst

    if field in ['strbasemag']:
        strbasemag = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        strbasemag.units         = 'Pa'
        strbasemag.long_name     = 'basal drag'
        strbasemag.standard_name = 'land_ice_basal_drag'
        strbasemag[:, :, :] = var_dst[:, :, :]
        del var_dst


    ncid.group = 'NORCE'
    ncid.model = 'CISM3'
    ncid.contact_name = 'Heiko Goelzer'
    ncid.contact_email = 'heig@norceresearch.no'
    ncid.crs = 'epsg:3031'
    ncid.close()

    count = count + 1
