import ftplib
import time
import ssl
import os
import io
import sys
import time
import paho.mqtt.client as mqtt
from Security import Security

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

if __name__ == '__main__':
    print()
    print("Path: ",sys.path)
    Cloud = Cloud_COM()
    # Cloud.FTP_Connect()
    # time.sleep(1)
    Cloud.startWaitNewSW(NewSW_CB)

    while True:
        time.sleep(1)
