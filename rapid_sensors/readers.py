"""Read RAPID / BDS binary files into physical units.

The public entry point is :func:`read`, which returns a
:class:`Recording`: a pandas DataFrame in physical units plus metadata
about the file.  Column names carry their units (e.g. ``Accel_X (g)``)
so an exported CSV is self-describing in Excel or any other tool.

Conversion gains follow the reference MATLAB implementations in
``matlab/`` and were validated against the sample data in ``data/``
(see tests/):

================  =========================================
rapid_v1          acc raw -> m/s^2 (gain 1, the 2022-11-01
                  corrected value), pressure raw*0.1 -> mbar
hig               acc raw*0.1 -> g
imp               acc raw*0.005 m/s^2 -> /9.81 g,
                  gyro raw*0.1 deg/s, mag raw*0.1 mT,
                  pressure raw*0.1 mbar, temp raw*0.01 C,
                  battery raw*0.01 V
bds100 / bds250   floats are already physical (mbar, C,
                  m/s^2, deg/s, uT, deg); time in ms
================  =========================================

Alignment note: the legacy MATLAB/Python V3 scripts paired the
timestamp of packet *i* with the sensor values of packet *i+1* (an
off-by-one inherited from the original fread loops).  These readers are
packet-aligned — timestamp and values always come from the same packet
— so V3 values appear one sample (0.5 ms HIG / 10 ms IMP) earlier than
in legacy CSV exports.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field as dataclass_field

import numpy as np
import pandas as pd

from .formats import FORMATS, TERMINATOR, PacketFormat, detect_format

__all__ = ["read", "Recording"]


@dataclass
class Recording:
    """One parsed sensor file.

    Attributes
    ----------
    data : pandas.DataFrame
        Measurements in physical units; column names include units.
    fmt : PacketFormat
        The binary format the file was parsed with.
    source : str
        Path of the input file.
    n_packets : int
        Number of complete packets parsed.
    n_bad_terminator : int
        Packets whose 0x0B end byte was wrong (RAPID formats only) —
        nonzero values usually mean a corrupted or misaligned file.
    n_resyncs : int
        Number of times the parser had to resynchronize on the packet
        frame markers after a corrupted region.  0 for a healthy file.
    n_skipped_bytes : int
        Bytes discarded as unparseable (corrupted regions plus any
        trailing partial packet from SD-card block padding).
    csv_formats : dict
        Per-column printf formats used for CSV export (fixed decimal
        places per physical quantity, matching the legacy exports).
    siblings : list of Recording
        Additional record types found in the same file.  The BDS logger
        can switch between its 100-record and 250-record modes mid-
        recording; each mode's data becomes its own Recording, with the
        majority type returned as the primary one.
    """

    data: pd.DataFrame
    fmt: PacketFormat
    source: str
    n_packets: int
    n_bad_terminator: int = 0
    n_resyncs: int = 0
    n_skipped_bytes: int = 0
    csv_formats: dict = dataclass_field(default_factory=dict)
    siblings: list = dataclass_field(default_factory=list)

    @property
    def duration_s(self) -> float:
        t = self.data["Time (s)"]
        return float(t.iloc[-1] - t.iloc[0]) if len(t) > 1 else 0.0

    def summary(self) -> str:
        lines = [
            f"file    : {self.source}",
            f"format  : {self.fmt.name} - {self.fmt.description}",
            f"packets : {self.n_packets} "
            f"({self.duration_s:.1f} s of data)",
            f"columns : {', '.join(self.data.columns)}",
        ]
        for sib in self.siblings:
            lines.append(f"note    : the file switches logger modes - it "
                         f"also contains {sib.n_packets} {sib.fmt.name} "
                         f"records ({sib.duration_s:.1f} s), exported as "
                         f"their own output")
        if self.n_resyncs:
            lines.append(
                f"WARNING : file has corrupted regions - parser "
                f"resynchronized {self.n_resyncs}x and skipped "
                f"{self.n_skipped_bytes} unreadable bytes (the legacy "
                f"readers would have decoded these regions as garbage "
                f"values)")
        if self.n_bad_terminator:
            frac = self.n_bad_terminator / max(self.n_packets, 1)
            lines.append(f"WARNING : {self.n_bad_terminator} packets "
                         f"({frac:.1%}) had a bad end-of-packet byte - "
                         f"the file may be corrupted")
        return "\n".join(lines)

    def to_csv(self, path) -> None:
        """Write the data as CSV with fixed per-column precision."""
        fmts = [self.csv_formats.get(c, "%.6g") for c in self.data.columns]
        np.savetxt(path, self.data.to_numpy(), fmt=fmts, delimiter=",",
                   header=",".join(self.data.columns), comments="")


# ---------------------------------------------------------------------------
# packet parsing with corruption recovery
# ---------------------------------------------------------------------------

def _parse_packets(raw: bytes, pf: PacketFormat):
    """Parse packets from raw bytes, resynchronizing over corruption.

    Fast path: if every packet on the naive grid carries its anchor
    bytes (the CR-LF frame marker for BDS, the 0x0B terminator for
    RAPID), the whole buffer is reinterpreted in one vectorized call.

    Recovery path: otherwise the buffer is walked packet by packet;
    wherever the anchor is missing, the parser scans forward for the
    next *chained* anchor (one whose following packet is anchored too)
    and continues from there.  This recovers all intact segments of a
    file with dropped or inserted bytes — regions the legacy readers
    silently decoded as garbage.

    Returns ``(records, n_resyncs, n_skipped_bytes)``.
    """
    psize = pf.packet_size
    off = pf.anchor_offset
    alen = len(pf.anchor)
    total = len(raw)
    n = total // psize

    grid = np.frombuffer(raw[: n * psize], dtype=np.uint8).reshape(n, psize)
    anchor_arr = np.frombuffer(pf.anchor, dtype=np.uint8)
    if (grid[:, off:off + alen] == anchor_arr).all():
        rec = np.frombuffer(raw[: n * psize], dtype=pf.dtype)
        return rec, 0, total - n * psize

    def anchored(p: int) -> bool:
        return raw[p + off: p + off + alen] == pf.anchor

    good = bytearray()
    pos = 0
    resyncs = 0
    skipped = 0
    while pos + psize <= total:
        if anchored(pos):
            good += raw[pos: pos + psize]
            pos += psize
            continue
        # find the next anchor whose successor packet is also anchored
        # (or that ends the file), so we don't lock onto anchor bytes
        # occurring by chance inside sensor values
        nxt = raw.find(pf.anchor, pos + 1)
        start = -1
        while nxt != -1:
            cand = nxt - off
            if cand > pos and cand + psize <= total and \
                    (cand + 2 * psize > total or anchored(cand + psize)):
                start = cand
                break
            nxt = raw.find(pf.anchor, nxt + 1)
        if start == -1:
            break  # no valid packet boundary in the rest of the file
        skipped += start - pos
        pos = start
        resyncs += 1
    skipped += total - pos  # unreadable tail or trailing partial packet
    rec = np.frombuffer(bytes(good), dtype=pf.dtype)
    return rec, resyncs, skipped


# ---------------------------------------------------------------------------
# per-format DataFrame builders
# ---------------------------------------------------------------------------

def _amag(ax, ay, az):
    return np.sqrt(ax * ax + ay * ay + az * az)


def _build_rapid_v1(rec: np.ndarray):
    fs = 2048.0
    n = rec.size
    # The counter cycles 1..2048 once per second (a per-second sample
    # index, not a continuous clock), so elapsed time comes from the
    # packet index at the fixed 2048 Hz rate.
    ax = rec["ax"].astype(np.float64)          # already m/s^2 (gain 1)
    ay = rec["ay"].astype(np.float64)
    az = rec["az"].astype(np.float64)
    cols = {
        "Time (s)": np.arange(n) / fs,
        "Counter": rec["counter"].astype(np.int64),
        "Pressure (mbar)": rec["p"].astype(np.float64) * 0.1,
        "Accel_X (m/s2)": ax,
        "Accel_Y (m/s2)": ay,
        "Accel_Z (m/s2)": az,
        "Accel_Mag (m/s2)": _amag(ax, ay, az),
    }
    fmts = {"Time (s)": "%.6f", "Counter": "%d",
            "Pressure (mbar)": "%.1f", "Accel_X (m/s2)": "%.2f",
            "Accel_Y (m/s2)": "%.2f", "Accel_Z (m/s2)": "%.2f",
            "Accel_Mag (m/s2)": "%.2f"}
    return cols, fmts


def _build_hig(rec: np.ndarray):
    ax = rec["ax"].astype(np.float64) * 0.1    # raw*0.1 -> g
    ay = rec["ay"].astype(np.float64) * 0.1
    az = rec["az"].astype(np.float64) * 0.1
    cols = {
        "Time (s)": rec["tick"].astype(np.float64) / 2000.0,
        "HIGAccel_X (g)": ax,
        "HIGAccel_Y (g)": ay,
        "HIGAccel_Z (g)": az,
        "HIGAccel_Mag (g)": _amag(ax, ay, az),
    }
    fmts = dict.fromkeys(cols, "%.1f")
    fmts["Time (s)"] = "%.4f"
    return cols, fmts


def _build_imp(rec: np.ndarray):
    acc_gain = 0.005 / 9.81                    # raw -> m/s^2 -> g
    ax = rec["ax"].astype(np.float64) * acc_gain
    ay = rec["ay"].astype(np.float64) * acc_gain
    az = rec["az"].astype(np.float64) * acc_gain
    cols = {
        # ticks advance on the shared 2000 Hz clock (by 20 per packet:
        # the IMP itself samples at 100 Hz)
        "Time (s)": rec["tick"].astype(np.float64) / 2000.0,
        "Accel_X (g)": ax,
        "Accel_Y (g)": ay,
        "Accel_Z (g)": az,
        "Accel_Mag (g)": _amag(ax, ay, az),
        "Gyro_X (deg/s)": rec["gx"].astype(np.float64) * 0.1,
        "Gyro_Y (deg/s)": rec["gy"].astype(np.float64) * 0.1,
        "Gyro_Z (deg/s)": rec["gz"].astype(np.float64) * 0.1,
        "Mag_X (mT)": rec["mx"].astype(np.float64) * 0.1,
        "Mag_Y (mT)": rec["my"].astype(np.float64) * 0.1,
        "Mag_Z (mT)": rec["mz"].astype(np.float64) * 0.1,
        "Pressure (mbar)": rec["p"].astype(np.float64) * 0.1,
        "P_Temp (C)": rec["ptemp"].astype(np.float64) * 0.01,
        "Battery (V)": rec["bat"].astype(np.float64) * 0.01,
    }
    fmts = dict.fromkeys(cols, "%.3f")
    fmts.update({"Time (s)": "%.4f", "Pressure (mbar)": "%.1f",
                 "P_Temp (C)": "%.2f", "Battery (V)": "%.2f"})
    return cols, fmts


def _build_bds(rec: np.ndarray, with_orientation: bool):
    t = rec["t_ms"].astype(np.float64)
    p_mean = (rec["P1"] + rec["P2"] + rec["P3"]).astype(np.float64) / 3.0
    ax = rec["ax"].astype(np.float64)          # BNO055 outputs m/s^2
    ay = rec["ay"].astype(np.float64)
    az = rec["az"].astype(np.float64)
    cols = {
        "Time (s)": (t - t[0]) / 1000.0,
        "Pressure (mbar)": p_mean,
        "P1 (mbar)": rec["P1"].astype(np.float64),
        "P2 (mbar)": rec["P2"].astype(np.float64),
        "P3 (mbar)": rec["P3"].astype(np.float64),
        "T1 (C)": rec["T1"].astype(np.float64),
        "T2 (C)": rec["T2"].astype(np.float64),
        "T3 (C)": rec["T3"].astype(np.float64),
        "Accel_X (m/s2)": ax,
        "Accel_Y (m/s2)": ay,
        "Accel_Z (m/s2)": az,
        "Accel_Mag (m/s2)": _amag(ax, ay, az),
        "Gyro_X (deg/s)": rec["gx"].astype(np.float64),
        "Gyro_Y (deg/s)": rec["gy"].astype(np.float64),
        "Gyro_Z (deg/s)": rec["gz"].astype(np.float64),
    }
    if with_orientation:
        cols.update({
            "Eul_Heading (deg)": rec["eul_heading"].astype(np.float64),
            "Eul_Roll (deg)": rec["eul_roll"].astype(np.float64),
            "Eul_Pitch (deg)": rec["eul_pitch"].astype(np.float64),
            "Quat_W": rec["quat_w"].astype(np.float64),
            "Quat_X": rec["quat_x"].astype(np.float64),
            "Quat_Y": rec["quat_y"].astype(np.float64),
            "Quat_Z": rec["quat_z"].astype(np.float64),
            "Mag_X (uT)": rec["mx"].astype(np.float64),
            "Mag_Y (uT)": rec["my"].astype(np.float64),
            "Mag_Z (uT)": rec["mz"].astype(np.float64),
        })
    cols.update({
        "Cal_Mag": rec["cal_mag"].astype(np.int64),
        "Cal_Acc": rec["cal_acc"].astype(np.int64),
        "Cal_Gyro": rec["cal_gyro"].astype(np.int64),
        "Cal_Sys": rec["cal_sys"].astype(np.int64),
    })
    fmts = dict.fromkeys(cols, "%.4f")
    fmts.update({"Time (s)": "%.3f", "Cal_Mag": "%d", "Cal_Acc": "%d",
                 "Cal_Gyro": "%d", "Cal_Sys": "%d"})
    for key in ("Pressure (mbar)", "P1 (mbar)", "P2 (mbar)", "P3 (mbar)"):
        fmts[key] = "%.2f"
    return cols, fmts


_BUILDERS = {
    "rapid_v1": lambda rec: _build_rapid_v1(rec),
    "hig": lambda rec: _build_hig(rec),
    "imp": lambda rec: _build_imp(rec),
    "bds100": lambda rec: _build_bds(rec, with_orientation=True),
    "bds250": lambda rec: _build_bds(rec, with_orientation=False),
}


def read(path, fmt: str = "auto") -> Recording:
    """Read one sensor file into physical units.

    Parameters
    ----------
    path : str or Path
        The binary file written by the sensor (``.txt``, ``.HIG``,
        ``.IMP``).
    fmt : str
        ``"auto"`` (default) detects the format from the file content;
        or force one of ``rapid_v1, hig, imp, bds100, bds250``.

    Returns
    -------
    Recording
        ``.data`` (DataFrame), ``.fmt``, ``.summary()``, ``.to_csv()``.
    """
    path = os.fspath(path)
    if fmt == "auto":
        pf = detect_format(path)
    else:
        try:
            pf = FORMATS[fmt]
        except KeyError:
            raise ValueError(f"unknown format {fmt!r}; expected one of: "
                             f"auto, {', '.join(FORMATS)}") from None

    with open(path, "rb") as fh:
        raw = fh.read()  # sensor files are tens of MB at most
    if pf.name.startswith("bds"):
        return _read_bds(raw, path, requested=None if fmt == "auto" else pf)

    rec, n_resyncs, n_skipped = _parse_packets(raw, pf)
    if rec.size == 0:
        raise ValueError(f"{path}: no complete {pf.packet_size}-byte "
                         f"{pf.name} packets found (empty, truncated, "
                         f"or not really a {pf.name} file?)")

    n_bad = 0
    if pf.terminator_field is not None:
        n_bad = int((rec[pf.terminator_field] != TERMINATOR).sum())

    cols, fmts = _BUILDERS[pf.name](rec)
    data = pd.DataFrame(cols)
    return Recording(data=data, fmt=pf, source=path,
                     n_packets=int(rec.size), n_bad_terminator=n_bad,
                     n_resyncs=n_resyncs, n_skipped_bytes=n_skipped,
                     csv_formats=fmts)


def _read_bds(raw: bytes, path: str,
              requested: PacketFormat | None) -> Recording:
    """Parse a BDS typed-record stream into one Recording per mode.

    The primary Recording is the requested type (when the caller forced
    one) or the file's majority type; any other mode's records become
    ``.siblings`` so mixed-mode files lose no data.
    """
    from .formats import BDS_MODE_TO_FORMAT, walk_bds_records

    segments, n_resyncs, n_skipped = walk_bds_records(raw)
    if not segments:
        raise ValueError(f"{path}: no valid BDS records found (empty, "
                         f"truncated, or not a BDS file?)")

    recs = {}
    for mode, seg in segments.items():
        sub_pf = FORMATS[BDS_MODE_TO_FORMAT[mode]]
        arr = np.frombuffer(seg, dtype=sub_pf.dtype)
        cols, fmts = _BUILDERS[sub_pf.name](arr)
        recs[sub_pf.name] = Recording(
            data=pd.DataFrame(cols), fmt=sub_pf, source=path,
            n_packets=int(arr.size), csv_formats=fmts)

    if requested is not None:
        if requested.name not in recs:
            found = ", ".join(f"{r.n_packets} {name} records"
                              for name, r in recs.items())
            raise ValueError(
                f"{path}: contains no {requested.name} records "
                f"(found: {found}) - use that format or format='auto'")
        primary_name = requested.name
    else:
        primary_name = max(recs, key=lambda k: recs[k].n_packets)

    primary = recs.pop(primary_name)
    primary.siblings = list(recs.values())
    primary.n_resyncs = n_resyncs
    primary.n_skipped_bytes = n_skipped
    return primary
