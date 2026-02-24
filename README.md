# pemPy

Python package to monitor and control PEM (polymer electrolyte membrane) electrolysis cells for tritium (³H) enrichment in water samples.

## Hardware

- **Core unit**: Raspberry Pi
- **Power supply**: Voltcraft PPS or RIDEN RDxxxx (configurable)
- **Load cell**: HX711 ADC for PEM weight/mass monitoring

## Installation

```bash
# With pip
pip install -e .

# With RIDEN power supply support
pip install -e ".[riden]"

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

- `[PEMCELLPSU]`: `TYPE`, `COMPORT`, `RESET`, `PROM`, `DEBUG`; for RIDEN also `BAUD`, `CURRENTMODE` (all required)
- `[LOADCELL]`: `AVG_READINGS`, `DOUT_PIN`, `SCK_PIN`
- `[ELECTROLYSIS]`: `STEP_ITERATIONS`, `WATER_TARGET`, `MAXVOLTAGE`, `MAXCURRENT`, `MINCURRENT`, `RAMPTIME`

## HX711 Load Cell Wiring

### HX711 ↔ Raspberry Pi (BCM)

| HX711 pin | RPi connection | Physical pin |
|-----------|----------------|--------------|
| VCC | 3.3V or 5V | 1 (3.3V) or 2 (5V) |
| GND | GND | 6, 9, 14, 20, etc. |
| DOUT | GPIO 5 (BCM) | 29 |
| SCK | GPIO 6 (BCM) | 31 |

Config: `DOUT_PIN = 5`, `SCK_PIN = 6` (BCM numbering; physical pin 6 is GND, not SCK).

### Load Cell ↔ HX711

| Load cell wire | HX711 terminal |
|----------------|----------------|
| Red (E+) | E+ |
| Black (E-) | E- |
| White (A+) | A+ |
| Green (A-) | A- |

B+ and B- (Channel B) are not used; leave them unconnected.

Wire colors may vary; check the load cell datasheet for E+/E- (excitation) and A+/A- (signal).

## License

GPL-3.0-or-later. See LICENSE.
