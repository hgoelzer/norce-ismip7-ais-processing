#!/usr/bin/env python
"""
ISMIP7 AIS scalar data processing

Converted from ISMIP7_scalar_processing.ipynb to a plain Python script.
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
# Strings for file naming convention:
# ----------------------------------------------------------------------
domain_id = 'AIS'  # Ice Sheet name
source_id = 'NORCE'
ism_id = 'CISM'
set_id = 'CORE'

dayPerY = 365.
sPerY = 31556926.

# ----------------------------------------------------------------------
# Command line arguments (defaults reproduce the previous hard-coded run)
# ----------------------------------------------------------------------
parser = argparse.ArgumentParser(description='ISMIP7 AIS scalar data processing')
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
# Experiment lookup: set_counter and time_range for the 11 CORE runs
# (m01/m02 pairs share the same set_counter; ocx is C011)
# ----------------------------------------------------------------------
exp_map = {
    'historical': ('C001', '1970-2014'),
    'ssp370':     ('C003', '2015-2100'),
    'ssp126':     ('C005', '2015-2300'),
    'ssp585':     ('C007', '2015-2300'),
    'ctrl2015':   ('C009', '2015-2300'),
    'ocx':        ('C011', '1979-2025'),
}
if exp in exp_map:
    set_counter_base, time_range = exp_map[exp]
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

fileScalar = f"{run_dir}/scalars.nc"


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
# Open input file
# ----------------------------------------------------------------------
try:
    cismfilescalar = Dataset(fileScalar, 'r')
    print('filenameScalar =', fileScalar)
except Exception:
    print('Error: Unable to open CISM file for expt ', exp)
    sys.exit('exiting program now')


# ----------------------------------------------------------------------
# READ SCALARS (function of time only).
# ----------------------------------------------------------------------
try:
    iareafc = cismfilescalar.variables['iareaf'][1::]                # area covered by floating ice (m^2)
    iareagc = cismfilescalar.variables['iareag'][1::]                # area covered by grounded ice (m^2)
    imassc  = cismfilescalar.variables['imass'][1::]                 # total ice mass (kg)
    imafc   = cismfilescalar.variables['imass_above_flotation'][1::] # total ice mass above flotation(kg)
    timeS   = cismfilescalar.variables['time'][:]

    nt = len(timeS)
    print('nt=', nt)
    tsmbfc  = cismfilescalar.variables['total_smb_flux'][:]      # total surface mass balance flux (kg.s^-1)
    tbmbfc  = cismfilescalar.variables['total_bmb_flux'][:]      # total basal mass balance flux (kg.s^-1)
    tbmltfc = cismfilescalar.variables['total_bmlt_float'][:]    # total basal mass balance flux for floating ice (kg.s^-1)
    tcalfc  = cismfilescalar.variables['total_calving_flux'][:]  # total calving mass balance flux (kg.s^-1)
    # tglfc   = cismfilescalar.variables['total_gl_flux'][:]       # total grounding line flux(kg.s^-1) - not available in NORCE output
    # tlatmeltfc  = cismfilescalar.variables['total_latmelt_flux'][:] # total lateral melt flux (kg.s^-1) - not available in NORCE output
    tglfc   = np.zeros_like(tcalfc)  # zeros - not available in NORCE output
    tlatmeltfc = np.zeros_like(tcalfc)  # zeros - not available in NORCE output
except Exception:
    sys.exit('Error: The output file is missing needed scalar(s).')


# ----------------------------------------------------------------------
# Time conversion helper
# ----------------------------------------------------------------------
EPOCH = date(1850, 1, 1)

def days_since_1850(year, month, day):
    """Whole days from 1850-01-01 (which is day 0) to the given Gregorian date."""
    return (date(year, month, day) - EPOCH).days


# ----------------------------------------------------------------------
# Main processing loop
# ----------------------------------------------------------------------
ST_var = ['lim', 'limnsw', 'iareagr', 'iareafl']
FL_var = ['tendacabf', 'tendlibmassbfgr', 'tendlibmassbffl',
          'tendlicalvf', 'tendlifmassbf', 'tendligroundf']


outField = ['lim', 'limnsw', 'iareagr', 'iareafl', 'tendacabf', 'tendlibmassbfgr',
            'tendlibmassbffl', 'tendlicalvf', 'tendlifmassbf', 'tendligroundf']

# Fields that needs to be overwritten for their first value
fieldoverwrite = ['tendacabf', 'tendlibmassbfgr', 'tendlibmassbffl',
                  'tendlicalvf', 'tendlifmassbf', 'tendligroundf']

timeST = np.zeros(nt)
timeFL = np.zeros(nt-1)


for t in range(nt):
    timeST[t] = days_since_1850(int(timeS[t]), 1, 1)  # time in days

for t in range(nt-1):
    timeFL[t] = days_since_1850(int(timeS[t]), 7, 1)  # time in days


# count = 0
for field in outField:
    # Create the field output file.
    outfilenamescal = f"{dstDir}{field}_{domain_id}_{source_id}_{ism_id}_{ISM_member_id}_{ESM_id}_{forcing_member_id}_{exp}_{set_counter}_{time_range}.nc"

    # Removing the output file if it already exists.
    if os.path.isfile(outfilenamescal):
        print('yup')
        os.remove(outfilenamescal)

    print('Created field output file', outfilenamescal)

    if field in ST_var:
        ncid = Dataset(outfilenamescal, 'w')
        ncid.createDimension('time', None)
        time    = ncid.createVariable('time', 'f4', ('time'))
        time[:] = timeST[1::]

        # time[:] = (timeS[1::]-1850)*dayPerY # time in days

        time.units         = "days since 1850-01-01"
        time.calendar      = "standard"
        time.axis          = "T"
        time.long_name     = "time"
        time.standard_name = "time"

        if field in ['lim']:
            lim = ncid.createVariable(field, 'f4', ('time'))
            lim.units         = 'kg'
            lim.long_name     = 'total ice mass'
            lim.standard_name = 'land_ice_mass'
            lim[:] = imassc[:]

        if field in ['limnsw']:
            limnsw = ncid.createVariable(field, 'f4', ('time'))
            limnsw.units         = 'kg'
            limnsw.long_name     = 'mass above flotation'
            limnsw.standard_name = 'land_ice_mass_not_displacing_sea_water'
            limnsw[:] = imafc[:]

        if field in ['iareagr']:
            iareagr = ncid.createVariable(field, 'f4', ('time'))
            iareagr.units         = 'm^2'
            iareagr.long_name     = 'grounded ice area'
            iareagr.standard_name = 'grounded_ice_sheet_area'
            iareagr[:] = iareagc[:]

        if field in ['iareafl']:
            iareafl = ncid.createVariable(field, 'f4', ('time'))
            iareafl.units         = 'm^2'
            iareafl.long_name     = 'floating ice area'
            iareafl.standard_name = 'floating_ice_shelf_area'
            iareafl[:] = iareafc[:]

        ncid.group = 'NORCE'
        ncid.model = 'CISM3'
        ncid.contact_name = 'Heiko Goelzer'
        ncid.contact_email = 'heig@norceresearch.no'
        ncid.crs = 'epsg:3031'
        ncid.close()


    if field in FL_var:
        ncid = Dataset(outfilenamescal, 'w')
        ncid.createDimension('time', None)
        ncid.createDimension('bnds', 2)

        time = ncid.createVariable('time', 'f4', ('time'))
        time.bounds        = 'time_bnds'
        time.units         = "days since 1850-01-01"
        time.calendar      = "standard"
        time.axis          = "T"
        time.long_name     = "time"
        time.standard_name = "time"
        # time[:] = (timeS[0:-1]-1850)*dayPerY + 182 # time in days
        time[:] = timeFL[:]

        time_bounds = ncid.createVariable('time_bounds', 'f4', ('time', 'bnds',))
        # time_bounds[:,0] = (timeS[0:-1]-1850)*dayPerY
        # time_bounds[:,1] = (timeS[0:-1]-1850)*dayPerY + dayPerY
        time_bounds[:, 0] = timeST[0:-1]
        time_bounds[:, 1] = timeS[1::]

        if field in ['tendacabf']:
            tendacabf = ncid.createVariable(field, 'f4', ('time'))
            tendacabf.units         = 'kg s-1'
            tendacabf.long_name     = 'total SMB flux'
            tendacabf.standard_name = 'tendency_of_land_ice_mass_due_to_surface_mass_balance'
            tendacabf[:] = (tsmbfc[1::] + tsmbfc[0:-1])/2.

        if field in ['tendlibmassbfgr']:
            tendlibmassbfg = ncid.createVariable(field, 'f4', ('time'))
            tendlibmassbfg.units         = 'kg s-1'
            tendlibmassbfg.long_name     = 'Total BMB flux beneath grounded ice'
            tendlibmassbfg.standard_name = 'tendency_of_land_ice_mass_due_to_basal_mass_balance'
            tendlibmassbfg[:] = (tbmbfc[1::] + tbmbfc[0:-1])/2. - (tbmltfc[1::] + tbmltfc[0:-1])/2.

        if field in ['tendlibmassbffl']:
            tendlibmassbffl = ncid.createVariable(field, 'f4', ('time'))
            tendlibmassbffl.units         = 'kg s-1'
            tendlibmassbffl.long_name     = 'total BMB flux beneath floating ice'
            tendlibmassbffl.standard_name = 'tendency_of_land_ice_mass_due_to_basal_mass_balance'
            tendlibmassbffl[:] = (tbmltfc[1::] + tbmltfc[0:-1])/2.

        if field in ['tendlicalvf']:
            tendlicalvf = ncid.createVariable(field, 'f4', ('time'))
            tendlicalvf.units         = 'kg s-1'
            tendlicalvf.long_name     = 'total calving flux'
            tendlicalvf.standard_name = 'tendency_of_land_ice_mass_due_to_calving'
            tendlicalvf[:] = (tcalfc[1::] + tcalfc[0:-1])/2.

        if field in ['tendlifmassbf']:
            # Not written: source variable not available in NORCE output
            tendlifmassbf = ncid.createVariable(field, 'f4', ('time'))
            tendlifmassbf.units         = 'kg s-1'
            tendlifmassbf.long_name     = 'total calving and ice front melting flux'
            tendlifmassbf.standard_name = 'tendency_of_land_ice_mass_due_to_calving_and_ice_front_melting'
            tendlifmassbf[:] = (tlatmeltfc[1::] + tlatmeltfc[0:-1])/2.  # zeros - not available in NORCE output

        if field in ['tendligroundf']:
            # Not written: source variable not available in NORCE output
            tendligroundf = ncid.createVariable(field, 'f4', ('time'))
            tendligroundf.units         = 'kg s-1'
            tendligroundf.long_name     = 'total grounding line flux'
            tendligroundf.standard_name = 'tendency_of_grounded_ice_mass'
            tendligroundf[:] = (tglfc[1::] + tglfc[0:-1])/2.  # zeros - not available in NORCE output

        ncid.group = 'NORCE'
        ncid.model = 'CISM3'
        ncid.contact_name = 'Heiko Goelzer'
        ncid.contact_email = 'heig@norceresearch.no'
        ncid.crs = 'epsg:3031'
        ncid.close()

    # We need to overwrite the 0-default value of the tendency scalars.
    # if field in fieldoverwrite:
    #    if (exp=='ctrl')or(exp=='historical'):
    #       # Here we replace the first value by the second value.
    #       name[0] = name[1]
