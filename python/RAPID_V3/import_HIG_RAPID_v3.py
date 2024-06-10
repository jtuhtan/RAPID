# -*- coding: utf-8 -*-
"""
Created on Mon Jun  10 11:43:21 2024

@author: Jeffrey Tuhtan, Tallinn University of Technology
Copyright 2024
CC BY-NC 4.0 License
https://creativecommons.org/licenses/by-nc/4.0/

This script opens the binary file of the HIG RAPID V3 sensors and converts it to a ASCII .csv file for further processing.
The data exported are unfiltered and have fixed precision of three decimal places for the high-g accelerometer.
"""

import os
import struct
import numpy as np
import csv


#  STEP 1: Initialize constants
FS = 2000  # Sampling rate in Hz
HIG_PREC = 1 # decimal place precision of exported high-g accelerometer (+/- 400g) data 

# STEP 2: User inputs the file path in to the command line where a series of folders containing .IMP files is located
filePath = input("Enter the directory folder which has .HIG files in it: ")
filePath = os.path.join(filePath, '')

filePathCSV = os.path.join(filePath, 'CSV')
os.makedirs(filePathCSV, exist_ok=True)

contents = [f for f in os.listdir(filePath) if f.endswith('.HIG')]

if 'CSV' in contents:
    contents.remove('CSV')

for fileNameTxt in contents:
    dataExportCSV = []
    fileNameNoExt = fileNameTxt.replace('.HIG', '')
    fileFull = os.path.join(filePath, fileNameTxt)
    print(f'Importing and transforming file: {fileNameTxt} ...')

# STEP 3: The .HIG RAPID V3 binary files are imported
    packetSize = 11  # 1 x int32 (4 bytes) + 3 x int16 (2 bytes) + 1 byte for 0x0B end of line

    with open(fileFull, 'rb') as file_ID:
        fstat = os.stat(fileFull)
        flen = (fstat.st_size // packetSize) - 1

        TimeRaw = []
        TimeSpot = []

        for _ in range(flen):
            time_raw = struct.unpack('>i', file_ID.read(4))[0]
            TimeRaw.append(time_raw)
            TimeSpot.append(file_ID.tell())
            file_ID.seek(7, 1)  # skip 7 bytes

        DataRaw = np.zeros((flen, 3), dtype=np.int16)
        
        for it in range(flen):
            if it == 0:
                file_ID.seek(4+11, 0) # skips very first entry to match MATLAB code time alignment
                DataRaw[it, 0] = struct.unpack('>h', file_ID.read(2))[0] # acc X
                DataRaw[it, 1] = struct.unpack('>h', file_ID.read(2))[0] # acc Y
                DataRaw[it, 2] = struct.unpack('>h', file_ID.read(2))[0] # acc Z
                file_ID.seek(5, 1)  # skip 5 bytes
            else:
                DataRaw[it, 0] = struct.unpack('>h', file_ID.read(2))[0] # acc X
                DataRaw[it, 1] = struct.unpack('>h', file_ID.read(2))[0] # acc Y
                DataRaw[it, 2] = struct.unpack('>h', file_ID.read(2))[0] # acc Z
                
                file_ID.seek(5, 1)  # skip 5 bytes

# STEP 4: Binary data are converted to floats and the gains are multiplied to convert the data into physical units
    GAIN_HIG = 0.1 # imu acc gain to convert raw data to units of g (1 g = 9.81 ms-2)

    # python dict holidng the converted sensor data, fixed precision from STEP 1 is applied
    RAPIDHIG = {
        'td': np.array(TimeRaw, dtype=np.float64),
        'ts': np.array(TimeRaw, dtype=np.float64) / FS,
        'ax': np.round(DataRaw[:, 0] * GAIN_HIG,HIG_PREC),
        'ay': np.round(DataRaw[:, 1] * GAIN_HIG,HIG_PREC),
        'az': np.round(DataRaw[:, 2] * GAIN_HIG,HIG_PREC),
    }
    
    # calculate the acceleration magnitude
    aMag = np.round(np.sqrt(RAPIDHIG['ax']**2 + RAPIDHIG['ay']**2 + RAPIDHIG['az']**2),HIG_PREC)

# STEP 5: Create python dict for CSV file export
    dataExportCSV = np.column_stack((
        RAPIDHIG['ts'], RAPIDHIG['ax'], RAPIDHIG['ay'], RAPIDHIG['az'], aMag,
    ))

# STEP 6: Export data to a 'CSV' folder in ASCII .csv text format
    cHeader = ['Time (s)', 'HIGAccel_X (g)', 'HIGAccel_Y (g)', 'HIGAccel_Z (g)', 'HIGAccel_Mag (g)']

    exportFile = os.path.join(filePathCSV, f'{fileNameNoExt}-HIG.csv')

    with open(exportFile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(cHeader)
        writer.writerows(dataExportCSV)

