# pemPy

Python package to monitor and control PEM (polymer electrolyte membrane) electrolysis cells for tritium (³H) enrichment in water samples.

## Hardware

- **Core unit**: Raspberry Pi
- **Power supply**: Voltcraft PPS or RIDEN RDxxxx (configurable)
- **Load cell**: HX711 ADC for PEM weight/mass monitoring

## Installation

```bash
# With pip (includes RPi.GPIO for Raspberry Pi)
pip install -e ".[rpi]"

# With RIDEN power supply support
pip install -e ".[rpi,riden]"

# With pipx (CLI tool)
pipx install .
```

## Usage

1. Copy `pemcell_config_TEMPLATE.txt` to `pemcell_config.txt` and edit.
2. Run:
   ```bash
   pemcell
   # or: python -m pempy.cli.pemcell --config pemcell_config.txt
   ```

## Configuration

- `[PEMCELLPSU] TYPE = pps` or `riden`
- For PPS: set `COMPORT` to the serial device
- For RIDEN: set `COMPORT`, optional `BAUD`, `CURRENTMODE` (LOW/HIGH)
- `[LOADCELL]`: `READINGS_AVG`, `DOUT_PIN`, `SCK_PIN`, `WATER_TARGET`

## License

GPL-3.0-or-later. See LICENSE.
