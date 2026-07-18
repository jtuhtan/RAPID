"""Benchmark: legacy import loops vs the vectorized rapid_sensors readers.

The legacy contenders reproduce the exact read strategy of the old
scripts on the repository's own sample data:

* IMP / HIG: ``python/legacy`` scripts — one ``struct.unpack`` call and
  one ``seek`` per value, multiple passes over the file (itself a port
  of the MATLAB ``fread``-with-skip loops).
* BDS: the old ``import_BDS_RAPID_v1.py`` — ``struct.iter_unpack`` of
  the whole file into a list of tuples, then a DataFrame.

Run:  python benchmarks/benchmark_convert.py
"""

import struct
import time
from pathlib import Path

import numpy as np

import rapid_sensors

DATA = Path(__file__).resolve().parent.parent / "data"


def legacy_imp(path):
    """The exact loop from python/legacy/import_IMP_RAPID_v3.py."""
    packet = 29
    flen = path.stat().st_size // packet - 1
    with open(path, "rb") as f:
        times = []
        for _ in range(flen):
            times.append(struct.unpack(">i", f.read(4))[0])
            f.seek(25, 1)
        data = np.zeros((flen, 12), dtype=np.int16)
        f.seek(4, 0)
        for it in range(1, flen):
            for col in range(9):
                data[it, col] = struct.unpack(">h", f.read(2))[0]
            f.seek(2, 1)
            data[it, 9] = struct.unpack(">h", f.read(2))[0]
            data[it, 10] = struct.unpack(">h", f.read(2))[0]
            f.seek(5, 1)
    return times, data


def legacy_hig(path, max_packets=None):
    """The exact loop from python/legacy/import_HIG_RAPID_v3.py."""
    packet = 11
    flen = path.stat().st_size // packet - 1
    if max_packets:
        flen = min(flen, max_packets)
    with open(path, "rb") as f:
        times = []
        for _ in range(flen):
            times.append(struct.unpack(">i", f.read(4))[0])
            f.seek(7, 1)
        data = np.zeros((flen, 3), dtype=np.int16)
        f.seek(4 + 11, 0)
        for it in range(flen):
            data[it, 0] = struct.unpack(">h", f.read(2))[0]
            data[it, 1] = struct.unpack(">h", f.read(2))[0]
            data[it, 2] = struct.unpack(">h", f.read(2))[0]
            f.seek(5, 1)
    return times, data


def legacy_bds(path):
    """The read strategy of the old BDS100 class (struct.iter_unpack)."""
    import pandas as pd
    binary = path.read_bytes()
    fmt = "HI22f4B"
    size = struct.calcsize(fmt)
    usable = (len(binary) // size) * size
    rows = [x for x in struct.iter_unpack(fmt, binary[:usable])]
    return pd.DataFrame(rows)


def bench(label, legacy_fn, path, scale=1.0):
    tic = time.perf_counter()
    legacy_fn(path)
    t_legacy = (time.perf_counter() - tic) * scale

    tic = time.perf_counter()
    rapid_sensors.read(path)
    t_new = time.perf_counter() - tic

    note = " (extrapolated)" if scale != 1.0 else ""
    print(f"{label:44s} legacy {t_legacy:8.2f}s{note}   "
          f"new {t_new:6.3f}s   speedup {t_legacy / t_new:8.0f}x")


def main():
    print("legacy import loops vs rapid_sensors.read()\n")
    imp = DATA / "RAPID/RAPID_V3/RAPID_V3_IMP/Turbine/B38-0928141315.IMP"
    hig = DATA / "RAPID/RAPID_V3/RAPID_V3_HIG/Turbine/B38-0928141315.HIG"
    bds = DATA / "BDS/100_Hz/C130909084837.txt"

    bench(f"IMP  {imp.name}  ({imp.stat().st_size/1e6:.1f} MB)",
          legacy_imp, imp)

    # the full HIG file has 1.2 M packets; the legacy loop is run on
    # 200k of them and scaled up linearly
    n_total = hig.stat().st_size // 11 - 1
    n_sub = 200_000
    bench(f"HIG  {hig.name}  ({hig.stat().st_size/1e6:.1f} MB)",
          lambda p: legacy_hig(p, n_sub), hig, scale=n_total / n_sub)

    bench(f"BDS  {bds.name}  ({bds.stat().st_size/1e6:.1f} MB)",
          legacy_bds, bds)


if __name__ == "__main__":
    main()
