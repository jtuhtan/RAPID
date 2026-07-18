"""Binary packet formats for the RAPID and BDS sensor families.

Every sensor writes fixed-size packets back to back (no file header).
Each format is described by a NumPy structured dtype, which lets the
whole file be parsed in a single vectorized ``np.fromfile`` call —
this is what makes the new readers orders of magnitude faster than the
per-value ``struct.unpack`` / MATLAB ``fread`` loops they replace.

Byte-level layouts are documented in docs/file_formats.md.  All layouts
here were verified against the sample files in ``data/`` (terminator
bytes, counter behavior, and physically plausible decoded values).

Formats
-------
rapid_v1  RAPID V1 / EDF strike sensor, 2048 Hz, ``.txt``
          11-byte packet: 5 x int16 big-endian + 0x0B terminator.
hig       RAPID V3 high-g accelerometer (+/-400 g), 2000 Hz, ``.HIG``
          11-byte packet: int32 tick + 3 x int16 (BE) + 0x0B.
imp       RAPID V3 IMU + pressure, ``.IMP``
          29-byte packet: int32 tick + 12 x int16 (BE) + 0x0B.
          NOTE: ticks advance by 20 per packet on the 2000 Hz clock,
          so the actual IMP sampling rate is 100 Hz.
bds100    BDS logger, 100 Hz mode (with BNO055 orientation), ``.txt``
          100-byte packet: uint16 marker + 2 pad bytes + uint32 ms
          + 22 x float32 + 4 calibration bytes, little-endian.
bds250    BDS logger, 250 Hz mode (no orientation), ``.txt``
          60-byte packet: as bds100 but with 12 floats.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["FORMATS", "PacketFormat", "detect_format", "DetectionError"]


# The 0x0B ("vertical tab") byte that terminates every RAPID packet.
TERMINATOR = 0x0B

# Every BDS record begins with a CR-LF frame marker (bytes 0x0D 0x0A,
# which read as 2573 in the little-endian uint16 "marker" field — the
# legacy code mislabeled this field "sample rate").  The *next* uint16
# is the mode field: 100 for a 100-byte orientation record, 250 for a
# 60-byte raw-IMU record.  A single file may contain both (the logger
# can switch modes mid-recording), so BDS files are parsed as a typed
# record stream rather than a fixed grid.
BDS_MARKER = 2573
BDS_ANCHOR = b"\x0d\x0a"
BDS_RECORD_SIZES = {100: 100, 250: 60}   # mode field value -> record bytes
BDS_MODE_TO_FORMAT = {100: "bds100", 250: "bds250"}


@dataclass(frozen=True)
class PacketFormat:
    """Description of one binary packet layout.

    ``anchor``/``anchor_offset`` describe a fixed byte pattern that
    every packet carries at a known position (the CR-LF frame marker of
    BDS records, the 0x0B terminator of RAPID packets).  The readers
    use it to verify packet alignment and to *resynchronize* after
    corrupted regions instead of silently decoding garbage.
    """

    name: str
    description: str
    dtype: np.dtype           # one packet, including terminator/padding
    extensions: tuple         # lowercase filename extensions
    nominal_rate_hz: float    # the device clock the counter refers to
    anchor: bytes             # fixed marker bytes present in every packet
    anchor_offset: int        # byte offset of the marker within a packet
    terminator_field: str | None = None  # dtype field holding 0x0B

    @property
    def packet_size(self) -> int:
        return self.dtype.itemsize


def _dt(fields) -> np.dtype:
    return np.dtype(fields)


FORMATS: dict[str, PacketFormat] = {
    "rapid_v1": PacketFormat(
        name="rapid_v1",
        description="RAPID V1 / EDF strike sensor (2048 Hz)",
        dtype=_dt([("counter", ">i2"), ("ax", ">i2"), ("ay", ">i2"),
                   ("az", ">i2"), ("p", ">i2"), ("eol", "u1")]),
        extensions=(".txt",),
        nominal_rate_hz=2048.0,
        anchor=b"\x0b",
        anchor_offset=10,
        terminator_field="eol",
    ),
    "hig": PacketFormat(
        name="hig",
        description="RAPID V3 high-g accelerometer, +/-400 g (2000 Hz)",
        dtype=_dt([("tick", ">i4"), ("ax", ">i2"), ("ay", ">i2"),
                   ("az", ">i2"), ("eol", "u1")]),
        extensions=(".hig",),
        nominal_rate_hz=2000.0,
        anchor=b"\x0b",
        anchor_offset=10,
        terminator_field="eol",
    ),
    "imp": PacketFormat(
        name="imp",
        description="RAPID V3 IMU + pressure (100 Hz on a 2000 Hz clock)",
        dtype=_dt([("tick", ">i4"), ("ax", ">i2"), ("ay", ">i2"),
                   ("az", ">i2"), ("gx", ">i2"), ("gy", ">i2"),
                   ("gz", ">i2"), ("mx", ">i2"), ("my", ">i2"),
                   ("mz", ">i2"), ("p", ">u2"), ("ptemp", ">i2"),
                   ("bat", ">i2"), ("eol", "u1")]),
        extensions=(".imp",),
        nominal_rate_hz=2000.0,   # tick clock; packets arrive at 100 Hz
        anchor=b"\x0b",
        anchor_offset=28,
        terminator_field="eol",
    ),
    "bds100": PacketFormat(
        name="bds100",
        description="BDS logger, 100 Hz mode (pressure + BNO055 IMU "
                    "with orientation)",
        # Record layout: CR-LF frame marker, then a uint16 mode field
        # (100 or 250) that identifies the record type, then the ms
        # clock, payload floats, and 4 BNO055 calibration bytes.
        dtype=_dt([("marker", "<u2"), ("mode", "<u2"), ("t_ms", "<u4"),
                   ("P1", "<f4"), ("T1", "<f4"), ("P2", "<f4"),
                   ("T2", "<f4"), ("P3", "<f4"), ("T3", "<f4"),
                   ("eul_heading", "<f4"), ("eul_roll", "<f4"),
                   ("eul_pitch", "<f4"),
                   ("quat_w", "<f4"), ("quat_x", "<f4"),
                   ("quat_y", "<f4"), ("quat_z", "<f4"),
                   ("mx", "<f4"), ("my", "<f4"), ("mz", "<f4"),
                   ("ax", "<f4"), ("ay", "<f4"), ("az", "<f4"),
                   ("gx", "<f4"), ("gy", "<f4"), ("gz", "<f4"),
                   ("cal_mag", "u1"), ("cal_acc", "u1"),
                   ("cal_gyro", "u1"), ("cal_sys", "u1")]),
        extensions=(".txt",),
        nominal_rate_hz=100.0,
        anchor=BDS_ANCHOR,
        anchor_offset=0,
    ),
    "bds250": PacketFormat(
        name="bds250",
        description="BDS logger, 250 Hz mode (pressure + raw IMU, "
                    "no orientation)",
        dtype=_dt([("marker", "<u2"), ("mode", "<u2"), ("t_ms", "<u4"),
                   ("P1", "<f4"), ("T1", "<f4"), ("P2", "<f4"),
                   ("T2", "<f4"), ("P3", "<f4"), ("T3", "<f4"),
                   ("ax", "<f4"), ("ay", "<f4"), ("az", "<f4"),
                   ("gx", "<f4"), ("gy", "<f4"), ("gz", "<f4"),
                   ("cal_mag", "u1"), ("cal_acc", "u1"),
                   ("cal_gyro", "u1"), ("cal_sys", "u1")]),
        extensions=(".txt",),
        nominal_rate_hz=250.0,
        anchor=BDS_ANCHOR,
        anchor_offset=0,
    ),
}


class DetectionError(ValueError):
    """Raised when a file's format cannot be identified confidently."""


def align_to_anchor(buf: bytes, fmt: PacketFormat) -> bytes:
    """Slice ``buf`` so it starts on a packet boundary.

    Scans for the format's anchor bytes at a position that is confirmed
    by the *next* packet's anchor too (a chain of two), which makes a
    false match inside sensor data very unlikely.  Returns ``buf``
    unchanged if it already starts on a boundary or no boundary is
    found.
    """
    psize = fmt.packet_size
    off = fmt.anchor_offset

    def anchored(start: int) -> bool:
        pos = start + off
        return buf[pos:pos + len(fmt.anchor)] == fmt.anchor

    if anchored(0) and anchored(psize):
        return buf
    search = 0
    while True:
        hit = buf.find(fmt.anchor, search)
        if hit == -1:
            return buf
        start = hit - off
        if start >= 0 and start + 2 * psize <= len(buf) \
                and anchored(start) and anchored(start + psize):
            return buf[start:]
        search = hit + 1


def walk_bds_records(raw: bytes):
    """Walk a BDS typed-record stream.

    Each record is ``[CR-LF][uint16 mode][uint32 ms][payload][4 cal]``,
    where the mode field (100 or 250) determines the record length.  A
    record is accepted when its frame marker is in place and the *next*
    record boundary carries a marker too (or the file ends), so stray
    CR-LF bytes inside sensor values cannot derail the parse.

    Returns
    -------
    (segments, n_resyncs, n_skipped) where ``segments`` maps the mode
    value to a bytes object holding that mode's records back to back.
    """
    total = len(raw)
    segments = {mode: bytearray() for mode in BDS_RECORD_SIZES}
    resyncs = 0
    skipped = 0
    pos = 0

    def record_at(p: int) -> int | None:
        """Record size if a valid record starts at p, else None."""
        if raw[p:p + 2] != BDS_ANCHOR or p + 4 > total:
            return None
        mode = raw[p + 2] | (raw[p + 3] << 8)
        size = BDS_RECORD_SIZES.get(mode)
        if size is None or p + size > total:
            return None
        nxt = p + size
        if nxt + 2 <= total and raw[nxt:nxt + 2] != BDS_ANCHOR:
            return None
        return size

    while pos + 2 <= total:
        size = record_at(pos)
        if size is not None:
            mode = raw[pos + 2] | (raw[pos + 3] << 8)
            segments[mode] += raw[pos:pos + size]
            pos += size
            continue
        # scan forward for the next valid record boundary
        nxt = raw.find(BDS_ANCHOR, pos + 1)
        start = -1
        while nxt != -1:
            if record_at(nxt) is not None:
                start = nxt
                break
            nxt = raw.find(BDS_ANCHOR, nxt + 1)
        if start == -1:
            break
        skipped += start - pos
        pos = start
        resyncs += 1
    skipped += total - pos  # unreadable or partial tail
    return ({m: bytes(b) for m, b in segments.items() if b},
            resyncs, skipped)


def _decode_sample(buf: bytes, fmt: PacketFormat) -> np.ndarray | None:
    buf = align_to_anchor(buf, fmt)
    n = len(buf) // fmt.packet_size
    if n < 4:
        return None
    return np.frombuffer(buf[: n * fmt.packet_size], dtype=fmt.dtype)


def _score_rapid_v1(buf: bytes) -> float:
    rec = _decode_sample(buf, FORMATS["rapid_v1"])
    if rec is None:
        return -1.0
    term = (rec["eol"] == TERMINATOR).mean()
    d = np.diff(rec["counter"].astype(np.int64))
    # the counter runs 1..2048 and wraps, so steps are +1 or -2047
    ctr = np.isin(d, (1, -2047)).mean()
    return float(0.5 * term + 0.5 * ctr)


def _score_bds_family(buf: bytes):
    """(score, records-per-mode) for the BDS record stream in ``buf``."""
    segments, _resyncs, skipped = walk_bds_records(buf)
    if not segments:
        return -1.0, {}
    consumed = (len(buf) - skipped) / max(len(buf), 1)
    counts = {}
    sane = []
    for mode, seg in segments.items():
        rec = np.frombuffer(seg, dtype=FORMATS[BDS_MODE_TO_FORMAT[mode]].dtype)
        counts[mode] = rec.size
        cal = np.column_stack([rec["cal_mag"], rec["cal_acc"],
                               rec["cal_gyro"], rec["cal_sys"]])
        sane.append(((cal >= 0) & (cal <= 3)).all(axis=1).mean())
        p1 = rec["P1"]
        sane.append((np.isfinite(p1) & (p1 > 0) & (p1 < 20000)).mean())
    return float(consumed * np.mean(sane)), counts


def detect_format(path, sample_packets: int = 200) -> PacketFormat:
    """Identify the packet format of a sensor file.

    ``.HIG`` and ``.IMP`` files are identified by extension.  ``.txt``
    files (shared by RAPID V1 and the BDS logger) are identified from
    the content of chunks taken at the start and middle of the file:
    RAPID V1 by its 0x0B packet terminators and wrapping counter, BDS
    by walking its CR-LF-framed typed record stream.  For BDS the
    returned format is the file's *majority* record type; mixed-mode
    files are fully handled by :func:`rapid_sensors.read`, which
    exports every record type it finds.

    Raises
    ------
    DetectionError
        If no candidate (or more than one) fits.  The error message
        explains how to force a format with ``format=`` / ``--format``.
    """
    import os

    ext = os.path.splitext(str(path))[1].lower()
    if ext == ".hig":
        return FORMATS["hig"]
    if ext == ".imp":
        return FORMATS["imp"]

    size = os.path.getsize(path)
    chunk = sample_packets * max(BDS_RECORD_SIZES.values())
    with open(path, "rb") as fh:
        chunks = [fh.read(chunk)]
        if size > 3 * chunk:
            fh.seek((size // 2) - (size // 2) % 4)
            chunks.append(fh.read(chunk))

    v1_score = float(np.mean([_score_rapid_v1(c) for c in chunks]))
    bds_counts: dict = {}
    bds_scores = []
    for c in chunks:
        score, counts = _score_bds_family(c)
        bds_scores.append(score)
        for mode, cnt in counts.items():
            bds_counts[mode] = bds_counts.get(mode, 0) + cnt
    bds_score = float(np.mean(bds_scores))

    if v1_score >= 0.9 and v1_score - bds_score >= 0.1:
        return FORMATS["rapid_v1"]
    if bds_score >= 0.9 and bds_score - v1_score >= 0.1 and bds_counts:
        majority = max(bds_counts, key=bds_counts.get)
        return FORMATS[BDS_MODE_TO_FORMAT[majority]]
    raise DetectionError(
        f"cannot confidently identify the format of {path} "
        f"(scores: rapid_v1={v1_score:.2f}, bds={bds_score:.2f}). "
        f"If you know the sensor type, force it with format='<name>' / "
        f"--format <name>; valid names: {', '.join(FORMATS)}")
