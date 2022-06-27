# %%
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.signal as sig

import importData

plt.style.use("seaborn-whitegrid")
plt.rcParams["figure.figsize"] = (25, 5)

# %% read table and convert timestamps ms->s
mymeas = importData.EDF(
    "test_data/EDF/A010521122600.txt"
)  # The testdata is not from an actual impact, hence the algorithm will not work correctly
mymeas.plot_data_overview(save=False, show=True)
df = mymeas.data

df[["accx", "accy", "accz"]].plot()
df["accmag"].plot()


# %% Compute moment of inertia of sensor along axes
mSensor = 0.0383  # Mass of the sensor in kg
mSensor = 0.050
# %% Compound trans. acceleration to magnitude to remove g without absolute ref. Frame
transNorm = df["accmag"].to_numpy()
try:
    idx_cut = [
        np.argwhere(np.abs(transNorm) > 1)[0][0],
        np.argwhere(np.abs(transNorm) > 1)[-1][0],
    ]  # [2314, 2762]
except:
    idx_cut = [transNorm[0], transNorm[-1]]
print(f"{idx_cut=}")
print(f"{np.mean(transNorm[:idx_cut[0]])=}")
print(f"{np.mean(transNorm[idx_cut[0]:idx_cut[1]])=}")
print(f"{np.mean(transNorm[idx_cut[0]+100:idx_cut[1]])=}")
print(f"{np.mean(transNorm[idx_cut[1]:])=}")

# %% Remove sensor drift, use 3 distinct parts: before strike, strike, after strike
transNorm = sig.detrend(transNorm, bp=[idx_cut[0], idx_cut[1]])
print(f"{np.mean(transNorm[:idx_cut[0]])=}")
print(f"{np.mean(transNorm[idx_cut[0]:idx_cut[1]])=}")
print(f"{np.mean(transNorm[idx_cut[0]+100:idx_cut[1]])=}")
print(f"{np.mean(transNorm[idx_cut[1]:])=}")

# %% Integrate trans. acceleration to velocity
transVel = np.cumsum(transNorm) * np.gradient(df["time"])  # sample rate
plt.plot(transVel)

# %% Translation E = 0.5 * m * v**2
transKin = 0.5 * mSensor * transVel ** 2
plt.plot(transKin)
plt.figure()
plt.plot(np.gradient(transKin) / np.gradient(df["time"]))  # correct for 100 Hz sampling

# %%
Ekin = transKin
print(f"{np.mean(Ekin[:idx_cut[0]])=}")
print(f"{np.mean(Ekin[idx_cut[0]:idx_cut[1]])=}")
print(f"{np.mean(Ekin[idx_cut[0]+100:idx_cut[1]])=}")
print(f"{np.mean(Ekin[idx_cut[1]:])=}")
plt.plot(transKin)

# %%
Ekin = Ekin[idx_cut[0] - 20 : idx_cut[1] + 50]
t = df["time"][idx_cut[0] - 20 : idx_cut[1] + 50]

# %% Change in Ekin in respect to time
dEkindt = np.gradient(Ekin, t)
# %%
plt.plot(t, dEkindt)
plt.title("dEkin/dt")
plt.figure()
plt.plot(t, Ekin)
plt.title("Ekin")

# %%
