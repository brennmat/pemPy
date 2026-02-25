"""Tests for HX711 load cell module (outliers_filter only, no hardware)."""

import pytest

try:
    from pempy.loadcell.hx711 import outliers_filter
except ImportError:
    pytest.skip("RPi.GPIO not available (run on Raspberry Pi or install pempy[rpi])", allow_module_level=True)


def test_outliers_filter_removes_extreme_values():
    data = [10, 11, 12, 13, 100]
    assert 100 not in outliers_filter(data)


def test_outliers_filter_returns_empty_for_empty_input():
    assert outliers_filter([]) == []


def test_outliers_filter_ignores_false_values():
    data = [10, False, 11, 12]
    assert outliers_filter(data) == [10, 11, 12]
