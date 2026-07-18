import os
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "data"


def data_file(*parts) -> Path:
    path = DATA.joinpath(*parts)
    if not path.exists():
        pytest.skip(f"sample data not present: {path}")
    return path


@pytest.fixture(scope="session")
def v1_shock():
    return data_file("RAPID", "RAPID_V1", "Shock_Test_400g",
                     "A030401151125.txt")


@pytest.fixture(scope="session")
def hig_file():
    return data_file("RAPID", "RAPID_V3", "RAPID_V3_HIG", "Turbine",
                     "B38-0928141315.HIG")


@pytest.fixture(scope="session")
def imp_file():
    return data_file("RAPID", "RAPID_V3", "RAPID_V3_IMP", "Turbine",
                     "B38-0928141315.IMP")


@pytest.fixture(scope="session")
def bds100_file():
    return data_file("BDS", "100_Hz", "C130909084837.txt")


@pytest.fixture(scope="session")
def bds250_file():
    return data_file("BDS", "250_Hz", "C1170314150039.txt")


# C350419125306.txt lives in the 100_Hz folder but is a mixed-mode
# recording: ~30 s of 100-mode records followed by ~7 min of 250-mode
# records, so its majority (detected) type is bds250.
_EXPECTED_OVERRIDES = {"C350419125306.txt": "bds250"}


def all_sample_files():
    """(path, expected_format) for every sensor file shipped in data/."""
    if not DATA.exists():
        return []
    cases = []
    for path in DATA.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(DATA).as_posix()
        if path.suffix == ".HIG":
            expected = "hig"
        elif path.suffix == ".IMP":
            expected = "imp"
        elif path.suffix == ".txt" and rel.startswith("BDS/100_Hz"):
            expected = "bds100"
        elif path.suffix == ".txt" and rel.startswith("BDS/250_Hz"):
            expected = "bds250"
        elif path.suffix == ".txt" and rel.startswith("RAPID/RAPID_V1"):
            expected = "rapid_v1"
        else:
            continue
        cases.append((path, _EXPECTED_OVERRIDES.get(path.name, expected)))
    return cases
