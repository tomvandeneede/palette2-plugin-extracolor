import serial
from threading import Thread

class Omega():
    def __init__(self, plugin):
        self._plugin = plugin
        self._logger = plugin._logger
        self._logger.info("Hello from Omega") 

        self.activeDrive = "1"
        self.currentFilepath = "/home/s1/test2c.msf"

        #self.omegaSerial = serial.Serial("/dev/ttyACM1", 9600)
        self.sentCounter = 0

        self.msfCU = ""
        self.msfNS = ""
        self.splices = []


        self.stop = False

        #thread.start()

    def connectOmega(self, port):
        self.omegaSerial = serial.Serial(port, 9600)
        thread = Thread(target=self.omegaReadThread, args=(self.omegaSerial,))
        thread.daemon = True
        thread.start()

    def setActiveDrive(self, drive):
        self.activeDrive = drive
        self._logger.info("Omega: active drive set to: %s" % self.activeDrive)

    def setFilepath(self, filepath):
        self.currentFilepath = filepath
        self._logger.info("Omega: current file set to: %s" % self.currentFilepath)

    def startSingleColor(self):
        self._logger.info("Omega: start Single Color Mode with drive %s" % self.activeDrive)
        cmdStr = "O4 D%s\n" % self.activeDrive
        self._logger.info("Omega: Sending %s" % cmdStr)
        self.omegaSerial.write(cmdStr)

    def startSpliceDemo(self):
        self._logger.info("Omega: start Splice Demo w/o printer")
        f = open(self.currentFilepath)
        for line in f:
            if "cu" in line:
                self.msfCU = line[3:7]
                self._logger.info("Omega: setting CU to %s" % self.msfCU)
            elif "ns" in line:
                self.msfNS = line[3:7]
                self._logger.info("Omega: setting NS to %s" % self.msfNS)
            elif "(" in line:
                splice = (line[2:3], line[4:12])
                self._logger.info("Omega: Adding Splice D: %s, Dist: %s" % (splice[0], splice[1]))
                self.splices.append(splice)
        f.close()
        self.omegaSerial.write("O3\n")

    def sendPrintStart(self):
        self._logger.info("Omega: Sending 'O31'")
        self.omegaSerial.write("O31\n")

    def sendCmd(self, cmd):
        self._logger.info("Omega: Sending '%s'" % cmd)
        self.omegaSerial.write(cmd + "\n")

    def printerTest(self):
        self._plugin._logger.info("Sending commands from Omega")
        self._plugin._printer.commands(["G28", "G1 X150 Y150 Z10 F6000"])
        self._plugin._printer.commands(["M109 S220", "M83", "G1 E50.00"])

    def sendNextData(self):
        if self.sentCounter == 0:
            cmdStr = "O25 D%s\n" % self.msfCU
            self.omegaSerial.write(cmdStr)
            self.sentCounter = self.sentCounter + 1
        elif self.sentCounter == 1:
            cmdStr = "O26 D%s\n" % self.msfNS
            self.omegaSerial.write(cmdStr)
            self.sentCounter = self.sentCounter + 1
        elif self.sentCounter > 1:
            splice = self.splices[self.sentCounter - 2]
            cmdStr = "O2%d D%s\n" % ((int(splice[0]) + 1), splice[1])
            self.omegaSerial.write(cmdStr)
            self.sentCounter = self.sentCounter + 1

    def omegaReadThread(self, ser):
        self._logger.info("Omega Read Thread: Starting thread")
        while self.stop is not True:
            line = ser.readline()
            print(line)
            if "O20" in line:
                self.sendNextData()
            elif "O30" in line:
                #send gcode command
                print line
                #self._plugin._printer.commands(["M109 S220", "M83", "G1 E50.00 F2000"])
        ser.close()

    def shutdown(self):
        self.stop = True
