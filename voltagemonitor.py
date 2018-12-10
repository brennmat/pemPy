# from https://circuitpython.readthedocs.io/projects/ads1x15/en/latest/

import time
import board
import busio
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Create the I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create the ADC object using the I2C bus
ads = ADS.ADS1015(i2c)

# Create single-ended input on channel 0
chan = AnalogIn(ads, ADS.P0)

# Create differential input between channel 0 and 1
#chan = AnalogIn(ads, ADS.P0, ADS.P1)

print("{:>5}\t{:>5}".format('raw', 'v'))

U0 = 2.605
a  = -9.615

t0 = time.time();

dt = 0.5

while True:
    t = time.time() - t0
    U = chan.voltage
    I = a*(U-U0)
    print("{:>5.1f} s:\t U = {:>5.3f} V\t I = {:>5.3f} A".format(t , U, I))
    time.sleep(dt)
