"""Overview figures for quick visual checks of a converted file."""

from __future__ import annotations

import os

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (backend must be set first)

from .readers import Recording

__all__ = ["plot_overview"]

# keep figures snappy even for multi-million-sample files
_MAX_POINTS = 200_000


def _decimate(*series):
    n = len(series[0])
    step = max(1, n // _MAX_POINTS)
    return [s[::step] for s in series]


def plot_overview(recording: Recording, path, dpi: int = 130) -> None:
    """Save a one-glance PNG of the recording.

    Pressure-bearing formats get the classic dual-axis plot (pressure
    + acceleration magnitude vs time, as in the legacy MATLAB PDFs);
    the HIG accelerometer gets its three axes and the magnitude.
    """
    df = recording.data
    t = df["Time (s)"].to_numpy()
    acc_col = next(c for c in df.columns if c.startswith(("Accel_Mag",
                                                          "HIGAccel_Mag")))
    acc_unit = acc_col.split("(")[1].rstrip(")")

    fig, ax1 = plt.subplots(figsize=(12, 4.5))
    ax1.set_xlabel("Time (s)")

    if "Pressure (mbar)" in df.columns:
        p = df["Pressure (mbar)"].to_numpy()
        a = df[acc_col].to_numpy()
        td, pd_, ad = _decimate(t, p, a)
        ax1.plot(td, pd_, color="C0", lw=0.8)
        ax1.set_ylabel("Pressure (mbar)", color="C0")
        ax1.tick_params(axis="y", labelcolor="C0")
        ax1.ticklabel_format(useOffset=False)
        ax2 = ax1.twinx()
        ax2.plot(td, ad, color="C3", lw=0.6, alpha=0.85)
        ax2.set_ylabel(f"Acceleration magnitude ({acc_unit})", color="C3")
        ax2.tick_params(axis="y", labelcolor="C3")
    else:  # HIG: acceleration only
        axes_cols = [c for c in df.columns
                     if c.startswith("HIGAccel_") and "Mag" not in c]
        series = _decimate(t, *[df[c].to_numpy() for c in axes_cols],
                           df[acc_col].to_numpy())
        td, comps, mag = series[0], series[1:-1], series[-1]
        for c, name in zip(comps, axes_cols):
            ax1.plot(td, c, lw=0.5, alpha=0.7, label=name)
        ax1.plot(td, mag, color="k", lw=0.7, label=acc_col)
        ax1.set_ylabel(f"Acceleration ({acc_unit})")
        ax1.legend(loc="upper right", fontsize=8)

    ax1.set_title(f"{os.path.basename(recording.source)}  "
                  f"[{recording.fmt.name}, {recording.n_packets} samples, "
                  f"{recording.duration_s:.1f} s]")
    ax1.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
