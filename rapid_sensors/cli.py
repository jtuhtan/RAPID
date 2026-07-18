"""``rapid-convert``: turn sensor binaries into CSV files + plots.

Typical use::

    rapid-convert data/RAPID/RAPID_V3/RAPID_V3_IMP/Turbine       # a folder
    rapid-convert B38-0928141315.IMP --plot                      # one file
    rapid-convert measurement.txt --info                         # inspect only

For every input file this writes ``CSV/<name>-<format>.csv`` next to it
(the folder convention of the legacy scripts) and, with ``--plot``,
``PLOTS/<name>-<format>.png``.  The sensor type is detected from the
file content; force it with ``--format`` if needed.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from .formats import FORMATS, DetectionError
from .readers import read

_SENSOR_EXTENSIONS = (".txt", ".hig", ".imp")


def _collect_files(inputs, recursive: bool):
    """Expand files/folders into a list of candidate sensor files."""
    files = []
    for item in inputs:
        if os.path.isfile(item):
            files.append(item)
        elif os.path.isdir(item):
            if recursive:
                for base, _dirs, names in os.walk(item):
                    files += [os.path.join(base, n) for n in names]
            else:
                files += [os.path.join(item, n) for n in os.listdir(item)
                          if os.path.isfile(os.path.join(item, n))]
        else:
            sys.exit(f"error: {item} is neither a file nor a folder")
    return [f for f in files
            if os.path.splitext(f)[1].lower() in _SENSOR_EXTENSIONS]


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        prog="rapid-convert",
        description="Convert RAPID / BDS sensor binaries to CSV "
                    "(and overview plots).",
        epilog="Formats: " + "; ".join(
            f"{name} = {f.description}" for name, f in FORMATS.items()))
    parser.add_argument("inputs", nargs="+",
                        help="sensor files and/or folders containing them")
    parser.add_argument("--format", default="auto",
                        choices=["auto", *FORMATS],
                        help="sensor format (default: detect per file)")
    parser.add_argument("--out-dir", default=None,
                        help="write all CSVs here (default: a CSV/ "
                             "subfolder next to each input file)")
    parser.add_argument("--plot", action="store_true",
                        help="also write an overview PNG per file")
    parser.add_argument("--info", action="store_true",
                        help="only print file summaries; write nothing")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="descend into subfolders of input folders")
    args = parser.parse_args(argv)

    files = _collect_files(args.inputs, args.recursive)
    if not files:
        sys.exit("error: no sensor files (.txt, .HIG, .IMP) found in the "
                 "given inputs")

    failures = 0
    for path in files:
        try:
            tic = time.perf_counter()
            rec = read(path, fmt=args.format)
            toc = time.perf_counter() - tic
        except (DetectionError, ValueError) as exc:
            print(f"SKIPPED {path}\n  {exc}")
            failures += 1
            continue

        print(rec.summary())
        print(f"parsed  : {toc:.2f} s")
        if not args.info:
            stem = os.path.splitext(os.path.basename(path))[0]
            out_dir = args.out_dir or os.path.join(os.path.dirname(path)
                                                   or ".", "CSV")
            os.makedirs(out_dir, exist_ok=True)
            written = []
            # a mixed-mode BDS file yields one output per record type
            for part in (rec, *rec.siblings):
                csv_path = os.path.join(out_dir,
                                        f"{stem}-{part.fmt.name}.csv")
                part.to_csv(csv_path)
                written.append(csv_path)
                if args.plot:
                    plot_dir = args.out_dir or os.path.join(
                        os.path.dirname(path) or ".", "PLOTS")
                    os.makedirs(plot_dir, exist_ok=True)
                    from .plots import plot_overview
                    png_path = os.path.join(
                        plot_dir, f"{stem}-{part.fmt.name}.png")
                    plot_overview(part, png_path)
                    written.append(png_path)
            for w in written:
                print(f"written : {w}")
        print()

    total = len(files)
    print(f"done: {total - failures}/{total} files converted"
          + (f", {failures} skipped" if failures else ""))
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
