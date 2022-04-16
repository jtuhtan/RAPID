function [dataOut, xq, RMSE] = interpolateRegFcn(dataIn, nOut, interpMethod)

% FORMAT: [DATAOUT, XQ, RMSE] = INTERPOLATEREGFCN(DATAIN, NOUT, INTERPMETHOD)
%   
%   Interpolate values to a fixed number of intervals (0 to 1)  
%
%   This function takes a univariate data set and interpolates it uniformly
%   to an output data set with fixed length.
%
%   INTERPOLATEREGFCN(DATAIN, NOUT, INTERPMETHOD) interpolates a 1D vector
%   of continuous data, DATAIN to a fixed number of entries, NOUT (default = 100) using one
%   of the methods defined by INTERPMETHOD (default = 'linear').
%
%   [DATAOUT, XQ, RMSE] returns the interpolated 1D vector, DATAOUT in
%   equally spaced intervals, XQ over the range [0, 1]. The root mean
%   square error, RMSE is calculated for the closest matching range values
%   between DATAIN and DATAOUT and can be used to estimate the
%   interpolation error.
% -------------------------------------------------------------------------
%    author:      Jeffrey A. Tuhtan
%    affiliation: Dept. of Computer Systems, Tallinn University of Technology, Estonia
%    email:      jeffrey.tuhtan@taltech.ee
%    
%    $Revision: 1.1 $ $Date: 2022/04/16 14:35:00 $

if isempty(dataIn)
	dataOut = NaN;
	return
end

if nargin < 2
    nOut = 100; % default value of nOut
end

if nargin < 3
    interpMethod = 'linear'; % default value of interpMethod
end

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
