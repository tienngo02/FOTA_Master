import subprocess
import time
# from apscheduler.schedulers.background import BackgroundScheduler
import serial.tools.list_ports
import serial


PYTHON = 'python3.12'
APP = 'App.py'
BOOT = 'Boot.py'
CLIENT = 'FOTA_Client.py'

NOTIFY_NEW_SW = bytes([1, 120, 0, 0, 0, 0, 0, 0])
RESPONSE_CONFIRMATION = bytes([1, 121, 0, 0, 0, 0])
REQUEST_FLASH_SW = bytes([1, 122, 0, 0, 0, 111, 0, 0])
FLASH_SUCCESS_YET = bytes([1, 123, 0, 0, 0, 0, 0, 0])


def getPort():
    ports = serial.tools.list_ports.comports()
    N = len(ports)
    commPort = "None"

    for i in range(0, N):
        port = ports[i]
        strPort = str(port)
        print(strPort)
        # if "S" in strPort:
        splitPort = strPort.split(" ")
        commPort = (splitPort[0])
    return commPort


MAX_RETRIES = 5
RETRY_DELAY = 3


def connect_serial_port():
    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            ser = serial.Serial(port=getPort(), baudrate=115200, parity=serial.PARITY_NONE,
                                stopbits=serial.STOPBITS_ONE,
                                bytesize=serial.EIGHTBITS, timeout=1)
            print("Open successfully")
            return ser

        except serial.SerialException as e:
            attempt += 1
            print(f"Attempt {attempt} failed")
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                print("Can not open the port.")
                return None


ser = connect_serial_port()


def flash_SW():
    print("Flash SW for FOTA Client")
    subprocess.Popen([PYTHON, BOOT, 'activate_Client'])
    exit()


def notify_New_SW():
    message = NOTIFY_NEW_SW
    print('--------------------------')
    ser.write(message)
    print(message)
    print('--------------------------')
    time.sleep(0.01)


def classify_msg(msg):
    if msg == RESPONSE_CONFIRMATION:
        print("Send function has been confirmed")
    elif msg == REQUEST_FLASH_SW:
        flash_SW()
    else:
        print('Invalid message')


def receive_message():
    bytesToRead = ser.inWaiting()
    if bytesToRead > 0:
        start_byte = ser.read(1)
        if start_byte == b'#':
            print('Start byte receive')
            data_bytes = ser.read(8)
            message = [b for b in data_bytes]
            print('Next 8 bytes:', message)
            classify_msg(message)


time.sleep(1)
byteRead = ser.inWaiting()
if byteRead > 0:
    data = ser.read(byteRead)
    data_value = [b for b in data]
    print(data)


notify_New_SW()

while True:
    receive_message()
    time.sleep(0.01)