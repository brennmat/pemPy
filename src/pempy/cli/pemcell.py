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
import math
import sys
import threading
import time

from termcolor import colored

wait_ENTER_msg = ""


def _require(config, section, key):
    """Return config value; exit with error if section or key is missing."""
    if not config.has_section(section):
        print(f"Error: Missing config section [{section}]")
        sys.exit(1)
    if not config.has_option(section, key):
        print(f"Error: Missing config [{section}] {key}")
        sys.exit(1)
    return config.get(section, key)


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
        help="Log file path (default: <samplename>_YYYY-MM-DD-HH.MM.SS.log)",
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

    try:
        PSU = get_powersupply(config)
        PSU.output(False)
    except ValueError as err:
        print(f"Error: {err}")
        sys.exit(1)
    except (serial.SerialException, OSError, RuntimeError):
        print("Error: Power supply not responding. Check that it is connected, powered on, and the correct port is set in the config.")
        sys.exit(1)

    GPIO.setmode(GPIO.BCM)
    loadcell_num_readings = int(_require(config, "LOADCELL", "AVG_READINGS"))
    step_iterations = int(_require(config, "ELECTROLYSIS", "STEP_ITERATIONS"))
    step_weight_readings = math.ceil(loadcell_num_readings / step_iterations)
    loadcell_dout = int(_require(config, "LOADCELL", "DOUT_PIN"))
    loadcell_sck = int(_require(config, "LOADCELL", "SCK_PIN"))

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

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H.%M.%S")
    logfilename = args.logfile or f"{samplename}_{timestamp}.log"
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

    MW_target = float(_require(config, "ELECTROLYSIS", "WATER_TARGET"))
    I_min = float(_require(config, "ELECTROLYSIS", "MINCURRENT"))
    I_max = float(_require(config, "ELECTROLYSIS", "MAXCURRENT"))
    U_max = float(_require(config, "ELECTROLYSIS", "MAXVOLTAGE"))
    T_ramp = float(_require(config, "ELECTROLYSIS", "RAMPTIME"))

    printit(f"Max. cell voltage = {U_max} V", logfile)
    printit(f"Min. cell current = {I_min} A", logfile)
    printit(f"Max. cell current = {I_max} A", logfile)
    printit(f"Ramp time = {T_ramp/60} min", logfile)
    printit(f"Processing start = {MW_ini:.1f} g of water", logfile)
    printit(f"Processing target = {MW_target:.1f} g of water", logfile)
    printit(f"Step iterations = {step_iterations}, weight readings per iteration = {step_weight_readings}", logfile)

    input("Ready for electrolysis? Press ENTER to start or CTRL-C to abort...")

    Q = 0.0
    t0 = time.time()
    t2 = t0
    I = I_min
    I_last = I_min
    tt = 0

    print("")
    printit("Starting electrolysis (press ENTER to pause)...", logfile)
    print("")
    PSU.voltage(U_max)
    PSU.current(I_min)
    PSU.output(True)

    # Electrolysis data: screen header + file header
    screen_header = "datetime             Run time(s)   U(V)   I(A)    Q(C)    Water(g)   %      Estimated time left"
    file_header = "datetime\tRun time(s)\tU(V)\tI(A)\tQ(C)\tWater(g)"
    print(screen_header)
    logfile.write(file_header + "\n")
    logfile.flush()

    screen_rows = []  # last 3 data lines for rolling display

    BUTTON = []
    threading.Thread(target=wait_ENTER, args=(BUTTON, "Stopping electrolysis..."), daemon=True).start()

    do_process = True
    current_on = True

    while do_process:
        if current_on:
            t1 = t2
            weights, Us, Is, dts = [], [], [], []
            t_prev = time.time()
            broke_on_button = False

            for _ in range(step_iterations):
                if BUTTON:
                    current_on = False
                    broke_on_button = True
                    break
                w = LOADCELL.get_weight_mean(step_weight_readings)
                if w is not False:
                    weights.append(w)
                r = PSU.reading()
                t_now = time.time()
                dt = t_now - t_prev
                Us.append(r[0])
                Is.append(r[1])
                dts.append(dt)
                t_prev = t_now

            t2 = time.time()
            if broke_on_button or not Us or not Is or not weights:
                continue

            tt = tt + (t2 - t1)
            Q = Q + sum(I_i * dt_i for I_i, dt_i in zip(Is, dts))  # Coulombs
            UC = sum(Us) / len(Us)
            IC = sum(Is) / len(Is)
            MW = MW_ini - (M_FULL - sum(weights) / len(weights))

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

            # Screen: show last 3 data lines (rolling)
            pct = MW / MW_ini * 100
            now = datetime.datetime.now()
            dt_str = now.strftime("%Y-%m-%d %H:%M:%S")
            run_time = tt - (t2 - t1) / 2  # processing time at center of step (excludes pause)
            screen_row = f"{dt_str}  {run_time:10.1f}  {UC:5.2f}  {IC:5.2f}  {Q:8.2E}  {MW:8.1f}  {pct:5.1f}  {tl:.2f}{tl_unit}"
            prev_count = len(screen_rows)
            screen_rows.append(screen_row)
            screen_rows = screen_rows[-3:]
            if prev_count > 0:
                print(f"\033[{prev_count}A", end="")  # move up to overwrite
            for row in screen_rows:
                print(f"\r\033[2K{row}")  # start of line, erase, content

            # File: append data row (datetime, run_time, values)
            logfile.write(f"{dt_str}\t{run_time:.1f}\t{UC:.2f}\t{IC:.2f}\t{Q:.2E}\t{MW:.1f}\n")
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
