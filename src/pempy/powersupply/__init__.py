"""
Power supply drivers for PEM cell control.
"""

import configparser

from pempy.powersupply.base import PowerSupply
from pempy.powersupply.pps import PPS

__all__ = ["PowerSupply", "PPS", "RIDEN", "get_powersupply"]


def __getattr__(name):
    if name == "RIDEN":
        from pempy.powersupply.riden import RIDEN
        return RIDEN
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _require(config, section, key):
    """Return config value; raise ValueError if section or key is missing."""
    if not config.has_section(section):
        raise ValueError(f"Missing config section [{section}]")
    if not config.has_option(section, key):
        raise ValueError(f"Missing config [{section}] {key}")
    return config.get(section, key)


def get_powersupply(config):
    """
    Factory: create power supply instance from config parser section.
    Expects config to have [PEMCELLPSU] with TYPE = 'pps' or 'riden'.
    All required keys must be present; no fallback values.
    """
    try:
        return _get_powersupply(config)
    except configparser.NoOptionError as err:
        raise ValueError(f"Missing config [{err.section}] {err.option}") from err
    except configparser.NoSectionError as err:
        raise ValueError(f"Missing config section [{err.section}]") from err


def _get_powersupply(config):
    section = "PEMCELLPSU"
    psu_type = _require(config, section, "TYPE").lower()
    comport = _require(config, section, "COMPORT")

    if psu_type == "pps":
        _require(config, section, "RESET")
        _require(config, section, "PROM")
        reset = config.getboolean(section, "RESET")
        prom_raw = config.get(section, "PROM")
        prom = prom_raw.strip() or None
        debug = config.getboolean(section, "DEBUG", fallback=False)
        return PPS(port=comport, reset=reset, prom=prom, debug=debug)
    elif psu_type == "riden":
        from pempy.powersupply.riden import RIDEN
        baud = int(_require(config, section, "BAUD"))
        currentmode = _require(config, section, "CURRENTMODE")
        return RIDEN(port=comport, baud=baud, currentmode=currentmode)
    else:
        raise ValueError(f"Unknown power supply type: {psu_type}")
