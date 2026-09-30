# Handoff to the AIS processing (norce-ismip7-ais-processing)

Suggested changes to port back from the GrIS processing
(`norce-imsip7-gris-processing`, commits `2cd4e63` and `01e9cfc` on `main`).
The GrIS scripts were originally adapted from the AIS version, so these
changes apply in the reverse direction.

AIS repo: `/nird/datalake/NS11016K/users/heig/ISMIP7/data_processing/norce-ismip7-ais-processing`
(git `main` at `f848717`). The "current AIS state" notes below were checked
against that checkout on 2026-09-30.

Note on nird storage: the AIS repo and its output live on the **datalake**
(`/nird/datalake/NS11016K/...`), while the CISM run trees and the conda
envs live on **datapeak** (`/nird/datapeak/NS11016K/...`). Both are mounted;
`PATH_EXP` in the AIS config already points across (datapeak input →
datalake output), which is fine — but keep in mind that datalake and
datapeak have different characteristics (datalake is the project's
long-term storage; datapeak is scratch-like). The interpreter path in the
AIS `config.py` currently points to datapeak, which is another reason for
change §1.

Summary of what applies:

| # | Change | AIS state | Action |
|---|--------|-----------|--------|
| 1 | Interpreter decoupling | `PYTHON` hardcoded in `config.py` + `config_16km.py` | **Port** |
| 2 | Config-driven metadata | `ncid.model = 'CISM3'` stale in all 4 scripts | **Port (bug fix)** |
| 3 | `--exp` counter ids | names only | **Port** |
| 4 | Experiment name = output name | `exp_out` translation exists | **Port** |
| 5 | `libmassbffl` fill rule | already correct (`np.where(f_float > 0, ...)`) | none |

---

## 1. Remove the hardcoded python interpreter

**Current AIS state:** `config.py` and `config_16km.py` both contain

```python
PYTHON = '/nird/datapeak/NS11016K/miniforge3_26/envs/nc/bin/python'
```

and `run_all_CORE.py` launches the child scripts with it:

```python
from config import PYTHON, PATH_EXP
...
cmd = [PYTHON, os.path.join(SCRIPT_DIR, script), ...]
```

This breaks as soon as the env is rebuilt/moved, and silently uses a stale
interpreter. It also hardwires a datapeak path into a datalake repo.

**Fix (GrIS commit `2cd4e63`):**

- Delete the `PYTHON` constant from `config.py` (and `config_16km.py`).
- Launch the child scripts with the interpreter that runs the wrapper:

```python
cmd = [sys.executable, os.path.join(SCRIPT_DIR, script),
       '--exp', exp, '--ESM_num', ESM_num or 'm01', '--RCM_num', RCM_num]
...
proc = subprocess.run(cmd)
```

- Document the environment in the README instead of hardcoding it:

```
conda create -n ismip7 -c conda-forge python=3.11 netcdf4 numpy scipy
conda activate ismip7
python run_all_CORE.py
```

The processing scripts need only `netCDF4`, `numpy`, `scipy` (no
matplotlib). Whoever runs the wrapper controls the interpreter by choosing
which `python` to invoke it with.

---

## 2. Config-driven metadata (fixes stale hardcoded attributes)

**Current AIS state:** all 4 scripts have an identical hardcoded attribute
block, e.g. `ISMIP7_scalar_processing.py` lines 266-270:

```python
ncid.group = 'NORCE'
ncid.model = 'CISM3'          # <-- STALE: config ISM_ID is 'CISM8'
ncid.contact_name = 'Heiko Goelzer'
ncid.contact_email = 'heig@norceresearch.no'
ncid.crs = 'epsg:3031'
```

The `CISM3` is a leftover from an older naming scheme; the file names and
output tree use `ISM_ID` from config (`CISM8` for the 8 km ensemble), so
the `model` attribute disagrees with the file names. The contact is also
incomplete (GrIS now lists Maria Paz Lira as first contact). Additionally
`domain_id = 'AIS'`, `source_id = 'NORCE'`, `set_id = 'CORE'` are
hardcoded in each script instead of coming from config.

**Fix (GrIS commit `01e9cfc`):** all metadata lives once in `config.py`:

```python
DOMAIN_ID = 'AIS'     # Ice sheet
SOURCE_ID = 'NORCE'   # Modelling group (also global attribute `group`)
SET_ID = 'CORE'       # Experiment set
ISM_ID = 'CISM8'      # already in AIS config; attribute `model` should use it
CONTACT_NAME = 'Maria Paz Lira, Heiko Goelzer'
CONTACT_EMAIL = 'mali@norceresearch.no, heig@norceresearch.no'
```

Each script imports them and uses them consistently:

```python
from config import (PATH_EXP, DST_PATH, ISM_ID, CONTACT_NAME, CONTACT_EMAIL,
                    DOMAIN_ID, SOURCE_ID, SET_ID)

domain_id = DOMAIN_ID
source_id = SOURCE_ID
ism_id = ISM_ID      # can be overridden with --ism_id
set_id = SET_ID
```

and the attribute block becomes:

```python
ncid.group = source_id
ncid.model = ism_id
ncid.contact_name = CONTACT_NAME
ncid.contact_email = CONTACT_EMAIL
ncid.crs = 'epsg:3031'
```

This makes the `model` attribute automatically follow `ISM_ID`, so the
8 km (`CISM8`) and 16 km (`CISM`) outputs stay self-consistent without
touching the scripts.

**Data impact:** existing AIS output files carry the wrong `model`
attribute (`CISM3`); after the fix, re-run the affected experiments (or
patch the attributes in place) and re-validate with isschecker.

---

## 3. `--exp` accepts CORE counter ids (C001..C011)

**Current AIS state:** `run_all_CORE.py` filters by name only:

```python
runs = [r for r in RUNS if r[0] == args.exp]
```

so running a single CORE case (e.g. "just C004") requires knowing that
C004 = ssp370 m02.

**Fix:** keep the `RUNS` list (its order already matches the CORE.csv
counters) and let `runs_for_exp` accept either experiment names or counter
ids (case-insensitive):

```python
def runs_for_exp(exp):
    key = exp.lower()
    if key.startswith('c') and key[1:].isdigit():
        idx = int(key[1:]) - 1
        if 0 <= idx < len(RUNS):
            return [RUNS[idx]]
        sys.exit(f'Error: unknown counter {exp} (valid: C001..C011)')
    runs = [r for r in RUNS if r[0] == exp]
    if not runs:
        sys.exit(f'Error: unknown experiment {exp}')
    return runs
```

with `parser.add_argument('--exp', nargs='+', ...)` so several cases can be
given at once: `python run_all_CORE.py --exp C003 C004 ctrl2015`.

---

## 4. Experiment names = data-request names (no `exp_out`)

**Current AIS state:** the scripts carry a translation line, e.g.
`ISMIP7_scalar_processing.py` line 58:

```python
# 'ctrl' for the control run, while the input directory is named ctrl2015.
exp_out = 'ctrl' if exp == 'ctrl2015' else exp
```

and the output filename uses `exp_out`. This is an asymmetry: `ssp126` is
used directly while `ctrl2015` needs a translation, and the special case
must be repeated in all 4 scripts.

**Fix (GrIS commit `01e9cfc`):** make the data-request name the single
identifier everywhere and resolve the input directory via `run_dir_map`
only (exactly like the ocx directory is already resolved). The `exp_out`
variable is deleted:

```python
# exp is the data-request experiment name used in the output file names
# ('ctrl', not the input directory name 'ctrl2015'; see run_dir_map).

exp_map = {
    'historical': 'C001', 'ssp370': 'C003', 'ssp126': 'C005',
    'ssp585': 'C007', 'ctrl': 'C009', 'ocx': 'C011',
}

def run_dir(exp, ESM_num, RCM_num):
    if exp == 'ocx':
        return f"{path_exp}/ocx_{RCM_num}"
    if exp == 'ctrl':
        return f"{path_exp}/ctrl2015_{ESM_num}_{RCM_num}"
    return f"{path_exp}/{exp}_{ESM_num}_{RCM_num}"
```

The output filename f-string uses `exp` directly:

```python
f"{dstDir}{field}_{domain_id}_{source_id}_{ism_id}_{ISM_member_id}_"
f"{ESM_id}_{forcing_member_id}_{exp}_{set_counter}_{time_range}.nc"
```

Consequences: `--exp ctrl` (not `ctrl2015`) selects the control runs, and
the wrapper `RUNS` list entries become `('ctrl', 'm01', 'r01')` etc. The
input directories on disk keep their `ctrl2015_*` names — only the
identifier changes.

---

## 5. `libmassbffl` fill rule — already correct in AIS

The GrIS hit a checker error here (isschecker 0.5.1): the data request
defines `libmassbffl` only where there is floating ice, so cells without
floating ice must hold the `_FillValue` (9.969209968386869e+36) — the old
"0-fill everywhere" rule is wrong.

**The AIS scripts already do this correctly**
(`ISMIP7_variable_HgridFL_processing.py`):

```python
# The data request defines this variable only where there is floating
# ice; cells without floating ice hold the fill value.
libmassbffl[:, :, :] = np.where(f_float[:, :, :] > 0,
                                basal_flux_dst[:, :, :]*f_float[:, :, :],
                                netCDF4.default_fillvals['f4'])
```

No change needed — this is listed only so the rule is on record: variables
"defined only where there is floating/grounded ice" hold `_FillValue`
elsewhere (same pattern as `libmassbfgr`), while variables the data request
does not allow missing values in (`dlithkdt`, `lifmassbf`) stay 0-filled.
The rule is per-variable, driven by the data request definition.

---

## 6. Minor points (already correct in both repos, listed for completeness)

- `time_range` in output file names is derived from the data
  (`time_dst[t]-1`), so it adjusts automatically when a run is extended.
- The scripts run at module level (no `main()`): never `import` them;
  syntax-check with `python -m py_compile` only.
- Never call `set_auto_scale(False)`; verify fill placement with
  `set_auto_mask(False)` + `np.isclose`.
- ST time stamps = Jan 1 of year+1, FL = Jul 1 of year; the time bounds
  variable must be named `time_bnds` (AIS already did this in `ac807fa`).
- Unit conversions: `acabf` ← `acab` × rhoi/sPerY, etc.

---

## Suggested port order for AIS

1. Interpreter decoupling (§1) — small, zero-risk, unblocks env changes.
2. Config-driven metadata (§2) — **fixes the stale `model='CISM3'`
   attribute**; re-run or attribute-patch existing output afterwards.
3. Counter-id `--exp` (§3) — convenience, no data impact.
4. `ctrl` naming symmetry (§4) — identifier change only; input dirs keep
   their `ctrl2015_*` names; re-run C009/C010 so file names use `ctrl`.
5. `libmassbffl` fill rule (§5) — nothing to do, already correct.

---

## Port status (2026-09-30)

**All actionable items (§1–§4) have been implemented and all 11 CORE runs
regenerated.**

- §1: `PYTHON` removed from `config.py`/`config_16km.py`; the wrapper
  launches child scripts with `sys.executable`. Environment documented in
  the README (conda recipe).
- §2: metadata (`DOMAIN_ID`, `SOURCE_ID`, `SET_ID`, `CONTACT_NAME`,
  `CONTACT_EMAIL`) lives in `config.py`; all 4 scripts import it and write
  `ncid.model = ism_id` (fixes the stale `CISM3` attribute) and the updated
  contacts (Maria Paz Lira first).
- §3: `run_all_CORE.py --exp` accepts experiment names and/or CORE counter
  ids (`C001..C011`, case-insensitive), several at once (`nargs='+'`).
- §4: `exp_out` deleted; the data-request name `ctrl` is the single
  identifier (`--exp ctrl`, `exp_map`, output file names); input
  directories keep their `ctrl2015_*` names via the `run_dir` helper.
- §5: confirmed already correct, no change.
- Additionally: `ISM_ID` in `config.py` changed from `CISM8` to `CISM`
  (output tree `AIS/NORCE/CISM/CORE/`; the previous output was cleaned out
  and all 11 runs regenerated with the new id, `model='CISM'` attribute,
  and `ctrl` file names). Note both configs now use `CISM`, so the 8 km
  and 16 km ensembles share the same output tree.
- Remaining: re-validate the regenerated output with isschecker.
