#!/usr/bin/env python3

# Monitor current applied to PEM cell, and determine charge (cumulative current)
#
# Setup: Raspberry Pi connected to Voltcraft PPS power supply via USB cable (UART interface in PPS)
#
# This file is part of pemPy, a toolbox for operation of PEM electrolysis cells.
#
# pemPy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# pemPy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with ruediPy.  If not, see <http://www.gnu.org/licenses/>.
# 
# pemPy: a toolbox for operation of PEM electrolysis cells.
# Copyright 2019, Matthias Brennwald (brennmat@gmail.com)

# make shure Python knows where to look for the RUEDI Python code
# http://stackoverflow.com/questions/4580101/python-add-pythonpath-during-command-line-module-run
# Example (bash): export PYTHONPATH=~/pemPy

import argparse
import datetime
import time

# import pemPy classes:
import classes.pps_powersupply

# connect to PSU:
PSU = classes.pps_powersupply.PPS(port='/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0', reset=False, prom=None)

# make sure PSU is turned off:
PSU.output(False)



##############################
# parsing of input arguments #
##############################
parser = argparse.ArgumentParser(description='Monitor current through PEM 3H enrichment cells and determine cumulative charge.')
parser.add_argument('--datafile', nargs='?', help='data file (name/path)')
args = parser.parse_args()
if args.datafile is not None:
	f = open(args.datafile,'w')
	print('Saving output to file ' + args.datafile + '...')
else:
	f = None


####################
# helper functions #
####################

def printit(text,f=''):
	# print date/time followed by text either to stdout (if f is empty) or to file (if f is not empty)

	# prepend date/time:
	now = datetime.datetime.now()
	text = now.strftime("%Y-%m-%d %H:%M:%S") + '\t' + text

	#print text:
	if f:
		print(text,file=f)
		f.flush()
	else:
		print(text)
	return


################
# Main program #
################


t0 = time.time();

# total charge ('Ampere-hours'), in Coulomb:
Q = 0.0

# set output voltage and current:
printit('Turning on power supply',f)
PSU.voltage(5.0)
PSU.current(3.5)
PSU.output(True)

# Say hello:
printit('Monitoring cell current and total charge',f)

# Monitor current and voltage:
t2 = time.time()
while True:

	# pause between two readings:
	t1 = t2
	time.sleep(15)

	# read current and voltage at PSU terminals:
	r = PSU.reading();

	# voltage at PSU terminals:
	UC = r[0];

	# current from PSU
	IC = r[1];

	# cumulative current (charge, in Ah):
	t2 = time.time()
	Q = Q + IC*(t2-t1)/3600

	# show data:
	printit("{:>.1f}...{:>.1f} s:\t U-PSU = {:>.2f} V\tI-PSU = {:>.2f} A\tQ = {:>.2E} Ah".format(t1-t0 , t2-t0 , UC, IC , Q ),f)
