#!/usr/bin/env python3
"""Interactive load cell calibration and reading example."""
import RPi.GPIO as GPIO
from pempy.loadcell import HX711

try:
    GPIO.setmode(GPIO.BCM)
    LOADCELL = HX711(dout_pin=5, pd_sck_pin=6)
    num_readings = 500

    input("Put empty PEM cell on the load cell and press Enter")
    print("Zeroing load cell...")
    for _ in range(2):
        LOADCELL.zero(20)
    err = LOADCELL.zero(num_readings)
    if err:
        raise ValueError("Tare unsuccessful.")

    reading = LOADCELL.get_raw_data_mean(num_readings)
    if reading is not False:
        print("Load cell zero value (raw value):", reading)
    else:
        print("invalid data", reading)

    known_weight_grams = input("Put calibration weight on PEM cell and enter its weight (g): ")
    try:
        value = float(known_weight_grams)
    except ValueError:
        print("Expected float, got:", known_weight_grams)
        raise

    for _ in range(2):
        LOADCELL.get_data_mean(20)
    reading = LOADCELL.get_data_mean(num_readings)
    if reading is not False:
        ratio = reading / value
        LOADCELL.set_scale_ratio(ratio)
        print("Load cell calibration completed.")
    else:
        raise ValueError("Cannot calculate mean value. Variable reading:", reading)

    print("Reading in infinite loop. Press CTRL+C to exit.")
    input("Press Enter to begin reading")

    while True:
        M = LOADCELL.get_weight_mean(num_readings)
        if M is not False:
            print(f"{M:.2f} g")

except (KeyboardInterrupt, SystemExit):
    print("Bye :)")
finally:
    GPIO.cleanup()
