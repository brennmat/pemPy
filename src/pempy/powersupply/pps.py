"""
Voltcraft PPS power supply driver.
"""

import sys
import serial

from pempy.powersupply.base import PowerSupply

PPS_MODELS = {
    (18.0, 10.0): "PPS11810",
    (36.2, 7.0): "PPS11360",
    (60.0, 2.5): "PPS11603",
    (18.0, 20.0): "PPS13610",
    (36.2, 12.0): "PPS16005",
    (60.0, 5.0): "PPS11815",
    (18.2, 12.0): "PPS11810",
}

PPS_TIMEOUT = 1.00


def _pps_debug(s):
    sys.stdout.write(s)
    sys.stdout.flush()


class PPS(PowerSupply):
    """
    Voltcraft PPS power supply.
    port: serial port (e.g. /dev/ttyUSB0)
    reset: disable output when connecting
    prom: preset number 0,1,2 to load on init (or None)
    """

    def __init__(self, port="/dev/ttyUSB0", reset=False, prom=None, debug=False):
        try:
            from packaging.version import Version
            use_exclusive = Version(serial.__version__) >= Version("3.3")
        except ImportError:
            use_exclusive = False

        if use_exclusive:
            self._Serial = serial.Serial(port, timeout=PPS_TIMEOUT, exclusive=True)
        else:
            self._Serial = serial.Serial(port, timeout=PPS_TIMEOUT)

        self._Serial.flushInput()
        self._Serial.flushOutput()
        self._debug = bool(debug)

        try:
            model = self.limits()
            self._MODEL = PPS_MODELS[model]
            self._VMAX = model[0]
            self._IMAX = model[1]
        except serial.SerialTimeoutException:
            raise RuntimeError(f"No Voltcraft PPS powersupply connected to {port}")
        except KeyError:
            raise RuntimeError(f"Unknown Voltcraft PPS model with max V: {model[0]}, I: {model[1]}")

        if bool(reset):
            self.output(False)
            self.voltage(0)
            self.current(0)
        if prom is not None:
            self.use_preset(prom)

    VMAX = property(lambda self: self._VMAX, None, None, "maximum output voltage")
    IMAX = property(lambda self: self._IMAX, None, None, "maximum output current")
    MODEL = property(lambda self: self._MODEL, None, None, "PS model number")

    def _query(self, cmd):
        if self._debug:
            _pps_debug(f"PPS <- {cmd}<CR>\n")
        self._Serial.write((cmd + "\r").encode())

        b = []
        if self._debug:
            _pps_debug("PPS -> ")
        while True:
            ch = self._Serial.read(1).decode("utf-8")
            b.append(ch)
            if self._debug:
                _pps_debug(ch.replace("\r", "<CR>"))
            if ch == "":
                raise serial.SerialTimeoutException()
            if b[-3:] == list("OK\r"):
                break
        if self._debug:
            _pps_debug("\n")
        return "".join(b[:-4])

    def limits(self):
        s = self._query("GMAX")
        self.IMULT = 100.0 if s == "362700" else 10.0
        V = int(s[0:3]) / 10.0
        I = int(s[3:6]) / self.IMULT
        return (V, I)

    def output(self, state):
        state = int(not bool(state))
        self._query(f"SOUT{state}")

    def voltage(self, voltage):
        voltage = max(min(int(float(voltage) * 10), int(self.VMAX * 10)), 0)
        self._query(f"VOLT{voltage:03d}")

    def current(self, current):
        current = max(min(int(float(current) * self.IMULT), int(self.IMAX * self.IMULT)), 0)
        self._query(f"CURR{int(current):03d}")

    def reading(self):
        s = self._query("GETD")
        V = int(s[0:4]) / 100.0
        I = int(s[4:8]) / 100.0
        MODE = ("CV", "CC")[bool(int(s[8]))]
        return (V, I, MODE)

    def store_presets(self, VC0, VC1, VC2):
        VC = VC0 + VC1 + VC2
        V_vals = [max(min(int(float(x) * 10), int(self.VMAX * 10)), 0) for x in VC[::2]]
        I_vals = [max(min(int(float(x) * self.IMULT), int(self.IMAX * self.IMULT)), 0) for x in VC[1::2]]
        self._query("PROM" + "".join(f"{v:03d}{i:03d}" for v, i in zip(V_vals, I_vals)))

    def load_presets(self):
        s = self._query("GETM")
        return [
            (int(s[0:3]) / 10.0, int(s[3:6]) / self.IMULT),
            (int(s[7:10]) / 10.0, int(s[10:13]) / self.IMULT),
            (int(s[14:17]) / 10.0, int(s[17:20]) / self.IMULT),
        ]

    def use_preset(self, nbr):
        nbr = int(nbr)
        nbr = nbr if nbr in (0, 1, 2) else (2 if nbr > 2 else 0)
        self._query(f"RUNM{nbr}")

    @property
    def preset(self):
        s = self._query("GETS")
        return (int(s[0:3]) / 10.0, int(s[3:6]) / self.IMULT)

    @preset.setter
    def preset(self, VC):
        self.preset_voltage = VC[0]
        self.preset_current = VC[1]

    @property
    def preset_voltage(self):
        s = self._query("GOVP")
        return int(s[0:3]) / 10.0

    @preset_voltage.setter
    def preset_voltage(self, voltage):
        voltage = max(min(int(float(voltage) * 10), int(self.VMAX * 10)), 0)
        self._query(f"SOVP{voltage:03d}")

    @property
    def preset_current(self):
        s = self._query("GOCP")
        return int(s[0:3]) / self.IMULT

    @preset_current.setter
    def preset_current(self, current):
        current = max(min(int(float(current) * self.IMULT), int(self.IMAX * self.IMULT)), 0)
        self._query(f"SOCP{int(current):03d}")

    def power_dissipation(self):
        V, I, _ = self.reading()
        return V * I
