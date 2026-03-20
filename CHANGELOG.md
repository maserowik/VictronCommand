# Changelog

All notable changes to the Victron Battery Monitor project are documented here.

---

## [Unreleased]

---

## [1.3.0] - 2026-03-20

### Added
- `requirements.txt`: Added with pinned versions — `matplotlib==3.10.8` and `pyserial==3.5`.
- `README.md`: Added requirements and virtual environment install instructions using `requirements.txt`.

---

## [1.2.0] - 2026-03-20

### Added
- `victron_live_graph.py`: **Session isolation** — pressing Start now clears `victron_log.csv` (retaining the header row) so each saved file contains only data from that session, not accumulated data from prior runs.

---

## [1.1.0] - 2026-03-20

### Added
- `victron_live_graph.py`: **Truck Type selector** — `RS1` / `CR1` radio buttons, defaults to `RS1`. Selection is embedded in the saved filename.
- `victron_live_graph.py`: **Load Status selector** — `Unloaded` / `Loaded` radio buttons, defaults to `Unloaded`. Selection is embedded in the saved filename.
- `victron_live_graph.py`: Saved filename now follows the hydraulic test tooling convention: `{TruckType}_{Serial}_{LoadStatus}_{YYYY-MM-DD_HH-MM}.csv`.

### Removed
- `victron_live_graph.py`: Removed "Truck:" and "Load Status:" text labels above the radio button groups.

---

## [1.0.0] - 2026-03-20

### Added
- `victron_live_graph.py`: Initial release of the live graph script.
- `victron_live_graph.py`: **Serial number entry** with validation — exactly 10 digits, digits only, must start with `9`.
- `victron_live_graph.py`: **Start / Stop buttons** embedded in the matplotlib figure toolbar area.
- `victron_live_graph.py`: On Stop, saves a copy of `victron_log.csv` named with serial number and session start timestamp.
- `victron_live_graph.py`: **Status bar** showing logging state, errors, and save confirmation.
- `victron_live_graph.py`: Four live subplots — Voltage, Current, Power, State of Charge — updated every second.
- `victron_live_graph.py`: Real timestamps on the x-axis using `matplotlib.dates`.
- `victron_live_graph.py`: Zero-value rows filtered out before plotting to remove partial-frame noise from the logger.
- `victron_live_graph.py`: Rolling window of last 200 valid data points displayed.
- `victron_logger.py`: Initial release. Reads VE.Direct serial data at 19200 baud, writes to `victron_log.csv` in append mode.
- `victron_logger.py`: Auto-detects platform — uses `COM15` on Windows, `/dev/ttyUSB0` on Linux.
- `victron_logger.py`: Filters zero-voltage rows before writing to CSV.
- `victron_logger.py`: Validates that all required fields (`V`, `I`, `P`, `SOC`) are present before writing a row.
