import serial.tools.list_ports
import time
import serial
import sys
#from apscheduler.schedulers.background import BackgroundScheduler

msg = bytes([])
NOTIFY_NEW_SW = bytes([1, 120, 0, 0, 0, 0, 0, 0])
RESPONSE_CONFIMATION = bytes([1, 121, 0, 0, 0, 0])
REQUEST_FLASH_SW = bytes([1, 122, 0, 0, 0, 111, 0, 0])
FLASH_SUCCESS_YET = bytes([1, 123, 0, 0, 0, 0, 0, 0])

flash_Success = False


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


portName = getPort()
print(portName)

try:
    ser = serial.Serial(port=portName, baudrate=115200, parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS, timeout=1)
    print("Open successfully")
except:
    print("Can not open the port")


# Send function
def flash_SW():
    print("Flash SW for FOTA Client")
    # if flash_Success == True:
    #     pass
    # else:  # flash the old SW when meet error
    #     pass
    # pass


def notify_New_SW():
    message = NOTIFY_NEW_SW
    print('--------------------------')
    ser.write(message)
    print(message)
    print('--------------------------')
    time.sleep(0.01)

def send_Msg():
    # create msg
    pass
    # message = NOTIFY_NEW_SW
    # print('--------------------------')
    # ser.write(message)
    # print(message)
    # print('--------------------------')
    # time.sleep(0.01)

def classify_msg(msg):
    if msg == RESPONSE_CONFIMATION:
        print("Send function has been confirmed")
    elif msg == REQUEST_FLASH_SW:
        flash_SW()

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

# scheduler = BackgroundScheduler()
# scheduler.add_job(receive_message, 'interval', seconds=0.01)
# scheduler.start()

# message = bytes([1, 120, 0, 0, 0, 111, 0, 0])
# print('--------------------------')
# ser.write(message)
# print(message)
# print('--------------------------')
# time.sleep(0.01)

notify_New_SW()

while True:
    receive_message()
    time.sleep(0.01)



