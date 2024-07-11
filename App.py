import subprocess
import time
import json
from apscheduler.schedulers.background import BackgroundScheduler

import ftplib
import ssl
import os
import io
import sys
import time
import paho.mqtt.client as mqtt
from Security import Security

import serial.tools.list_ports
import serial


JSONFILE = 'Version_information_file.json'

APP = 'App.py'
BOOT = 'Boot.py'
CLIENT = 'FOTA_Client.py'
arg = "activation_boot"

print("Old SW is running...")


# Server communication and security
#=======================================================

# new_SW_topic = '/SW/Jetson/#'

File_path = os.path.abspath(__file__)
Folder_Dir = os.path.dirname(File_path)
sys.path.append(Folder_Dir)

class MyFTP_TLS(ftplib.FTP_TLS):
    """Explicit FTPS, with shared TLS session"""
    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn,
                                            server_hostname=self.host,
                                            session=self.sock.session)  # this is the fix
        return conn, size
    

class Cloud_COM:
    def __init__(self) -> None:
        self.host = 'begvn.home'
        self.FTPport = 21
        self.MQTTPort = 8883
        self.MQTTProtocol = "tcp"
        self.user = 'user1'
        self.passwd = '123456'
        self.acct = 'Normal'
        self.ca_cert_path = Folder_Dir + '/certs/ca.crt'
        print(self.ca_cert_path)
        self.ssl_context = ssl.create_default_context(cafile=self.ca_cert_path)
        self.ftps = MyFTP_TLS(context=self.ssl_context)
        # self.ftps.context
        self.ftps.set_debuglevel(1)
        self.MQTTclient = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                    protocol=mqtt.MQTTv5,
                    transport=self.MQTTProtocol)
        self.MQTTclient.tls_set(ca_certs=self.ca_cert_path)
        self.isFTPConnected = False
        self.isMQTTConnected = False
        self.NewMasterApp = False
        self.NewMasterBoot = False
        self.NewClient = False
        # self.isReceiveResponse = False

    def __del__(self):
        self.FTP_Disconnect()

    def FTP_Connect(self):
        try:
            self.ftps.connect(self.host, self.FTPport)

            # print(self.ftps.getwelcome())
            # print(self.ftps.sock)

            self.ftps.auth()

            self.ftps.login(self.user, self.passwd, self.acct)

            self.ftps.set_pasv(True)
            self.ftps.prot_p()
            self.ftps.cwd("SW")
            self.isFTPConnected = True
        except:
            print("FTP Connect failed")
            return

    def FTP_Disconnect(self):
        self.ftps.quit()
        self.isFTPConnected = False

    def MQTT_Connect(self):
        self.MQTTclient.username_pw_set(self.user, self.passwd)
        self.MQTTclient.connect(self.host,self.MQTTPort)
        self.MQTTclient.loop_start()
        self.MQTTclient.on_message = self.MQTT_On_message
        self.isMQTTConnected = True

    def MQTT_Disconnect(self):
        # self.MQTTclient.loop_stop()
        self.MQTTclient.disconnect()
        self.isMQTTConnected = False

    def MQTT_On_message(self,client, userdata, message):
        print(message.payload.decode())
        payload = message.payload.decode()
        topic = message.topic
        if topic == "SW/Jetson/FOTA_Master_App" or topic == "SW/Jetson/FOTA_Master_Boot" or topic == "SW/Jetson/FOTA_Client":
            self.NotifiSW_CB(self,payload)


    def startWaitNewSW(self,NewSWCB):
        if self.isFTPConnected == False:
            self.FTP_Connect()
        if self.isMQTTConnected == False:
            self.MQTT_Connect()
        self.NotifiSW_CB = NewSWCB
        self.MQTTclient.subscribe("SW/Jetson/#",qos=2)
    
    def GetNewSW(self,SWname):
        try:
            Unverified_SW_io = io.BytesIO()
            self.ftps.retrbinary('RETR ' + SWname,Unverified_SW_io.write)
            Unverified_SW_io.seek(0)
            Unverified_SW = Unverified_SW_io.read()
            print(len(Unverified_SW_io.read()))
            Verified_SW = Security.Verify_Decrypt(Unverified_SW)
            return Verified_SW
        except Exception as e:
            print("Failed to get new SW, e: ",e)
            return 


def NewSW_CB(Cloud,Swname):
    print("CB: ",Swname)
    global New_SW
    New_SW = Cloud.GetNewSW(Swname)
    splitName = Swname.split('_v')
    file_name = splitName[0]
    file_name += '_new.py'
    with open(file_name, "wb") as file:
        file.write(New_SW)

#=======================================================



# Version file control
#=======================================================
class version_file_control:
    data = None

    def __init__(self):
        with open(JSONFILE, 'r') as file:
            self.data = json.load(file)
         
    def read_2latest_version(self, file_name):
        return self.data[file_name]['running'], self.data[file_name]['non-running']
        
    def update_version(self):
        return 


# UART Communication
#=========================================================

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
    #run boot to flash SW for Client
    #todo


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

# notify_New_SW()

# while True:
#     receive_message()
#     time.sleep(0.01)


#=========================================================


if __name__ == '__main__':
    print()
    print("Path: ",sys.path)
    Cloud = Cloud_COM()
    # Cloud.FTP_Connect()
    # time.sleep(1)
    Cloud.startWaitNewSW(NewSW_CB)

    while True:
        time.sleep(1)














def job():
    print(f"Old SW running at: {time.time()}")


scheduler = BackgroundScheduler()
scheduler.add_job(job, 'interval', seconds=5)
scheduler.start()


while True:
    user_input = input('Enter command (e.g., "App,1.1"): ')
    split_input = user_input.split(',')

    if len(split_input) < 2:
        print('Invalid input format. Please use "Command,Version" format.')
        continue

    command, version = split_input[0], split_input[1]

    try:
        version = float(version)
    except ValueError:
        print('Invalid version number. Please enter a valid number.')
        continue

    Version_file_control = version_file_control()

    if command == 'App':
        running, non_running = Version_file_control.read_2latest_version('FOTA_Master_App')
        if version > running and version > non_running:
            print("Comparing with two latest versions in FOTA Master")
            if Download_NewSW():
                print("Download new software success")
                Version_file_control.update_version('FOTA_Master_App', version)
                subprocess.Popen(['python', BOOT, arg])
                exit()

    elif command == 'Bootloader':
        print('todo')

    elif command == 'Client':
        print('todo')

    else:
        print('Error: Unrecognized command.')

    time.sleep(1)

    # user_input = input('Enter command: ')
    # split_input = user_input.split(',')

    # Version_file_control = version_file_control()

    # if split_input[0] == 'App':
    #     running, non_running = Version_file_control.read_2latest_version('FOTA_Master_App')
    #     if float(split_input[1]) > running and split_input[1] > non_running :
    #         print("Compare with two latest version in FOTA Master")
    #         if Download_NewSW():
    #             print("Download new software success")
    #             subprocess.Popen(['python', bootloader, arg])
    #             exit()

    # elif split_input[0] == 'Bootloader':
    #     print('todo')

    # elif split_input[0] == 'Client':
    #     print('todo')
        
    # else:
    #      print('Error')
    