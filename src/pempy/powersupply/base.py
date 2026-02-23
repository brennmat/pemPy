"""
Abstract base class for power supplies used with PEM cells.
"""

from abc import ABC, abstractmethod


class PowerSupply(ABC):
    """
    Interface for power supplies driving PEM electrolysis cells.
    All implementations must provide: output(), voltage(), current(), reading().
    """

    @abstractmethod
    def output(self, state: bool) -> None:
        """Enable (True) or disable (False) the output."""
        pass

    @abstractmethod
    def voltage(self, voltage: float) -> None:
        """Set output voltage in volts."""
        pass

    @abstractmethod
    def current(self, current: float) -> None:
        """Set current limit in amperes."""
        pass

    @abstractmethod
    def reading(self) -> tuple:
        """Return (voltage_V, current_A, mode) where mode is 'CV' or 'CC'."""
        pass
