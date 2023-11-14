# launcher_script.py
import subprocess

num_charge_points = 5 # The number of charge points to be created.

# Loop to create multiple terminal windows.
for i in range(num_charge_points):
    cp_id = f"CP_{i+1}"
    subprocess.run(f'start cmd /k python charge_point.py {cp_id}', shell=True)
