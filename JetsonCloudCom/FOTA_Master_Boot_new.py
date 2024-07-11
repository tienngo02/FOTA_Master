import threading
from src.templates.threadwithstop import ThreadWithStop
from src.utils.messages.allMessages import (
    BatteryLvl,
    ImuData,
    InstantConsumption,
    EnableButton,
)


class threadRead(ThreadWithStop):
    """This thread read the data that NUCLEO send to Raspberry PI.\n

    Args:
        f_serialCon (serial.Serial): Serial connection between the two boards.
        f_logFile (FileHandler): The path to the history file where you can find the logs from the connection.
        queueList (dictionar of multiprocessing.queues.Queue): Dictionar of queues where the ID is the type of messages.
    """

    # ===================================== INIT =========================================
    def __init__(self, f_serialCon, f_logFile, queueList):
        super(threadRead, self).__init__()
        self.serialCon = f_serialCon
        self.logFile = f_logFile
        self.buff = ""
        self.isResponse = False
        self.queuesList = queueList
        self.acumulator = 0
        self.Queue_Sending()

    # ====================================== RUN ==========================================
    def run(self):
        while self._running:
            read_chr = self.serialCon.read()
            try:
                read_chr = read_chr.decode("ascii")
                if read_chr == "@":
                    self.isResponse = True
                    if len(self.buff) != 0:
                        self.sendqueue(self.buff)
                    self.buff = ""
                elif read_chr == "\r":
                    self.isResponse = False
                    if len(self.buff) != 0:
                        self.sendqueue(self.buff)
                    self.buff = ""
                if self.isResponse:
                    self.buff += read_chr
            except UnicodeDecodeError:
                pass

    # ==================================== SENDING =======================================
    def Queue_Sending(self):
        """Callback function for enable button flag."""
        self.queuesList[EnableButton.Queue.value].put(
            {
                "Owner": EnableButton.Owner.value,
                "msgID": EnableButton.msgID.value,
                "msgType": EnableButton.msgType.value,
                "msgValue": True,
            }
        )
        threading.Timer(1, self.Queue_Sending).start()

    def sendqueue(self, buff):
        """This function select which type of message we receive from NUCLEO and send the data further."""
        if buff[0] == 1:
            print(buff[2:-2])
        elif buff[0] == 2:
            print(buff[2:-2])
        elif buff[0] == 3:
            print(buff[2:-2])
        elif buff[0] == 4:
            print(buff[2:-2])
        elif buff[0] == 5:
            self.queuesList[BatteryLvl.Queue].put(
                {
                    "Owner": BatteryLvl.Owner,
                    "msgID": BatteryLvl.msgID,
                    "msgType": BatteryLvl.msgType,
                    "msgValue": int(buff[2:-3]),
                }
            )
        elif buff[0] == 6:
            self.queuesList[InstantConsumption.Queue].put(
                {
                    "Owner": InstantConsumption.Owner,
                    "msgID": InstantConsumption.msgID,
                    "msgType": InstantConsumption.msgType,
                    "msgValue": int(buff[2:-3]),
                }
            )
        elif buff[0] == 7:
            buff = buff[2:-2]
            splitedBuffer = buff.split(";")
            data = {
                "roll": splitedBuffer[0],
                "pitch": splitedBuffer[1],
                "yaw": splitedBuffer[2],
                "accelx": splitedBuffer[3],
                "accely": splitedBuffer[4],
                "accelz": splitedBuffer[5],
            }
            self.queuesList[ImuData.Queue].put(
                {
                    "Owner": ImuData.Owner,
                    "msgID": ImuData.msgID,
                    "msgType": ImuData.msgType,
                    "msgValue": data,
                }
            )