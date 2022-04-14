dataList = {D1; D2; D3; D4; D5; D6; D7; D8; D9; D10; D11; D12; D13; D4; D15; D16; D17; D18; D19; D20}; % create a list of data you want to process sequentially

clear dataOut dataOutBatch
close all

for it = 1:size(dataList,1)

    dataIn = dataList{it,1};
    nIn = size(dataIn,2); % get the size nIn of the input data set
    dataInReg = linspace(0,1,nIn); % create a registration vector from 0 to 1 with the same number of entries, nIn as the registered data set

    nOut = 1000;
    interpMethod = 'linear';

    [dataOut, xq, RMSE] = interpolateRegFcn(dataIn, nOut, interpMethod);

    dataOutBatch(it,:) = dataOut;
    RMSEBatch(it) = RMSE;

end

dataOutBatchMean = mean(dataOutBatch,1); % calculate the ensemble mean
dataOutBatchStd = std(dataOutBatch,1); % calcualte the ensemble standard deviation
xlabel('Registered Time Series (0 - 1)');
ylabel('Measurement Value');

figure(1)
LineW = 2; % Line thickness
a = 0.2; % alpha transparency value (0 to 1)
c = [1 0 0]; % RGB color
p = [90]; % percentiles plotted
plot_distribution_prctile(xq,dataOutBatch,'LineWidth',LineW,'Alpha',a,'Color',c,'Prctile',p);
hold off
title('Mean Registered Time Series, Including Percentile Bounds');
