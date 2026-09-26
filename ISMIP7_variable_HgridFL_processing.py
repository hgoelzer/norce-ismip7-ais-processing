#!/usr/bin/env python
"""
ISMIP7 AIS flux variables processing (Hgrid FL)

Converted from ISMIP7_variable_HgridFL_processing.ipynb to a plain Python script.
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
source_id = 'NCAR'
ism_id = 'CISM'
set_id = 'CORE'

dayPerY = 365.
sPerY = 31536000.
rhoi = 917

fill_value = netCDF4.default_fillvals['f4']

ESM_id = 'CESM2-WACCM'
ISM_member_id = 'm001'
forcing_member_id = 'f001'
# exp = 'historical'
exp = 'ssp585'
res = '8000'

res_km_str = str(int(int(res)/1000))

path_exp = '/glade/campaign/cesm/development/liwg/leguy/ISMIP7/Experiments/AIS/'

fileVar = f"{path_exp}{ESM_id}/{exp}/out_Antarctica_{res_km_str}km.thk.nc"
fileVarVel = f"{path_exp}{ESM_id}/{exp}/out_Antarctica_{res_km_str}km.velo.nc"


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


if exp in ['historical']:
    set_counter = 'C001'
    time_range = '2000-2014'

if exp in ['ssp585']:
    set_counter = 'C007'
    time_range = '2015-2300'


# ----------------------------------------------------------------------
# Output directory
# ----------------------------------------------------------------------
dstPath = f"/glade/campaign/cesm/development/liwg/leguy/ISMIP7/Experiments/{domain_id}/data_processing/"
dstDir = f"{dstPath}{domain_id}/{source_id}/{ism_id}/{set_id}/{set_counter}/"

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

time_dst = nidsrc['time'][:]
x_dst = nidsrc['x1'][:]
y_dst = nidsrc['y1'][:]

ice_mask = nidsrc['ice_mask'][1::, :, :]
f_ground = nidsrc['f_ground_cell'][1::, :, :]*ice_mask
f_float = (1-f_ground)*ice_mask


acab_dst         = nidsrc['acab_applied_tavg'][1::, :, :]
basal_flux_dst   = nidsrc['basal_mbal_flux_tavg'][1::, :, :]
dthckdt_dst      = nidsrc['dthck_dt'][1::, :, :]
calving_flux_dst = nidsrc['calving_flux_tavg'][1::, :, :]
latmelt_dst      = nidsrc['latmelt_flux_tavg'][1::, :, :]

thk_init = nidsrc['thk'][0:2, :, :]
dthckdt_dst[0, :, :] = (thk_init[1, :, :]-thk_init[0, :, :])/(time_dst[1]-time_dst[0])

nidsrc.close()

nt = len(time_dst)
nx = len(x_dst)
ny = len(y_dst)


print(f"nt={nt}, ny={ny}, nx={nx}")


# readListPrevExptString = [ 'licalvf', 'dlithkdt',  'acabf']
if exp in ['historical']:
    # Need to read in the last time slice of the spin-up
    filePrev = f"/glade/campaign/cesm/development/liwg/leguy/ISMIP7/Spinup_input/Antarctica_{res_km_str}km.restart.spin.nc"

else:
    # Need to read the last time slice of the historical
    filePrev = f"{path_exp}{ESM_id}/historical/out_Antarctica_{res_km_str}km.thk.nc"

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
timeST = np.zeros(nt)
timeFL = np.zeros(nt-1)

for t in range(nt):
    timeST[t] = days_since_1850(int(time_dst[t]), 1, 1)  # time in days

for t in range(nt-1):
    timeFL[t] = days_since_1850(int(time_dst[t]), 7, 1)  # time in days

print(time_dst)


# ----------------------------------------------------------------------
# Main processing loop
# ----------------------------------------------------------------------
for field in fieldFL:
    # Create the field output file.
    dstFile = f"{dstDir}{field}_{domain_id}_{source_id}_{ism_id}_{ISM_member_id}_{ESM_id}_{forcing_member_id}_{exp}_{set_counter}_{time_range}.nc"

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

    time_bounds = ncid.createVariable('time_bounds', 'f4', ('time', 'bnds',))
    time_bounds[:, 0] = timeST[0:-1]
    time_bounds[:, 1] = timeST[1::]

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
        acabf[:, :, :] = acab_dst[1::, :, :]*rhoi/sPerY

    if field in ['libmassbfgr']:
        libmassbfgr = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        libmassbfgr.units         = 'kg m-2 s-1'
        libmassbfgr.long_name     = 'basal mass balance flux beneath grounded ice'
        libmassbfgr.standard_name = 'land_ice_basal_specific_mass_balance_flux'
        libmassbfgr[:, :, :] = basal_flux_dst[1::, :, :]*f_ground[1::, :, :]

    if field in ['libmassbffl']:
        libmassbffl = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        libmassbffl.units         = 'kg m-2 s-1'
        libmassbffl.long_name     = 'basal mass balance flux beneath floating ice'
        libmassbffl.standard_name = 'land_ice_basal_specific_mass_balance_flux'
        libmassbffl[:, :, :] = basal_flux_dst[1::, :, :]*f_float[1::, :, :]

    if field in ['dlithkdt']:
        dlithkdt = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        dlithkdt.units         = 'm s-1'
        dlithkdt.long_name     = 'ice thickness imbalance'
        dlithkdt.standard_name = 'tendency_of_land_ice_thickness'
        dlithkdt[:, :, :] = (dthckdt_dst[1:, :, :] + dthckdt_dst[0:-1, :, :])/2./sPerY

    if field in ['licalvf']:
        licalvf = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        licalvf.units         = 'kg m-2 s-1'
        licalvf.long_name     = 'calving flux'
        licalvf.standard_name = 'land_ice_specific_mass_flux_due_to_calving'
        # licalvf[:,:,:] = calving_flux_dst[1::,:,:]
        # Temporary fix for positive values
        licalvf[:, :, :] = np.where(calving_flux_dst[1::, :, :] > 0, 0, calving_flux_dst[1::, :, :])

    if field in ['lifmassbf']:
        lifmassbf = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        lifmassbf.units         = 'kg m-2 s-1'
        lifmassbf.long_name     = 'loss of ice mass resulting from ice front melting'
        lifmassbf.standard_name = 'land_ice_specific_mass_flux_due_to_ice_front_melting'
        lifmassbf[:, :, :] = latmelt_dst[1::, :, :]


    if field in ['ligroundf']:
        ligroundf = ncid.createVariable(field, 'f4', ('time', 'y', 'x'), fill_value=netCDF4.default_fillvals['f4'])
        ligroundf.units         = 'kg m-2 s-1'
        ligroundf.long_name     = 'Flux of ice mass across the grounding line'
        ligroundf.standard_name = 'land_ice_specific_grounding_line_flux'
        ligroundf[:, :, :] = 0

    ncid.group = 'NCAR'
    ncid.model = 'CISM3'
    ncid.contact_name = 'Gunter Leguy and Bill Lipscomb'
    ncid.contact_email = 'gunterl@ucar.edu and lipscomb@ucar.edu'
    ncid.crs = 'epsg:3031'
    ncid.close()
