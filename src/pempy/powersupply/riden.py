"""
RIDEN (RUIDEN) RDxxxx power supply driver.
See https://github.com/ShayBox/Riden for Modbus register details.
"""

import logging
import time

import minimalmodbus
import serial

from pempy.powersupply.base import PowerSupply

logger = logging.getLogger(__name__)

RIDEN_SPECS = {
    "RD6006": (0.0, 60.0, 6.0, 360, 0.001, 0.001, 0.0, 0.0, 0.3),
    "RD6006P": (0.0, 60.0, 6.0, 360, 0.001, 0.0001, 0.0, 0.0, 1.5),
    "RD6012": (0.0, 60.0, 12.0, 720, 0.001, 0.001, 0.0, 0.0, 0.3),
    "RD6012P_6A": (0.0, 60.0, 6.0, 360, 0.001, 0.0001, 0.0, 0.0, 1.8),
    "RD6012P_12A": (0.0, 60.0, 12.0, 720, 0.001, 0.001, 0.0, 0.0, 1.8),
    "RD6018": (0.0, 60.0, 18.0, 1080, 0.001, 0.001, 0.0, 0.0, 0.3),
}

MAX_COMM_ATTEMPTS = 10


class RIDEN(PowerSupply):
    """
    RIDEN (RUIDEN) RDxxxx power supply.
    port: serial port path
    baud: baud rate (default 115200)
    currentmode: 'LOW' or 'HIGH' for 6012P
    """

    def __init__(self, port, baud=115200, currentmode="LOW"):
        try:
            self._instrument = minimalmodbus.Instrument(port=port, slaveaddress=1)
            self._instrument.serial.baudrate = baud
            self._instrument.serial.timeout = 1.0
            time.sleep(0.2)
        except (OSError, RuntimeError, serial.SerialException) as e:
            raise RuntimeError(f"Could not connect to RIDEN powersupply at {port}: {e}") from e

        OCP_max = OVP_max = None
        try:
            mdl = self._get_register(0)
            if 60060 <= mdl <= 60064:
                self.MODEL = "RD6006"
                OVP_max, OCP_max = 61.0, 6.1
                logger.warning("RIDEN %s operation is untested", self.MODEL)
            elif mdl == 60065:
                self.MODEL = "RD6006P"
                OVP_max, OCP_max = 61.0, 6.1
            elif 60120 <= mdl <= 60124:
                self.MODEL = "RD6012"
                OVP_max, OCP_max = 61.0, 12.1
                logger.warning("RIDEN %s operation is untested", self.MODEL)
            elif 60125 <= mdl <= 60129:
                if currentmode.upper() == "LOW":
                    self.MODEL = "RD6012P_6A"
                    self._set_register(20, 0)
                    OCP_max = 6.1
                else:
                    self.MODEL = "RD6012P_12A"
                    self._set_register(20, 1)
                    OCP_max = 12.1
                OVP_max = 61.0
            elif 60180 <= mdl <= 60189:
                self.MODEL = "RD6018"
                OVP_max, OCP_max = 61.0, 18.1
                logger.warning("RIDEN %s operation is untested", self.MODEL)
            else:
                logger.warning("Unknown RIDEN model ID: %s", mdl)
                self.MODEL = "<unknown>"

            if self.MODEL not in RIDEN_SPECS:
                raise RuntimeError(f"Unknown RIDEN model: {self.MODEL}")

            spec = RIDEN_SPECS[self.MODEL]
            self.VMIN = spec[0]
            self.VMAX = spec[1]
            self.IMAX = spec[2]
            self.PMAX = spec[3]
            self.VRESSET = spec[4]
            self.VRESREAD = spec[4]
            self.IRESSET = spec[5]
            self.IRESREAD = spec[5]
            self.VOFFSETMAX = spec[6]
            self.IOFFSETMAX = spec[7]
            self.MAXSETTLETIME = spec[8]
            self.READIDLETIME = self.MAXSETTLETIME / 5

        except KeyError as e:
            raise RuntimeError(f"Unknown RIDEN type/model {getattr(self, 'MODEL', '?')}") from e
        except (OSError, RuntimeError, serial.SerialException) as e:
            raise RuntimeError(f"Could not determine RIDEN type/model: {e}") from e

        if OCP_max is not None and OVP_max is not None:
            logger.info("Adjusting OVP to %s V and OCP to %s A", OVP_max, OCP_max)
            mul_U = self._voltage_multiplier()
            mul_I = self._current_multiplier()
            for r in [82, 86, 90, 94, 98, 102, 106, 110, 114, 118]:
                self._set_register(r, OVP_max * mul_U)
                self._set_register(r + 1, OCP_max * mul_I)

    def _set_register(self, register, value):
        for _ in range(MAX_COMM_ATTEMPTS):
            try:
                self._instrument.write_register(register, int(value))
                return
            except (OSError, RuntimeError, serial.SerialException):
                pass
        raise RuntimeError(
            f"Communication with RIDEN {self.MODEL} at {self._instrument.serial.port} failed"
        )

    def _get_register(self, register):
        for _ in range(MAX_COMM_ATTEMPTS):
            try:
                return self._instrument.read_register(register)
            except (OSError, RuntimeError, serial.SerialException):
                pass
        raise RuntimeError(
            f"Communication with RIDEN {self.MODEL} at {self._instrument.serial.port} failed"
        )

    def _get_N_registers(self, register_start, N):
        for _ in range(MAX_COMM_ATTEMPTS):
            try:
                return self._instrument.read_registers(register_start, N)
            except (OSError, RuntimeError, serial.SerialException):
                pass
        raise RuntimeError(
            f"Communication with RIDEN {self.MODEL} at {self._instrument.serial.port} failed"
        )

    def output(self, state):
        self._set_register(18, int(bool(state)))

    def voltage(self, voltage):
        voltage = max(min(voltage, self.VMAX), self.VMIN)
        self._set_register(8, round(voltage * self._voltage_multiplier()))

    def current(self, current):
        current = max(min(current, self.IMAX), 0.0)
        self._set_register(9, round(current * self._current_multiplier()))

    def reading(self):
        V_mult = self._voltage_multiplier()
        I_mult = self._current_multiplier()
        u = self._get_N_registers(10, 2)
        V = u[0] / V_mult
        I = u[1] / I_mult
        mode = "CC" if self._get_register(17) == 1 else "CV"
        return (V, I, mode)

    def _voltage_multiplier(self):
        return 1.0 / float(RIDEN_SPECS[self.MODEL][4])

    def _current_multiplier(self):
        return 1.0 / float(RIDEN_SPECS[self.MODEL][5])
