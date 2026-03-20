# Victron Battery Monitor

A two-script Python tool for logging and live-plotting battery data from a Victron Battery Monitor over serial (VE.Direct protocol).

---

## Files

| File | Purpose |
|---|---|
| `victron_logger.py` | Reads VE.Direct serial data and appends it to `victron_log.csv` |
| `victron_live_graph.py` | Live plot of `victron_log.csv` with session controls |
| `victron_log.csv` | Working log file — created/appended by the logger, cleared on each new session |
| `requirements.txt` | Python package dependencies |

---

## Requirements

Python 3.8 or later is required.

### Install dependencies

**Standard:**
```bash
pip install -r requirements.txt
```

**Using a virtual environment (recommended):**
```bash
python -m venv .venv

# Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

---

## Usage

### 1. Start the logger

The logger must be running before the live graph will have data to display.

**Windows:**
```bash
python victron_logger.py
```

**Linux:**
```bash
python3 victron_logger.py
```

The logger auto-detects the platform and uses `COM15` on Windows or `/dev/ttyUSB0` on Linux. Edit `get_port()` in `victron_logger.py` if your port differs.

The logger runs until you press `CTRL+C`. It appends data to `victron_log.csv` continuously.

---

### 2. Start the live graph

In a second terminal:

**Windows:**
```bash
python victron_live_graph.py
```

**Linux:**
```bash
python3 victron_live_graph.py
```

---

### 3. Recording a session

In the live graph window:

1. Select **Truck Type** — `RS1` or `CR1`
2. Select **Load Status** — `Unloaded` or `Loaded`
3. Enter the **Serial Number** — must be exactly 10 digits and start with `9` (e.g. `9876567894`)
4. Press **Start** — clears `victron_log.csv` so the session starts fresh, then begins plotting
5. Press **Stop** — stops plotting and saves the session data as a named CSV file

---

### 4. Saved file naming

Saved files follow the same convention as the hydraulic test tooling:

```
{TruckType}_{SerialNumber}_{LoadStatus}_{YYYY-MM-DD_HH-MM}.csv
```

**Example:**
```
RS1_9876567894_Unloaded_2026-03-20_14-43.csv
```

The file is saved in the same directory the script is run from.

---

## Serial Number Validation

| Rule | Detail |
|---|---|
| Length | Exactly 10 characters |
| Characters | Digits only |
| First digit | Must be `9` |

Any violation is shown in the status bar and blocks the session from starting.

---

## Charts

The live graph displays four subplots updated every second:

| Chart | Unit | Description |
|---|---|---|
| Voltage | V | Battery terminal voltage |
| Current | A | Charge / discharge current (negative = discharging) |
| Power | W | Instantaneous power |
| State of Charge | % | Battery SOC as reported by the Victron BMS |

Up to the last 200 valid data points are shown. Zero-value rows (produced when the logger reads a partial serial frame) are filtered out automatically.

---

## Notes

- `victron_log.csv` is excluded from git via `.gitignore` (`*.csv`). Saved session files are also excluded. Store them manually as needed.
- The logger opens the serial port at **19200 baud** as required by the VE.Direct protocol.
- Both scripts can run on the same machine simultaneously. The logger writes to disk and the graph reads from disk independently.
