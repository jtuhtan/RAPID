"""End-to-end CLI tests on the repository's own sample data."""

import numpy as np
import pandas as pd
import pytest

from rapid_sensors.cli import main


class TestConvert:
    def test_single_file_to_out_dir(self, bds250_file, tmp_path):
        out = tmp_path / "out"
        main([str(bds250_file), "--out-dir", str(out)])
        csvs = list(out.glob("*.csv"))
        assert len(csvs) == 1
        df = pd.read_csv(csvs[0])
        assert "Time (s)" in df.columns
        assert "Pressure (mbar)" in df.columns
        assert len(df) > 1000

    def test_plot_written(self, v1_shock, tmp_path):
        out = tmp_path / "out"
        main([str(v1_shock), "--out-dir", str(out), "--plot"])
        assert list(out.glob("*.csv"))
        assert list(out.glob("*.png"))

    def test_info_writes_nothing(self, imp_file, tmp_path, capsys):
        out = tmp_path / "out"
        main([str(imp_file), "--out-dir", str(out), "--info"])
        assert not out.exists()
        text = capsys.readouterr().out
        assert "imp" in text
        assert "packets" in text

    def test_folder_input(self, bds250_file, tmp_path):
        out = tmp_path / "out"
        main([str(bds250_file.parent), "--out-dir", str(out)])
        assert len(list(out.glob("*.csv"))) >= 1

    def test_csv_roundtrip_values(self, imp_file, tmp_path):
        from rapid_sensors import read
        out = tmp_path / "out"
        main([str(imp_file), "--out-dir", str(out)])
        df = pd.read_csv(next(out.glob("*.csv")))
        rec = read(imp_file)
        # CSV precision is fixed per column; battery has 2 decimals
        np.testing.assert_allclose(df["Battery (V)"],
                                   rec.data["Battery (V)"], atol=0.005)

    def test_garbage_file_skipped_with_error_exit(self, tmp_path):
        junk = tmp_path / "junk.txt"
        junk.write_bytes(np.random.default_rng(1).bytes(8192))
        with pytest.raises(SystemExit):
            main([str(junk), "--out-dir", str(tmp_path / "o")])
