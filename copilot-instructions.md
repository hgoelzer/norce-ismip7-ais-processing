# Copilot Instructions — NORCE ISMIP7 AIS Processing

Project: post-processing of NORCE CISM AIS runs into ISMIP7-compliant NetCDF output
(11 CORE experiments), validated with the ISM_SimulationChecker (`isschecker`).

## Layout

- 4 processing scripts (module-level, no `main()`; argparse with defaults imported from `config.py`):
  - `ISMIP7_scalar_processing.py` — scalar time series (10 variables) from `scalars.nc`
  - `ISMIP7_variable_HgridST_processing.py` — state variables on x1/y1 grid (lithk, orog, base, topg, sftgif/sftgrf/sftflf)
  - `ISMIP7_variable_HgridFL_processing.py` — flux variables on x1/y1 grid (acabf, libmassbfgr, libmassbffl, dlithkdt, licalvf, lifmassbf, ligroundf)
  - `ISMIP7_variable_VelogridST_processing.py` — velocity variables on x0/y0 grid (xvelmean, yvelmean, strbasemag)
- `run_all_CORE.py` — wrapper over all 4 scripts for all 11 runs (`--exp`, `--dryrun` flags)
- `config.py` — central config (paths, interpreter). **Edit this, not the scripts**, to change paths.
- `CORE.csv` — experiment table: counter_id, experiment_id (lowercase: `ctrl`, not `ctrl2015`), start/end year, ESM_id
- Output: `AIS/NORCE/CISM/CORE/{C001..C011}/` — 27 files per case

## Environments & commands

- Processing python: `/nird/datapeak/NS11016K/miniforge3_26/envs/nc/bin/python` (netCDF4, numpy, scipy)
- Compliance checker: isschecker 0.5.1 in env `/nird/datapeak/NS11016K/miniforge3_26/envs/isschecker` (python 3.14)
- Run everything: `/nird/datapeak/NS11016K/miniforge3_26/envs/nc/bin/python run_all_CORE.py --exp <exp>` (exp = input dir name, e.g. `ctrl2015`)
- Long batch runs: execute in background and check the summary table at the end.

## Input data

- NORCE model output: `/nird/datapeak/NS11016K/users/heig/CISM/AIS/ais_16km_ismip7/AIS_16km_v01_geo01_ghf01_smb03_bas01_otf01_mel02_tun01_pow/ensemble_v1/`
- Per run dir `{exp}_{m}_{r}/`: `output.nc` (state, ice_mask), `output_tavg.nc` (basal_mbal_flux_tavg, calving_flux_tavg), `output_g0.nc` (uvel_mean, vvel_mean, btract on x0/y0), `scalars.nc`, `restart_in.nc`
- 11 runs: {historical,ssp370,ssp126,ssp585,ctrl2015}_{m01,m02}_r01 + ocx_r01
- ESM mapping: m01=CESM2-WACCM, m02=MRI-ESM2-0; ocx has no ESM → ESM_id='ERA', ISM_member_id='m001'; ocx run dir has no `_{ESM_num}` segment
- Experiment → counter: historical→C001/C002 (1970-2014), ssp370→C003/C004 (2015-2100), ssp126→C005/C006 (2015-2300), ssp585→C007/C008 (2015-2300), ctrl2015→C009/C010 (2015-2300), ocx→C011 (1990-2025). m02 gets base counter +1 (`C%03d`).
- HgridFL filePrev logic: historical → ctrl2015 restart_in.nc; ocx → ocx restart_in.nc (no historical predecessor); else → historical output.nc

## Critical domain rules (do not violate)

1. **Use `ice_mask`, never `ice_domain_mask`** — `ice_domain_mask` is ALL ZEROS in this CISM config. Using it zeroes sftgif/sftgrf/sftflf and causes 100%-cell checker errors.
2. **Masking per data request**: variables defined only where ice exists (libmassbfgr, libmassbffl, xvelmean, yvelmean, strbasemag) → `np.where(mask>0, val, netCDF4.default_fillvals['f4'])`. But **dlithkdt and lifmassbf permit NO missing values** → write 0 where there is no ice.
3. **`exp_out` mapping**: checker requires lowercase `ctrl`; input dir is `ctrl2015` → `exp_out = 'ctrl' if exp == 'ctrl2015' else exp` in all 4 scripts (filenames use `exp_out`).
4. **Time conventions**: ST variables → Jan 1 of year+1; FL variables → Jul 1 of year; `time_range` tag derived from data (`time_dst[t]-1`).
5. **licalvf** has a temporary positive-clamp (`np.where(calving>0, 0, calving)`); **lifmassbf** is zeros — `latmelt_flux_tavg` not yet available in model output. NCAR-original reads are kept as comments for easy switchover.
6. **netCDF4 auto-masking pitfall**: `v == fv` never matches on auto-masked reads. To verify fill placement use `nid.set_auto_mask(False)` + `np.isclose(v, fv, rtol=1e-5)`.

## Compliance checker notes

- Checker results (2026-09-26): all 11 cases pass except (a) accepted cosmetic base/topg cm-level errors (ELEVATION_TOLERANCE=1e-2; user decision — do NOT "fix"), (b) C011 ocx: 27 'ERA' naming errors — expected for reanalysis forcing, left as is.
- Local test-only patch: `ocx;1990;1990;2025;36` added to `.../envs/isschecker/lib/python3.14/site-packages/isschecker/data/experiments_ismip7.csv` (backup `.orig`). Lost on isschecker update. `VALID_ESM_NAMES` in checker.py intentionally NOT patched.
- The user reruns the checker themselves — do not run it unprompted.

## Workflow conventions

- User drives step-by-step; confirm before large changes or full-batch reruns.
- `cp` is aliased interactive on the login node — use `\cp -f`.
- Commit messages: concise imperative summary + bullet body of the substantive changes.
