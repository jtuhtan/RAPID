# Legacy Python import scripts (deprecated)

> **⚠️ Deprecated.** These are the original stand-alone import scripts,
> kept for reference. Use the `rapid_sensors` package at the repository
> root instead (`pip install -e .` then `rapid-convert --help`) — it is
> 3–18× faster, auto-detects the sensor type, recovers corrupted and
> mixed-mode files, and is covered by tests.

Known issues in these scripts (all fixed in `rapid_sensors`):

1. **`import_BDS_RAPID_v1.py` does not run as-is**: it imports
   `jupyter_client` (unused) and `from importData import Rapid` (a
   module that does not exist in this repository), uses the
   `seaborn-whitegrid` matplotlib style (removed in matplotlib 3.6),
   and its `__main__` block feeds 100 Hz files into the 250 Hz class.
2. **Outdated RAPID V1 gain**: the `EDF` class divides accelerations by
   10, the pre-2022-11-01 gain. Its CSV output under-reports
   acceleration by a factor of 10 (see
   [docs/file_formats.md](../../docs/file_formats.md)).
3. **One-packet misalignment**: `import_HIG_RAPID_v3.py` and
   `import_IMP_RAPID_v3.py` pair the timestamp of packet *i* with the
   sensor values of packet *i+1*.
4. **No corruption handling**: files that lose byte alignment mid-way
   (or BDS files that switch logger modes) are silently decoded into
   garbage rows after that point.
