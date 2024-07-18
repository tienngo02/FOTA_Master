import subprocess
import time
import json
import threading

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

PYTHON = 'python3.12'
APP = 'App.py'
BOOT = 'Boot.py'
CLIENT = 'FOTA_Client.py'

# global ser
newClient = False
# stop_thread = False
# thread = None
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
        self.ftps.connect(self.host, self.FTPport)

        # print(self.ftps.getwelcome())
        # print(self.ftps.sock)

        self.ftps.auth()

        self.ftps.login(self.user, self.passwd, self.acct)

        self.ftps.set_pasv(True)
        self.ftps.prot_p()
        self.ftps.cwd("SW")
        self.isFTPConnected = True

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
        try:
            if self.isFTPConnected == False:
                self.FTP_Connect()
            if self.isMQTTConnected == False:
                self.MQTT_Connect()
            self.NotifiSW_CB = NewSWCB
            self.MQTTclient.subscribe("SW/Jetson/#",qos=2)
            return True
        except Exception as e:
            print("Connect error: ",e)
            return False
    
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

# isCBProcessing = False 

def NewSW_CB(Cloud, Swname):
    # global isProcessing
    # if isCBProcessing == True:
    #     return
    try:
        print("CB: ", Swname)
        splitName = Swname.split('_v')
        file_name = splitName[0]
        version = int(splitName[1])

        version_control_obj = Version_File_Control()
        running, non_running = version_control_obj.read_2latest_version(file_name)

        if version > running and version > non_running:
            print('Download: ' + Swname)
            New_SW = Cloud.GetNewSW(Swname)
            if New_SW:
                new_file_name = file_name + '_new.py'
                with open(new_file_name, "wb") as file:
                    file.write(New_SW)
                version_control_obj.update_version(file_name, version)
                activate_newSW(file_name)
                
        elif version == non_running and version_control_obj.activate(file_name):
            activate_newSW(file_name)


    except Exception as e:
        print("NewSW_CB() error: ", e)

def activate_newSW(file_name):
    # global stop_thread
    # global thread
    if file_name == 'FOTA_Master_App':
        # stop_thread = True
        # thread.join()
        subprocess.Popen([PYTHON, BOOT, 'activate_App'])
    
        exit()
    elif file_name == 'FOTA_Master_Boot':
        # stop_thread = True
        # thread.join()
        subprocess.Popen([PYTHON, BOOT, 'activate_Boot'])
        
        exit()
    elif file_name == 'FOTA_Client':
        global newClient
        global ser
        ser = connect_serial_port()
        if ser:
            time.sleep(1)
            byteRead = ser.inWaiting()
            if byteRead > 0:
                data = ser.read(byteRead)
                data_value = [b for b in data]
                # print(data)
            newClient = True
            notify_New_SW()
        # subprocess.Popen([PYTHON, BOOT, 'activate_Client'])
        # exit()
    else:
        print('Invalid file name')


def connectToServer():
    connectCount = 0
    isConnect = Cloud.startWaitNewSW(NewSW_CB)
    while connectCount < 5 :
        if isConnect:
            break
        else:
            print("Connect server error, retrying")
            time.sleep(5)
            isConnect = Cloud.startWaitNewSW(NewSW_CB)
            connectCount += 1
    
    if not isConnect:
        print("Can not connect to server")

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

    def activate(self, file_name):
        return self.data[file_name]['activate']

    def deactive(self, filename):
        self.data[filename]['activate'] = False
        with open(JSONFILE, 'w') as file:
            json.dump(self.data, file, indent=4)


'''
=========================================================
UART Communication
=========================================================
'''

NOTIFY_NEW_SW = bytes([35, 1, 120, 0, 0, 0, 0, 0, 0])
RESPONSE_CONFIRMATION = bytes([1, 121, 0, 0, 0, 0])
REQUEST_FLASH_SW = bytes([1, 122, 0, 0, 0, 111, 0, 0])
FLASH_SUCCESS_YET = bytes([35, 1, 123, 0, 0, 0, 0, 0, 0])


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
            seri = serial.Serial(port=getPort(), baudrate=115200, parity=serial.PARITY_NONE,
                                stopbits=serial.STOPBITS_ONE,
                                bytesize=serial.EIGHTBITS, timeout=1)
            print("Open successfully")
            return seri

        except serial.SerialException as e:
            attempt += 1
            print(f"Attempt {attempt} failed")
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                print("Can not open the port.")
                return None


# ser = connect_serial_port()
TIMEOUT = 5
startTime = 0
isFlashSuccess = False

def flash_SW():

    global newClient
    global ser
    global isFlashSuccess
    bytesRead = ser.inWaiting()
    ser.read(bytesRead)
    ser.close()
    newClient = False
    time.sleep(1)
    print("Flash SW for FOTA Client")
    # subprocess.Popen([PYTHON, BOOT, 'activate_Client'])
    # exit()

    subprocess.run([PYTHON, BOOT, 'activate_Client'])
    
    ser = connect_serial_port()
    if ser:
        time.sleep(1)
        byteRead = ser.inWaiting()
        if byteRead > 0:
            data = ser.read(byteRead)
            data_value = [b for b in data]
            # print(data)
        ser.write(FLASH_SUCCESS_YET)
        startTime = time.time()
        while True:
            current = time.time()
            if isFlashSuccess:
                print("New client flash success")
                ser.close()
                isFlashSuccess = False
                break
            if current - startTime > TIMEOUT:
                print("New client error")
                bytesRead = ser.inWaiting()
                ser.read(bytesRead)
                ser.close()
                # global stop_thread
                # global thread
                # stop_thread = True
                # thread.join()
                subprocess.Popen([PYTHON, BOOT, 'rollback_Client'])
                
                exit()

            receive_message()
            time.sleep(0.001)


def notify_New_SW():
    message = NOTIFY_NEW_SW
    print('--------------------------')
    ser.write(message)
    print(message)
    print('--------------------------')
    time.sleep(0.01)


def classify_msg(msg):
    if msg[1] == 121:
        print("Send function has been confirmed")
    elif msg[1] == 122:
        flash_SW()
    elif msg[1] == 124:
        global isFlashSuccess
        isFlashSuccess = True
    else:
        print('Invalid message')


def receive_message():
    global ser
    bytesToRead = ser.inWaiting()
    if bytesToRead > 0:
        start_byte = ser.read(1)
        if start_byte == b'#':
            print('Start byte receive')
            data_bytes = ser.read(8)
            message = [b for b in data_bytes]
            print('Next 8 bytes:', message)
            classify_msg(message)


'''
=========================================================
Main
=========================================================
'''


# def handle_activate_newSW():
#     global stop_thread
#     while not stop_thread:
#         version_control_obj = Version_File_Control()
#         if version_control_obj.activate('FOTA_Master_Boot'):
#             activate_newSW('FOTA_Master_Boot')
            
#         elif version_control_obj.activate('FOTA_Master_App'):
#             activate_newSW('FOTA_Master_App')
            
#         elif version_control_obj.activate('FOTA_Client'):
#             activate_newSW('FOTA_Client')
#             # version_control_obj.deactive('FOTA_Client')
 
#         time.sleep(1)


if __name__ == '__main__':
    try:
        print("New APP")
        print("Path: ", sys.path)
        Cloud = Cloud_COM()
        connectToServer()
        # thread = threading.Thread(target=handle_activate_newSW)
        # thread.daemon = True
        # thread.start()

        # ser = connect_serial_port()
        # time.sleep(1)
        # byteRead = ser.inWaiting()
        # if byteRead > 0:
        #     data = ser.read(byteRead)
        #     data_value = [b for b in data]
        while True:
            if newClient:
                receive_message()
            time.sleep(0.001)
    except Exception as e:
        print('App is error, rollback app')
        subprocess.Popen(['python3.12', 'Boot.py', 'rollback_App'])
        exit()
