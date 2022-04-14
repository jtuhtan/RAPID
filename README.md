# RAPID
Sensor data post-processing scripts from RAPID (Robust Autonomous Pressure and Inertial Devices).

Current code supports three types of sensors: RAPID, EU FITHydro Barotrauma Detection System (BDS) and fish backpacks for the reduction of live fish testing through science and technology (RETERO).

MATLAB 2022a

## Examples

Several examples are provided in the `data/` folder to run the RAPID scripts, located in the `examples/` folder.

Download an example file and run from MATLAB:

    [dataOut, xq, RMSE] = interpolateRegFcn(dataIn, nOut, interpMethod)
