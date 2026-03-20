import serial
import csv
from datetime import datetime
import platform

def get_port():
    if platform.system() == "Windows":
        return "COM15"
    else:
        return "/dev/ttyUSB0"

PORT = get_port()
BAUD = 19200

print(f"Running on: {platform.system()}")
print(f"Using port: {PORT}")

ser = serial.Serial(PORT, BAUD, timeout=1)

data = {}

def is_valid(data):
    return (
        "V" in data and
        "I" in data and
        "P" in data and
        "SOC" in data
    )

with open("victron_log.csv", "a", newline="") as f:
    writer = csv.writer(f)

    if f.tell() == 0:
        writer.writerow(["Timestamp", "Voltage", "Current", "Power", "SOC"])

    print("Logging started... Press CTRL+C to stop.")

    while True:
        line = ser.readline().decode(errors="ignore").strip()

        if not line:
            continue

        parts = line.split("\t")

        if len(parts) == 2:
            key, value = parts
            data[key] = value

        if "Checksum" in line:

            if not is_valid(data):
                data = {}
                continue

            try:
                timestamp = datetime.now()

                voltage = float(data["V"]) / 1000
                current = float(data["I"]) / 1000
                power = float(data["P"])
                soc = float(data["SOC"]) / 10

                # Filter obviously bad data
                if voltage <= 0:
                    data = {}
                    continue

                writer.writerow([timestamp, voltage, current, power, soc])
                f.flush()

                print(timestamp, voltage, current, power, soc)

            except Exception as e:
                print("Parse error:", e)

            data = {}
