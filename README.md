# pemPy
Python code to monitor and control operation of polymer electrolyte membrane (PEM) electrolysis cell for 3H enrichment in water.

Hardware:
- Core unit: Raspberry Pi (RPi)
- PEM cell power supply: Voltcraft PPS, controlled by RPi via serial port (USB connection) 
- Sensor for current flow through PEM cell: ACS712-10A Hall sensor, using Adafruit 1085 ADC board connected to I2C bus of RPi to read the the Hall voltage signal
