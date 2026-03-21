import csv
import shutil
import platform
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.widgets as mwidgets
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation
from datetime import datetime
from pathlib import Path

CSV_FILE = "victron_log.csv"

# ── Output root — mirrors gui.py test_results structure ───────────────────────
# Windows : C:\Users\mserowik\Documents\VictronConnect\test_results
# Linux   : ~/Documents/VictronConnect/test_results
if platform.system() == "Windows":
    OUTPUT_ROOT = Path(r"C:\Users\mserowik\Documents\VictronConnect\test_results")
else:
    OUTPUT_ROOT = Path.home() / "Documents" / "VictronConnect" / "test_results"

# ── Constants ─────────────────────────────────────────────────────────────────
MIN_SESSION_SECONDS  = 10    # warn if Stop pressed sooner than this
WATCHDOG_TIMEOUT_SEC = 10    # warn if no new rows arrive within this window

# ── State ─────────────────────────────────────────────────────────────────────
logging_active  = False
serial_number   = ""
truck_type      = "RS1"
load_status     = "Unloaded"
log_start_time  = None
last_row_time   = None   # wall-clock time the last new CSV row was detected
last_row_count  = 0      # used to detect whether new rows have arrived
watchdog_warned = False  # only show the watchdog warning once per session
start_marker_dt = None   # datetime of the Start press — drawn on charts

# ── Data reader ───────────────────────────────────────────────────────────────
def read_data():
    timestamps, voltage, current, power, soc = [], [], [], [], []
    try:
        with open(CSV_FILE, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        for row in rows[-200:]:
            v = float(row["Voltage"])
            if v <= 0:
                continue
            timestamps.append(datetime.fromisoformat(row["Timestamp"]))
            voltage.append(v)
            current.append(float(row["Current"]))
            power.append(float(row["Power"]))
            soc.append(float(row["SOC"]))
    except Exception as e:
        print("Read error:", e)
    return timestamps, voltage, current, power, soc

def get_raw_row_count():
    """Return total number of data rows in the CSV (excluding header)."""
    try:
        with open(CSV_FILE, "r") as f:
            return sum(1 for _ in f) - 1
    except Exception:
        return 0

# ── Clear the log file (keep header row only) ─────────────────────────────────
def clear_log():
    try:
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Voltage", "Current", "Power", "SOC"])
        print(f"Cleared {CSV_FILE} for new session.")
    except Exception as e:
        print(f"Could not clear {CSV_FILE}: {e}")

# ── Validation ────────────────────────────────────────────────────────────────
def validate_serial(text):
    t = text.strip()
    if len(t) != 10:
        return False, "Must be exactly 10 digits"
    if not t.isdigit():
        return False, "Digits only"
    if t[0] != "9":
        return False, "Must start with 9"
    return True, ""

# ── Figure layout ─────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 9))
fig.suptitle("Victron Battery Monitor", fontsize=13, y=0.99)

# --- Serial TextBox ---
ax_serial = fig.add_axes([0.06, 0.925, 0.20, 0.042])
serial_box = mwidgets.TextBox(ax_serial, "Serial: ", initial="",
                               color="white", hovercolor="#f0f0f0")
serial_box.label.set_fontsize(9)

# --- Truck type radio (RS1 / CR1) ---
ax_truck = fig.add_axes([0.30, 0.900, 0.16, 0.075])
ax_truck.set_facecolor(fig.get_facecolor())
for spine in ax_truck.spines.values():
    spine.set_visible(False)
ax_truck.set_xticks([])
ax_truck.set_yticks([])
radio_truck = mwidgets.RadioButtons(ax_truck, ("RS1", "CR1"),
                                     activecolor="steelblue")
for lbl in radio_truck.labels:
    lbl.set_fontsize(9)

# --- Load status radio (Unloaded / Loaded) ---
ax_load = fig.add_axes([0.49, 0.900, 0.18, 0.075])
ax_load.set_facecolor(fig.get_facecolor())
for spine in ax_load.spines.values():
    spine.set_visible(False)
ax_load.set_xticks([])
ax_load.set_yticks([])
radio_load = mwidgets.RadioButtons(ax_load, ("Unloaded", "Loaded"),
                                    activecolor="darkorange")
for lbl in radio_load.labels:
    lbl.set_fontsize(9)

# --- Start / Stop buttons ---
ax_start  = fig.add_axes([0.06, 0.870, 0.08, 0.040])
ax_stop   = fig.add_axes([0.15, 0.870, 0.08, 0.040])
btn_start = mwidgets.Button(ax_start, "Start", color="#d4edda", hovercolor="#a8d5b5")
btn_stop  = mwidgets.Button(ax_stop,  "Stop",  color="#f8d7da", hovercolor="#f1aeb5")
btn_start.label.set_fontsize(9)
btn_stop.label.set_fontsize(9)

# --- Status text ---
ax_status = fig.add_axes([0.25, 0.862, 0.72, 0.052])
ax_status.axis("off")
status_txt = ax_status.text(0, 0.5, "", va="center", ha="left",
                             fontsize=9, color="gray",
                             transform=ax_status.transAxes)

def set_status(msg, color="gray"):
    status_txt.set_text(msg)
    status_txt.set_color(color)
    fig.canvas.draw_idle()

# ── Four data subplots ────────────────────────────────────────────────────────
positions = [
    (0.06, 0.48, 0.40, 0.34),
    (0.55, 0.48, 0.40, 0.34),
    (0.06, 0.06, 0.40, 0.34),
    (0.55, 0.06, 0.40, 0.34),
]
ax_v, ax_i, ax_p, ax_s = [fig.add_axes(p) for p in positions]

def setup_ax(ax, title, ylabel, color):
    ax.set_title(title, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.tick_params(axis="x", rotation=30, labelsize=7)
    line, = ax.plot([], [], color=color, linewidth=1)
    return line

line_v = setup_ax(ax_v, "Voltage",          "V",  "steelblue")
line_i = setup_ax(ax_i, "Current",          "A",  "tomato")
line_p = setup_ax(ax_p, "Power",            "W",  "darkorange")
line_s = setup_ax(ax_s, "State of Charge",  "%",  "seagreen")

# Keep track of start marker vertical lines so we can remove old ones
start_marker_lines = []

# ── Lock / unlock controls ────────────────────────────────────────────────────
def lock_controls():
    """Disable serial entry and radio buttons while logging is active."""
    serial_box.set_active(False)
    serial_box.color         = "#e8e8e8"
    serial_box.hovercolor    = "#e8e8e8"
    ax_serial.set_facecolor("#e8e8e8")
    for rb in (radio_truck, radio_load):
        for circle in rb.circles:
            circle.set_visible(False)
        for lbl in rb.labels:
            lbl.set_color("gray")

def unlock_controls():
    """Re-enable serial entry and radio buttons after logging stops."""
    serial_box.set_active(True)
    serial_box.color         = "white"
    serial_box.hovercolor    = "#f0f0f0"
    ax_serial.set_facecolor("white")
    for rb in (radio_truck, radio_load):
        for circle in rb.circles:
            circle.set_visible(True)
        for lbl in rb.labels:
            lbl.set_color("black")

# ── Start marker on charts ────────────────────────────────────────────────────
def draw_start_markers(dt):
    """Draw a vertical dashed line at the session start time on all four charts."""
    for line in start_marker_lines:
        try:
            line.remove()
        except Exception:
            pass
    start_marker_lines.clear()
    for ax in (ax_v, ax_i, ax_p, ax_s):
        vl = ax.axvline(dt, color="green", linewidth=1.0,
                        linestyle="--", alpha=0.7, label="Session Start")
        start_marker_lines.append(vl)

# ── Radio callbacks ───────────────────────────────────────────────────────────
def on_truck_select(label):
    global truck_type
    truck_type = label

def on_load_select(label):
    global load_status
    load_status = label

radio_truck.on_clicked(on_truck_select)
radio_load.on_clicked(on_load_select)

# ── Button callbacks ──────────────────────────────────────────────────────────
def on_start(event):
    global logging_active, serial_number, log_start_time
    global last_row_time, last_row_count, watchdog_warned, start_marker_dt

    text = serial_box.text
    valid, msg = validate_serial(text)
    if not valid:
        set_status(f"Invalid serial: {msg}", "crimson")
        return
    if logging_active:
        set_status("Already logging - press Stop first", "crimson")
        return

    clear_log()

    serial_number   = text.strip()
    logging_active  = True
    log_start_time  = datetime.now()
    start_marker_dt = log_start_time
    last_row_time   = datetime.now()
    last_row_count  = 0
    watchdog_warned = False

    lock_controls()
    draw_start_markers(start_marker_dt)

    set_status(
        f"Logging  |  Serial: {serial_number}  |  "
        f"Truck: {truck_type}  |  Load: {load_status}  |  "
        f"Started: {log_start_time.strftime('%H:%M:%S')}",
        "green"
    )

def on_stop(event):
    global logging_active
    if not logging_active:
        set_status("Not currently logging", "crimson")
        return

    # ── Minimum session duration warning ─────────────────────────────────────
    elapsed = (datetime.now() - log_start_time).total_seconds()
    if elapsed < MIN_SESSION_SECONDS:
        answer = _confirm_short_session(elapsed)
        if not answer:
            set_status(
                f"Logging  |  Serial: {serial_number}  |  "
                f"Truck: {truck_type}  |  Load: {load_status}  |  "
                f"Started: {log_start_time.strftime('%H:%M:%S')}",
                "green"
            )
            return

    logging_active = False
    unlock_controls()

    # ── Session summary popup ─────────────────────────────────────────────────
    ts, v, i, p, s = read_data()
    if v:
        _show_summary(elapsed, v, i, p, s)

    save_csv()

def _confirm_short_session(elapsed):
    """Return True if the operator confirms saving a very short session."""
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    answer = messagebox.askyesno(
        "Short Session Warning",
        f"The session ran for only {elapsed:.0f} seconds "
        f"(minimum recommended: {MIN_SESSION_SECONDS}s).\n\n"
        "The recorded data may not be meaningful.\n\n"
        "Save anyway?"
    )
    root.destroy()
    return answer

def _show_summary(elapsed, v, i, p, s):
    """Display a session summary popup with min / max / average per metric."""
    import tkinter as tk
    from tkinter import messagebox

    def fmt(data):
        return f"min {min(data):.3f}   avg {sum(data)/len(data):.3f}   max {max(data):.3f}"

    mins, secs = divmod(int(elapsed), 60)
    summary = (
        f"Session Duration:   {mins}m {secs}s\n"
        f"Data Points:        {len(v)}\n"
        "\n"
        f"Voltage  (V):   {fmt(v)}\n"
        f"Current  (A):   {fmt(i)}\n"
        f"Power    (W):   {fmt(p)}\n"
        f"SOC      (%):   {fmt(s)}\n"
    )
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Session Summary", summary)
    root.destroy()

# ── Save CSV ──────────────────────────────────────────────────────────────────
def save_csv():
    ts         = log_start_time.strftime("%Y-%m-%d_%H-%M")
    filename   = f"{truck_type}_{serial_number}_{load_status}_{ts}.csv"
    output_dir = OUTPUT_ROOT / truck_type / serial_number / load_status / ts

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        dest = output_dir / filename
        shutil.copy2(CSV_FILE, dest)
        set_status(f"Saved: {dest}", "steelblue")
        print(f"Saved: {dest}")
    except Exception as e:
        set_status(f"Save failed: {e}", "crimson")
        print(f"Save error: {e}")

btn_start.on_clicked(on_start)
btn_stop.on_clicked(on_stop)

# ── Animation loop ────────────────────────────────────────────────────────────
def update(_frame):
    global last_row_time, last_row_count, watchdog_warned

    if not logging_active:
        return

    # ── Watchdog — detect if logger has stopped feeding data ─────────────────
    current_count = get_raw_row_count()
    if current_count > last_row_count:
        last_row_count = current_count
        last_row_time  = datetime.now()
        if watchdog_warned:
            # Data has resumed — clear the warning
            watchdog_warned = False
            set_status(
                f"Logging  |  Serial: {serial_number}  |  "
                f"Truck: {truck_type}  |  Load: {load_status}  |  "
                f"Started: {log_start_time.strftime('%H:%M:%S')}",
                "green"
            )
    else:
        gap = (datetime.now() - last_row_time).total_seconds()
        if gap >= WATCHDOG_TIMEOUT_SEC and not watchdog_warned:
            watchdog_warned = True
            set_status(
                f"WARNING: No new data for {gap:.0f}s — "
                "check logger is running and device is connected",
                "crimson"
            )

    # ── Update charts ─────────────────────────────────────────────────────────
    ts, v, i, p, s = read_data()
    if not ts:
        return

    for line, data in [(line_v, v), (line_i, i), (line_p, p), (line_s, s)]:
        line.set_data(ts, data)
        ax = line.axes
        ax.relim()
        ax.autoscale_view()

    fig.canvas.draw_idle()

ani = FuncAnimation(fig, update, interval=1000, cache_frame_data=False)

set_status("Select truck & load status, enter serial number, then press Start.")
plt.show()
