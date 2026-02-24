#!/usr/bin/env python3
"""
Control and monitor isotope enrichment runs with PEM cells.

Setup: Raspberry Pi connected to...
- Power supply (Voltcraft PPS or RIDEN) via USB/serial
- HX711 load cell ADC for PEM weight data
"""

import argparse
import configparser
import datetime
import sys
import threading
import time

from termcolor import colored

wait_ENTER_msg = ""


def wait_ENTER(button_list, msg):
    global wait_ENTER_msg
    wait_ENTER_msg = msg
    input()
    if wait_ENTER_msg:
        print(colored(wait_ENTER_msg + "\n", "red"))
    button_list.append(None)


def printit(text, f=None):
    now = datetime.datetime.now()
    text = now.strftime("%Y-%m-%d %H:%M:%S") + "\t" + text
    if f:
        print(text, file=f)
        f.flush()
    print(text)


def _prompt_float(prompt, min_val=None, min_inclusive=True):
    """Prompt until user enters a valid float. min_val enforces minimum value."""
    while True:
        s = input(prompt).strip()
        if not s:
            print("Please enter a number (or Ctrl+C to abort).")
            continue
        try:
            val = float(s)
            if min_val is not None:
                if min_inclusive and val < min_val:
                    print(f"Value must be >= {min_val}.")
                    continue
                elif not min_inclusive and val <= min_val:
                    print(f"Value must be > {min_val}.")
                    continue
            return val
        except ValueError:
            print("Invalid input. Please enter a number.")


def main():
    parser = argparse.ArgumentParser(
        description="Control and monitor H isotope enrichment of water samples with PEM cells"
    )
    parser.add_argument(
        "--config",
        default="pemcell_config.txt",
        help="Configuration file path (default: pemcell_config.txt)",
    )
    parser.add_argument(
        "--logfile",
        help="Log file path (default: pemcell_<samplename>.log)",
    )
    args = parser.parse_args()

    # Defer RPi-specific imports until after --help (allows CLI to work on non-RPi)
    import serial
    import RPi.GPIO as GPIO
    from pempy.loadcell import HX711
    from pempy.powersupply import get_powersupply

    config = configparser.ConfigParser()
    if not config.read(args.config):
        print(f"Error: Could not read config file: {args.config}")
        sys.exit(1)

    # Ensure TYPE exists for PSU (default pps)
    if not config.has_section("PEMCELLPSU"):
        config.add_section("PEMCELLPSU")
    if not config.has_option("PEMCELLPSU", "TYPE"):
        config.set("PEMCELLPSU", "TYPE", "pps")

    try:
        PSU = get_powersupply(config)
        PSU.output(False)
    except (serial.SerialException, OSError, RuntimeError):
        print("Error: Power supply not responding. Check that it is connected, powered on, and the correct port is set in the config.")
        sys.exit(1)

    GPIO.setmode(GPIO.BCM)
    loadcell_num_readings = int(config.get("LOADCELL", "READINGS_AVG", fallback="500"))
    loadcell_dout = config.getint("LOADCELL", "DOUT_PIN", fallback=5)
    loadcell_sck = config.getint("LOADCELL", "SCK_PIN", fallback=6)

    LOADCELL = HX711(dout_pin=loadcell_dout, pd_sck_pin=loadcell_sck)

    # Early check: load cell must respond before we prompt the user
    probe_n = 5
    probe_ok = sum(
        1 for _ in range(probe_n)
        if LOADCELL._read() not in (False, 0x7FFFFF, 0x800000)
    )
    if probe_ok < probe_n // 2:
        print(
            "Error: Load cell not responding. Check that the HX711 is connected "
            "(DOUT, SCK, VCC, GND) and the load cell is wired to the HX711."
        )
        GPIO.cleanup()
        sys.exit(1)

    samplename = ""
    while not samplename:
        samplename = input("Enter sample name / label: ").strip()

    logfilename = args.logfile or f"pemcell_{samplename}.log"
    logfile = open(logfilename, "w")
    if not logfile:
        print("Could not open log file!")
        sys.exit(1)
    print(f"\nLogging output to {logfilename}...\n")

    printit("Sample: " + samplename, logfile)

    # Calibrate load cell ZERO
    input("Remove PEM cell from the load cell and press Enter")
    print("Zeroing load cell...")
    try:
        err = LOADCELL.zero(loadcell_num_readings)
        if err:
            raise ValueError(err)
        reading = LOADCELL.get_raw_data_mean(loadcell_num_readings)
        if reading is False:
            raise ValueError("empty reading")
        print("Load cell zero value (raw value):", reading)
    except (ValueError, TypeError) as err:
        print("Could not determine load cell ZERO:", err)
        sys.exit(1)

    # Calibrate load cell SENSITIVITY
    try:
        M_CAL = float(input("Mount full PEM cell without connecting the wires and enter weight (grams): "))
        if M_CAL < 0.0:
            raise ValueError("Full weight must not be negative")
    except ValueError as err:
        print("Invalid input:", err)
        sys.exit(1)

    try:
        reading = LOADCELL.get_data_mean(loadcell_num_readings)
        if reading is False:
            raise ValueError("Could not read load cell data")
        ratio = reading / M_CAL
        print("calibrated ratio =", ratio, "g/raw-units")
        LOADCELL.set_scale_ratio(ratio)
        print("Load cell calibration completed.")
    except (ValueError, TypeError) as err:
        print("Could not determine load cell SENSITIVITY:", err)
        sys.exit(1)

    input("Attach wires from PEM and cooler top to power supplies, then press ENTER!")
    try:
        M_FULL = LOADCELL.get_weight_mean(loadcell_num_readings)
        if M_FULL is False:
            raise ValueError("could not read load cell")
        print("Full weight with wires connected =", M_FULL, "g")
    except (ValueError, TypeError) as err:
        print("Could not determine full weight with PSU wires connected:", err)
        sys.exit(1)

    try:
        MW_ini = float(input("Enter amount of water in PEM cell (grams): "))
        if MW_ini <= 0.0:
            raise ValueError("water weight must be positive")
    except ValueError as err:
        print("Invalid input:", err)
        sys.exit(1)

    MW_target = float(config.get("LOADCELL", "WATER_TARGET", fallback="20.0"))
    I_min = float(config.get("PEMCELLPSU", "MINCURRENT", fallback="1.0"))
    I_max = float(config.get("PEMCELLPSU", "MAXCURRENT", fallback="5.0"))
    U_max = float(config.get("PEMCELLPSU", "MAXVOLTAGE", fallback="7.0"))
    T_ramp = float(config.get("PEMCELLPSU", "RAMPTIME", fallback="1200"))

    printit(f"Max. cell voltage = {U_max} V", logfile)
    printit(f"Min. cell current = {I_min} A", logfile)
    printit(f"Max. cell current = {I_max} A", logfile)
    printit(f"Ramp time = {T_ramp/60} min", logfile)
    printit(f"Processing start = {MW_ini:.1f} g of water", logfile)
    printit(f"Processing target = {MW_target:.1f} g of water", logfile)

    input("Ready for electrolysis? Press ENTER to start or CTRL-C to abort...")

    Q = 0.0
    t0 = time.time()
    t2 = t0
    I = I_min
    I_last = I_min
    tt = 0

    print("")
    printit("Starting electrolysis (press ENTER to pause)...", logfile)
    PSU.voltage(U_max)
    PSU.current(I_min)
    PSU.output(True)

    # Electrolysis data: screen header + file header
    screen_header = "Time(s)    U(V)   I(A)    Q(Ah)   Water(g)   %      ETA"
    file_header = "datetime\tepoch\tU_V\tI_A\tQ_Ah\twater_g\tpct\ttime_left"
    print(screen_header)
    logfile.write(file_header + "\n")
    logfile.flush()

    BUTTON = []
    threading.Thread(target=wait_ENTER, args=(BUTTON, "Stopping electrolysis..."), daemon=True).start()

    do_process = True
    current_on = True

    while do_process:
        if current_on:
            t1 = t2
            time.sleep(10)

            if BUTTON:
                current_on = False

            r = PSU.reading()
            UC, IC = r[0], r[1]
            MW = MW_ini - (M_FULL - LOADCELL.get_weight_mean(loadcell_num_readings))

            t2 = time.time()
            tt = tt + (t2 - t1)
            Q = Q + IC * (t2 - t1) / 3600

            if MW < MW_ini:
                rate = (MW_ini - MW) / tt
                tl = (MW - MW_target) / rate
                if tl > 3600 * 24:
                    tl, tl_unit = tl / 3600 / 24, "d"
                elif tl > 3600:
                    tl, tl_unit = tl / 3600, "h"
                elif tl > 60:
                    tl, tl_unit = tl / 60, "min"
                else:
                    tl_unit = "s"
            else:
                tl, tl_unit = float("nan"), "?"

            # Screen: update line in place
            pct = MW / MW_ini * 100
            screen_row = f"{t1-t0:.1f}-{t2-t0:.1f}  {UC:5.2f}  {IC:5.2f}  {Q:8.2E}  {MW:8.1f}  {pct:5.1f}  {tl:.2f}{tl_unit}"
            print(f"\r{screen_row}   ", end="", flush=True)

            # File: append data row (datetime, epoch, values)
            now = datetime.datetime.now()
            epoch = int(time.time())
            dt_str = now.strftime("%Y-%m-%d %H:%M:%S")
            logfile.write(f"{dt_str}\t{epoch}\t{UC:.2f}\t{IC:.2f}\t{Q:.2E}\t{MW:.1f}\t{pct:.1f}\t{tl:.2f}{tl_unit}\n")
            logfile.flush()

            if MW <= MW_target:
                current_on = False
                global wait_ENTER_msg
                wait_ENTER_msg = ""
                print()  # newline to end the data line
                printit("*** Water mass target reached! Press ENTER...", logfile)

            if t2 - t0 < T_ramp:
                I = I_min + (I_max - I_min) * (t2 - t0) / T_ramp
            else:
                I = I_max

            if I != I_last:
                PSU.current(I)
                I_last = I

        else:
            print()  # newline to end the data line
            printit("Turning off power supply...", logfile)
            PSU.current(0.0)

            u = ""
            print("")
            while u not in ("X", "C"):
                u = input("Electrolysis paused. Enter C to continue or X to exit: ").upper()

            print("")
            if u == "X":
                do_process = False
            else:
                printit("Turning on power supply...", logfile)
                PSU.current(I)
                current_on = True
                I_last = I
                t2 = time.time()
                BUTTON.clear()
                threading.Thread(
                    target=wait_ENTER,
                    args=(BUTTON, "Stopping electrolysis..."),
                    daemon=True,
                ).start()

    PSU.output(False)
    GPIO.cleanup()
    printit("Done.", logfile)


if __name__ == "__main__":
    main()
