# norce-ismip7-ais-processing

NORCE post-processing of CISM AIS output to ISMIP7 AIS CORE format.

The scripts read the NORCE CISM `ensemble_v1` model output and write
ISMIP7-formatted NetCDF files per experiment and variable, organised in
`C001`–`C011` output directories (see `CORE.csv` for the experiment list).

## Repository contents

| File | Purpose |
|------|---------|
| `config.py` | Top-level configuration: Python interpreter, model output path, output path |
| `run_all_CORE.py` | Wrapper: runs all 4 scripts for all 11 CORE experiments |
| `ISMIP7_scalar_processing.py` | Scalar (time-only) variables: lim, limnsw, iareagr, iareafl, tend* |
| `ISMIP7_variable_HgridST_processing.py` | Horizontal-grid state variables: lithk, orog, topg, base, sftgif, sftgrf, sftflf |
| `ISMIP7_variable_HgridFL_processing.py` | Horizontal-grid flux variables: acabf, dlithkdt, ligroundf, lifmassbf |
| `ISMIP7_variable_VelogridST_processing.py` | Velocity-grid state variables (skipped: source vars not in NORCE output) |
| `CORE.csv` | ISMIP7 CORE experiment definition (counter_id, experiment, years, ESM) |

## Configuration

All paths and the Python interpreter are set in **`config.py`** and apply to
all scripts at once:

- `PYTHON` — interpreter used by the wrapper (needs netCDF4, numpy, scipy)
- `PATH_EXP` — path to the CISM `ensemble_v1` model output directory
- `DST_PATH` — base path for the ISMIP7 output data

Individual scripts can still override the paths on the command line with
`--path_exp` and `--dstPath`.

## Running all experiments (wrapper)

```bash
python run_all_CORE.py                 # all 11 CORE runs
python run_all_CORE.py --exp ssp126    # one experiment (all members)
python run_all_CORE.py --dryrun        # print commands without executing
```

The wrapper cycles through the 11 (experiment, ESM member) combinations,
skips runs with missing input, and prints a summary table at the end.

## Running standalone scripts

Each processing script takes the same arguments:

```bash
python ISMIP7_scalar_processing.py \
    --exp ssp585 \
    --ESM_num m01 \
    --RCM_num r01
# optional overrides:
#    --path_exp /path/to/ensemble_v1
#    --dstPath  /path/to/output
```

- `--exp`: `historical`, `ssp370`, `ssp126`, `ssp585`, `ctrl2015`, `ocx`
- `--ESM_num`: `m01` (CESM2-WACCM) or `m02` (MRI-ESM2-0); the `ocx` run has
  no ESM member and is identified by `--RCM_num r01` only
- Defaults (`ssp585`, `m01`, `r01`) reproduce a single standard run

## Output

Files are written to `{DST_PATH}/AIS/NORCE/CISM/CORE/{C001..C011}/` with the
ISMIP7 naming convention:

```
{field}_{domain_id}_{source_id}_{ism_id}_{ISM_member_id}_{ESM_id}_{forcing_member_id}_{exp}_{set_counter}_{time_range}.nc
```

e.g. `lim_AIS_NORCE_CISM_m001_CESM2-WACCM_f001_ssp585_C007_2015-2300.nc`

## Known data gaps

Some NCAR source variables are not available in the NORCE CISM output. The
scripts read the NORCE equivalents where they exist and fall back to
zeros/None otherwise; the original NCAR reads are kept as comments for easy
switch-over when the variables become available. Affected fields:
`libmassbfgr`, `libmassbffl`, `licalvf`, `xvelmean`, `yvelmean`,
`strbasemag` (skipped) and `lifmassbf`, `tendlifmassbf`, `tendligroundf`,
`ligroundf` (zero-filled).
