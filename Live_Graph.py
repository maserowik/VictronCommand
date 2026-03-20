import csv
import time
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

CSV_FILE = "victron_log.csv"

timestamps = []
voltage = []
current = []
power = []
soc = []

def read_data():
    try:
        with open(CSV_FILE, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            timestamps.clear()
            voltage.clear()
            current.clear()
            power.clear()
            soc.clear()

            for row in rows[-100:]:  # last 100 points
                timestamps.append(row["Timestamp"])
                voltage.append(float(row["Voltage"]))
                current.append(float(row["Current"]))
                power.append(float(row["Power"]))
                soc.append(float(row["SOC"]))
    except Exception as e:
        print("Read error:", e)

def update(frame):
    read_data()

    plt.clf()

    plt.subplot(2, 2, 1)
    plt.plot(voltage)
    plt.title("Voltage")

    plt.subplot(2, 2, 2)
    plt.plot(current)
    plt.title("Current")

    plt.subplot(2, 2, 3)
    plt.plot(power)
    plt.title("Power")

    plt.subplot(2, 2, 4)
    plt.plot(soc)
    plt.title("SOC")

    plt.tight_layout()

ani = FuncAnimation(plt.gcf(), update, interval=1000)

plt.show()