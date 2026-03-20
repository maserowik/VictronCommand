import csv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.animation import FuncAnimation
from datetime import datetime

CSV_FILE = "victron_log.csv"

def read_data():
    timestamps, voltage, current, power, soc = [], [], [], [], []
    try:
        with open(CSV_FILE, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        for row in rows[-200:]:  # last 200 raw rows
            v = float(row["Voltage"])
            if v <= 0:            # skip zero/bad rows
                continue
            timestamps.append(datetime.fromisoformat(row["Timestamp"]))
            voltage.append(v)
            current.append(float(row["Current"]))
            power.append(float(row["Power"]))
            soc.append(float(row["SOC"]))
    except Exception as e:
        print("Read error:", e)
    return timestamps, voltage, current, power, soc

fig, axes = plt.subplots(2, 2, figsize=(12, 7))
fig.suptitle("Victron Battery Monitor", fontsize=13)
ax_v, ax_i, ax_p, ax_s = axes.flat

def setup_ax(ax, title, ylabel, color):
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.tick_params(axis="x", rotation=30, labelsize=7)
    line, = ax.plot([], [], color=color, linewidth=1)
    return line

line_v = setup_ax(ax_v, "Voltage",        "V",    "steelblue")
line_i = setup_ax(ax_i, "Current",        "A",    "tomato")
line_p = setup_ax(ax_p, "Power",          "W",    "darkorange")
line_s = setup_ax(ax_s, "State of Charge", "%",   "seagreen")

def update(_frame):
    ts, v, i, p, s = read_data()
    if not ts:
        return

    for line, data in [(line_v, v), (line_i, i), (line_p, p), (line_s, s)]:
        line.set_data(ts, data)
        ax = line.axes
        ax.relim()
        ax.autoscale_view()

    fig.autofmt_xdate()

ani = FuncAnimation(fig, update, interval=1000, cache_frame_data=False)
plt.tight_layout()
plt.show()