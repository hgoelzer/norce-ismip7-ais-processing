# Active Context — NORCE ISMIP7 AIS Processing

## Current state (2026-10-13)

- 8km CORE submission (11 runs, C001..C011) is complete and
  checker-validated; regenerate with `run_all_CORE.py` if needed.
- **New: PPE tree for the 16km ensemble.** `run_all_PPEcore.py` runs the
  same 11 CORE experiments and writes
  `AIS/NORCE/CISM/{SET_ID}/{counter}/` (`PPE/P001..P011`) with a fixed
  ISM member ID (`m002` for PPEcore; prefix derived from `set_id[0]`).
- **`config.py` is the single source of truth** (2026-10-13): the 4
  scripts take `--set_id` / `--ism_member_id` with defaults from
  `SET_ID` / `ISM_MEMBER_ID` in the active config (was: ESM_map-derived
  member index). FL/Velo previously hardcoded `set_id = 'CORE'`; now
  unified to config + CLI override.
- `run_all_PPEcore.py` gained `--config <module>` (default `config.py`)
  to select the configuration module; it passes the module's `PATH_EXP`,
  `SET_ID`, `ISM_MEMBER_ID` to the children via `--path_exp` /
  `--set_id` / `--ism_member_id`. Two equivalent ways to run PPEcore:
  `python run_all_PPEcore.py --config config_16km.py`, or copy
  `config_16km.py` over `config.py` and run without `--config`.
- `config_16km.py` now carries `SET_ID='PPE'`, `ISM_MEMBER_ID='m002'`
  (plus the 16km `PATH_EXP`); `config_08km.py` and `config.py` carry
  `SET_ID='CORE'`, `ISM_MEMBER_ID='m001'`.
- **Naming fix (2026-10-13): all runs get `ISM_member_id='m001'` by
  default** — the ESM_id (CESM2-WACCM / MRI-ESM2-0 / ERA) alone
  distinguishes the forcing; `ESM_map` now maps member → ESM_id only.
  The former m01→m001 / m02→m002 split was wrong. PPEcore sets the
  member via config (`ISM_MEMBER_ID='m002'`) or `--ism_member_id`.
- **Consequence: existing CORE output for the m02 runs
  (C002, C004, C006, C008, C010) still carries `m002` file names —
  those cases must be regenerated (and old `*m002*` files removed)
  to match the corrected naming.**
- `--exp` in `run_all_PPEcore.py` accepts experiment names, P001..P011,
  and (for convenience) C001..C011 — same runs either way.
- Validated (2026-10-13, config-source refactor): py_compile of all
  scripts; `--dryrun` of `run_all_PPEcore.py` with `--config
  config_16km.py` (SET_ID=PPE, ISM_MEMBER_ID=m002, 16km input) and with
  default `config.py`; end-to-end copy-workflow test (config_16km.py
  copied over config.py, scalar script run with no CLI set/member args)
  produced `P004/*_m002_MRI-ESM2-0_*_P004_*.nc` in a scratch dir
  (removed; config.py restored to the 8km settings afterwards).
  No real PPE output written yet.

## Queued next steps

- Regenerate the CORE m02 cases (C002, C004, C006, C008, C010) with
  `run_all_CORE.py --exp C002 C004 C006 C008 C010` after removing the
  stale `*m002*` files in those directories; then rerun the checker on them.
- Run the full PPE batch (`run_all_PPEcore.py`) and check the summary
  table; then run the user's isschecker pass on the PPE tree.
- Future submissions (real PPE members etc.) can reuse the same
  `--set_id`/`--ism_member_id` mechanism with a new wrapper.
