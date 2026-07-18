# MATLAB import scripts (reference implementation)

These are the original MATLAB import scripts. They remain the reference
for the binary formats and gains (the Python package was validated
against them), and they still work — but for routine conversion the
Python CLI at the repository root is the maintained, much faster path:

```bash
pip install -e .
rapid-convert my_measurement_folder --plot
```

## Using the MATLAB scripts

| Script | Sensor | Input |
|---|---|---|
| `RAPID_V1/rapid_import_V1.m` | RAPID V1 / EDF (2048 Hz) | one `.txt` file (edit `filePath`/`fileName` at the top) |
| `RAPID_V3/rapid_import_HIG_V3.m` | V3 high-g accelerometer | a folder of `.HIG` files (chosen via `uigetdir`) |
| `RAPID_V3/rapid_import_IMP_V3.m` | V3 IMU + pressure | a folder of `.IMP` files (chosen via `uigetdir`) |

Before running, note:

* The V3 scripts depend on `sort_nat.m` from the MATLAB File Exchange
  (https://www.mathworks.com/matlabcentral/fileexchange/10959-sort_nat-natural-order-sort)
  and contain an `addpath(...)` line pointing at the author's machine —
  edit it to wherever you saved `sort_nat.m`.
* `rapid_import_V1.m` likewise has a hard-coded example `filePath`.
* Put `.IMP` and `.HIG` files in separate folders (the scripts convert
  every matching file in the chosen folder).

## Known quirks (documented, not fixed here)

* The V3 scripts pair the timestamp of packet *i* with the data of
  packet *i+1*; the Python package is packet-aligned (see
  [docs/file_formats.md](../docs/file_formats.md)).
* The per-value `fread` loops make these scripts slow on large files.
* The V1 accelerometer gain was corrected to 1 on 2022-11-01 —
  `rapid_import_V1.m` is correct, but CSVs produced before that date
  (or with the legacy Python `EDF` class) under-report acceleration
  by 10×.
* BDS files that switch logger modes mid-recording, or files with
  corrupted regions, are not handled — use the Python package for
  those.
