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


print()
print("================================")
print("App is running...")


JSONFILE = 'Version_information_file.json'

PYTHON = 'python3'
APP = 'App.py'
BOOT = 'Boot.py'
CLIENT = 'FOTA_Client.py'


'''
=========================================================
Server communication and security
=========================================================
'''
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


def NewSW_CB(Cloud, Swname):
    try:
        print("CB: ", Swname)
        splitName = Swname.split('_v')
        file_name = splitName[0]
        version = int(splitName[1])

        version_control_obj = Version_File_Control()
        running, non_running = version_control_obj.read_2latest_version(file_name)

        if version > running and version > non_running:
            New_SW = Cloud.GetNewSW(Swname)
            if New_SW:
                new_file_name = file_name + '_new.py'
                with open(new_file_name, "wb") as file:
                    file.write(New_SW)
                version_control_obj.update_version(file_name, version)

                if file_name == 'FOTA_Master_App':
                    subprocess.Popen([PYTHON, BOOT, 'activate_App'])
                    exit()
                elif file_name == 'FOTA_Master_Boot':
                    subprocess.Popen([PYTHON, BOOT, 'activate_Boot'])
                    exit()
                elif file_name == 'FOTA_Client':
                    # subprocess.Popen([PYTHON, BOOT, 'activate_Client'])
                    # exit()
                    notify_New_SW()
                else:
                    print('Invalid file name')

    except Exception as e:
        print("NewSW_CB() error: ", e)


'''
=========================================================
Version file control
=========================================================
'''


class Version_File_Control:
    data = None

    def __init__(self):
        with open(JSONFILE, 'r') as file:
            self.data = json.load(file)
         
    def read_2latest_version(self, file_name):
        return self.data[file_name]['running'], self.data[file_name]['non-running']
        
    def update_version(self, file_name, version):
        self.data[file_name]['non-running'] = version
        self.data[file_name]['activate'] = True
        with open(JSONFILE, 'w') as file:
            json.dump(self.data, file, indent=4)


'''
=========================================================
UART Communication
=========================================================
'''

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

# notify_New_SW()

# while True:
#     receive_message()
#     time.sleep(0.01)


'''
=========================================================
Main
=========================================================
'''

if __name__ == '__main__':
    print()
    print("Path: ", sys.path)
    Cloud = Cloud_COM()
    # Cloud.FTP_Connect()
    # time.sleep(1)
    Cloud.startWaitNewSW(NewSW_CB)

    while True:
        receive_message()
        time.sleep(0.01)



    