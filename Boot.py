import os
import subprocess
import sys
import time
from apscheduler.schedulers.background import BackgroundScheduler


# def job():
#     print(f"New SW running at: {time.time()}")


# scheduler = BackgroundScheduler()
# scheduler.add_job(job, 'interval', seconds=2)
# scheduler.start()


print()
print("================================")
print("Bootloader is running...")


APP = 'App.py'
BOOT = 'Boot.py'
CLIENT = 'FOTA_Client.py'

NEW_BOOT = 'FOTA_Master_Boot_new.py'
NEW_APP = 'FOTA_Master_App_new.py'
NEW_CLIENT = 'FOTA_Client_new.py'

BACKUP_BOOT = 'FOTA_Master_Boot_backup.py'
BACKUP_APP = 'FOTA_Master_App_backup.py'
BACKUP_CLIENT = 'FOTA_Client_backup.py'


def flashClient():
    #FIX
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


def main_run():
    user_input = sys.argv[1]

    if user_input == "runningApp":
        print("Run App")
        subprocess.Popen(['python', APP])

    elif user_input == "activation_boot":
        print("Activation new boot")
        os.rename(BOOT, BACKUP_BOOT)
        os.rename(NEW_BOOT, BOOT)
        subprocess.Popen(['python', BOOT, 'runningApp'])

    elif user_input == "rollback_boot":
        print("Rollback boot")
        os.rename(BOOT, NEW_BOOT)
        os.rename(BACKUP_BOOT, BOOT)
        subprocess.Popen(['python', BOOT, 'runningApp'])

    elif user_input == "activationApp":
        print("Activation App")
        os.rename(APP, BACKUP_APP)
        os.rename(NEW_APP, APP)
        subprocess.Popen(['python', APP])

    elif user_input == "rollbackApp":
        print("Rollback app")
        os.rename(APP, NEW_APP)
        os.rename(BACKUP_APP, APP)
        subprocess.Popen(['python', APP])

    else:
        print("Wrong")



if __name__ == '__main__':
    main_run()
    print("Bootloader finished.")
    exit()
