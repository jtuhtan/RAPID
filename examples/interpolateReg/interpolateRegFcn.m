% interpolateRegFcn - function version to process lots of data!

% Takes a univariate data set, dataIn of length, nIn and interpolates it uniformly to a data set, dataOut of length nOut
% Copyright 2022 Tallinn University of Technology
% Assoc. Prof. Jeffrey A. Tuhtan jetuht@ttu.ee

function [dataOut, xq, RMSE] = interpolateRegFcn(dataIn, nOut, interpMethod)

    %% STEP 1: ALGORITHM INTERPOLATES dataIn TO A NEW DATA SET, "dataOut" WITH UNIFORM LENGTH, "nOut"
    nIn = size(dataIn,2); % get the size nIn of the input data set
    dataInReg = linspace(0,1,nIn); % create a registration vector from 0 to 1 with the same number of entries, nIn as the registered data set
    
    xq = linspace(0,1,nOut); % create a registration vector from 0 to 1 with the fixed number of entries equal to nOut
    
    dataOut = interp1(dataInReg,dataIn,xq,interpMethod); % interpolate
    
    % find the nearest entries between dataIn and dataOut
    TMP = bsxfun(@(x,y) abs(x-y), dataInReg(:), reshape(xq,1,[]));
    [D, idxB] = min(TMP,[],2); % idxB is the corresponding row of dataOut which is the closest to dataIn
    
    dataOutCompare = dataOut(idxB); % get the values from dataOut which are the closest to the original dataIn values
    xqdataOutCompare = xq(idxB); % get the corresponding registered time values from xq
    %%
    
    %% STEP 2: COMPARE THE ROOT MEAN SQUARED ERROR BETWEEN ORIGINAL DATA AND INTERPOLATED DATA
    RMSE = sqrt(sum((dataOutCompare - dataIn).^2)/nIn) % calculate the root mean square error between the dataOut and dataIn after interpolating
    %%

end
