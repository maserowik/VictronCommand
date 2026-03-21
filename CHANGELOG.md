# Changelog — Victron Battery Monitor

All notable changes to this project are documented in this file. Entries are organized by date and component. The most recent changes appear first.

---

## [2026-03-20]

### victron_live_graph.py

#### Features Added

**1. Structured Output Folder — Mirrors Hydraulic Automated Testing Tool**

- Saved CSV files are no longer written to the script's working directory. Results are now saved to a structured folder under `C:\Users\mserowik\Documents\VictronConnect\test_results\` on Windows and `~/Documents/VictronConnect/test_results/` on Linux.
- The folder structure mirrors the Hydraulic Automated Testing Tool convention from `gui.py`:
  ```
  test_results/{TruckType}/{SerialNumber}/{LoadStatus}/{YYYY-MM-DD_HH-MM}/
  ```
- Example output path:
  ```
  C:\Users\mserowik\Documents\VictronConnect\test_results\
      RS1\9876567894\Unloaded\2026-03-20_14-43\
          RS1_9876567894_Unloaded_2026-03-20_14-43.csv
  ```
- The output directory is created automatically using `Path.mkdir(parents=True, exist_ok=True)` if it does not already exist.
- Platform detection uses `platform.system()` — the same approach used by `victron_logger.py` for serial port selection.

### README.md

#### Updated

**1. Saved File Naming and Location Section**

- Renamed section from "Saved File Naming" to "Saved File Naming and Location".
- Added output root paths for Windows and Linux.
- Added folder structure diagram matching the new `test_results/{TruckType}/{SerialNumber}/{LoadStatus}/{timestamp}/` layout.
- Added a concrete example showing the full path for an RS1, Unloaded session.
- Added a note in the Notes section clarifying that the Windows output path is hardcoded and must be updated in `OUTPUT_ROOT` if the username or path differs.
- Updated version to 1.4.

---

## [2026-03-20]

### requirements.txt

#### Added

**1. Pinned Dependency Versions**

- Updated `requirements.txt` to pin exact versions for all dependencies: `matplotlib==3.10.8` and `pyserial==3.5`.
- Pinned versions ensure consistent behaviour across installations and prevent unintended breakage from upstream package updates.

---

## [2026-03-20]

### victron_live_graph.py

#### Features Added

**1. Session Isolation — Clear Log on Start**

- Pressing **Start** now clears `victron_log.csv` immediately before logging begins, retaining only the header row.
- This ensures the saved CSV file at the end of each session contains only data collected during that session, not accumulated data from prior runs.
- The clear operation is performed by `clear_log()`, which rewrites the file with the header row only. The logger (`victron_logger.py`) detects the fresh file and resumes appending new rows immediately.

---

## [2026-03-20]

### victron_live_graph.py

#### Features Added

**1. Truck Type Selector**

- Added `RS1` / `CR1` radio buttons to the control strip. Default selection is `RS1`, matching the Hydraulic Automated Testing Tool default.
- The selected truck type is embedded in the saved CSV filename and output folder path.

**2. Load Status Selector**

- Added `Unloaded` / `Loaded` radio buttons to the control strip. Default selection is `Unloaded`, matching the Hydraulic Automated Testing Tool default.
- The selected load status is embedded in the saved CSV filename and output folder path.

**3. Saved Filename Convention**

- Saved files follow the same naming convention as the Hydraulic Automated Testing Tool: `{TruckType}_{Serial}_{LoadStatus}_{YYYY-MM-DD_HH-MM}.csv`.
- Example: `RS1_9876567894_Unloaded_2026-03-20_14-43.csv`.

#### Removed

**4. Radio Button Group Labels**

- Removed the "Truck:" and "Load Status:" text labels that appeared above the radio button groups. The radio options are self-descriptive and the labels added visual clutter.

---

## [2026-03-20]

### victron_live_graph.py

#### Initial Release

**1. Serial Number Entry and Validation**

- Added a `TextBox` widget for manual serial number entry.
- Validation enforces three rules before a session can start: exactly 10 digits, digits only, and must start with `9`. Any violation is reported in the status bar and blocks the session from starting.

**2. Start and Stop Controls**

- Added **Start** and **Stop** buttons embedded in the matplotlib figure above the chart area.
- Start validates the serial number and begins the live plot update loop.
- Stop halts the update loop and immediately saves the session CSV.

**3. Status Bar**

- Added a status text area to the right of the Start/Stop buttons.
- Displays idle instructions, active logging details (serial, truck, load, start time), validation errors, and save confirmation or failure messages.

**4. Saved File on Stop**

- On Stop, a copy of `victron_log.csv` is saved with a filename derived from truck type, serial number, load status, and the session start timestamp.

**5. Live Chart Display**

- Four subplots displayed simultaneously: Voltage (V), Current (A), Power (W), State of Charge (%).
- Charts update every second using `FuncAnimation`.
- X-axis displays real timestamps in `HH:MM` format using `matplotlib.dates`.
- Data gaps (e.g. logger restart) appear as visual breaks in the line rather than being compressed.

**6. Zero-Row Filtering**

- Rows where Voltage is zero or less are excluded before plotting. These rows are produced by the logger when a partial VE.Direct serial frame is received and do not represent real measurements.

**7. Rolling Data Window**

- The last 200 raw rows from `victron_log.csv` are read on each refresh. After zero-row filtering this yields approximately 100 valid data points.

---

### victron_logger.py

#### Initial Release

**1. VE.Direct Serial Reader**

- Reads the Victron VE.Direct text protocol from a USB serial port at 19200 baud.
- Assembles key-value pairs from tab-delimited lines and commits a complete data row on each `Checksum` frame boundary.

**2. Cross-Platform Port Detection**

- Automatically selects `COM15` on Windows and `/dev/ttyUSB0` on Linux via `platform.system()`. Edit `get_port()` to override.

**3. Data Validation and Filtering**

- Only writes a row when all four required fields (`V`, `I`, `P`, `SOC`) are present in the current frame.
- Rows where the calculated voltage is zero or less are discarded before writing.

**4. CSV Output**

- Appends data to `victron_log.csv` in the working directory. Creates the file with a header row on first run if it does not exist.
- Calls `f.flush()` after each row to ensure data is written to disk immediately and visible to the live graph.

---

### Known Limitations

- `victron_log.csv` is excluded from git via `.gitignore`. Saved session files are also excluded by the `*.csv` rule. Files must be backed up manually after each session.
- The logger serial port defaults are `COM15` (Windows) and `/dev/ttyUSB0` (Linux). If your system uses a different port, `get_port()` in `victron_logger.py` must be edited manually — there is no GUI port selector.
- The Windows output root path is hardcoded to `C:\Users\mserowik\Documents\VictronConnect\test_results`. If the username or path differs, update `OUTPUT_ROOT` in `victron_live_graph.py`.
- There is a brief moment after pressing Start where `victron_log.csv` contains only the header row while the logger has not yet appended new data. The charts will appear empty for up to one second before new readings arrive.
