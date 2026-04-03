import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import re
import tkinter as tk
from tkinter import filedialog
import sys
import os

# 1. Initialize tkinter and hide the main background window
root = tk.Tk()
root.withdraw()

# 2. Prompt user to select the Log File
print("Waiting for log file selection...")
log_file = filedialog.askopenfilename(
    title="Select the Test Run Log File (.txt)",
    filetypes=[("Text/Log Files", "*.txt *.log"), ("All Files", "*.*")]
)
if not log_file:
    print("No log file selected. Exiting.")
    sys.exit()
print(f" -> Selected Log: {os.path.basename(log_file)}\n")

# 3. Prompt user to select the Victron CSV File
print("Waiting for CSV file selection...")
csv_file = filedialog.askopenfilename(
    title="Select the Victron CSV Data File",
    filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
)
if not csv_file:
    print("No CSV file selected. Exiting.")
    sys.exit()
print(f" -> Selected Victron CSV: {os.path.basename(csv_file)}\n")

print("Generating perfectly smooth velocity profile...")

# 4. Extract Meta Data from the Victron CSV Filename
base_name = os.path.basename(csv_file).replace('.csv', '')
parts = base_name.split('_')
if len(parts) >= 4:
    truck_type = parts[0]
    serial_num = parts[1]
    load_status = parts[2]
    date_time = f"{parts[3]} {parts[4].replace('-', ':')}"
else:
    truck_type, serial_num, load_status, date_time = "N/A", "N/A", "N/A", "N/A"

# 5. Parse text log file for the vertical physical stroke lines and continuous velocity
tasks_and_actions = []
velocity_data = []
current_task = "Unknown"
cmd_counter = 0

# Regex to catch the embedded CSV rows containing velocity (Group 1: Time, Group 2: Velocity)
regex_vel = re.compile(r'^(\d{10}\.\d+),[-0-9\.]+,[-0-9\.]+,[-0-9\.]+,([-0-9\.]+),')

with open(log_file, 'r') as f:
    for line in f:
        line = line.strip()
        
        # A. Catch when a new Task Script starts
        match_task = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \| .*? \| RunTask \| Running task (.*\.yml)', line)
        if match_task:
            current_task = match_task.group(2).replace('RS1_', '').replace('.yml', '')
            cmd_counter = 0  
        
        # B. Catch the hydraulic commands for the vertical task lines
        match_cmd = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) .*? \[HYD_COMMAND\] axis: (.*?) --> (.*)', line)
        if match_cmd:
            ts_str, axis, val = match_cmd.groups()
            if "Process" not in current_task and "initialize" not in current_task:
                cmd_counter += 1
                if cmd_counter == 1:
                    label = f"{current_task} (Init)"
                elif cmd_counter == 2:
                    label = f"{current_task} (Outward)"
                elif cmd_counter == 3:
                    label = f"{current_task} (Return)"
                else:
                    label = f"{current_task} (Extra)"
                    
                tasks_and_actions.append({
                    "time": pd.to_datetime(ts_str, format="%Y-%m-%d %H:%M:%S,%f"), 
                    "task_label": label
                })

        # C. Catch continuous embedded velocity data
        match_vel = regex_vel.match(line)
        if match_vel:
            unix_ts = float(match_vel.group(1))
            est_vel = float(match_vel.group(2))
            velocity_data.append({"Time_s": unix_ts, "Velocity": est_vel})

df_primary_moves = pd.DataFrame(tasks_and_actions)

# Process Velocity Data
df_vel = pd.DataFrame(velocity_data)
if not df_vel.empty:
    # Convert UNIX to readable Eastern Time
    df_vel['Timestamp'] = pd.to_datetime(df_vel['Time_s'], unit='s').dt.tz_localize('UTC').dt.tz_convert('America/New_York').dt.tz_localize(None)
    df_vel = df_vel.drop_duplicates(subset=['Timestamp']).sort_values('Timestamp')
    
    # THE MAGIC FIX: Take the absolute value (Speed) so all lines point UP as positive hills
    df_vel['Speed'] = df_vel['Velocity'].abs()
    
    # Smooth it out to create that perfect ramp-up / ramp-down curve
    df_vel['Smooth_Speed'] = df_vel['Speed'].rolling(window=8, min_periods=1, center=True).mean()

# 6. Load the Victron CSV data and Calculate Summary Stats
df_csv = pd.read_csv(csv_file, parse_dates=['Timestamp'])
elapsed_seconds = (df_csv['Timestamp'].max() - df_csv['Timestamp'].min()).total_seconds()
mins, secs = divmod(int(elapsed_seconds), 60)

def fmt(data):
    return f"Min: {data.min():>8.2f}   |   Avg: {data.mean():>8.2f}   |   Max: {data.max():>8.2f}"

# Format the summary text
summary_text = (
    f"TEST RUN DETAILS                  SESSION SUMMARY\n"
    f"──────────────────────────────    ────────────────────────────────────────────────────────────────────────\n"
    f"Truck:      {truck_type:<18}    Duration:    {int(mins)}m {int(secs)}s\n"
    f"Serial:     {serial_num:<18}    Voltage (V): {fmt(df_csv['Voltage'])}\n"
    f"Load:       {load_status:<18}    Current (A): {fmt(df_csv['Current'])}\n"
    f"Date/Time:  {date_time:<18}    Power (W/10):{fmt(df_csv['Power'] / 10)}\n"
    f"                                  SOC (%):     {fmt(df_csv['SOC'])}\n"
)

# 7. Plot the CSV streams
fig, ax1 = plt.subplots(figsize=(16, 10))
plt.subplots_adjust(bottom=0.28, right=0.92) 

# Primary Y-Axis (Left) for Electrical Data
line1 = ax1.plot(df_csv['Timestamp'], df_csv['Voltage'], label='Voltage (V)', color='blue', linewidth=1.5)
line2 = ax1.plot(df_csv['Timestamp'], df_csv['Current'], label='Current (A)', color='red', linewidth=1.5)
line3 = ax1.plot(df_csv['Timestamp'], df_csv['Power'] / 10, label='Power (W/10)', color='green', linewidth=1.5)

ax1.set_ylabel('Electrical Sensor Values', fontsize=12, color='black', fontweight='bold')
ax1.tick_params(axis='y', labelcolor='black')
lines = line1 + line2 + line3

# Secondary Y-Axis (Right) for the Velocity Profile (Hills)
if not df_vel.empty:
    ax2 = ax1.twinx() 
    
    # Plot the smooth line (Removed the shading/fill_between)
    line4 = ax2.plot(df_vel['Timestamp'], df_vel['Smooth_Speed'], 
                     label='Motion Profile (Speed mm/s)', color='purple', linewidth=2.0)
    
    ax2.set_ylabel('Motion Speed Profile (mm/s)', fontsize=12, color='purple', fontweight='bold', labelpad=15)
    ax2.tick_params(axis='y', labelcolor='purple')
    
    # Force the Y-axis to start at 0 so the "speed bumps" touch the bottom naturally
    ax2.set_ylim(bottom=0)
    lines += line4 

# 8. Overlay the vertical lines for every physical stroke
if not df_primary_moves.empty:
    for i, row in df_primary_moves.iterrows():
        t_start = row['time']
        clean_name = row['task_label']
        
        if df_csv['Timestamp'].min() <= t_start <= df_csv['Timestamp'].max():
            if 'Init' in clean_name:
                line_style, line_alpha = ':', 0.5
            elif 'Outward' in clean_name:
                line_style, line_alpha = '-', 0.8
            else:
                line_style, line_alpha = '--', 0.6
            
            ax1.axvline(x=t_start, color='black', linestyle=line_style, alpha=line_alpha, linewidth=1.2)
            y_pos_fraction = 0.95 - (i % 5) * 0.15 
            
            ax1.text(t_start, y_pos_fraction, f" {clean_name}", 
                    rotation=90, verticalalignment='top', fontsize=9, fontweight='bold', 
                    color='black', bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=2),
                    transform=ax1.get_xaxis_transform()) 

# Set labels and title
ax1.set_title(f"Victron Electrical Draw & Motion Profile: {truck_type} ({serial_num})", fontsize=15, fontweight='bold', pad=15)

# Legend consolidation - Moved to LOWER RIGHT, just under the graph itself!
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='upper right', bbox_to_anchor=(1.0, -0.12), ncol=2) 

ax1.grid(True, linestyle=':', alpha=0.7)

# Format the X-axis
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
for label in ax1.get_xticklabels():
    label.set_rotation(45)

# 9. Add the Summary Text Box
fig.text(0.08, 0.04, summary_text, fontsize=11, family='monospace', 
         horizontalalignment='left', verticalalignment='bottom', 
         bbox=dict(facecolor='#f8f9fa', edgecolor='#dee2e6', boxstyle='round,pad=1'))

# Show the resulting plot directly to the user
plt.show()