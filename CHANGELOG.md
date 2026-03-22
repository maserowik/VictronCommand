# Changelog — Victron Battery Monitor

All notable changes to this project are documented in this file. Entries are organized by date and component. The most recent changes appear first.

---

## [2026-03-20]

### victron_monitor.py

#### Features Added

**1. Automatic COM Port Detection by USB VID/PID**

- Removed the hardcoded `SERIAL_PORT` constant. The logger now scans all available serial ports on every connection attempt and automatically connects to the Victron VE.Direct USB adapter.
- Port detection uses `serial.tools.list_ports.comports()` to enumerate all available ports and matches on USB Vendor ID `0x0403` and Product ID `0x6015` — the FTDI FT230X chip used in the Victron VE.Direct-USB cable.
- Falls back to a description string match for "victron" or "VE.Direct" on systems where the OS does not expose USB VID/PID information.
- If the device is unplugged and reconnected on a different COM port, the logger detects and connects to the new port automatically within 5 seconds — no restart required.
- If no matching device is found, the status bar shows `Searching for Victron device...` and the logger retries every 5 seconds.
- The VID and PID values are defined as named constants (`VICTRON_VID` and `VICTRON_PID`) at the top of the script for easy reference.
- Status bar messages updated to reflect the detected port name rather than a hardcoded value (e.g. `Connected: COM3` instead of `Connected: COM15`).
- Disconnection message updated to: `Disconnected from {port} — searching again in 5s`.

### README.md

#### Updated

**1. USB Port Detection Documentation**

- Updated Usage section — removed manual port configuration note, replaced with description of automatic port detection behaviour.
- Added note explaining reconnection behaviour when device is unplugged and reconnected on a different COM port.
- Added note in the Notes section documenting the VID/PID values used for detection and the description-string fallback.
- Updated Logger Status examples to show dynamic port name (e.g. `COM3`) instead of hardcoded port.
- Updated version to 2.1.

---

## [2026-03-20]

### victron_monitor.py

#### Features Added — Script Consolidation

**1. Combined Logger and Live Graph — Single Script**

- `victron_logger.py` and `victron_live_graph.py` merged into `victron_monitor.py`.
- Serial logger runs in a background `threading.Thread(daemon=True)` that starts automatically on launch.
- Logger reconnects automatically every 5 seconds on any error or disconnection.
- Graceful fallback if `pyserial` is not installed — GUI opens with an error in the status bar.
- Logger thread shuts down cleanly when the window is closed.

**2. Logger Status in the Status Bar**

- Status bar shows current logger connection state when no session is active.

**3. Configurable Constants**

- `SERIAL_PORT`, `OUTPUT_ROOT`, `BAUD`, `MIN_SESSION_SECONDS`, and `WATCHDOG_TIMEOUT_SEC` all defined as named constants at the top of the script.

---

## [2026-03-20]

### victron_live_graph.py

#### Features Added

**1. Control Locking on Session Start**

- Serial field and radio buttons locked on Start, unlocked on Stop.
- Prevents mid-session changes inconsistent with the saved filename and folder.

**2. Session Start Marker on Charts**

- Green dashed vertical line drawn at session start time on all four charts.

**3. Minimum Session Duration Warning**

- Warning dialog if Stop is pressed within 10 seconds of Start.
- `MIN_SESSION_SECONDS = 10` — adjustable constant.

**4. Session Summary Popup on Stop**

- Shows session duration, data point count, and min/avg/max for all four metrics before saving.

**5. Watchdog — Logger Health Monitor**

- Red status bar warning if no new CSV rows arrive for 10 seconds during a session.
- Clears automatically when data resumes.
- `WATCHDOG_TIMEOUT_SEC = 10` — adjustable constant.

---

## [2026-03-20]

### victron_live_graph.py

#### Features Added

**1. Structured Output Folder — Mirrors Hydraulic Automated Testing Tool**

- Results saved to `C:\Users\mserowik\Documents\VictronConnect\test_results\` on Windows, `~/Documents/VictronConnect/test_results/` on Linux.
- Folder structure: `test_results/{TruckType}/{SerialNumber}/{LoadStatus}/{YYYY-MM-DD_HH-MM}/`.
- Output directory created automatically if it does not exist.

---

## [2026-03-20]

### requirements.txt

#### Added

**1. Pinned Dependency Versions**

- `matplotlib==3.10.8` and `pyserial==3.5` pinned for consistent installations.

---

## [2026-03-20]

### victron_live_graph.py

#### Features Added

**1. Session Isolation — Clear Log on Start**

- Pressing Start clears `victron_log.csv` (header retained) so each saved file contains only current session data.

---

## [2026-03-20]

### victron_live_graph.py

#### Features Added

**1. Truck Type Selector** — `RS1` / `CR1` radio buttons, default `RS1`.

**2. Load Status Selector** — `Unloaded` / `Loaded` radio buttons, default `Unloaded`.

**3. Saved Filename Convention** — `{TruckType}_{Serial}_{LoadStatus}_{YYYY-MM-DD_HH-MM}.csv`.

#### Removed

**4. Radio Button Group Labels** — "Truck:" and "Load Status:" text labels removed.

---

## [2026-03-20]

### victron_live_graph.py — Initial Release

**1.** Serial number entry with validation (10 digits, digits only, starts with `9`).
**2.** Start / Stop buttons with status bar.
**3.** Four live subplots: Voltage, Current, Power, State of Charge.
**4.** Real timestamps on x-axis.
**5.** Zero-row filtering.
**6.** Rolling 200-row data window.

---

### victron_logger.py — Initial Release

**1.** VE.Direct serial reader at 19200 baud.
**2.** Cross-platform port detection (`COM15` Windows / `/dev/ttyUSB0` Linux).
**3.** Frame validation — all four fields required before writing.
**4.** CSV append with immediate flush.

---

### Known Limitations

- `victron_log.csv` and saved session files are excluded from git (`*.csv`). Back up manually after each session.
- The Windows output root path is hardcoded. Update `OUTPUT_ROOT` in `victron_monitor.py` if the username or path differs.
- Port detection relies on the FTDI VID/PID (`0x0403` / `0x6015`). If a third-party VE.Direct cable uses a different chip, it may not be detected by VID/PID but may still match on the description string fallback.
- The session summary calculates statistics from the rolling 200-row window. For very long sessions this reflects only the most recent data points.
- There is a brief moment after pressing Start where `victron_log.csv` contains only the header row. Charts will appear empty for up to one second before new readings arrive.
