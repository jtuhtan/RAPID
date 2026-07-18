# File Format Reference

Byte-level layouts of every supported sensor file, as implemented in
[`rapid_sensors/formats.py`](../rapid_sensors/formats.py). All layouts
were verified against the sample files in [`data/`](../data) — frame
markers, counter behavior, and physically plausible decoded values —
and are pinned by the test suite.

All files are sequences of fixed-layout binary packets with **no file
header**. Multi-byte RAPID values are **big-endian**; BDS values are
**little-endian**. A trailing partial packet (SD-card block padding) may
follow the last complete packet and is ignored.

## RAPID V1 / EDF (`.txt`) — 11 bytes per packet, 2048 Hz

| Offset | Type | Field | To physical units |
|---|---|---|---|
| 0–1 | int16 BE | sample counter | cycles 1…2048 once per second |
| 2–3 | int16 BE | acc X | ×1 → m/s² |
| 4–5 | int16 BE | acc Y | ×1 → m/s² |
| 6–7 | int16 BE | acc Z | ×1 → m/s² |
| 8–9 | int16 BE | pressure | ×0.1 → mbar |
| 10 | byte | terminator | always `0x0B` |

The counter is a per-second sample index, not a running clock, so
elapsed time is reconstructed from the packet index at 2048 Hz.

**Gain history:** the accelerometer gain was corrected from 10 to 1 on
2022-11-01 (`matlab/RAPID_V1/rapid_import_V1.m`). The 400 g and 50 g
shock-test files in `data/` confirm gain 1: their peaks decode to
~520 g and ~104 g (overshoot above nominal is normal in shock testing),
while gain 10 would give an implausible 52 g / 10 g. The legacy Python
`EDF` class still used gain 10 — CSVs made with it under-report
acceleration by 10×.

## RAPID V3 HIG (`.HIG`) — 11 bytes per packet, 2000 Hz

| Offset | Type | Field | To physical units |
|---|---|---|---|
| 0–3 | int32 BE | tick | ÷2000 → seconds |
| 4–5 | int16 BE | acc X | ×0.1 → g |
| 6–7 | int16 BE | acc Y | ×0.1 → g |
| 8–9 | int16 BE | acc Z | ×0.1 → g |
| 10 | byte | terminator | always `0x0B` |

The tick advances by 1 per packet (true 2000 Hz sampling). Sensor
range ±400 g; the turbine sample file peaks at 368.7 g.

## RAPID V3 IMP (`.IMP`) — 29 bytes per packet, 100 Hz

| Offset | Type | Field | To physical units |
|---|---|---|---|
| 0–3 | int32 BE | tick | ÷2000 → seconds (shared clock with HIG) |
| 4–9 | 3 × int16 BE | acc X, Y, Z | ×0.005 → m/s², ÷9.81 → g |
| 10–15 | 3 × int16 BE | gyro X, Y, Z | ×0.1 → deg/s |
| 16–21 | 3 × int16 BE | mag X, Y, Z | ×0.1 → mT |
| 22–23 | uint16 BE | pressure | ×0.1 → mbar |
| 24–25 | int16 BE | pressure-sensor temp | ×0.01 → °C |
| 26–27 | int16 BE | battery voltage | ×0.01 → V |
| 28 | byte | terminator | always `0x0B` |

**The tick advances by 20 per packet**: the IMP shares the HIG's
2000 Hz clock but actually samples at **100 Hz**. This is why HIG and
IMP files from one deployment can be merged on `Time (s)` directly.

## BDS (`.txt`) — typed records, little-endian

Each record is framed and self-describing:

```
[0x0D 0x0A][uint16 mode][uint32 t_ms][payload: N × float32][4 × uint8 cal]
```

| Mode field | Record size | Payload (22 or 12 float32) |
|---|---|---|
| 100 | 100 bytes | P1, T1, P2, T2, P3, T3, Eul heading, Eul roll, Eul pitch, Quat w, x, y, z, Mag x, y, z, Acc x, y, z, Gyro x, y, z |
| 250 | 60 bytes | P1, T1, P2, T2, P3, T3, Acc x, y, z, Gyro x, y, z |

* Floats are already in physical units: pressure mbar, temperature °C,
  acceleration m/s², gyro deg/s, magnetometer µT, Euler angles deg,
  unit quaternion.
* `t_ms` is the on-board millisecond clock — use it for timing; the
  mode number does **not** guarantee the sampling rate (the sample
  files log at ~96 Hz in both modes).
* The four calibration bytes are the BNO055 levels (magnetometer,
  accelerometer, gyroscope, system), each 0…3.
* **A single file may mix both record types** — the logger can switch
  modes mid-recording. `data/BDS/100_Hz/C350419125306.txt` does exactly
  this (30 s of mode-100, then 7 min of mode-250, joined by a 4-byte
  stub). The reader splits such files into one output per mode.

Historical note: the legacy import code read the CR-LF frame marker
(2573 as a little-endian uint16) as a field labeled "sample rate" and
treated the real mode field as struct padding — which is why it could
only ever parse single-mode files.

## Parsing strategy and corruption recovery

Clean files are parsed in a single vectorized pass (a NumPy structured
dtype over the whole buffer). Before accepting the fast path, every
packet's frame marker (`0x0B` terminator for RAPID, leading CR-LF for
BDS) is checked; if any are out of place, the parser walks the file
packet by packet, and at each broken position scans forward for the
next *chained* marker (one whose following packet is also marked) and
resumes there. Skipped byte counts and resync counts are reported in
the conversion summary. The legacy readers had no such check and
decoded misaligned regions into silent garbage.

## Alignment note vs. legacy CSVs

The legacy V3 scripts (MATLAB and Python) paired the timestamp of
packet *i* with the sensor values of packet *i+1*. The new readers are
packet-aligned: timestamp and values come from the same packet. V3
values therefore appear one sample earlier (0.5 ms HIG / 10 ms IMP)
than in legacy exports; a test pins this relationship.
