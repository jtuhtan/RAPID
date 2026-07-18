# User Guide

Everything you need to go from a memory card full of sensor files to
clean CSV tables and figures — no programming experience required for
the command-line part, and a small Python API when you want more.

## 1. Install

You need Python 3.9 or newer (https://www.python.org/downloads/ — on
Windows, tick *"Add python.exe to PATH"* during installation). Then:

```bash
git clone https://github.com/jtuhtan/RAPID.git
cd RAPID
pip install -e .
```

This installs the `rapid_sensors` package and the `rapid-convert`
command. Check it works and see all options:

```bash
rapid-convert --help
```

> If `rapid-convert` is not found, `python -m rapid_sensors.cli` does
> exactly the same thing.

## 2. Convert your first file

Copy the files from the sensor's memory card to a folder, then:

```bash
rapid-convert path/to/your/measurements
```

For every sensor file the tool prints a short report and writes a CSV
into a `CSV/` subfolder next to the file — the same folder convention
the original MATLAB scripts used. A typical report:

```
file    : B38-0928141315.IMP
format  : imp - RAPID V3 IMU + pressure (100 Hz on a 2000 Hz clock)
packets : 59996 (600.0 s of data)
columns : Time (s), Accel_X (g), ..., Pressure (mbar), P_Temp (C), Battery (V)
parsed  : 0.01 s
written : CSV/B38-0928141315-imp.csv
```

Useful options:

| Option | Effect |
|---|---|
| `--plot` | also write an overview PNG per file (into `PLOTS/`) |
| `--info` | only print the report, write nothing |
| `-r` | recurse into subfolders |
| `--out-dir DIR` | collect all outputs in one folder instead of `CSV/` subfolders |
| `--format NAME` | skip auto-detection (`rapid_v1`, `hig`, `imp`, `bds100`, `bds250`) |

**How detection works:** `.HIG` and `.IMP` extensions are unambiguous.
For `.txt` files (used by both RAPID V1 and BDS) the tool reads a few
hundred packets from the start and middle of the file and checks which
binary layout actually fits — packet frame markers, counter behavior,
calibration flags, plausible pressure values. If a file cannot be
identified confidently you get an error telling you to use `--format`
rather than a silently wrong conversion.

## 3. Understand the output

Column headers carry their units, so the CSV is self-explanatory in any
tool. The channels per sensor:

**RAPID V1 / EDF (2048 Hz)** — `Time (s)`, `Counter` (the device's
1..2048 per-second sample index), `Pressure (mbar)`,
`Accel_X/Y/Z/Mag (m/s2)`. Note the V1 timestamps assume an unbroken
recording (the device stores no absolute clock).

**RAPID V3 HIG (2000 Hz)** — `Time (s)`, `HIGAccel_X/Y/Z/Mag (g)` from
the ±400 g accelerometer. At rest this sensor shows a noise floor of a
few g — that is normal for a high-g MEMS part; it is built to resolve
strikes, not gravity.

**RAPID V3 IMP (100 Hz)** — `Time (s)`, `Accel_X/Y/Z/Mag (g)`,
`Gyro_X/Y/Z (deg/s)`, `Mag_X/Y/Z (mT)`, `Pressure (mbar)`,
`P_Temp (C)`, `Battery (V)`. The time stamps tick on the same 2000 Hz
clock as the HIG (so the two files of one deployment share a time
base), but IMP samples arrive every 20 ticks — i.e. at 100 Hz.

**BDS** — `Time (s)` (from the on-board millisecond clock),
`Pressure (mbar)` (mean of the three sensors) plus the individual
`P1/P2/P3 (mbar)` and `T1/T2/T3 (C)`, `Accel_X/Y/Z/Mag (m/s2)`,
`Gyro_X/Y/Z (deg/s)`, and — in 100-mode records — the BNO055 fusion
output: Euler angles, the orientation quaternion, and the magnetometer.
`Cal_Mag/Acc/Gyro/Sys` are the BNO055 calibration levels (0 = not
calibrated … 3 = fully calibrated): treat orientation output with
`Cal_Sys < 2` with caution.

> **BDS sampling rate:** the mode names (100 / 250) describe the record
> type, not a guaranteed rate — the example files in `data/` log at
> ~96 Hz in both modes. Always use the `Time (s)` column, which comes
> from the device's real millisecond clock, rather than assuming a
> fixed rate.

**Gravity is included.** Acceleration channels and magnitudes are raw
sensor output; at rest, `Accel_Mag` reads ~1 g (9.81 m/s²). (Some
legacy scripts subtracted 9.81 from the magnitude; the new outputs do
not, so you can apply your own gravity handling.)

## 4. Warnings you may see

* *"file has corrupted regions - parser resynchronized Nx"* — the file
  lost byte alignment somewhere (power loss, SD glitch). The parser
  skipped the unreadable bytes and recovered the intact packets. The
  skipped byte count tells you how much was lost.
* *"the file switches logger modes"* — a BDS recording that changed
  record type mid-file. Both segments are exported, as
  `<name>-bds100.csv` and `<name>-bds250.csv`.
* *"bad end-of-packet byte"* — some packets failed their integrity
  check; inspect the file (and the overview plot) before trusting it.

## 5. Work with the CSVs

**Excel / LibreOffice** — open directly; the first row holds the
headers.

**Python**

```python
import pandas as pd
df = pd.read_csv("CSV/B38-0928141315-imp.csv")
df.plot(x="Time (s)", y="Pressure (mbar)")
```

or skip the CSV entirely:

```python
import rapid_sensors
rec = rapid_sensors.read("B38-0928141315.IMP")
df = rec.data                      # pandas DataFrame
print(rec.summary())               # the same report the CLI prints
rec.to_csv("out.csv")
for sib in rec.siblings:           # extra segments of mixed BDS files
    sib.to_csv(f"out-{sib.fmt.name}.csv")
```

**MATLAB**

```matlab
T = readtable('CSV/B38-0928141315-imp.csv', 'VariableNamingRule', 'preserve');
plot(T.('Time (s)'), T.('Pressure (mbar)'));
```

## 6. Troubleshooting

| Problem | What to do |
|---|---|
| "cannot confidently identify the format" | The file is damaged, empty, or not from these sensors. If you know what it is, add `--format <name>` — the parser will then recover what it can. |
| A `.txt` file detects as the wrong type | Force it: `--format rapid_v1` (or `bds100` / `bds250`). Detection reports its scores in the error message. |
| CSV values look 10× too small vs. old results | Old results from the legacy Python `EDF` class used an outdated V1 gain. The new values follow the corrected MATLAB reference (see the [format reference](file_formats.md#quirks)). |
| V3 values shifted by one sample vs. old CSVs | Intentional: the legacy scripts paired each timestamp with the *next* packet's values; the new reader is packet-aligned. |
| Conversion is slow over a network drive | Copy files locally first — parsing itself takes milliseconds; the disk is the bottleneck. |
| `pip install` fails | Upgrade pip (`python -m pip install -U pip`) and re-try; any Python ≥ 3.9 works. |

## 7. Going further

* Byte-level packet layouts, gains and quirks:
  [File Format Reference](file_formats.md)
* Speed comparison against the legacy loops:
  `python benchmarks/benchmark_convert.py`
* The original scripts, kept for reference:
  [`matlab/`](../matlab/README.md), [`python/legacy/`](../python/legacy/README.md)
