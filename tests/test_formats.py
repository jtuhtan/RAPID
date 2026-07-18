"""Format auto-detection: every sample file in data/ must be identified."""

import numpy as np
import pytest

from rapid_sensors import DetectionError, detect_format

from conftest import all_sample_files

CASES = all_sample_files()


@pytest.mark.parametrize(
    "path,expected", CASES,
    ids=[f"{exp}:{p.name}" for p, exp in CASES] or None)
def test_detects_every_sample_file(path, expected):
    assert detect_format(path).name == expected


def test_garbage_rejected(tmp_path):
    junk = tmp_path / "junk.txt"
    junk.write_bytes(np.random.default_rng(0).bytes(4096))
    with pytest.raises(DetectionError, match="--format"):
        detect_format(junk)


def test_tiny_file_rejected(tmp_path):
    tiny = tmp_path / "tiny.txt"
    tiny.write_bytes(b"\x00" * 8)
    with pytest.raises(DetectionError):
        detect_format(tiny)
