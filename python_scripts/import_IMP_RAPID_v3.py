# -*- coding: utf-8 -*-
"""
Created on Sat Jun  8 10:05:44 2024

@author: Jeffrey Tuhtan, Tallinn University of Technology
Copyright 2024
CC BY-NC 4.0 License
https://creativecommons.org/licenses/by-nc/4.0/

This script opens the binary file of the RAPID V3 sensors and converts it to a ASCII .csv file for further processing.
The data exported are unfiltered and have fixed precision of three decimal places for the IMU (acceleration, rate gyro and magnetometer)
and have one decimal place precision for the pressure sensor, and two decimal place precision for the temperature of the pressure
sensor and the battery voltage.
"""

import os
import struct
import numpy as np
import csv


#  STEP 1: Initialize constants
FS = 2000  # Sampling rate in Hz
IMU_PREC = 3 # decimal place precision of exported data 
P_PREC = 1 # decimal place precision of pressure sensor
T_BAT_PREC = 2 # decimal place precision of pressure sensor temp and battery voltage

# STEP 2: User inputs the file path in to the command line where a series of folders containing .IMP files is located
filePath = input("Enter the directory folder which has .IMP files in it: ")
filePath = os.path.join(filePath, '')

filePathCSV = os.path.join(filePath, 'CSV')
os.makedirs(filePathCSV, exist_ok=True)

contents = [f for f in os.listdir(filePath) if f.endswith('.IMP')]

if 'CSV' in contents:
    contents.remove('CSV')

for fileNameTxt in contents:
    dataExportCSV = []
    fileNameNoExt = fileNameTxt.replace('.IMP', '')
    fileFull = os.path.join(filePath, fileNameTxt)
    print(f'Importing and transforming file: {fileNameTxt} ...')

# STEP 3: The .IMP RAPID V3 binary files are imported
    packetSize = 29  # 1 x int32 (4 bytes) + 12 x int16 (2 bytes) + one byte for 0x0B end of line

    with open(fileFull, 'rb') as file_ID:
        fstat = os.stat(fileFull)
        flen = (fstat.st_size // packetSize) - 1

        TimeRaw = []
        TimeSpot = []

        for _ in range(flen):
            time_raw = struct.unpack('>i', file_ID.read(4))[0]
            TimeRaw.append(time_raw)
            TimeSpot.append(file_ID.tell())
            file_ID.seek(25, 1)  # skip 25 bytes

        DataRaw = np.zeros((flen, 12), dtype=np.int16)
        DataRawP = np.zeros(flen, dtype=np.uint16)
        
        for it in range(flen):
            if it == 0:
                file_ID.seek(4, 0)
            else:
                DataRaw[it, 0] = struct.unpack('>h', file_ID.read(2))[0] # acc X
                DataRaw[it, 1] = struct.unpack('>h', file_ID.read(2))[0] # acc Y
                DataRaw[it, 2] = struct.unpack('>h', file_ID.read(2))[0] # acc Z
                
                DataRaw[it, 3] = struct.unpack('>h', file_ID.read(2))[0] # gyro X
                DataRaw[it, 4] = struct.unpack('>h', file_ID.read(2))[0] # gyro Y
                DataRaw[it, 5] = struct.unpack('>h', file_ID.read(2))[0] # gyro Z
                
                DataRaw[it, 6] = struct.unpack('>h', file_ID.read(2))[0] # mag X
                DataRaw[it, 7] = struct.unpack('>h', file_ID.read(2))[0] # mag Y
                DataRaw[it, 8] = struct.unpack('>h', file_ID.read(2))[0] # mag Z
                
                file_ID.seek(2, 1)  # skip 2 bytes for pressure sensor
                
                DataRaw[it, 9] = struct.unpack('>h', file_ID.read(2))[0] # pressure sensor temp
                DataRaw[it, 10] = struct.unpack('>h', file_ID.read(2))[0] # battery voltage
                
                file_ID.seek(5, 1)  # skip 5 bytes

        DataRaw[0, :] = DataRaw[1, :]

        for it in range(flen):
            if it == 0:
                file_ID.seek(TimeSpot[0] + 4 + (2 * 7), 0)
            else:
                DataRawP[it] = struct.unpack('>H', file_ID.read(2))[0]
                file_ID.seek(27, 1)  # skip 27 bytes

        DataRawP[0] = DataRawP[1]

# STEP 4: Binary data are converted to floats and the gains are multiplied to convert the data into physical units
    gain_ac = 0.005 / 9.81  # imu acc gain (g), comment out the / 9.81 if you wish to have units of ms-2
    gain_gy = 0.1  # imu gyro gain (deg/s)
    gain_mg = 0.1  # imu magnetometer gain (mT)
    gain_pr = 0.1  # pressure sensor gain (mbar)
    gain_t = 0.01  # pressure sensor temperature gain (C)
    gain_bt = 0.01  # battery voltage gain (V)

    # python dict holidng the converted sensor data, fixed precision from STEP 1 is applied
    RAPIDIMP = {
        'td': np.array(TimeRaw, dtype=np.float64),
        'ts': np.array(TimeRaw, dtype=np.float64) / FS,
        'ax': np.round(DataRaw[:, 0] * gain_ac,IMU_PREC),
        'ay': np.round(DataRaw[:, 1] * gain_ac,IMU_PREC),
        'az': np.round(DataRaw[:, 2] * gain_ac,IMU_PREC),
        'gx': np.round(DataRaw[:, 3] * gain_gy,IMU_PREC),
        'gy': np.round(DataRaw[:, 4] * gain_gy,IMU_PREC),
        'gz': np.round(DataRaw[:, 5] * gain_gy,IMU_PREC),
        'mx': np.round(DataRaw[:, 6] * gain_mg,IMU_PREC),
        'my': np.round(DataRaw[:, 7] * gain_mg,IMU_PREC),
        'mz': np.round(DataRaw[:, 8] * gain_mg,IMU_PREC),
        'p': np.round(DataRawP * gain_pr,P_PREC),
        't': np.round(DataRaw[:, 9] * gain_t,T_BAT_PREC),
        'b': np.round(DataRaw[:, 10] * gain_bt,T_BAT_PREC)
    }
    
    # calculate the acceleration magnitude
    aMag = np.round(np.sqrt(RAPIDIMP['ax']**2 + RAPIDIMP['ay']**2 + RAPIDIMP['az']**2),IMU_PREC)

# STEP 5: Create python dict for CSV file export
    dataExportCSV = np.column_stack((
        RAPIDIMP['ts'], RAPIDIMP['ax'], RAPIDIMP['ay'], RAPIDIMP['az'], aMag,
        RAPIDIMP['gx'], RAPIDIMP['gy'], RAPIDIMP['gz'], RAPIDIMP['mx'], RAPIDIMP['my'],
        RAPIDIMP['mz'], RAPIDIMP['p'], RAPIDIMP['t'], RAPIDIMP['b']
    ))

# STEP 6: Export data to a 'CSV' folder in ASCII .csv text format
    cHeader = ['Time (s)', 'Accel_X (g)', 'Accel_Y (g)', 'Accel_Z (g)', 'Accel_Mag (g)',
               'Gyro_X (deg/s)', 'Gyro_Y (deg/s)', 'Gyro_Z (deg/s)', 'Mag_X (mT)',
               'Mag_Y (mT)', 'Mag_Z (mT)', 'Pressure (mbar)', 'P_Temp (C)', 'Battery (V)']

    exportFile = os.path.join(filePathCSV, f'{fileNameNoExt}-IMP.csv')

    with open(exportFile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(cHeader)
        writer.writerows(dataExportCSV)

