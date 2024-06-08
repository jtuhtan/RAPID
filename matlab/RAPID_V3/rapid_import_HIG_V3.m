% RAPIDHIG_import_HIG - Read binary file from dual digital accelerometer proto
% Copyright 2024 Tallinn University of Technology
% Jeffrey A. Tuhtan jetuht@ttu.ee
% Last updated: 2024.05.24

% Dependencies: sort_nat.m
% https://www.mathworks.com/matlabcentral/fileexchange/10959-sort_nat-natural-order-sort

%% Description
% The user should place RAPID files ending with .HIG into a folder. 
% Then run this script, and select the folder location when prompted 
% (see 'uigetdir' command below).
% 
% This script then opens each binary file (STEP 1), and converts each of
% the three accelerometer axes into a float and applies the gain (STEP 2)
% converting the raw data to units of g. The data are then saved in boty
% MAT binary file (STEP 3) as well as CSV (STEP 4). Finally, a plot is
% created which shows the time series of each of the three axes as well as
% the magnitude (STEP 5).
%%

clear all
close all

fs = 2000; % sample rate of high-g accelerometer in Hz

addpath('C:\Users\Admin\OneDrive - TalTech\MATLAB\dependencies'); % dependency: sort_nat.m creates list of files in a specified folder.

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

for itFile = 1:size(contents,1)
    idx = strcmp(contents{itFile,1}(end-3:end),'.HIG');
    if idx > 0
     contentsHIG(itFile,1) = contents(itFile); % create list of only HIG files in the directory, ignoring all other file types
    else end
end

for itFile = 1:size(contentsHIG,1) % This iterates over all available files in the folder ending with *.HIG
    close all
    clear dataExport dataExportCSV dataExportMAT
    fileNameTxt = char(contentsHIG(itFile));
    fileNameNoExt = erase(fileNameTxt,'.HIG');
    fileFull = strcat(filePath,fileNameTxt);
    figName = fileNameTxt;
    disp(['Importing and transforming file: ',fileNameTxt,' ...']);

%% STEP 1: Import binary files
% HIG file has a 4 column format: Timing, Ax, Ay, Az
packetSize = 11; % 1 x uint32 (4 bytes) + 3 x int16 (2 bytes) + one byte for 0x0B end of line

    % Load binary file
    file_ID = fopen(fileFull);

    fstat = dir(fileFull);
    flen = floor((fstat.bytes/packetSize))-1;

    precisionT = '*uint32'; % time steps use int32
    precisionD = '*int16'; % acceleration data use int16
    skipT = 7; % number of bytes to skip when reading time
    skipD = 9; % number of bytes to skip when reading data
    format = 'ieee-be';
    
    for it = 1:flen % read whole file
        TimeRaw(it,1) = fread(file_ID,1,precisionT,skipT,format); % read first entry, integer sequential number from -1999 to 1999
        TimeSpot(it,1) = ftell(file_ID);
    end
    
    for itParam = 1:3 % loop over all three HIGH G parameters
        for it = 1:flen % second entry, HIGH G X
            if it == 1
               fseek(file_ID,TimeSpot(1)+4+(2*(itParam-1)),'bof'); % return to begin of file, skip ahead 4 bytes to the first int16 register
            else
            end
            AccRaw(it,itParam) = fread(file_ID,1,precisionD,skipD,format);
        end
    end 

    fclose(file_ID); % close the file
%%

%% STEP 2: Convert to float and apply gain
gain_hg = 10; % high g gain convert from binary to units of g (1 g = 9.81 m/s^2)

% Create data structure for MAT exporting
RAPIDHIG.tid = double(TimeRaw); % time index with step size of 1
RAPIDHIG.ts = RAPIDHIG.tid ./ fs; % time stamp in seconds
RAPIDHIG.ax = double(AccRaw(:,1)) ./ gain_hg;
RAPIDHIG.ay = double(AccRaw(:,2)) ./ gain_hg;
RAPIDHIG.az = double(AccRaw(:,3)) ./ gain_hg;
RAPIDHIG.am = (RAPIDHIG.ax.^2 + RAPIDHIG.ay.^2 + RAPIDHIG.az.^2).^0.5; % acceleration magnitude

medianHIG(itFile,1) = median(RAPIDHIG.ax)
medianHIG(itFile,2) = median(RAPIDHIG.ay)
medianHIG(itFile,3) = median(RAPIDHIG.az)

meanHIG(itFile,1) = mean(RAPIDHIG.ax)
meanHIG(itFile,2) = mean(RAPIDHIG.ay)
meanHIG(itFile,3) = mean(RAPIDHIG.az)

% Create array with CSV data for exporting
dataExportCSV(:,1) = RAPIDHIG.ts;
dataExportCSV(:,2) = RAPIDHIG.ax;
dataExportCSV(:,3) = RAPIDHIG.ay;
dataExportCSV(:,4) = RAPIDHIG.az;
%%

%% STEP 3: Export results to MAT folder with MAT binary format
dataExportMAT = strcat(filePathMAT,fileNameNoExt,'-HIG.mat');
save(dataExportMAT,'RAPIDHIG');
%%

%% STEP 4: Export results to CSV folder with CSV text format
% Create the header text
cHeader = {'Time (s)','Accel_X (g)','Accel_Y (g)','Accel_Z (g)'}; 

commaHeader = [cHeader;repmat({','},1,numel(cHeader))]; % Insert commas
commaHeader = commaHeader(:)';
textHeader = cell2mat(commaHeader); % cHeader in text with commas
textHeader = textHeader(1:end-1);

% Write header to file
exportFile = strcat(filePathCSV,fileNameNoExt,'-HIG.csv');
fid = fopen(exportFile,'wt'); 
fprintf(fid,'%s\n',textHeader)
fclose(fid)

% Write HIG sensor data to CSV
dlmwrite(exportFile,dataExportCSV,'-append');
%%

%% STEP 5: Make a figure to display the HIG time series data for each axis and the accelerometer magnitude
figure(1);
plot(RAPIDHIG.ts,RAPIDHIG.am,'.-k');
hold on
plot(RAPIDHIG.ts,RAPIDHIG.ax,'.-r');
plot(RAPIDHIG.ts,RAPIDHIG.ay,'.-g');
plot(RAPIDHIG.ts,RAPIDHIG.az,'.-b');
xlabel('Time (s)');
ylabel('Accel Mag (g)');
legend('Accel Mag','Accel X','Accel Y','Accel Z');
title(contentsHIG(itFile));
%%

end
