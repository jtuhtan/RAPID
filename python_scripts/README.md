# Data Processing for Strike Experiments on the BDS Sensor Probe

## Purpose

This collection of scripts processes the data generated during strike events by the BDS sensors developed by the workgroup of Environmental Sensing at Taltech, Tallinn. As the sensor is only recording at 100 or 250 Hz, it is unable to pick up the actual impact. Yet the dissipation of the kinetic energy transferred into the probe will take a lot longer. The hypothesis is, that the sensor will be able to pick this up as a decreasing amount of movement of the sensor probe. The goal is to use this energy dissipation profile as a means to infer information about the impact. most importantly the strike velocity.

## Usage

### importData.py

1. Place the raw data file from the BDS probe within the project folder. Despite the name, it is not a text file but rather a bytecode file. You will not be able to open it with an editor
2. Open the script `importData.py` and change the filename at the bottom according to your filename and relative file location between your data file and the script
3. **Change the class to your measurement and sensor**: When processing data from a BDS probe at 250 Hz, use the class `BDS250`. For BDS at 100 Hz `BDS100` and for the EDF Sensor `EDF`
4. Run the script. The processed data, a csv file, will be put in the folder `./csv` in the project directory

### calc_kinEXXX.py

1. Open either `calc_kinE_BDS.py` or `calc_kinE_EDF.py` and change the filename according to your filename
2. Run the script interactively, cells are devided by `# %%`. This is a marker for visual studio code to run the session as if in a jupyter notebook, however without the html embedding. This greatly facilitates version control. If you do not wish to use vscode copy and paste cells in a jupyter notebook.
3. Pay close attention to the output, both the graphs and the values printed while executing the script as these can show if everything is working correctly
4. The final result, the kinetic energy with respect to time, is saved within the `Ekin` variable

## Calculating the kinetic Energy

- The acceleration is composited into the magnitude which has the earth's gravitation already subtracted during post_processing in `importData.py`. Thereby, the absolute position of the sensor is not needed, which would be highly inaccurate during the strike event anyway. Also, the contribution of each axis to the total acceleration is irrelevant to the amount of kinetic energy stored in the probe.
- The amount of kinetic energy stored in the rotation of the probe is depending on the axis of rotation, hence they are treated separately
- During integration and differentiation, the time difference between sample points has to be taken into account. For 100Hz this means diving the integrated value by 100 for integration or multiplying it by 100 for differentiation. The numpy function `np.gradient()` can accept an array of timestamps when the measurement of the same index in the measurement-array was taken
- the drift of the accelerometer is different before and after the strike event. Therefore linear detrending is employed on the signal in 3 separate regions given to the `sig.detrend` function by the breakpoint parameter `bp`. The breakpoints are located directly before the strike event and after the sensor has stopped moving
- the recurring lines similar to this: `print(f'{np.mean(transNorm[:idx_cut[0]])=}')` are used to check if the signal is in-fact zero-mean or has a trend/drifts or if there is decreasing kinetic energy during the strike
- To prevent truncating the relevant part of the data, arbitrarily chosen distance values (like -20 and +50) are used

## Author
Written by Wolf Iring Kösters (wolf.kosters ät taltech.ee), an Early Stage Researcher (PhD student) at Tallinn University of Technology (Taltech), Estonia and Otto von Guericke University Magdeburg (OvGU), Germany.

The project has received funding from the European Union's Horizon 2020 research and innovation program under the Marie Sklodowska-Curie grant agreement No 860108.