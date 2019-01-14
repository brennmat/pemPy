#!/usr/bin/env python3

# Python program for testing the pemPy code
# 
#
# Copyright 2019, Matthias Brennwald (brennmat@gmail.com)
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
# Copyright 20169, Matthias Brennwald (brennmat@gmail.com)

# make shure Python knows where to look for the RUEDI Python code
# http://stackoverflow.com/questions/4580101/python-add-pythonpath-during-command-line-module-run
# Example (bash): export PYTHONPATH=~/pemPy

# import pemPy classes:
import classes.pps_powersupply

# connect to PSU:
PSU = classes.pps_powersupply.PPS(port='/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0', reset=False, prom=None)

# make sure PSU is turned on:
PSU.output(True)

# set output voltage:
PSU.voltage(5.3)

# set output current:
PSU.voltage(2.5)

# monitor voltage and current at PSU terminals:
while 1:
	r = PSU.reading();
	print ('Voltage: ' + str(r[0]) + ' V, current = ' + str(r[1]) + ' A, limit: ' + r[2])
