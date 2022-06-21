import os
import operator
import random
import numpy as np
from struct import *
import binascii
import sys
import mmap
import csv
import math
import pandas as pd 
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import glob


fmt      = '>h' #big-endian binary format
length   = 11 #size of bytes per line   
p_gain   = 10
acc_gain = 10
fs       = 2048 #sample rate in Hz

os.chdir(r'/home/iring/Projects/RAPID') #directory .txt files
files = glob.glob('*.txt') #take only txt files

# Read each 11 bytes (length of each line of the file) 
def read_row(mm, length):
	count = 0
	while True:
		count += 1
		row = mm.read(length) 
		if not len(row) == length: 
			break 
		yield row

# Get raw data and unpack bytes in big-endian format
def unpacking(row): 
	list_values = []
	index = unpack('>h', bytes(row[0:2]))[0]
	index = index - 1
	list_values.append(index)
	acc_x = unpack('>h', bytes(row[2:4]))[0]
	acc_x = float(acc_x) / acc_gain
	list_values.append(acc_x)
	acc_y = unpack('>h', bytes(row[4:6]))[0]
	acc_y = acc_y / acc_gain
	list_values.append(acc_y)
	acc_z = unpack('>h', bytes(row[6:8]))[0]
	acc_z = acc_z / acc_gain
	list_values.append(acc_z)
	pressure = unpack('>h', bytes(row[8:10]))[0] 
	pressure = pressure / p_gain
	list_values.append(pressure)
	amag = round(math.sqrt(pow(acc_x, 2) + pow(acc_y, 2) + pow(acc_z, 2)),2)
	list_values.append(amag)
	return list_values

# Open file, map bytes, and get the results of unpacked bytes 
def get_results(filename, length):
	with open(filename,'rb') as file:
		mm = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
		results = [
			unpacking(row) for row in read_row(mm, length)
			]
	return results
		
# Create CSV file
def create_csv(filename, results):
	with open(f'{os.path.splitext(filename)[0]}.csv', 'w+', newline='') as file:
		writer = csv.writer(file)
		writer.writerow(["Index","Time [s]","P [mbar]","AX [m/s2]","AY [m/s2]","AZ [m/s2]","AMag [m/s2]"])
		for ind, val in enumerate(results):
			writer.writerow([ind,ind/fs,val[4],val[1],val[2],val[3],val[5]])
# Create plot
def create_plot(filename, results, fs):
	x_axis  = []
	y_left  = []
	y_right = []

	# Add the results to the axes lists 
	for ind, val in enumerate(results): 
		xaxis = ind / fs
		x_axis.append(xaxis)
		yleft = val[5]
		y_left.append(yleft)
		yright = val[4]
		y_right.append(yright)	

	# Create figure with secondary y-axis
	fig = make_subplots(specs=[[{"secondary_y": True}]])

	# Add traces
	fig.add_trace(
	    go.Scatter(x=x_axis, y=y_left, name="Acceleration Magnitude data"), #X should be the time 
	    secondary_y=False,
	)

	fig.add_trace(
	    go.Scatter(x=x_axis, y=y_right, name="Total Pressure data"),
	    secondary_y=True,
	)

	# Add figure title
	fig.update_layout(
	    title_text= filename
	)

	# Set x-axis title
	fig.update_xaxes(title_text="<b>Time </b> (seconds)")

	# Set y-axes titles
	fig.update_yaxes(title_text="<b>Acceleration Magnitude </b> (g)", secondary_y=False)
	fig.update_yaxes(title_text="<b>Total Pressure </b> (mbar)", secondary_y=True)

	fig.show()
	#fig.write_image(f'{os.path.splitext(filename)[0]}.pdf')

# Export results to CSV and PDF
for x in files:
	filename = x
	create_csv(filename, get_results(filename, length))
	create_plot(filename, get_results(filename, length),fs)
