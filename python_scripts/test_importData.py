import unittest
import pandas as pd
from pandas.testing import assert_frame_equal

import importData


class TestImportData(unittest.TestCase):
    def __init__(self, methodName: str = ...) -> None:
        super().__init__(methodName)
        from pathlib import Path

        self.dtcsv = Path("csv")
        self.drcsv = Path("test_csv")
        self.rawdata = Path("test_data")
        self.fBDS100 = Path("BDS100/B250224193556")
        self.fBDS250 = Path("BDS250/B070622135103")
        self.fEDF = Path("EDF/A010521122600")

        self.tBDS100 = self.dtcsv / self.fBDS100.with_suffix(".csv")
        self.rBDS100 = self.drcsv / self.fBDS100.with_suffix(".csv")
        self.aBDS100 = self.rawdata / self.fBDS100.with_suffix(".txt")

        self.tBDS250 = self.dtcsv / self.fBDS250.with_suffix(".csv")
        self.rBDS250 = self.drcsv / self.fBDS250.with_suffix(".csv")
        self.aBDS250 = self.rawdata / self.fBDS250.with_suffix(".txt")

        self.tEDF = self.dtcsv / self.fEDF.with_suffix(".csv")
        self.rEDF = self.drcsv / self.fEDF.with_suffix(".csv")
        self.aEDF = self.rawdata / self.fEDF.with_suffix(".txt")

    def test_EDF(self):
        mymeas = importData.EDF(self.aEDF)
        test_df = mymeas.data
        ref_df = pd.read_csv(self.rEDF)
        assert_frame_equal(test_df, ref_df)

    def test_BDS100(self):
        mymeas = importData.BDS100(self.aBDS100)
        test_df = mymeas.data
        ref_df = pd.read_csv(self.rBDS100)
        assert_frame_equal(test_df, ref_df)

    def test_BDS250(self):
        mymeas = importData.BDS250(self.aBDS250)
        test_df = mymeas.data
        ref_df = pd.read_csv(self.rBDS250)
        assert_frame_equal(test_df, ref_df)


if __name__ == "__main__":
    unittest.main()
