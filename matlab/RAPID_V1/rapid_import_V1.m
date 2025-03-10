% rapidImport - Read binary file from the RAPID sensor
% Copyright 2022 Tallinn University of Technology
% Jeffrey A. Tuhtan jetuht@ttu.ee

% NOTE: This code is only for RAPID V1 sensors!
% If your sensor generates separate HIG and IMP files, this code will not convert your files. Please use rapid_import_HIG_V3.m and rapid_import_IMP_V3.m

%%
% This script will import a single RAPID sensor binary file in the user-defined folder "filePath" and file "fileName" in 
% the SETTINGS FOR IMPORT SCRIPT section below.
% It will convert the binary data into a MATLAB .mat file, human readable .csv file, and export a diagnostic plot showing the acceleration magnitude
% and pressure time series as a .pdf file with the same name as the "fileName". New subfolders named MAT, CSV and PDF will be created in the "filePath"
% defined by the user.
%%

%% SETTINGS FOR IMPORT SCRIPT
fs = 2048; % sample rate in Hz
% Gain for each type of sensor
acc_gain = 1; % accelerometer gain (Updated from 10.0 on 2022.11.01)
p_gain = 10; % pressure sensor gain
filePath = 'C:\Users\Admin\OneDrive - TalTech\Projects\2022_RETERO_2\Strike_Tests\2022.07.28_EDF\2022.10.20_Cloud_Download\2022.07.28_Strike_Data\1.0 ms-1 to 9.0 ms-1 2x Strikes Each\1 ms-1\';
fileName = 'T040728161904.txt'; % full file path including the file name to import and convert from binary
fileFull = strcat(filePath,fileName);
%%

%% Create subfolders for CSV MAT and PDF export files
filePathCSV = strcat(filePath,'CSV\'); % Make folder for PDF plots of results
mkdir(filePathCSV);

filePathMAT = strcat(filePath,'MAT\'); % Make folder for MAT files which store the raw and processed data
mkdir(filePathMAT);

filePathPDF = strcat(filePath,'PDF\'); % Make folder for MAT files which store the raw and processed data
mkdir(filePathPDF);
%%

%% STEP 1: Import binary files
% 5 column format: Timing, Ax, Ay, Az, Pressure
packetSize = 11; % 5 x int16 (2 bytes) + one byte for 0x0B end of line

% Load binary file
file_ID = fopen(fileFull);

fstat = dir(fileFull);
flen = floor((fstat.bytes/packetSize))-1;

precision = '*int16';
format = 'ieee-be';
skip = 9; % number of bytes to skip when reading
    
for it = 1:flen % read whole file
    ARaw(it,1) = fread(file_ID,1,precision,skip,format); % read first entry, integer sequential number from -1999 to 1999
    Aspot(it,1) = ftell(file_ID);
end    

 for it = 1:flen % second entry, raw Acc x 
    if it == 1
    fseek(file_ID,Aspot(1)+2,'bof'); % return to begin of file, skip ahead 2 bytes to second int16 register
    else
    end
    BRaw(it,1) = fread(file_ID,1,precision,skip,format);
 end  

 for it = 1:flen % third entry, raw Acc y
    if it == 1
    fseek(file_ID,Aspot(1)+4,'bof'); % return to begin of file, skip ahead 4 bytes to third int16 register
    else
    end
    CRaw(it,1) = fread(file_ID,1,precision,skip,format);
 end  

for it = 1:flen % fourth entry, raw Acc z
    if it == 1
    fseek(file_ID,Aspot(1)+6,'bof'); % return to begin of file, skip ahead 6 bytes to fourth int16 register
    else
    end
    DRaw(it,1) = fread(file_ID,1,precision,skip,format);
end 

for it = 1:flen % fifth entry, Pressure (mbar)
    if it == 1
    fseek(file_ID,Aspot(1)+8,'bof'); % return to begin of file, skip ahead 8 bytes to fifth int16 register
    else
    end
    ERaw(it,1) = fread(file_ID,1,precision,skip,format);
end
    
fclose(file_ID); % close the file
%%

%% Check timing using counter information
counterSize = floor(size(ARaw,1)./fs); % get the number of seconds
counterCheck = ARaw(fs:fs:size(ARaw,1));
counterFindBadTiming = counterCheck(counterCheck<fs & counterCheck>fs); % look for time stamps which do not match the sampling rate
%%

%% STEP 2: Convert to float including gain
B = double(BRaw);
C = double(CRaw);
D = double(DRaw);

rapid.tr = ARaw;
rapid.ax = B ./ acc_gain;
rapid.ay = C ./ acc_gain;
rapid.az = D ./ acc_gain;
rapid.amag = sqrt(rapid.ax.^2 + rapid.ay.^2 + rapid.az.^2);

rapid.p = (double(ERaw))/p_gain;
rapid.count = (0:1:size(rapid.tr,1)-1)';
%%

%% Export results to MAT folder with MAT binary format
    dataExportMAT = strcat(filePathMAT,erase(fileName,'.txt'),'.mat');
    save(dataExportMAT,'rapid');
%%

%% STEP 4: Export as csv text file for reporting / sharing raw data
cHeader = {'Time [Count, 2048 Hz]','P [mbar]','AX [m/s2]','AY [m/s2]','AZ [m/s2]','AMag [m/s2]'}; % header

commaHeader = [cHeader;repmat({','},1,numel(cHeader))]; % insert commas
commaHeader = commaHeader(:)';
textHeader = cell2mat(commaHeader); % Header in text with commas
textHeader = textHeader(1:end-1);

% write header to file
exportFile = strcat(filePathCSV,'\',erase(fileName,'.txt'),'.csv');
fid = fopen(exportFile,'wt'); 
fprintf(fid,'%s\n',textHeader)
fclose(fid)

dataExportCSV(:,1) = rapid.count;
dataExportCSV(:,2) = rapid.p;
dataExportCSV(:,3) = round(rapid.ax,2);
dataExportCSV(:,4) = round(rapid.ay,2);
dataExportCSV(:,5) = round(rapid.az,2);
dataExportCSV(:,6) = round(rapid.amag,2);

% write data to end of file
dlmwrite(exportFile,dataExportCSV,'-append','precision',6);

%% STEP 5: Export accel mag and pressure vs. time figure as PDF
gridStatus = 'on';
figFontSize = 12; % axis text font size
figLineWidth = 1;
fig1 = figure('units','normalized','outerposition',[0 0 1 1]);
left_color = [1 0 0];
right_color = [0 0 1];
set(fig1,'defaultAxesColorOrder',[left_color; right_color]);

tsMax = rapid.count./fs;
tsMax = tsMax(end);
amagMean = mean(rapid.amag);

figure(1)
subplot(2,1,1)
plot(rapid.count./fs,rapid.amag,'-r');
ylabel('Acceleration Magnitude (m/s^2)')
grid on
xlim([0 tsMax]);
title(fileName);

subplot(2,1,2)
plot(rapid.count./fs,rapid.p,'-b');
xlabel('Time (seconds)')
ylabel('Total Pressure (mbar)')
grid on
xlim([0 tsMax]);

print(fig1,strcat(filePathPDF,'\',erase(fileName,'.txt'),'.pdf'),'-dpdf','-bestfit');

pause(1)
%%
