# Copilot Instructions — NORCE ISMIP7 AIS Processing

Project: post-processing of NORCE CISM AIS runs into ISMIP7-compliant NetCDF output
(11 CORE experiments), validated with the ISM_SimulationChecker (`isschecker`).

## Layout

- 4 processing scripts (module-level, no `main()`; argparse with defaults imported from `config.py`):
  - `ISMIP7_scalar_processing.py` — scalar time series (10 variables) from `scalars.nc`
  - `ISMIP7_variable_HgridST_processing.py` — state variables on x1/y1 grid (lithk, orog, base, topg, sftgif/sftgrf/sftflf)
  - `ISMIP7_variable_HgridFL_processing.py` — flux variables on x1/y1 grid (acabf, libmassbfgr, libmassbffl, dlithkdt, licalvf, lifmassbf, ligroundf)
  - `ISMIP7_variable_VelogridST_processing.py` — velocity variables on x0/y0 grid (xvelmean, yvelmean, strbasemag)
- `run_all_CORE.py` — wrapper over all 4 scripts for all 11 runs (`--exp` accepts experiment names and/or CORE counter ids `C001..C011`, `nargs='+'`; `--dryrun` flag). Child scripts are launched with `sys.executable` — the interpreter that runs the wrapper.
- `config.py` — central config (paths, `ISM_ID`, metadata: `DOMAIN_ID`, `SOURCE_ID`, `SET_ID`, `CONTACT_NAME`, `CONTACT_EMAIL`). **Edit this, not the scripts**, to change paths/metadata. No `PYTHON` constant: the wrapper uses `sys.executable`.
- `config_16km.py` — saved 16km settings; to re-run the 16km ensemble, copy it over `config.py`
- `CORE.csv` — experiment table: counter_id, experiment_id (lowercase: `ctrl`, not `ctrl2015`), start/end year, ESM_id
- Output: `AIS/NORCE/{ism_id}/CORE/{C001..C011}/` — 27 files per case; `ism_id` comes from `ISM_ID` in `config.py` (CLI override: `--ism_id`)

## Environments & commands

- Processing python: `/nird/datapeak/NS11016K/miniforge3_26/envs/nc/bin/python` (netCDF4, numpy, scipy). Needs only netCDF4/numpy/scipy; recreate with `conda create -n ismip7 -c conda-forge python=3.11 netcdf4 numpy scipy`.
- Compliance checker: isschecker 0.5.1 in env `/nird/datapeak/NS11016K/miniforge3_26/envs/isschecker` (python 3.14)
- Run everything: `<python> run_all_CORE.py --exp <exp|counter_id>` (exp = data-request name, e.g. `ctrl`; counter ids C001..C011 also accepted; several selections at once: `--exp C003 C004 ctrl`)
- Long batch runs: execute in background and check the summary table at the end.

## Input data

- Two ensembles, selected via `PATH_EXP` + `ISM_ID` in `config.py` (swap pattern: `config.py` is the active config; `config_16km.py` holds the 16km settings):
  - 8km: `.../ais_08km_ismip7/AIS_08km_v03_geo01_ghf01_smb03_bas01_otf01_mel02_tun01_pow/ensemble_v1/` with `ISM_ID='CISM'` (output → `AIS/NORCE/CISM/CORE/`; changed from 'CISM8' 2026-09-30, output dir cleaned and all 11 runs regenerated)
  - 16km: `.../ais_16km_ismip7/AIS_16km_v01_geo01_ghf01_smb03_bas01_otf01_mel02_tun01_pow/ensemble_v1/` with `ISM_ID='CISM'` (output → `AIS/NORCE/CISM/CORE/`; NOTE: both configs now use 'CISM', so the two resolutions share the output tree — do not run both without moving/renaming output in between)
- Per run dir `{exp}_{m}_{r}/`: `output.nc` (state, ice_mask), `output_tavg.nc` (basal_mbal_flux_tavg, calving_flux_tavg), `output_g0.nc` (uvel_mean, vvel_mean, btract on x0/y0), `scalars.nc`, `restart_in.nc`
- 11 runs: {historical,ssp370,ssp126,ssp585,ctrl2015}_{m01,m02}_r01 + ocx_r01
- ESM mapping: m01=CESM2-WACCM, m02=MRI-ESM2-0; ocx has no ESM → ESM_id='ERA', ISM_member_id='m001'; ocx run dir has no `_{ESM_num}` segment
- Experiment → counter: historical→C001/C002 (1970-2014), ssp370→C003/C004 (2015-2100), ssp126→C005/C006 (2015-2300), ssp585→C007/C008 (2015-2300), ctrl→C009/C010 (2015-2300), ocx→C011 (1990-2025). m02 gets base counter +1 (`C%03d`).
- **`ctrl` naming**: `--exp ctrl` selects the control runs (data-request name, used in output file names); the input directories on disk keep their `ctrl2015_*` names — resolved via the `run_dir` helper in each script and in `run_all_CORE.py`. Never pass `ctrl2015` to `--exp`.
- **Metadata**: `ncid.group = source_id`, `ncid.model = ism_id`, contacts from `CONTACT_NAME`/`CONTACT_EMAIL` in config — all driven by `config.py`, never hardcoded in the scripts (the old hardcoded `model='CISM3'` was a bug, fixed 2026-09-30).
- HgridFL filePrev logic: historical → ctrl2015 restart_in.nc; ocx → ocx restart_in.nc (no historical predecessor); else → historical output.nc

## Critical domain rules (do not violate)

1. **Use `ice_mask`, never `ice_domain_mask`** — `ice_domain_mask` is ALL ZEROS in this CISM config. Using it zeroes sftgif/sftgrf/sftflf and causes 100%-cell checker errors.
2. **Masking per data request**: variables defined only where ice exists (libmassbfgr, libmassbffl, xvelmean, yvelmean, strbasemag) → `np.where(mask>0, val, netCDF4.default_fillvals['f4'])`. But **dlithkdt and lifmassbf permit NO missing values** → write 0 where there is no ice.
3. **`ctrl` naming**: the data-request experiment name is `ctrl` (used in `--exp`, `exp_map`, and output file names); the input directory is `ctrl2015` — the mapping lives only in the `run_dir` helper in each script and in `run_all_CORE.py`.
4. **Time conventions**: ST variables → Jan 1 of year+1; FL variables → Jul 1 of year; `time_range` tag derived from data (`time_dst[t]-1`).
5. **CF bounds naming**: the time bounds variable MUST be named `time_bnds` (matching `time:bounds = "time_bnds"`). It was previously created as `time_bounds`, which the checker flagged as an unexpected variable in every FL/scalar file with bounds. Fixed 2026-09-27 in `ISMIP7_scalar_processing.py` and `ISMIP7_variable_HgridFL_processing.py`.
6. **licalvf** has a temporary positive-clamp (`np.where(calving>0, 0, calving)`); **lifmassbf** is zeros — `latmelt_flux_tavg` not yet available in model output. NCAR-original reads are kept as comments for easy switchover.
7. **netCDF4 auto-masking pitfall**: `v == fv` never matches on auto-masked reads. To verify fill placement use `nid.set_auto_mask(False)` + `np.isclose(v, fv, rtol=1e-5)`.

## Compliance checker notes

- Checker results (2026-09-27): all 11 cases pass. The former cosmetic base/topg consistency errors (C003–C010) are FIXED in `ISMIP7_variable_HgridST_processing.py` (see "base/topg cosmetic fix" below). The former "unexpected variable 'time_bounds'" warnings are FIXED by renaming the bounds variable to `time_bnds` (see rule 5). Remaining known issues: (a) C011 ocx: 27 'ERA' naming errors — expected for reanalysis forcing, left as is; (b) warning "lithk > 0 where sftgif is 0" in all runs — pre-existing CISM behavior (thin margin ice below the ~0.5 m mask threshold, max 0.5 m), warning-only, accepted.
- **base/topg cosmetic fix** (in `ISMIP7_variable_HgridST_processing.py`, applied before writing base/orog):
  - Case 1: where `sftgrf == 1` (wholly grounded) and `|lsurf − topg| > 0.009` → `base = topg`.
  - Case 2: where `sftflf == 1` (wholly floating) and `lsurf − topg <= 0.011` → `base = topg + 0.1 m`.
  - The same delta is added to `orog` so the checker identity `orog = base + lithk` (1 cm tolerance) stays intact.
  - Detection thresholds sit 1 mm inside the checker's `ELEVATION_TOLERANCE = 1e-2` m (float32 safety).
  - **Mask test must use a tolerance (`MASK_TOL = 1e-6`), not `== 1.0`**: `f_float = 1 − f_ground` is float64 in the source and can be 0.999999997 in memory while rounding to exactly 1.0 in the written float32 files — exact equality misses those cells.
  - Every run logs the number of adjusted cells and the orog correction statistics; a correction > 1 m (`OROG_WARN_LIMIT`) triggers a strong WARNING (not a cosmetic artifact — investigate).
  - `verify_base_topg.py` replicates the checker's consistency tests offline on all 11 runs (exit 1 on any violation).
- Local test-only patch: `ocx;1990;1990;2025;36` added to `.../envs/isschecker/lib/python3.14/site-packages/isschecker/data/experiments_ismip7.csv` (backup `.orig`). Lost on isschecker update. `VALID_ESM_NAMES` in checker.py intentionally NOT patched.
- The user reruns the checker themselves — do not run it unprompted.

## Workflow conventions

- User drives step-by-step; confirm before large changes or full-batch reruns.
- `cp` is aliased interactive on the login node — use `\cp -f`.
- Commit messages: concise imperative summary + bullet body of the substantive changes.
