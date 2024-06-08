import struct
from abc import ABC, abstractmethod
from pathlib import Path
from jupyter_client import BlockingKernelClient

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.style.use("seaborn-whitegrid")


class Rapid(ABC):
    def __init__(
        self, filename: str
    ) -> None:  # Attributes same for all Sensors can be placed here
        """This is an abstract class (ABC).
        It provides methods which are the same between the sensor / subclasses.
        This class is never called by the user, only by its children.

        """
        self.filename = Path(filename)
        self.dir_csv = Path("csv/")
        self.dir_plots = Path("plots/")

    def _mkdir(self, path_object: Path) -> None:
        path_object.mkdir(parents=True, exist_ok=True)

    def _save_as_csv(self, data, **kwargs) -> None:
        self._mkdir(self.dir_csv)
        data.to_csv(
            (self.dir_csv / self.filename.stem).with_suffix(".csv"),
            sep=",",
            index=False,
            **kwargs
        )

    def _process_and_save(self, savecsv, **kwargs) -> None:
        data = self._read_data()
        data = self._post_process(data)
        if savecsv == True:
            self._save_as_csv(data, **kwargs)
        return data

    @abstractmethod
    def _post_process(self, data: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError("Child must override post_process")
        return data

    def _read_data(self) -> pd.DataFrame:
        with open(self.filename.as_posix(), mode="r+b") as f:
            binary_data = f.read()
        len_fmt = struct.calcsize(self.fmt)
        max_accept_len = (len(binary_data) // len_fmt) * len_fmt
        bin_new = binary_data[0:max_accept_len]
        iter = struct.iter_unpack(self.fmt, bin_new)
        data = [x for x in iter]
        data = pd.DataFrame(data, columns=self.column_names_raw)
        return data

    def plot_data_overview(self, save: bool = True, show: bool = False) -> None:
        """Plots an overview for the generated data.
        This is primarily to spot problems before further user-processing.
        The save-option can be helpful as a visual aid for the future as to
        which measurements measured what.

        Parameters
        ----------
        save : bool
            Save the file at location specified in <sensorclass>.dir_plots, by default True
        show : bool
            Show an interactive plot when executed, by default False
        """
        t = self.data["time"][::10]
        pres = self.data["pres"].rolling(10).mean()[::10]
        accmag = self.data["accmag"].rolling(10).mean()[::10]

        color = "C0"
        fig, ax1 = plt.subplots(figsize=(25, 5))
        ax1.set_xlabel("time [s]")
        ax1.set_ylabel("Pressure [hPa]", color=color)
        ax1.plot(t, pres, color=color)
        ax1.tick_params(axis="y", labelcolor=color)
        ax1.ticklabel_format(useOffset=False)

        ax2 = ax1.twinx()
        color = "C1"
        ax2.set_ylabel("Acceleration magnitude [g]", color=color)
        ax2.plot(t, accmag, color=color)
        ax2.tick_params(axis="y", labelcolor=color)
        fig.tight_layout()

        if save == True:
            self._mkdir(self.dir_plots)
            plt.savefig((self.dir_plots / self.filename.name).with_suffix(".png"))
        if show == True:
            plt.show()
        plt.close()


from importData import Rapid


class BDS100(Rapid):
    def __init__(self, filename: str, savecsv: bool = True, **kwargs) -> None:
        """This class processes BDS measurements at 100 Hz. 
        At that speed, the internal data fusion algorithm computes an absolute orientation, 
        which is used to get from a relative to an absolute acceleration.
        Acceleration magnitude is included in the ouput and 
        has gravity already removed.

        Parameters
        ----------
        filename : str
            Relative file location + filename of the measurement
        savecsv : bool, optional
            Saves the processed data as a csv file if True, by default True
        **kwargs : optional
            Keyword arguments for changing how the csv is generated and are feeded directly into pd.read_csv().
        """
        super().__init__(filename)
        self.dir_csv = self.dir_csv / "BDS100"
        self.dir_plots = self.dir_plots / "BDS100"
        self.fmt = "HI22f4B"  # format string to set byteorder
        self.column_names_raw = [
            "sample rate",
            "time",
            "P1",
            "T1",
            "P2",
            "T2",
            "P3",
            "T3",
            "eul head",
            "eul roll",
            "eul pitch",
            "quat w",
            "quatx",
            "quaty",
            "quatz",
            "magx",
            "magy",
            "magz",
            "accx",
            "accy",
            "accz",
            "gyrox",
            "gyroy",
            "gyroz",
            "calmag",
            "calacc",
            "calgyro",
            "calimu",
        ]
        self.data = super()._process_and_save(savecsv, **kwargs)

    def _post_process(self, data: pd.DataFrame) -> pd.DataFrame:
        data["time"] = (data["time"] - data["time"][0]) / 1000
        data.insert(1, "pres", np.average(data[["P1", "P2", "P3"]], axis=-1))
        data.insert(1, "accmag", np.linalg.norm(data[["accx", "accy", "accz"]], axis=-1))
        data["accmag"] -= 9.81
        data = data[
            [
                "time",
                "pres",
                "accx",
                "accy",
                "accz",
                "accmag",
                "gyrox",
                "gyroy",
                "gyroz",
                "quat w",
                "quatx",
                "quaty",
                "quatz",
                "calmag",
                "calacc",
                "calgyro",
                "calimu",
            ]
        ]
        return data

    def _absolute_orientation(self, data: pd.DataFrame) -> pd.DataFrame:
        import quaternion

        # Translate body acc with earths mag field to abs reference frame
        quat_ref_frame = quaternion.as_quat_array(
            data[["quat w", "quatx", "quaty", "quatz"]]
        )

        acc_earth = np.zeros((0, 3))
        for idx, q in enumerate(quat_ref_frame):
            acc = quaternion.rotate_vectors(q, data.loc[idx, "accx":"accz"])
            acc_earth = np.vstack((acc_earth, acc))
        acc_earth[:, 2] -= 9.81
        data.insert(5, "absaccx", acc_earth[:, 0])
        data.insert(6, "absaccy", acc_earth[:, 1])
        data.insert(7, "absaccz", acc_earth[:, 2])
        return data


class BDS250(Rapid):
    def __init__(self, filename: str, savecsv: bool = True, **kwargs) -> None:
        """This class processes BDS measurements at 250 Hz. 
        At that speed, there is no absolute orientation computation, 
        outputs are absolute pressure, accelerometer and gyroscope.
        Acceleration magnitude is included in the ouput and 
        has gravity already removed.

        Parameters
        ----------
        filename : str
            Relative file location + filename of the measurement
        savecsv : bool, optional
            Saves the processed data as a csv file if True, by default True
        **kwargs : optional
            Keyword arguments for changing how the csv is generated and are feeded directly into pd.read_csv().
        """
        super().__init__(filename)
        self.dir_csv = self.dir_csv / "BDS250"
        self.dir_plots = self.dir_plots / "BDS250"
        self.fmt = "HI12f4B"
        self.column_names_raw = [
            "samplerate",
            "time",
            "P1",
            "T1",
            "P2",
            "T2",
            "P3",
            "T3",
            "accx",
            "accy",
            "accz",
            "gyrox",
            "gyroy",
            "gyroz",
            "calmag",
            "calacc",
            "calgyro",
            "calimu",
        ]
        self.data = super()._process_and_save(savecsv, **kwargs)

    def _post_process(self, data: pd.DataFrame) -> pd.DataFrame:
        data["time"] = (data["time"] - data["time"][0]) / 1000
        data.insert(1, "pres", np.average(data[["P1", "P2", "P3"]], axis=-1))
        data.insert(1, "accmag", np.linalg.norm(data[["accx", "accy", "accz"]], axis=-1))
        data["accmag"] -= 9.81
        data = data[
            [
                "time",
                "pres",
                "accx",
                "accy",
                "accz",
                "accmag",
                "gyrox",
                "gyroy",
                "gyroz",
                "calacc",
                "calgyro",
                "calimu",
            ]
        ]
        return data


class EDF(Rapid):
    def __init__(self, filename: str, savecsv: bool = True, **kwargs) -> None:
        """This class processes EDF measurements at 2048 Hz. 
        Outputs are absolute pressure and accelerometer.
        Acceleration magnitude is included in the ouput and 
        has gravity already removed.

        Parameters
        ----------
        filename : str
            Relative file location + filename of the measurement
        savecsv : bool, optional
            Saves the processed data as a csv file if True, by default True
        **kwargs : optional
            Keyword arguments for changing how the csv is generated and are feeded directly into pd.read_csv().
        """
        super().__init__(filename)
        self.dir_csv = self.dir_csv / "EDF"
        self.dir_plots = self.dir_plots / "EDF"
        self.fmt = ">5hx"
        self.column_names_raw = ["index", "accx", "accy", "accz", "pres"]
        self.p_gain = 10
        self.acc_gain = 10
        self.fs = 2048
        self.data = super()._process_and_save(savecsv, **kwargs)

    def _post_process(self, data: pd.DataFrame) -> pd.DataFrame:
        data[["accx", "accy", "accz"]] /= self.acc_gain
        data["pres"] /= self.p_gain
        data.insert(1, "time", data.index / self.fs)
        data.insert(1, "accmag", np.linalg.norm(data[["accx", "accy", "accz"]], axis=-1))
        data["accmag"] -= 9.81
        data = data[["time", "pres", "accx", "accy", "accz", "accmag"]]
        return data


if __name__ == "__main__":

    for f in Path("./test_data/BDS100").glob("*.txt"):
        filename = f
        mymeas = BDS250(filename)
        mymeas.plot_data_overview()
