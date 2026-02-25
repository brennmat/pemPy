"""Tests for power supply module (config parsing only, no hardware)."""

import configparser

import pytest

from pempy.powersupply import _require, get_powersupply


def test_require_raises_on_missing_section():
    config = configparser.ConfigParser()
    with pytest.raises(ValueError, match="Missing config section"):
        _require(config, "MISSING", "key")


def test_require_raises_on_missing_key():
    config = configparser.ConfigParser()
    config.add_section("FOO")
    with pytest.raises(ValueError, match="Missing config"):
        _require(config, "FOO", "missing_key")


def test_require_returns_value_when_present():
    config = configparser.ConfigParser()
    config["FOO"] = {"key": "value"}
    assert _require(config, "FOO", "key") == "value"


def test_get_powersupply_raises_on_unknown_type():
    config = configparser.ConfigParser()
    config["PEMCELLPSU"] = {"TYPE": "unknown", "COMPORT": "/dev/ttyUSB0"}
    with pytest.raises(ValueError, match="Unknown power supply type"):
        get_powersupply(config)
