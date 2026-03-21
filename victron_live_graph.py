import csv
import shutil
import platform
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.widgets as mwidgets
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

# ── State ─────────────────────────────────────────────────────────────────────
logging_active = False
serial_number  = ""
truck_type     = "RS1"
load_status    = "Unloaded"
log_start_time = None

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
    text = serial_box.text
    valid, msg = validate_serial(text)
    if not valid:
        set_status(f"Invalid serial: {msg}", "crimson")
        return
    if logging_active:
        set_status("Already logging - press Stop first", "crimson")
        return

    clear_log()

    serial_number  = text.strip()
    logging_active = True
    log_start_time = datetime.now()
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
    logging_active = False
    save_csv()

def save_csv():
    """
    Mirror gui.py output folder structure:
        {OUTPUT_ROOT}/{truck}/{serial}/{load}/{timestamp}/
        {TruckType}_{SerialNumber}_{LoadStatus}_{YYYY-MM-DD_HH-MM}.csv

    Example:
        C:\\Users\\mserowik\\Documents\\VictronConnect\\test_results\\
            RS1\\9876567894\\Unloaded\\2026-03-20_14-43\\
                RS1_9876567894_Unloaded_2026-03-20_14-43.csv
    """
    ts        = log_start_time.strftime("%Y-%m-%d_%H-%M")
    filename  = f"{truck_type}_{serial_number}_{load_status}_{ts}.csv"
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
    if not logging_active:
        return
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
