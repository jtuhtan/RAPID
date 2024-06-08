% rapid_import_IMP_V3 - Read binary file from pressure and IMU
% Copyright 2024 Tallinn University of Technology
% Jeffrey A. Tuhtan jetuht@ttu.ee
% Last updated: 2024.05.24

% Dependencies: sort_nat.m
% https://www.mathworks.com/matlabcentral/fileexchange/10959-sort_nat-natural-order-sort

%% Description
% The user should place RAPID files ending with .IMP into a folder. 
% Then run this script, and select the folder location when prompted 
% (see 'uigetdir' command below).
% 
% This script then opens each IMP binary file (STEP 1), and converts each of
% the three imu datasets (accelerometer, rate gyro, magnetometer) pressure
% sensor, and battery into a float and applies the gain for each of the sensing modalities
% (STEP 2), converting the raw data to physical units (g, deg/s, mT,
% mbar, C and V). The data are then saved in both
% MAT binary file (STEP 3) as well as CSV (STEP 4). Finally, a plot is
% created which shows the time series of each of the three axes as well as
% the magnitude (STEP 5).
%%

clear all
close all

% Load dependencies
addpath('C:\Users\Admin\OneDrive - TalTech\MATLAB\dependencies'); % dependency: sort_nat.m creates list of files in a specified folder.

fs = 2000; % Sampling rate in Hz

filePath = uigetdir; % User selects the directory folder which has .HIG files in it
filePath = strcat(filePath,'\');

filePathMAT = strcat(filePath,'MAT\'); % Make a folder for the exported MAT binary files which store the raw and processed data
mkdir(filePathMAT);

filePathCSV = strcat(filePath,'CSV\'); % Make a folder for the exported CSV text files which store the raw binary data data
mkdir(filePathCSV);

contents = cellstr(ls(filePath));
contents = sort_nat(contents(3:end,1)); % uses FEX SORT_NAT to get correct sorting otherwise 1,10,2,24,etc. will be used by MATLAB

idx = strcmp(contents,'CSV'); % ignore CSV folder if present
contents(idx) = [];
idx = strcmp(contents,'MAT'); % ignore MAT folder if present
contents(idx) = [];
idx = strcmp(contents,'PDF'); % ignore PDF folder if present
contents(idx) = [];

filePathPDF = strcat(filePath,'PDF\');
mkdir(filePathPDF);

for itFile = 1:size(contents,1) % This iterates over all available files in the folder, ending with *.txt
    close all
    clear dataExport dataExportCSV dataExportMAT
    fileNameTxt = char(contents(itFile));
    fileNameNoExt = erase(fileNameTxt,'.IMP');
    fileFull = strcat(filePath,fileNameTxt);
    figName = fileNameTxt;
    disp(['Importing and transforming file: ',fileNameTxt,' ...']);

%% STEP 1: Import binary files
% IMP raw file has a 13 column format: Timing, Ax, Ay, Az, GyroX, GyroY, GyroZ, MagX, MagY, Magz, Pressure, Pressure_Temp, Battery
packetSize = 29; % 1 x int32 (4 bytes) + 12 x int16 (2 bytes) + one byte for 0x0B end of line

    % Load binary file
    file_ID = fopen(fileFull);

    fstat = dir(fileFull);
    flen = floor((fstat.bytes/packetSize))-1;

    precisionT = '*int32'; % time steps use int32
    precisionP = '*uint16'; % pressure sensor data use uint16
    precisionD = '*int16'; % imu data use int16
    skipT = 25; % number of bytes to skip when reading time
    skipD = 27; % number of bytes to skip when reading data
    format = 'ieee-be';
    
    for it = 1:flen % read whole file
    TimeRaw(it,1) = fread(file_ID,1,precisionT,skipT,format); % read first entry, integer sequential number from -1999 to 1999
    TimeSpot(it,1) = ftell(file_ID);
%   disp(['Importing line ' num2str(it),' of ',num2str(flen), ' - ', num2str(100*(it/flen)),'%']);
    end
    
for itParam = 1:12 % loop over all 12 variables, convert as int16
    for it = 1:flen %
        if it == 1
           fseek(file_ID,TimeSpot(1)+4+(2*(itParam-1)),'bof'); % return to begin of file, skip ahead 4 bytes to the first int16 register
        else
           DataRaw(it,itParam) = fread(file_ID,1,precisionD,skipD,format);
        end
    end
end 

DataRaw(1,:) = DataRaw(2,:); % assign zero time zero entry second time entry values

for itParam = 10 % loop over pressure sensor only, convert as uint16
    for it = 1:flen %
        if it == 1
           fseek(file_ID,TimeSpot(1)+4+(2*(itParam-1)),'bof'); % return to begin of file, skip ahead 4 bytes to the first int16 register
        else
           DataRawP(it,1) = fread(file_ID,1,precisionP,skipD,format);
        end
    end
end 

DataRawP(1) = DataRawP(2); % assign zero time zero entry second time entry values

    fclose(file_ID); % close the file

%% STEP 2: Convert to float and apply gain to covert to physical units
gain_ac = 0.005; % imu acc gain (m/s2)
gain_ac = gain_ac./9.81; % convert imu acc from m/s2 to g (1 g = 9.81 m/s2) comment out this line if you wish to have units of m/s2 instead of g
gain_gy = 0.1; % imu gyro gain (deg/s)
gain_mg = 0.1; % imu magnetometer gain (mT)
gain_pr = 0.1; % pressure sensor gain (mbar)
gain_t = 0.01; % pressure sensor temperature gain (C)
gain_bt = 0.01; % battery voltage gain (V)

RAPIDIMP.td = double(TimeRaw); % time index with step size of 1
RAPIDIMP.ts = RAPIDIMP.td ./ fs; % time stamp in seconds

RAPIDIMP.ax = double(DataRaw(:,1)) .* gain_ac;
RAPIDIMP.ay = double(DataRaw(:,2)) .* gain_ac;
RAPIDIMP.az = double(DataRaw(:,3)) .* gain_ac;
RAPIDIMP.am = (RAPIDIMP.ax.^2 + RAPIDIMP.ay.^2 + RAPIDIMP.az.^2).^0.5;

RAPIDIMP.gx = double(DataRaw(:,4)) .* gain_gy;
RAPIDIMP.gy = double(DataRaw(:,5)) .* gain_gy;
RAPIDIMP.gz = double(DataRaw(:,6)) .* gain_gy;

RAPIDIMP.mx = double(DataRaw(:,7)) .* gain_mg;
RAPIDIMP.my = double(DataRaw(:,8)) .* gain_mg;
RAPIDIMP.mz = double(DataRaw(:,9)) .* gain_mg;

RAPIDIMP.p = double(DataRawP(:,1)) .* gain_pr;
RAPIDIMP.t = double(DataRaw(:,11)) .* gain_t;
RAPIDIMP.b = double(DataRaw(:,12)) .* gain_bt;

% Create array with CSV data of 14 columns for exporting
dataExportCSV(:,1) = RAPIDIMP.ts;
dataExportCSV(:,2) = RAPIDIMP.ax;
dataExportCSV(:,3) = RAPIDIMP.ay;
dataExportCSV(:,4) = RAPIDIMP.az;
dataExportCSV(:,5) = RAPIDIMP.am;
dataExportCSV(:,6) = RAPIDIMP.gx;
dataExportCSV(:,7) = RAPIDIMP.gy;
dataExportCSV(:,8) = RAPIDIMP.gz;
dataExportCSV(:,9) = RAPIDIMP.mx;
dataExportCSV(:,10) = RAPIDIMP.my;
dataExportCSV(:,11) = RAPIDIMP.mz;
dataExportCSV(:,12) = RAPIDIMP.p;
dataExportCSV(:,13) = RAPIDIMP.t;
dataExportCSV(:,14) = RAPIDIMP.b;
%%

%% STEP 3: Export results to MAT folder with MAT binary format
    dataExportMAT = strcat(filePathMAT,fileNameNoExt,'-IMP.mat');
    save(dataExportMAT,'RAPIDIMP');
%%

%% STEP 4: Export results to CSV folder with CSV text format
% Create the header text
cHeader = {'Time (s)','Accel_X (g)','Accel_Y (g)','Accel_Z (g)','Accel_Mag (g)','Gyro_X (deg/s)','Gyro_Y (deg/s)','Gyro_Z (deg/s)','Mag_X (mT)','Mag_Y (mT)','Mag_Z (mT)','Pressure (mbar)','P_Temp (C)','Battery (V)'}; 

commaHeader = [cHeader;repmat({','},1,numel(cHeader))]; % Insert commas
commaHeader = commaHeader(:)';
textHeader = cell2mat(commaHeader); % cHeader in text with commas
textHeader = textHeader(1:end-1);

% Write header to file
exportFile = strcat(filePathCSV,fileNameNoExt,'-IMP.csv');
fid = fopen(exportFile,'wt'); 
fprintf(fid,'%s\n',textHeader);
fclose(fid);

% Write IMP sensor data to CSV
dlmwrite(exportFile,dataExportCSV,'-append');
%%

%% STEP 5: Plot results
fh = figure(1);
fh.WindowState = 'maximized'; % show full screen size

subplot(2,1,1)
plot(RAPIDIMP.ts,RAPIDIMP.am,'-r');
ylabel('Acceleration Magnitude (g)')
grid on
title(fileNameTxt)

subplot(2,1,2)
plot(RAPIDIMP.ts,RAPIDIMP.p,'-b');
xlabel('Time (seconds)')
ylabel('Total Pressure (mbar)')
grid on
% ylim([500 5500]);
% ylim([950 1200]);

%% Export current figure as image
figName = erase(fileNameTxt,'.IMP');
figureExport = strcat(filePathPDF,figName,'.pdf');
% saveas(gcf,figureExport);
% print(figureExport,'-dpdf','-fillpage')
% orient(fig1,'landscape')
print(fh,figureExport,'-dpdf','-bestfit')
pause(3)
end
