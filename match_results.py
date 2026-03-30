import pandas as pd
import matplotlib.pyplot as plt
import re

log_file = "your_log_file.txt"
csv_file = "your_data_file.csv"

# 1. Parse the task kick-off times from the text log file
task_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \| .*? \[TASK: (.*?)\]')
task_starts = {}

with open(log_file, 'r') as f:
    for line in f:
        match = task_pattern.search(line)
        if match:
            ts_str, task_name = match.groups()
            # We only capture the first occurrence (kick-off) of each task
            if task_name not in task_starts:
                task_starts[task_name] = pd.to_datetime(ts_str, format="%Y-%m-%d %H:%M:%S,%f")

df_tasks = pd.DataFrame(list(task_starts.items()), columns=['Task', 'Start_Time'])

# 2. Load the CSV data
df_csv = pd.read_csv(csv_file, parse_dates=['Timestamp'])

# 3. Plot the CSV streams
plt.figure(figsize=(14, 7))
plt.plot(df_csv['Timestamp'], df_csv['Voltage'], label='Voltage (V)', color='blue', alpha=0.7)
plt.plot(df_csv['Timestamp'], df_csv['Current'], label='Current (A)', color='red', alpha=0.7)
plt.plot(df_csv['Timestamp'], df_csv['Power'] / 10, label='Power (W/10)', color='green', alpha=0.7)

# 4. Overlay the vertical lines for each Task Kick-off
for _, row in df_tasks.iterrows():
    t_start = row['Start_Time']
    
    # Only plot if the task starts within the timeframe of the CSV data
    if df_csv['Timestamp'].min() <= t_start <= df_csv['Timestamp'].max():
        plt.axvline(x=t_start, color='black', linestyle='--', alpha=0.5)
        # Add the task name near the top of the line
        plt.text(t_start, df_csv['Voltage'].max(), row['Task'], 
                 rotation=90, verticalalignment='top', horizontalalignment='right', fontsize=9)

plt.title('System Metrics Over Time with Task Execution Events')
plt.xlabel('Timestamp')
plt.ylabel('Sensor Values')
plt.legend(loc='upper right')
plt.grid(True)
plt.tight_layout()

# Save the resulting plot
plt.savefig('Task_Matching_Overlay.png')
plt.show()