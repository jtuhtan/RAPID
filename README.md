# Code Repository and Example Data for BDS, RAPID and Fish Backpack Sensors
Current code supports three types of sensors: Robust Autonomous Pressure and Inertial Devices (RAPID), EU H2020 FITHydro Barotrauma Detection System (BDS) and Fish Backpacks for the reduction of live fish testing through science and technology (RETERO).

This repository includes open-source code, tutorials and example data for sensor data post-processing. The user guides for the sensor hardware are located here:

**BDS ->** https://biorobotics.pages.taltech.ee/bds/en/

**Fish Backpacks ->** https://biorobotics.pages.taltech.ee/backpack/en/

**RAPID ->** https://biorobotics.pages.taltech.ee/edf/en/

# Programming languages used in this repository
MATLAB 2022a, Python 3.10

![EDF_OFB](https://user-images.githubusercontent.com/460746/163399316-5f4cba75-5c80-47d2-96d9-b1fc5f33d51a.jpg)

## Examples

Several examples are provided in the `data/` folder to run the RAPID scripts, located in the `examples/` folder.

Download an example file and run from MATLAB:

    [dataOut, xq, RMSE] = interpolateRegFcn(dataIn, nOut, interpMethod)

## Acknowledgements
We are greatful for the funding received to support the the creation, development and updates of this unique Open Science code and data repository:

-> EU H2020: FITHydro - Fishfriendly Innovative Technologies for Hydropower (https://www.fithydro.eu/)

-> Estonian Research Council: PRG1243 - Multiscale Natural Flow Sensing for Coasts and Rivers  (https://www.etis.ee/Portal/Projects/Display/3613041e-dc87-4d79-860a-e8851d80b1af?lang=ENG)

-> German Federal Ministry of Education and Research: RETERO - Reduction of live fish testing through science and technology (https://retero.org/)
