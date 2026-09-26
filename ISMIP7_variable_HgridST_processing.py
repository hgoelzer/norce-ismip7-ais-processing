#!/usr/bin/env python
"""
ISMIP7 AIS Hgrid state variable processing (Hgrid ST)

Converted from ISMIP7_variable_HgridST_processing.ipynb to a plain Python script.
"""

# Import packages
import numpy as np
from netCDF4 import Dataset
import sys, os
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

fileVar = f"{path_exp}/{exp}_{ESM_num}_{RCM_num}/output.nc"


fieldST = ['lithk', 'orog', 'topg', 'base', 'sftgif', 'sftgrf', 'sftflf']


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

# ice_mask = nidsrc['ice_mask'][1::, :, :]  # not available in NORCE output
ice_mask = nidsrc['ice_domain_mask'][1::, :, :]
f_ground = nidsrc['f_ground_cell'][1::, :, :]*ice_mask
f_float = (1-f_ground)*ice_mask

thk_dst   = nidsrc['thk'][1::, :, :]
topg_dst  = nidsrc['topg'][1::, :, :]
usurf_dst = nidsrc['usurf'][1::, :, :]
lsurf_dst = nidsrc['lsurf'][1::, :, :]

nidsrc.close()

nt = len(time_dst)
nx = len(x_dst)
ny = len(y_dst)


print(f"nt={nt}, ny={ny}, nx={nx}")


# ----------------------------------------------------------------------
# Time axis
# ----------------------------------------------------------------------
timeST = np.zeros(nt)

for t in range(nt):
    timeST[t] = days_since_1850(int(time_dst[t]), 1, 1)  # time in days

print(time_dst)


# ----------------------------------------------------------------------
# Main processing loop
# ----------------------------------------------------------------------
for field in fieldST:
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


    if field in ['lithk']:
        lithk = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        lithk.units         = 'm'
        lithk.long_name     = 'ice thickness'
        lithk.standard_name = 'land_ice_thickness'
        lithk.comment       = 'the thickness of the ice sheet'
        lithk[:, :, :] = thk_dst[:, :, :]

    if field in ['orog']:
        orog = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        orog.units         = 'm'
        orog.long_name     = 'surface elevation'
        orog.standard_name = 'surface_altitude'
        orog.comment       = 'the altitude or surface elevation of the ice sheet'
        orog[:, :, :] = usurf_dst[:, :, :]

    if field in ['base']:
        base = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        base.units         = 'm'
        base.long_name     = 'base elevation'
        base.standard_name = 'base_altitude'
        base.comment       = 'the altitude of the lower ice surface elevation of the ice sheet'
        base[:, :, :] = lsurf_dst[:, :, :]

    if field in ['topg']:
        topg = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        topg.units         = 'm'
        topg.long_name     = 'bedrock elevation'
        topg.standard_name = 'bedrock_altitude'
        topg.comment       = 'the bedrock topography'
        topg[:, :, :] = topg_dst[:, :, :]


    if field in ['sftgif']:
        sftgif = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        sftgif.units         = '1'
        sftgif.long_name     = 'land ice area fraction'
        sftgif.standard_name = 'land_ice_area_fraction'
        sftgif.comment       = 'fraction of grid cell covered by land ice (ice sheet, ice shelf, ice cap, glacier)'
        sftgif[:, :, :] = ice_mask[:, :, :]

    if field in ['sftgrf']:
        sftgrf = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        sftgrf.units         = '1'
        sftgrf.long_name     = 'grounded ice sheet area fraction'
        sftgrf.standard_name = 'grounded_ice_sheet_area_fraction'
        sftgrf.comment       = 'fraction of grid cell covered by grounded ice sheet, where grounded indicates that the quantity corresponds to the ice sheet that flows over bedrock'
        sftgrf[:, :, :] = f_ground[:, :, :]

    if field in ['sftflf']:
        sftflf = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        sftflf.units         = '1'
        sftflf.long_name     = 'floating ice sheet area fraction'
        sftflf.standard_name = 'floating_ice_shelf_area_fraction'
        sftflf.comment       = 'fraction of grid cell covered by ice sheet flowing over seawater'
        sftflf[:, :, :] = f_float[:, :, :]


    ncid.group = 'NORCE'
    ncid.model = 'CISM3'
    ncid.contact_name = 'Heiko Goelzer'
    ncid.contact_email = 'heig@norceresearch.no'
    ncid.crs = 'epsg:3031'
    ncid.close()
