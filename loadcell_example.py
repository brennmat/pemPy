#!/usr/bin/env python3
import RPi.GPIO as GPIO  # import GPIO
### from hx711 import HX711  # import the class HX711
import classes.loadcell_HX711

try:
    GPIO.setmode(GPIO.BCM)  # set GPIO pin mode to BCM numbering
    # Create an object hx which represents your real hx711 chip
    # Required input parameters are only 'dout_pin' and 'pd_sck_pin'
    LOADCELL = classes.loadcell_HX711.HX711( dout_pin=5,
                                             pd_sck_pin=6,
                                             tempsens_serialport='/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0',
                                             TZero = [1.18,2.11],
                                             TRatio = 1.0
                                           )
    
    num_readings = 500

    # TSENS = classes.temperaturesensor_MAXIM.temperaturesensor_MAXIM ( serialport = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0' , label = 'TEMP-LOADCELL' )
    # T0,unit = TSENS.temperature('nofile')
    # print ('Load cell temperature: ',T0,unit)
    # TO = float(T0)

    # measure tare and save the value as offset for current channel
    # and gain selected. That means channel A and gain 128
    input('Put empty PEM cell on the load cell and press Enter')
    print('Zeroing load cell...')

    # repeat zeroing, since first run usually isn't very accurate
    err = LOADCELL.zero(20)
    err = LOADCELL.zero(20)
    err = LOADCELL.zero(num_readings)

    # check if successful
    if err:
        raise ValueError('Tare is unsuccessful.')

    # set reference temperature to current temp:
    LOADCELL.set_reference_temperature()
    print (LOADCELL._T0)

    reading = LOADCELL.get_raw_data_mean(num_readings)
    if reading:  # always check if you get correct value or only False
        # now the value is close to 0
        print('Load cell zero value (raw value):',
              reading)
    else:
        print('invalid data', reading)

    # In order to calculate the conversion ratio to some units, in my case I want grams,
    # you must have known weight.
    known_weight_grams = input('Put calibration weight on PEM cell and enter its weight (g): ')
    try:
        value = float(known_weight_grams)
    except ValueError:
        print('Expected integer or float and I have got:',known_weight_grams)

    reading = LOADCELL.get_data_mean(20)
    reading = LOADCELL.get_data_mean(20)
    reading = LOADCELL.get_data_mean(num_readings)
    if reading:
        # print('Load cell calibration value (raw value):', reading)
        # set scale ratio for particular channel and gain which is
        # used to calculate the conversion to units. Required argument is only
        # scale ratio. Without arguments 'channel' and 'gain_A' it sets
        # the ratio for current channel and gain.
        ratio = reading / value  # calculate the ratio for channel A and gain 128
        LOADCELL.set_scale_ratio(ratio)  # set ratio for current channel
        print('Load cell calibration completed.')
    else:
        raise ValueError('Cannot calculate mean value. Try debug mode. Variable reading:', reading)

    # Read data several times and return mean value
    # subtracted by offset and converted by scale ratio to
    # desired units. In my case in grams.
    print("Now, I will read data in infinite loop. To exit press 'CTRL + C'")
    input('Press Enter to begin reading')

    # coefficients for T compensation of load cell reading
    TZ = [1.18,2.11] # zero offset compensation coefficients
    TS = 0.0 # sensitivity compensation

    while True:
        # read load cell:
        Mcomp,Mraw,DT = LOADCELL.get_weight_mean_compensated(num_readings)
        T0 = LOADCELL.get_reference_temperature()

        # temperature compensation for load-cell reading
        # T,T_unit = TSENS.temperature('nofile')
        # DT = float(T)-T0
        # Mcorr = float ( ( M + (DT**TZ[0])*TZ[1]) * ( 1 + DT*TS ) )
        # if DT < 0:
        #     Mcorr = M - ((-DT)**TZ[0])*TZ[1]
        # else:
        #     Mcorr = M + (DT**TZ[0])*TZ[1]
        # Mcorr = Mcorr * ( 1 + DT*TS )
        
        # print raw and T compensated mass reading:

        print ( '%.2f\t%.2f\t%.2f\t%.2f' % (Mraw,Mcomp,T0+DT,DT) )

except (KeyboardInterrupt, SystemExit):
    print('Bye :)')

finally:
    GPIO.cleanup()
