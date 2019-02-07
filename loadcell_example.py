#!/usr/bin/env python3
import RPi.GPIO as GPIO  # import GPIO
### from hx711 import HX711  # import the class HX711
import classes.hx711_loadcell


try:
    GPIO.setmode(GPIO.BCM)  # set GPIO pin mode to BCM numbering
    # Create an object hx which represents your real hx711 chip
    # Required input parameters are only 'dout_pin' and 'pd_sck_pin'
    hx = classes.hx711_loadcell.HX711(dout_pin=5, pd_sck_pin=6)
    
    num_readings = 500

    
    # measure tare and save the value as offset for current channel
    # and gain selected. That means channel A and gain 128
    input('Put empty PEM cell on the load cell and press Enter')
    print('Zeroing load cell...')
    err = hx.zero(num_readings)
    # check if successful
    if err:
        raise ValueError('Tare is unsuccessful.')


    reading = hx.get_raw_data_mean(num_readings)
    if reading:  # always check if you get correct value or only False
        # now the value is close to 0
        print('Load cell zero value (raw value):',
              reading)
    else:
        print('invalid data', reading)

    # In order to calculate the conversion ratio to some units, in my case I want grams,
    # you must have known weight.
    input('Put calibration weight on PEM cell and then press Enter')
    reading = hx.get_data_mean(num_readings)
    if reading:
        print('Load cell calibration value (raw value):', reading)
        known_weight_grams = input(
            'Calibration weight (grams): ')
        try:
            value = float(known_weight_grams)
            print(value, 'grams')
        except ValueError:
            print('Expected integer or float and I have got:',
                  known_weight_grams)

        # set scale ratio for particular channel and gain which is
        # used to calculate the conversion to units. Required argument is only
        # scale ratio. Without arguments 'channel' and 'gain_A' it sets
        # the ratio for current channel and gain.
        ratio = reading / value  # calculate the ratio for channel A and gain 128
        hx.set_scale_ratio(ratio)  # set ratio for current channel
        print('Load cell calibration completed.')
    else:
        raise ValueError('Cannot calculate mean value. Try debug mode. Variable reading:', reading)

    # Read data several times and return mean value
    # subtracted by offset and converted by scale ratio to
    # desired units. In my case in grams.
    print("Now, I will read data in infinite loop. To exit press 'CTRL + C'")
    input('Press Enter to begin reading')
    while True:
        print(hx.get_weight_mean(num_readings), 'g')

except (KeyboardInterrupt, SystemExit):
    print('Bye :)')

finally:
    GPIO.cleanup()