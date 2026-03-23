import csv
import shutil
import platform
import threading
import time
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.widgets as mwidgets
from matplotlib.animation import FuncAnimation
from datetime import datetime
from pathlib import Path

# ── Serial import (graceful fallback if pyserial not installed) ───────────────
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

# ── Configuration ─────────────────────────────────────────────────────────────
CSV_FILE             = "victron_log.csv"
BAUD                 = 19200
MIN_SESSION_SECONDS  = 10    
WATCHDOG_TIMEOUT_SEC = 10    

VICTRON_VID = 0x0403
VICTRON_PID = 0x6015

# ── Output Root — Mirrors gui.py structure ────────────────────────────────────
# Using a raw string (r"") is critical for Windows paths to work correctly
if platform.system() == "Windows":
    OUTPUT_ROOT = Path(r"C:\Users\mserowik\Documents\VictronConnect\test_results")
else:
    OUTPUT_ROOT = Path.home() / "Documents" / "VictronConnect" / "test_results"

# ── State ─────────────────────────────────────────────────────────────────────
logging_active     = False
serial_number      = ""
truck_type         = "RS1"
load_status        = "Unloaded"
log_start_time     = None
last_row_time      = None
last_row_count     = 0
watchdog_warned    = False
start_marker_dt    = None
start_marker_lines = []
logger_status      = "Starting..."

# ── Helper Functions ──────────────────────────────────────────────────────────
def find_victron_port():
    if not SERIAL_AVAILABLE: return None
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == VICTRON_VID and port.pid == VICTRON_PID:
            return port.device
        desc = (port.description or "").lower()
        mfr  = (port.manufacturer or "").lower()
        if "victron" in desc or "ve.direct" in desc or "victron" in mfr:
            return port.device
    return None

def check_write_permission():
    """Verify output directory is writable before starting test."""
    try:
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        test_file = OUTPUT_ROOT / ".write_test"
        test_file.touch()
        test_file.unlink()
        return True, ""
    except Exception as e:
        return False, str(e)

# ── Logger thread ─────────────────────────────────────────────────────────────
def _init_csv():
    p = Path(CSV_FILE)
    if not p.exists() or p.stat().st_size == 0:
        with open(CSV_FILE, "w", newline="") as f:
            csv.writer(f).writerow(["Timestamp", "Voltage", "Current", "Power", "SOC"])

def _logger_thread():
    global logger_status
    if not SERIAL_AVAILABLE:
        logger_status = "ERROR: pyserial not installed"
        return
    _init_csv()
    while True:
        port = find_victron_port()
        if port is None:
            logger_status = "Searching for Victron device..."
            time.sleep(5)
            continue
        try:
            ser = serial.Serial(port, BAUD, timeout=1)
            logger_status = f"Connected: {port}"
            data = {}
            with open(CSV_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                while True:
                    line = ser.readline().decode(errors="ignore").strip()
                    if not line: continue
                    parts = line.split("\t")
                    if len(parts) == 2:
                        key, value = parts
                        data[key] = value
                    if "Checksum" in line:
                        if all(k in data for k in ("V", "I", "P", "SOC")):
                            try:
                                v, i, p = float(data["V"])/1000, float(data["I"])/1000, float(data["P"])
                                soc = float(data["SOC"])/10
                                if v > 0:
                                    writer.writerow([datetime.now().isoformat(), v, i, p, soc])
                                    f.flush()
                            except: pass
                        data = {}
        except:
            logger_status = "Disconnected - Retrying..."
            time.sleep(5)

_logger_thread_obj = threading.Thread(target=_logger_thread, daemon=True)
_logger_thread_obj.start()

# ── Save CSV (The Fix for Folder Creation) ────────────────────────────────────
def save_csv():
    """
    Saves log using gui.py exact convention: 
    Path:     test_results / {Truck} / {Serial} / {Load} / {YYYYMMDD_HHMMSS} /
    Filename: {Truck}_{Serial}_{Load}_{YYYY-MM-DD_HH-MM}.csv
    """
    if log_start_time is None:
        print("Save aborted: No session start time recorded.")
        return

    # Folder/File Timestamps match gui.py logic
    ts_folder = log_start_time.strftime("%Y%m%d_%H%M%S")
    ts_filename = log_start_time.strftime("%Y-%m-%d_%H-%M")
    
    filename = f"{truck_type}_{serial_number}_{load_status}_{ts_filename}.csv"
    
    # Construct total path
    output_dir = OUTPUT_ROOT / truck_type / serial_number / load_status / ts_folder

    print(f"Attempting to create directory: {output_dir}") # Console verification

    try:
        # parents=True creates the entire folder tree if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        dest = output_dir / filename
        shutil.copy2(CSV_FILE, dest) # Copy temp file to permanent location
        
        set_status(f"Saved: {filename}", "steelblue")
        print(f"SUCCESS: File saved to {dest}")
    except Exception as e:
        set_status(f"Save failed: {e}", "crimson")
        print(f"CRITICAL SAVE ERROR: {e}")

def read_data():
    ts, v, i, p, s = [], [], [], [], []
    try:
        with open(CSV_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in list(reader)[-200:]:
                ts.append(datetime.fromisoformat(row["Timestamp"]))
                v.append(float(row["Voltage"]))
                i.append(float(row["Current"]))
                p.append(float(row["Power"]))
                s.append(float(row["SOC"]))
    except: pass
    return ts, v, i, p, s

# ── GUI Setup ─────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 9))
fig.suptitle("Victron Battery Monitor", fontsize=13, y=0.99)

ax_serial = fig.add_axes([0.06, 0.925, 0.20, 0.042])
serial_box = mwidgets.TextBox(ax_serial, "Serial: ", initial="", color="white")

ax_truck = fig.add_axes([0.30, 0.900, 0.16, 0.075], frameon=False)
radio_truck = mwidgets.RadioButtons(ax_truck, ("RS1", "CR1"))

ax_load = fig.add_axes([0.49, 0.900, 0.18, 0.075], frameon=False)
radio_load = mwidgets.RadioButtons(ax_load, ("Unloaded", "Loaded"))

ax_start, ax_stop = fig.add_axes([0.06, 0.870, 0.08, 0.040]), fig.add_axes([0.15, 0.870, 0.08, 0.040])
btn_start, btn_stop = mwidgets.Button(ax_start, "Start", color="#d4edda"), mwidgets.Button(ax_stop, "Stop", color="#f8d7da")

ax_status = fig.add_axes([0.25, 0.862, 0.72, 0.052], frameon=False)
ax_status.axis("off")
status_txt = ax_status.text(0, 0.5, "", va="center", fontsize=9, color="gray")

def set_status(msg, color="gray"):
    status_txt.set_text(msg); status_txt.set_color(color); fig.canvas.draw_idle()

# Plots
positions = [(0.06, 0.48, 0.40, 0.34), (0.55, 0.48, 0.40, 0.34), (0.06, 0.06, 0.40, 0.34), (0.55, 0.06, 0.40, 0.34)]
axs = [fig.add_axes(p) for p in positions]
lines = [axs[0].plot([], [], 'steelblue')[0], axs[1].plot([], [], 'tomato')[0], 
         axs[2].plot([], [], 'darkorange')[0], axs[3].plot([], [], 'seagreen')[0]]

for ax, title, unit in zip(axs, ["Voltage", "Current", "Power", "SOC"], ["V", "A", "W", "%"]):
    ax.set_title(title); ax.set_ylabel(unit)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

# ── Logic ─────────────────────────────────────────────────────────────────────
def on_start(event):
    global logging_active, serial_number, log_start_time
    
    s_text = serial_box.text.strip()
    if len(s_text) != 10 or not s_text.isdigit() or s_text[0] != '9':
        set_status("Invalid Serial (10 digits, starts with 9)", "crimson")
        return
    
    ok, err = check_write_permission()
    if not ok:
        set_status(f"Permission Error: {err}", "crimson")
        return

    # Start the session
    log_start_time = datetime.now()
    serial_number = s_text
    logging_active = True
    
    # Clean the temp log file
    with open(CSV_FILE, "w", newline="") as f:
        csv.writer(f).writerow(["Timestamp", "Voltage", "Current", "Power", "SOC"])
    
    set_status(f"LOGGING: {truck_type}_{serial_number}_{load_status}", "green")
    print(f"Session started: {log_start_time.strftime('%H:%M:%S')}")

def on_stop(event):
    global logging_active
    if not logging_active: return
    logging_active = False
    save_csv() # This triggers the folder creation and file copy

btn_start.on_clicked(on_start)
btn_stop.on_clicked(on_stop)

radio_truck.on_clicked(lambda l: globals().update(truck_type=l))
radio_load.on_clicked(lambda l: globals().update(load_status=l))

def update(_frame):
    if not logging_active:
        set_status(f"Logger: {logger_status}", "gray")
        return
    ts, v, i, p, s = read_data()
    if not ts: return
    for line, data in zip(lines, [v, i, p, s]):
        line.set_data(ts, data)
        line.axes.relim(); line.axes.autoscale_view()
    fig.canvas.draw_idle()

ani = FuncAnimation(fig, update, interval=1000, cache_frame_data=False)
plt.show()