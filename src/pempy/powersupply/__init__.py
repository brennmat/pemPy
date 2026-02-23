"""
Power supply drivers for PEM cell control.
"""

from pempy.powersupply.base import PowerSupply
from pempy.powersupply.pps import PPS

__all__ = ["PowerSupply", "PPS", "RIDEN", "get_powersupply"]


def __getattr__(name):
    if name == "RIDEN":
        from pempy.powersupply.riden import RIDEN
        return RIDEN
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_powersupply(config):
    """
    Factory: create power supply instance from config parser section.
    Expects config to have [PEMCELLPSU] with TYPE = 'pps' or 'riden'.
    """
    section = "PEMCELLPSU"
    psu_type = config.get(section, "TYPE", fallback="pps").lower()
    comport = config.get(section, "COMPORT")

    if psu_type == "pps":
        return PPS(
            port=comport,
            reset=config.getboolean(section, "RESET", fallback=False),
            prom=config.get(section, "PROM", fallback=None),
            debug=config.getboolean(section, "DEBUG", fallback=False),
        )
    elif psu_type == "riden":
        from pempy.powersupply.riden import RIDEN
        return RIDEN(
            port=comport,
            baud=config.getint(section, "BAUD", fallback=115200),
            currentmode=config.get(section, "CURRENTMODE", fallback="LOW"),
            debug=config.getboolean(section, "DEBUG", fallback=False),
        )
    else:
        raise ValueError(f"Unknown power supply type: {psu_type}")
