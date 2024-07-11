import os
import subprocess
import sys
import time

#subprocess.Popen(['source myenv/bin/activate'])
#subprocess.run(['python3', 'run_command.py', 'stop'])
#time.sleep(3)
process = subprocess.run(['python3', 'run_command.py', 'cp', 'Client_Test/client_Phase1_GoLeft.py', '1'])
print('-------------')
print(process)
print('-------------')
time.sleep(3)
subprocess.run(['python3', 'run_command.py', 'start', '1'])
time.sleep(5)
process = subprocess.run(['python3', 'run_command.py', 'cp', 'Client_Test/client_Phase1_GoRight.py', '1'])
time.sleep(3)
print('-------------')
print(process)
print('-------------')
subprocess.run(['python3', 'run_command.py', 'start', '1'])
 
