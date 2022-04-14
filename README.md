# RAPID
Sensor data post-processing scripts from RAPID (Robust Autonomous Pressure and Inertial Devices).

Current code supports three types of sensors: RAPID, EU FITHydro Barotrauma Detection System (BDS) and fish backpacks for the reduction of live fish testing through science and technology (RETERO).

MATLAB 2022a

## Examples

Several examples are provided in the `data/` folder to run the RAPID scripts, located in the `examples/` folder.

Download an example file and run from MATLAB:

    [dataOut, xq, RMSE] = interpolateRegFcn(dataIn, nOut, interpMethod)

## Acknowledgements
We are greatful for the funding received to support the the creation, development and updating of this unique code repository:

-> EU H2020: FITHydro - Fishfriendly Innovative Technologies for Hydropower 
(https://www.fithydro.eu/)

-> Estonian Research Council: PRG1243 - Multiscale Natural Flow Sensing for Coasts and Rivers 
(https://www.etis.ee/Portal/Projects/Display/3613041e-dc87-4d79-860a-e8851d80b1af?lang=ENG)

-> German Federal Ministry of Education and Research: RETERO - Reduction of live fish testing through science and technology 
(https://retero.org/)
