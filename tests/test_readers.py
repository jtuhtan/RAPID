"""Reader correctness.

Two layers of protection:

1. *Independent cross-check*: the first packets of each file are also
   decoded with plain ``struct.iter_unpack`` (a second implementation
   of the byte layout) and must match the vectorized reader exactly.
2. *Physical sanity*: decoded values must land in physically plausible
   ranges for the instrument (atmospheric pressure, gravity, battery
   voltage, BNO055 calibration flags 0..3) — this is what catches a
   wrong gain or byte offset, and it reproduces the checks used to
   verify the formats against the legacy MATLAB readers.
"""

import struct

import numpy as np
import pytest

from rapid_sensors import read

N_CHECK = 2000  # packets cross-checked against the struct reference


def struct_reference(path, fmt_string, n):
    raw = open(path, "rb").read((struct.calcsize(fmt_string)) * n)
    n_full = len(raw) // struct.calcsize(fmt_string)
    return np.array(list(struct.iter_unpack(
        fmt_string, raw[: n_full * struct.calcsize(fmt_string)])))


class TestRapidV1:
    def test_matches_struct_reference(self, v1_shock):
        rec = read(v1_shock, fmt="rapid_v1")
        ref = struct_reference(v1_shock, ">5hB", N_CHECK)
        df = rec.data.head(len(ref))
        np.testing.assert_array_equal(df["Counter"], ref[:, 0])
        np.testing.assert_allclose(df["Accel_X (m/s2)"], ref[:, 1])
        np.testing.assert_allclose(df["Pressure (mbar)"], ref[:, 4] * 0.1)

    def test_physical_sanity(self, v1_shock):
        rec = read(v1_shock)
        assert rec.fmt.name == "rapid_v1"
        assert rec.n_bad_terminator == 0
        p = rec.data["Pressure (mbar)"]
        assert 900 < p.median() < 1100          # ~1 atm in the lab
        amax_g = rec.data["Accel_Mag (m/s2)"].max() / 9.81
        assert 100 < amax_g < 1000              # a 400 g shock test
        t = rec.data["Time (s)"]
        assert np.allclose(np.diff(t), 1 / 2048)

    def test_counter_wraps_at_2048(self, v1_shock):
        rec = read(v1_shock)
        c = rec.data["Counter"].to_numpy()
        assert c.min() >= 1 and c.max() <= 2048
        d = np.diff(c)
        assert np.isin(d, (1, -2047)).mean() > 0.99


class TestHig:
    def test_matches_struct_reference(self, hig_file):
        rec = read(hig_file)
        ref = struct_reference(hig_file, ">i3hB", N_CHECK)
        df = rec.data.head(len(ref))
        np.testing.assert_allclose(df["Time (s)"], ref[:, 0] / 2000.0)
        np.testing.assert_allclose(df["HIGAccel_X (g)"], ref[:, 1] * 0.1)
        np.testing.assert_allclose(df["HIGAccel_Z (g)"], ref[:, 3] * 0.1)

    def test_physical_sanity(self, hig_file):
        rec = read(hig_file)
        assert rec.fmt.name == "hig"
        assert rec.n_bad_terminator == 0
        # 2000 Hz tick advancing by 1 per packet
        t = rec.data["Time (s)"].to_numpy()
        assert np.allclose(np.diff(t), 1 / 2000)
        mag = rec.data["HIGAccel_Mag (g)"]
        assert mag.max() < 800                  # +/-400 g sensor
        assert 0 < mag.median() < 20            # noise floor at rest


class TestImp:
    def test_matches_struct_reference(self, imp_file):
        rec = read(imp_file)
        ref = struct_reference(imp_file, ">i9hH2hB", N_CHECK)
        df = rec.data.head(len(ref))
        np.testing.assert_allclose(df["Time (s)"], ref[:, 0] / 2000.0)
        np.testing.assert_allclose(df["Accel_X (g)"],
                                   ref[:, 1] * 0.005 / 9.81)
        np.testing.assert_allclose(df["Pressure (mbar)"], ref[:, 10] * 0.1)
        np.testing.assert_allclose(df["Battery (V)"], ref[:, 12] * 0.01)

    def test_physical_sanity(self, imp_file):
        rec = read(imp_file)
        assert rec.fmt.name == "imp"
        assert rec.n_bad_terminator == 0
        # at rest the IMU should read ~1 g total (gravity)
        assert 0.8 < rec.data["Accel_Mag (g)"].median() < 1.2
        assert 900 < rec.data["Pressure (mbar)"].min() < 1100
        assert 3.0 < rec.data["Battery (V)"].median() < 4.5
        assert 5 < rec.data["P_Temp (C)"].median() < 30

    def test_imp_samples_at_100hz(self, imp_file):
        # the tick counter runs at 2000 Hz but advances by 20 per
        # packet: the IMP's true sampling rate is 100 Hz
        rec = read(imp_file)
        dt = np.diff(rec.data["Time (s)"].to_numpy())
        assert np.isclose(np.median(dt), 0.010, atol=1e-6)


class TestBds:
    @pytest.mark.parametrize("fixture,n_cols",
                             [("bds100_file", 29), ("bds250_file", 19)])
    def test_shape_and_sanity(self, fixture, n_cols, request):
        rec = read(request.getfixturevalue(fixture))
        df = rec.data
        assert len(df.columns) == n_cols
        assert 900 < df["Pressure (mbar)"].median() < 1100
        for col in ("Cal_Mag", "Cal_Acc", "Cal_Gyro", "Cal_Sys"):
            assert df[col].between(0, 3).all()
        t = df["Time (s)"].to_numpy()
        assert t[0] == 0.0
        assert (np.diff(t) > 0).mean() > 0.999  # ms clock, monotonic

    def test_bds100_orientation_channels(self, bds100_file):
        rec = read(bds100_file)
        q = rec.data[["Quat_W", "Quat_X", "Quat_Y", "Quat_Z"]].to_numpy()
        qnorm = np.linalg.norm(q, axis=1)
        # unit quaternions from the BNO055 fusion (when calibrated)
        assert 0.9 < np.median(qnorm) < 1.1

    def test_bds100_matches_struct_reference(self, bds100_file):
        rec = read(bds100_file)
        # "x" pad bytes yield no values, so the unpacked tuple is:
        # 0 marker, 1 t_ms, 2..7 P/T pairs, 8..10 euler, 11..14 quat,
        # 15..17 mag, 18..20 acc, 21..23 gyro, 24..27 cal
        ref = struct_reference(bds100_file, "<HxxI22f4B", N_CHECK)
        df = rec.data.head(len(ref))
        np.testing.assert_allclose(df["P1 (mbar)"], ref[:, 2], rtol=1e-6)
        np.testing.assert_allclose(df["Accel_X (m/s2)"], ref[:, 18],
                                   rtol=1e-6)
        np.testing.assert_array_equal(df["Cal_Sys"], ref[:, -1])


class TestCorruptionRecovery:
    def test_mixed_mode_bds_file_fully_recovered(self):
        # this sample file switches logger modes mid-recording: ~30 s
        # of 100-mode records, a 4-byte stub, then ~7 min of 250-mode
        # records.  The stream parser must recover BOTH segments (the
        # legacy readers decoded everything after the switch as
        # garbage rows).
        from conftest import data_file
        path = data_file("BDS", "100_Hz", "C350419125306.txt")
        rec = read(path)
        assert rec.fmt.name == "bds250"        # majority type
        assert rec.n_packets > 40000
        assert rec.n_resyncs >= 1
        assert rec.n_skipped_bytes < 100       # only the stub + tail
        assert len(rec.siblings) == 1
        sib = rec.siblings[0]
        assert sib.fmt.name == "bds100"
        assert 2900 < sib.n_packets < 3100
        # both segments must be physically sane throughout
        for part in (rec, sib):
            df = part.data
            assert 900 < df["Pressure (mbar)"].median() < 1100
            for col in ("Cal_Mag", "Cal_Acc", "Cal_Gyro", "Cal_Sys"):
                assert df[col].between(0, 3).all()

    def test_forcing_minority_type_selects_it(self):
        from conftest import data_file
        path = data_file("BDS", "100_Hz", "C350419125306.txt")
        rec = read(path, fmt="bds100")
        assert rec.fmt.name == "bds100"
        assert 2900 < rec.n_packets < 3100
        assert rec.siblings[0].fmt.name == "bds250"

    def test_synthetic_corruption_roundtrip(self, bds250_file, tmp_path):
        raw = bds250_file.read_bytes()
        clean = read(bds250_file)
        # delete 7 bytes mid-file: everything after loses alignment
        cut = (len(raw) // 2 // 60) * 60
        mangled = tmp_path / "mangled.txt"
        mangled.write_bytes(raw[:cut] + raw[cut + 7:])
        rec = read(mangled, fmt="bds250")
        assert rec.n_resyncs >= 1
        # at most a couple of packets around the cut may be lost
        assert rec.n_packets >= clean.n_packets - 3
        np.testing.assert_allclose(
            rec.data["P1 (mbar)"].iloc[:100],
            clean.data["P1 (mbar)"].iloc[:100])


class TestLegacyAlignment:
    def test_new_reader_is_packet_aligned(self, imp_file):
        """The legacy V3 scripts paired time[i] with data of packet
        i+1; the new reader pairs time and data from the same packet.
        This documents (and pins) the intentional one-packet shift
        between legacy CSVs and new output."""
        rec = read(imp_file)
        # legacy-style read of the first packets: time from packet i,
        # acc from packet i+1
        ref = struct_reference(imp_file, ">i9hH2hB", 50)
        legacy_ax_row0 = ref[1, 1] * 0.005 / 9.81   # packet 1's data
        new_ax_row0 = rec.data["Accel_X (g)"].iloc[0]  # packet 0's data
        np.testing.assert_allclose(new_ax_row0,
                                   ref[0, 1] * 0.005 / 9.81)
        # and row 1 of the new output equals legacy row 0
        np.testing.assert_allclose(rec.data["Accel_X (g)"].iloc[1],
                                   legacy_ax_row0)


class TestErrors:
    def test_unknown_format_name(self, v1_shock):
        with pytest.raises(ValueError, match="unknown format"):
            read(v1_shock, fmt="banana")

    def test_empty_file(self, tmp_path):
        empty = tmp_path / "empty.HIG"
        empty.write_bytes(b"")
        with pytest.raises(ValueError, match="no complete"):
            read(empty)
