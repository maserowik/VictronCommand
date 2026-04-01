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
    
# Print the clean file name immediately after selection
print(f" -> Selected Log: {os.path.basename(log_file)}\n")

# 3. Prompt user to select the CSV File
print("Waiting for CSV file selection...")
csv_file = filedialog.askopenfilename(
    title="Select the Victron CSV Data File",
    filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
)
if not csv_file:
    print("No CSV file selected. Exiting.")
    sys.exit()

# Print the clean file name immediately after selection
print(f" -> Selected CSV: {os.path.basename(csv_file)}\n")

print("Generating plot...")

# 4. Extract Meta Data from the CSV Filename
base_name = os.path.basename(csv_file).replace('.csv', '')
parts = base_name.split('_')
if len(parts) >= 4:
    truck_type = parts[0]
    serial_num = parts[1]
    load_status = parts[2]
    date_time = f"{parts[3]} {parts[4].replace('-', ':')}"
else:
    truck_type, serial_num, load_status, date_time = "N/A", "N/A", "N/A", "N/A"

# 5. Parse ALL physical strokes (Init, Outward, Return) from the log
tasks_and_actions = []
current_task = "Unknown"
cmd_counter = 0

with open(log_file, 'r') as f:
    for line in f:
        # A. Catch when a new Task Script starts
        match_task = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \| .*? \| RunTask \| Running task (.*\.yml)', line)
        if match_task:
            current_task = match_task.group(2).replace('RS1_', '').replace('.yml', '')
            cmd_counter = 0  
        
        # B. Catch the hydraulic commands (the physical movement causing dips)
        match_cmd = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) .*? \[HYD_COMMAND\] axis: (.*?) --> (.*)', line)
        if match_cmd:
            ts_str, axis, val = match_cmd.groups()
            
            # Ignore the "Process" and "initialize" scripts
            if "Process" not in current_task and "initialize" not in current_task:
                cmd_counter += 1
                
                # Cmd 1 is Init, Cmd 2 is Outward, Cmd 3 is Return
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

df_primary_moves = pd.DataFrame(tasks_and_actions)

# 6. Load the CSV data and Calculate Summary Stats
df_csv = pd.read_csv(csv_file, parse_dates=['Timestamp'])

elapsed_seconds = (df_csv['Timestamp'].max() - df_csv['Timestamp'].min()).total_seconds()
mins, secs = divmod(int(elapsed_seconds), 60)

def fmt(data):
    # Enforces an exact character width (8.2f) so decimals and negative signs form perfect columns
    return f"Min: {data.min():>8.2f}   |   Avg: {data.mean():>8.2f}   |   Max: {data.max():>8.2f}"

# 7. Format the summary text into strict, left-justified columns
summary_text = (
    f"TEST RUN DETAILS                  SESSION SUMMARY\n"
    f"──────────────────────────────    ────────────────────────────────────────────────────────────────────────\n"
    f"Truck:      {truck_type:<18}    Duration:    {int(mins)}m {int(secs)}s\n"
    f"Serial:     {serial_num:<18}    Voltage (V): {fmt(df_csv['Voltage'])}\n"
    f"Load:       {load_status:<18}    Current (A): {fmt(df_csv['Current'])}\n"
    f"Date/Time:  {date_time:<18}    Power (W):   {fmt(df_csv['Power'])}\n"
    f"                                  SOC (%):     {fmt(df_csv['SOC'])}\n"
)

# 8. Plot the CSV streams
fig, ax = plt.subplots(figsize=(16, 10))
plt.subplots_adjust(bottom=0.28) # Lifts the bottom of the graph up to make room for the text box

ax.plot(df_csv['Timestamp'], df_csv['Voltage'], label='Voltage (V)', color='blue', linewidth=1.5)
ax.plot(df_csv['Timestamp'], df_csv['Current'], label='Current (A)', color='red', linewidth=1.5)
ax.plot(df_csv['Timestamp'], df_csv['Power'] / 10, label='Power (W/10)', color='green', linewidth=1.5)

# 9. Overlay the vertical lines for every physical stroke
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
            
            ax.axvline(x=t_start, color='black', linestyle=line_style, alpha=line_alpha, linewidth=1.2)
            
            y_pos_fraction = 0.95 - (i % 5) * 0.15 
            
            ax.text(t_start, y_pos_fraction, f" {clean_name}", 
                    rotation=90, verticalalignment='top', fontsize=9, fontweight='bold', 
                    color='black', bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=2),
                    transform=ax.get_xaxis_transform()) 

# Set labels and title
ax.set_title(f"Victron Sensor Data Overview: {truck_type} ({serial_num})", fontsize=15, fontweight='bold', pad=15)
ax.set_ylabel('Sensor Values', fontsize=12)

ax.legend(loc='upper right') 
ax.grid(True, linestyle=':', alpha=0.7)

# Format the X-axis
ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.xticks(rotation=45)

# 10. Add the Summary Text Box - LEFT JUSTIFIED
# x=0.08 aligns it nicely with the left side of the graph's plotting area
fig.text(0.08, 0.04, summary_text, fontsize=11, family='monospace', 
         horizontalalignment='left', verticalalignment='bottom', 
         bbox=dict(facecolor='#f8f9fa', edgecolor='#dee2e6', boxstyle='round,pad=1'))

# Show the resulting plot directly to the user
plt.show()