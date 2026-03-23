import csv
import shutil
import platform
import threading
import time
import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.widgets as mwidgets
from matplotlib.animation import FuncAnimation
from datetime import datetime
from pathlib import Path

# ── Serial import (graceful fallback) ─────────────────────────────────────────
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

# ── Configuration ─────────────────────────────────────────────────────────────
CSV_FILE = "victron_log.csv"
BAUD = 19200
VICTRON_VID = 0x0403
VICTRON_PID = 0x6015

# Windows path logic mirrors gui.py
if platform.system() == "Windows":
    OUTPUT_ROOT = Path(r"C:\Users\mserowik\Documents\VictronConnect\test_results")
else:
    OUTPUT_ROOT = Path.home() / "Documents" / "VictronConnect" / "test_results"

# ── Global State ──────────────────────────────────────────────────────────────
logging_active     = False
serial_number      = ""
truck_type         = "RS1"
load_status        = "Unloaded"
log_start_time     = None
last_row_time      = None
last_row_count     = 0
watchdog_warned    = False
logger_status      = "Starting..."

# ── Logger Thread ─────────────────────────────────────────────────────────────
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
        ports = serial.tools.list_ports.comports()
        port = next((p.device for p in ports if (p.vid == VICTRON_VID and p.pid == VICTRON_PID) or "victron" in (p.description or "").lower()), None)
        
        if port is None:
            logger_status = "Searching for Victron..."
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
                    if len(parts) == 2: data[parts[0]] = parts[1]
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

threading.Thread(target=_logger_thread, daemon=True).start()

# ── Summary & Save Logic ──────────────────────────────────────────────────────
def _show_summary(elapsed, v, i, p, s):
    """Generates the Session Summary popup."""
    def fmt(data):
        return f"min {min(data):.3f}   avg {sum(data)/len(data):.3f}   max {max(data):.3f}"

    mins, secs = divmod(int(elapsed), 60)
    summary = (
        f"Session Duration:   {mins}m {secs}s\n"
        f"Data Points:        {len(v)}\n\n"
        f"Voltage  (V):   {fmt(v)}\n"
        f"Current  (A):   {fmt(i)}\n"
        f"Power    (W):   {fmt(p)}\n"
        f"SOC      (%):   {fmt(s)}\n"
    )
    messagebox.showinfo("Session Summary", summary)

def save_csv():
    """Saves log using gui.py hierarchy and provides summary."""
    if log_start_time is None: return

    # 1. Gather all session data for summary
    ts_list, v_list, i_list, p_list, s_list = read_data_full()
    
    if v_list:
        elapsed = (datetime.now() - log_start_time).total_seconds()
        _show_summary(elapsed, v_list, i_list, p_list, s_list)

    # 2. Build Naming convention (Truck/Serial/Load/Timestamp)
    ts_folder = log_start_time.strftime("%Y%m%d_%H%M%S")
    ts_file   = log_start_time.strftime("%Y-%m-%d_%H-%M")
    filename  = f"{truck_type}_{serial_number}_{load_status}_{ts_file}.csv"
    output_dir = OUTPUT_ROOT / truck_type / serial_number / load_status / ts_folder

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        dest = output_dir / filename
        shutil.copy2(CSV_FILE, dest)
        set_status(f"Saved: {filename}", "steelblue")
        print(f"File created: {dest}")
    except Exception as e:
        messagebox.showerror("Save Error", f"Failed to create file:\n{e}")

def read_data_full():
    """Reads all rows for the summary."""
    ts, v, i, p, s = [], [], [], [], []
    try:
        with open(CSV_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts.append(datetime.fromisoformat(row["Timestamp"]))
                v.append(float(row["Voltage"]))
                i.append(float(row["Current"]))
                p.append(float(row["Power"]))
                s.append(float(row["SOC"]))
    except: pass
    return ts, v, i, p, s

# ── GUI Elements ──────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 9))
fig.suptitle("Victron Battery Monitor", fontsize=13)

ax_serial = fig.add_axes([0.06, 0.92, 0.20, 0.04])
serial_box = mwidgets.TextBox(ax_serial, "Serial: ", initial="", color="white")

ax_truck = fig.add_axes([0.30, 0.90, 0.15, 0.07], frameon=False)
radio_truck = mwidgets.RadioButtons(ax_truck, ("RS1", "CR1"))

ax_load = fig.add_axes([0.48, 0.90, 0.15, 0.07], frameon=False)
radio_load = mwidgets.RadioButtons(ax_load, ("Unloaded", "Loaded"))

ax_start, ax_stop = fig.add_axes([0.06, 0.86, 0.08, 0.04]), fig.add_axes([0.15, 0.86, 0.08, 0.04])
btn_start, btn_stop = mwidgets.Button(ax_start, "Start", color="#d4edda"), mwidgets.Button(ax_stop, "Stop", color="#f8d7da")

ax_status = fig.add_axes([0.25, 0.85, 0.70, 0.05], frameon=False)
ax_status.axis("off")
status_txt = ax_status.text(0, 0.5, "", va="center", fontsize=9, color="gray")

def set_status(msg, color="gray"):
    status_txt.set_text(msg); status_txt.set_color(color); fig.canvas.draw_idle()

# Data Subplots
axs = [fig.add_axes(p) for p in [(0.06, 0.48, 0.40, 0.32), (0.55, 0.48, 0.40, 0.32), (0.06, 0.08, 0.40, 0.32), (0.55, 0.08, 0.40, 0.32)]]
lines = [axs[0].plot([], [], 'steelblue')[0], axs[1].plot([], [], 'tomato')[0], axs[2].plot([], [], 'darkorange')[0], axs[3].plot([], [], 'seagreen')[0]]
for ax, t, u in zip(axs, ["Voltage", "Current", "Power", "SOC"], ["V", "A", "W", "%"]):
    ax.set_title(t); ax.set_ylabel(u); ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

# ── Callbacks ─────────────────────────────────────────────────────────────────
def on_start(event):
    global logging_active, serial_number, log_start_time
    s = serial_box.text.strip()
    if len(s) == 10 and s.isdigit() and s[0] == '9':
        log_start_time, serial_number, logging_active = datetime.now(), s, True
        with open(CSV_FILE, "w", newline="") as f:
            csv.writer(f).writerow(["Timestamp", "Voltage", "Current", "Power", "SOC"])
        set_status(f"RECORDING: {truck_type}_{serial_number}_{load_status}", "green")
    else:
        set_status("Error: Serial must be 10 digits starting with 9", "crimson")

def on_stop(event):
    global logging_active
    if logging_active:
        logging_active = False
        save_csv()

def safe_exit():
    """Safety: Ask to save if the 'X' is clicked during a test."""
    if logging_active:
        if messagebox.askyesno("Exit", "Logging is active! Save results before closing?"):
            save_csv()
    plt.close('all')

btn_start.on_clicked(on_start)
btn_stop.on_clicked(on_stop)
radio_truck.on_clicked(lambda l: globals().update(truck_type=l))
radio_load.on_clicked(lambda l: globals().update(load_status=l))

# Handle window close button
fig.canvas.manager.window.protocol("WM_DELETE_WINDOW", safe_exit)

def update(_frame):
    if not logging_active:
        set_status(f"Logger: {logger_status}", "gray")
        return
    try:
        ts, v, i, p, s = read_data_full()
        # Update live charts with last 200 points
        for line, data in zip(lines, [v[-200:], i[-200:], p[-200:], s[-200:]]):
            line.set_data(ts[-200:], data); line.axes.relim(); line.axes.autoscale_view()
    except: pass
    fig.canvas.draw_idle()

ani = FuncAnimation(fig, update, interval=1000, cache_frame_data=False)
plt.show()