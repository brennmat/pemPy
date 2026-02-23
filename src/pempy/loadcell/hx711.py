"""
HX711 load cell driver for Raspberry Pi GPIO.
Cloned from https://github.com/gandalf15/HX711
"""

import statistics as stat
import time

from termcolor import colored

try:
    import RPi.GPIO as GPIO
except ImportError:
    raise ImportError("RPi.GPIO is required for HX711. Install with: pip install pempy[rpi]")


class HX711:
    """
    HX711 load cell driver.
    dout_pin: GPIO pin for DOUT (BCM numbering)
    pd_sck_pin: GPIO pin for SCK (BCM numbering)
    gain_channel_A: 64 or 128
    select_channel: 'A' or 'B'
    """

    def __init__(
        self,
        dout_pin,
        pd_sck_pin,
        gain_channel_A=128,
        select_channel="A",
    ):
        if not isinstance(dout_pin, int):
            raise TypeError(f"dout_pin must be int, got {type(dout_pin)}")
        if not isinstance(pd_sck_pin, int):
            raise TypeError(f"pd_sck_pin must be int, got {type(pd_sck_pin)}")

        self._pd_sck = pd_sck_pin
        self._dout = dout_pin
        self._gain_channel_A = 0
        self._offset_A_128 = 0
        self._offset_A_64 = 0
        self._offset_B = 0
        self._last_raw_data_A_128 = 0
        self._last_raw_data_A_64 = 0
        self._last_raw_data_B = 0
        self._wanted_channel = ""
        self._current_channel = ""
        self._scale_ratio_A_128 = 1
        self._scale_ratio_A_64 = 1
        self._scale_ratio_B = 1
        self._debug_mode = False
        self._data_filter = outliers_filter

        GPIO.setup(self._pd_sck, GPIO.OUT)
        GPIO.setup(self._dout, GPIO.IN)
        self.select_channel(select_channel)
        self.set_gain_A(gain_channel_A)

    def warning(self, msg):
        print("\a")
        print(colored(f"***** WARNING from loadcell: {msg}\n", "red"))

    def select_channel(self, channel):
        channel = channel.capitalize()
        if channel == "A":
            self._wanted_channel = "A"
        elif channel == "B":
            self._wanted_channel = "B"
        else:
            raise ValueError(f'channel must be "A" or "B", got {channel}')
        self._read()
        time.sleep(0.5)

    def set_gain_A(self, gain):
        if gain not in (64, 128):
            raise ValueError(f"gain must be 64 or 128, got {gain}")
        self._gain_channel_A = gain
        self._read()
        time.sleep(0.5)

    def zero(self, readings=30):
        if not 0 < readings < 1001:
            raise ValueError(f"readings must be 1..1000, got {readings}")
        result = self.get_raw_data_mean(readings)
        if result is False:
            return True
        if self._current_channel == "A" and self._gain_channel_A == 128:
            self._offset_A_128 = result
            return False
        if self._current_channel == "A" and self._gain_channel_A == 64:
            self._offset_A_64 = result
            return False
        if self._current_channel == "B":
            self._offset_B = result
            return False
        if self._debug_mode:
            print(f"Cannot zero() channel/gain mismatch: {self._current_channel}, {self._gain_channel_A}")
        return True

    def set_offset(self, offset, channel="", gain_A=0):
        if not isinstance(offset, int):
            raise TypeError(f"offset must be int, got {type(offset)}")
        channel = channel.capitalize()
        if channel == "A" and gain_A == 128:
            self._offset_A_128 = offset
        elif channel == "A" and gain_A == 64:
            self._offset_A_64 = offset
        elif channel == "B":
            self._offset_B = offset
        elif channel == "":
            if self._current_channel == "A" and self._gain_channel_A == 128:
                self._offset_A_128 = offset
            elif self._current_channel == "A" and self._gain_channel_A == 64:
                self._offset_A_64 = offset
            else:
                self._offset_B = offset
        else:
            raise ValueError(f'channel must be "A" or "B", got {channel}')

    def set_scale_ratio(self, scale_ratio, channel="", gain_A=0):
        if not isinstance(gain_A, int):
            raise TypeError(f"gain_A must be int, got {type(gain_A)}")
        channel = channel.capitalize()
        if channel == "A" and gain_A == 128:
            self._scale_ratio_A_128 = scale_ratio
        elif channel == "A" and gain_A == 64:
            self._scale_ratio_A_64 = scale_ratio
        elif channel == "B":
            self._scale_ratio_B = scale_ratio
        elif channel == "":
            if self._current_channel == "A" and self._gain_channel_A == 128:
                self._scale_ratio_A_128 = scale_ratio
            elif self._current_channel == "A" and self._gain_channel_A == 64:
                self._scale_ratio_A_64 = scale_ratio
            else:
                self._scale_ratio_B = scale_ratio
        else:
            raise ValueError(f'channel must be "A" or "B", got {channel}')

    def set_data_filter(self, data_filter):
        if not callable(data_filter):
            raise TypeError(f"data_filter must be callable, got {type(data_filter)}")
        self._data_filter = data_filter

    def set_debug_mode(self, flag=False):
        if not isinstance(flag, bool):
            raise ValueError(f"flag must be bool, got {type(flag)}")
        self._debug_mode = flag
        print("Debug mode ENABLED" if flag else "Debug mode DISABLED")

    def _save_last_raw_data(self, channel, gain_A, data):
        if channel == "A" and gain_A == 128:
            self._last_raw_data_A_128 = data
        elif channel == "A" and gain_A == 64:
            self._last_raw_data_A_64 = data
        elif channel == "B":
            self._last_raw_data_B = data
        else:
            return False
        return True

    def _ready(self):
        return GPIO.input(self._dout) == 0

    def _set_channel_gain(self, num):
        for _ in range(num):
            start = time.perf_counter()
            GPIO.output(self._pd_sck, True)
            GPIO.output(self._pd_sck, False)
            if time.perf_counter() - start >= 0.00006:
                if self._debug_mode:
                    print("Not enough fast while setting gain and channel")
                result = self.get_raw_data_mean(6)
                if result is False:
                    return False
        return True

    def _read(self):
        GPIO.output(self._pd_sck, False)
        ready_counter = 0
        while not self._ready() and ready_counter <= 40:
            time.sleep(0.01)
            ready_counter += 1
            if ready_counter == 40:
                if self._debug_mode:
                    print("_read() not ready after 40 trials")
                return False

        data_in = 0
        for _ in range(24):
            start = time.perf_counter()
            GPIO.output(self._pd_sck, True)
            GPIO.output(self._pd_sck, False)
            if time.perf_counter() - start >= 0.00006:
                if self._debug_mode:
                    print("Not enough fast while reading data")
                return False
            data_in = (data_in << 1) | GPIO.input(self._dout)

        if self._wanted_channel == "A" and self._gain_channel_A == 128:
            if not self._set_channel_gain(1):
                return False
            self._current_channel, self._gain_channel_A = "A", 128
        elif self._wanted_channel == "A" and self._gain_channel_A == 64:
            if not self._set_channel_gain(3):
                return False
            self._current_channel, self._gain_channel_A = "A", 64
        else:
            if not self._set_channel_gain(2):
                return False
            self._current_channel = "B"

        if data_in in (0x7FFFFF, 0x800000):
            if self._debug_mode:
                print(f"Invalid data: {data_in}")
            return False

        signed_data = -(data_in ^ 0xFFFFFF) - 1 if (data_in & 0x800000) else data_in
        return signed_data

    def get_raw_data_mean(self, readings=30):
        backup_channel = self._current_channel
        backup_gain = self._gain_channel_A
        data_list = [self._read() for _ in range(readings)]

        if readings > 2 and self._data_filter:
            filtered_data = self._data_filter(data_list)
            if not filtered_data:
                return False
            data_mean = stat.mean(filtered_data)
        else:
            valid = [x for x in data_list if x is not False]
            if not valid:
                return False
            data_mean = stat.mean(valid)

        self._save_last_raw_data(backup_channel, backup_gain, data_mean)
        return int(data_mean)

    def get_data_mean(self, readings=30):
        result = self.get_raw_data_mean(readings)
        if result is False:
            return False
        if self._current_channel == "A" and self._gain_channel_A == 128:
            return result - self._offset_A_128
        if self._current_channel == "A" and self._gain_channel_A == 64:
            return result - self._offset_A_64
        return result - self._offset_B

    def get_weight_mean(self, readings=30):
        """Return weight in grams (or configured units)."""
        result = self.get_raw_data_mean(readings)
        if result is False:
            return False
        if self._current_channel == "A" and self._gain_channel_A == 128:
            return float((result - self._offset_A_128) / self._scale_ratio_A_128)
        if self._current_channel == "A" and self._gain_channel_A == 64:
            return float((result - self._offset_A_64) / self._scale_ratio_A_64)
        return float((result - self._offset_B) / self._scale_ratio_B)

    def get_weight_mean_uncompensated(self, readings=30):
        """Alias for get_weight_mean (kept for API compatibility)."""
        return self.get_weight_mean(readings)

    def get_current_channel(self):
        return self._current_channel

    def get_data_filter(self):
        return self._data_filter

    def get_current_gain_A(self):
        return self._gain_channel_A

    def get_last_raw_data(self, channel="", gain_A=0):
        channel = channel.capitalize()
        if channel == "A" and gain_A == 128:
            return self._last_raw_data_A_128
        if channel == "A" and gain_A == 64:
            return self._last_raw_data_A_64
        if channel == "B":
            return self._last_raw_data_B
        if channel == "":
            if self._current_channel == "A" and self._gain_channel_A == 128:
                return self._last_raw_data_A_128
            if self._current_channel == "A" and self._gain_channel_A == 64:
                return self._last_raw_data_A_64
            return self._last_raw_data_B
        raise ValueError(f"channel must be A or B, gain_A 128 or 64; got {channel}, {gain_A}")

    def get_current_offset(self, channel="", gain_A=0):
        channel = channel.capitalize()
        if channel == "A" and gain_A == 128:
            return self._offset_A_128
        if channel == "A" and gain_A == 64:
            return self._offset_A_64
        if channel == "B":
            return self._offset_B
        if channel == "":
            if self._current_channel == "A" and self._gain_channel_A == 128:
                return self._offset_A_128
            if self._current_channel == "A" and self._gain_channel_A == 64:
                return self._offset_A_64
            return self._offset_B
        raise ValueError(f"channel must be A or B, gain_A 128 or 64; got {channel}, {gain_A}")

    def get_current_scale_ratio(self, channel="", gain_A=0):
        channel = channel.capitalize()
        if channel == "A" and gain_A == 128:
            return self._scale_ratio_A_128
        if channel == "A" and gain_A == 64:
            return self._scale_ratio_A_64
        if channel == "B":
            return self._scale_ratio_B
        if channel == "":
            if self._current_channel == "A" and self._gain_channel_A == 128:
                return self._scale_ratio_A_128
            if self._current_channel == "A" and self._gain_channel_A == 64:
                return self._scale_ratio_A_64
            return self._scale_ratio_B
        raise ValueError(f"channel must be A or B, gain_A 128 or 64; got {channel}, {gain_A}")

    def power_down(self):
        GPIO.output(self._pd_sck, False)
        GPIO.output(self._pd_sck, True)
        time.sleep(0.01)

    def power_up(self):
        GPIO.output(self._pd_sck, False)
        time.sleep(0.01)

    def reset(self):
        self.power_down()
        self.power_up()
        result = self.get_raw_data_mean(6)
        return result is False


def outliers_filter(data_list):
    """Filter outliers using median absolute deviation."""
    data = [x for x in data_list if x is not False]
    if not data:
        return []
    m = 2.0
    data_median = stat.median(data)
    abs_distance = [abs(x - data_median) for x in data]
    mdev = stat.median(abs_distance)
    if not mdev:
        return data
    filtered = [data[i] for i in range(len(data)) if abs_distance[i] / mdev < m]
    return filtered
