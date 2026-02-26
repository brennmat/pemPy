# pemPy

Python package to monitor and control PEM (polymer electrolyte membrane) electrolysis cells for tritium (³H) enrichment in water samples.

## Hardware

- **Core unit**: Raspberry Pi
- **Power supply**: Voltcraft PPS or RIDEN RDxxxx (configurable)
- **Load cell**: HX711 ADC for PEM weight/mass monitoring

## Installation

1. Install with pipx. For local user only:
   ```bash
   pipx install git+https://github.com/brennmat/pemPy.git
   ```
   For system-wide use:
   ```bash
   pipx install --global git+https://github.com/brennmat/pemPy.git
   ```

2. Copy `pemcell_config_EXAMPLE.txt` to `~/pemcell_config.txt` and edit.

## Usage

1. Prepare the PEM cell:
   - Make sure PEM cell is dry; record the empty weight of the dry cell
   - Close outlet valve and fill water sample into the cell (up to 2 L)
   - Make sure the PEM cell is dry on the outside; record the weight of the full cell
   - Determine the water weight from the difference of the full weight and empty weight

2. Run:
   - Log in to Raspberry Pi controlling the PEM cell
   - Run `screen -R` to start (or re-attach to) a persistent terminal session that keeps running even if the shell connection drops
   - Run `pemcell`

3. Follow the interactive prompts:
   - **Enter sample name** — Label for this run
   - **Zero load cell** — Remove PEM cell from load cell, press ENTER
   - **Calibrate load cell** — Install full PEM cell (without wires) with known weight; enter weight in grams
   - **Attach wires** — Connect wires from PEM and cooler top to power supplies; press ENTER so wire weight is included in process control
   - **Enter water amount** — Grams of water in PEM cell
   - **Start** — Press ENTER to begin electrolysis
   - **Electrolysis** — Runs until water target weight is reached. Log file name is shown on screen; process information is displayed on screen, and saved to the log file. Press ENTER to pause (or stop) the electrolysis.

## Configuration

- `[PEMCELLPSU]`: `TYPE`, `COMPORT`, `RESET`, `PROM`; for RIDEN also `CURRENTMODE` (baud fixed at 115200)
- `[LOADCELL]`: `AVG_READINGS` (per step iteration; calibration uses STEP_ITERATIONS × AVG_READINGS), `DOUT_PIN`, `SCK_PIN`
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
