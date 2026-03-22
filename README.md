# Victron Battery Monitor

A single-script Python tool for logging and live-plotting battery data from a Victron Battery Monitor over serial (VE.Direct protocol). Designed for use alongside hydraulic testing on Seegrid RS1 and CR1 trucks to monitor battery state during test sessions.

---

## Table of Contents

1. [Purpose](#purpose)
2. [Scope](#scope)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Usage](#usage)
6. [Serial Number Validation](#serial-number-validation)
7. [Session Recording](#session-recording)
8. [Session Controls and Behaviour](#session-controls-and-behaviour)
9. [Saved File Naming and Location](#saved-file-naming-and-location)
10. [Charts](#charts)
11. [File Overview](#file-overview)
12. [Notes](#notes)
13. [Revision Control](#revision-control)

---

## Purpose

This tool provides live battery monitoring during hydraulic truck testing. It is designed for use by Quality Control (QC) personnel to:

- Continuously log battery voltage, current, power, and state of charge from a Victron Battery Monitor via the VE.Direct serial protocol
- Display four live-updating charts in a single window during a test session
- Associate logged data with a truck serial number, truck model, and load state
- Save a clean, session-scoped CSV file at the end of each test — containing only data from that session

---

## Scope

This tool applies to QC personnel performing battery monitoring during hydraulic testing on:

- **RS1** Seegrid trucks
- **CR1** Seegrid trucks

---

## Prerequisites

### Hardware
- Victron Battery Monitor with a VE.Direct to USB cable
- USB port on the test laptop

### Software Requirements
- **Python 3.8 or newer** — verify with `python3 --version` before installation

---

## Installation

### Step 1 — Copy the project files

Ensure the following files are present in the same directory:

```
victron_monitor.py
requirements.txt
```

### Step 2 — Create a virtual environment

```bash
python3 -m venv .venv
```

### Step 3 — Activate the virtual environment

**Linux:**
```bash
source .venv/bin/activate
```

**Windows:**
```bash
.venv\Scripts\activate
```

### Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

> **Important:** Ensure all dependencies install without errors before proceeding.

---

## Usage

Run the single combined script. The serial logger starts automatically in the background — no second terminal is needed.

**Linux:**
```bash
python3 victron_monitor.py
```

**Windows:**
```bash
python victron_monitor.py
```

The logger automatically scans all available COM ports on launch and connects to the Victron VE.Direct USB adapter by matching its USB Vendor ID and Product ID. No manual port configuration is required. The status bar shows the current connection state.

If the device is unplugged and reconnected — even on a different COM port — the logger will detect and reconnect to it automatically within 5 seconds.

---

## Serial Number Validation

The serial number field enforces the following rules before a session can be started:

| Rule | Detail |
|---|---|
| Length | Exactly 10 characters |
| Characters | Digits only — no letters, symbols, or spaces |
| First digit | Must be `9` |

If the entered serial fails any of these conditions, an error is shown in the status bar and the session does not start. Check the physical label on the truck and re-enter.

---

## Session Recording

In the live graph window:

1. Select **Truck Type** — `RS1` or `CR1`
2. Select **Load Status** — `Unloaded` or `Loaded`
3. Enter the **Serial Number** — must pass validation rules above (e.g. `9876567894`)
4. Press **Start** — clears `victron_log.csv`, locks controls, draws the session start marker on the charts, and begins live plotting
5. Press **Stop** — halts plotting, shows a session summary, unlocks controls, and saves the session CSV

> **Note:** Pressing Start clears `victron_log.csv` immediately. Any data from a previous session that has not been saved will be lost. Always press Stop and confirm the save before starting a new session.

---

## Session Controls and Behaviour

### Control Locking

Once **Start** is pressed the serial number field and both radio button groups (Truck Type and Load Status) are locked and cannot be changed until **Stop** is pressed. This prevents accidental mid-session changes that would cause the saved filename and folder to be inconsistent with the data collected.

### Session Start Marker

A green dashed vertical line is drawn on all four charts at the exact timestamp when **Start** was pressed. This makes the session boundary visible in the data.

### Minimum Session Duration Warning

If **Stop** is pressed within 10 seconds of pressing **Start**, a warning dialog is shown:

```
The session ran for only X seconds (minimum recommended: 10s).
The recorded data may not be meaningful.
Save anyway?
```

Selecting **No** returns to the active logging state without saving. Selecting **Yes** proceeds with the save.

### Session Summary

When **Stop** is pressed, a summary popup is displayed before the file is saved:

```
Session Duration:   Xm Ys
Data Points:        N

Voltage  (V):   min X.XXX   avg X.XXX   max X.XXX
Current  (A):   min X.XXX   avg X.XXX   max X.XXX
Power    (W):   min X.XXX   avg X.XXX   max X.XXX
SOC      (%):   min X.XXX   avg X.XXX   max X.XXX
```

### Watchdog — Logger Health Monitor

During an active session, the live graph monitors whether `victron_log.csv` is actively receiving new rows. If no new data has arrived for 10 seconds, the status bar changes to a red warning:

```
WARNING: No new data for Xs — check device is connected
```

If the logger reconnects and data resumes, the status bar automatically returns to the normal green logging state.

### Logger Status

When no session is active, the status bar displays the current logger connection state, for example:

```
Logger: Connected: COM3
Logger: Searching for Victron device...
Logger: Disconnected from COM3 — searching again in 5s
```

---

## Saved File Naming and Location

### Output Root

Saved files are written to a structured folder under:

**Windows:**
```
C:\Users\mserowik\Documents\VictronConnect\test_results\
```

**Linux:**
```
~/Documents/VictronConnect/test_results/
```

### Folder Structure

The output folder structure mirrors the Hydraulic Automated Testing Tool:

```
test_results/
  {TruckType}/
    {SerialNumber}/
      {LoadStatus}/
        {YYYY-MM-DD_HH-MM}/
          {TruckType}_{SerialNumber}_{LoadStatus}_{YYYY-MM-DD_HH-MM}.csv
```

### Example

For an RS1, serial `9876567894`, Unloaded, session started at 14:43 on 2026-03-20:

```
C:\Users\mserowik\Documents\VictronConnect\test_results\
  RS1\
    9876567894\
      Unloaded\
        2026-03-20_14-43\
          RS1_9876567894_Unloaded_2026-03-20_14-43.csv
```

The output directory is created automatically if it does not exist. The timestamp reflects when **Start** was pressed.

---

## Charts

The live graph displays four subplots, updated every second:

| Chart | Unit | Description |
|---|---|---|
| Voltage | V | Battery terminal voltage |
| Current | A | Charge / discharge current (negative = discharging) |
| Power | W | Instantaneous power draw |
| State of Charge | % | Battery SOC as reported by the Victron BMS |

Up to the last 200 valid data points are displayed. Zero-value rows produced by partial serial frames are filtered out automatically before plotting. A green dashed vertical line marks the session start time on each chart.

---

## File Overview

| File | Purpose |
|---|---|
| `victron_monitor.py` | Combined serial logger and live graph — single entry point |
| `victron_log.csv` | Working log file — written by the logger thread, cleared on each new session start |
| `requirements.txt` | Pinned Python package dependencies |
| `.gitignore` | Excludes CSV files, virtual environments, and OS/editor artifacts from git |

---

## Notes

- `victron_log.csv` and all saved session CSV files are excluded from git via `.gitignore` (`*.csv`). Session files are saved to `Documents\VictronConnect\test_results\` and should be backed up or archived from there as needed.
- The logger communicates at **19200 baud** as required by the VE.Direct protocol.
- Port detection matches on USB Vendor ID `0x0403` and Product ID `0x6015` (FTDI FT230X — used by the Victron VE.Direct-USB cable). If the OS does not expose VID/PID, the tool falls back to matching the port description string for "victron" or "VE.Direct".
- The logger thread runs as a daemon — it shuts down automatically when the window is closed.
- If `pyserial` is not installed, the logger thread reports an error in the status bar but the GUI will still open. Install dependencies via `pip install -r requirements.txt` to restore full functionality.
- The Windows output root path is hardcoded to `C:\Users\mserowik\Documents\VictronConnect\test_results`. If the username or path differs, update `OUTPUT_ROOT` in `victron_monitor.py`.
- The minimum session duration and watchdog timeout are defined as constants at the top of `victron_monitor.py` (`MIN_SESSION_SECONDS` and `WATCHDOG_TIMEOUT_SEC`) and can be adjusted if needed.

---

## Revision Control

All changes to this documentation must be reviewed and approved in accordance with Seegrid documentation standards.

**Last Updated:** March 2026
**Version:** 2.1

---

## License

Internal Seegrid tool — not for external distribution.
