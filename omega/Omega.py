import serial
import glob
from threading import Thread
from Queue import Queue

class Omega():
    def __init__(self, plugin):
        self._plugin = plugin
        self._logger = plugin._logger
        self._logger.info("Hello from Omega") 

        self.activeDrive = "1"
        self.currentFilepath = "/home/s1/mcor.msf"

        self.omegaSerial = None 
        self.sentCounter = 0

        self.msfCU = ""
        self.msfNS = "0"
        self.msfNA = "0"
        self.nAlgorithms = 0
        self.currentSplice = "0"
        self.inPong = False
        self.splices = []
        self.algorithms = []

        self.connected = False
        self.writeQueue = None
        self.readThread = None
        self.writeThread = None

        omegaPort = glob.glob('/dev/serial/by-id/*STMicro*')
        if len(omegaPort) > 0:
            self.connectOmega(omegaPort[0])
            self._logger.info("Connected to Omega")
        else:
            self._logger.info("Could not connect to Omega")

        self.stop = False

        #thread.start()

    def connectOmega(self, port):
        if self.connected is not True:
            port = glob.glob('/dev/serial/by-id/*STMicro*')
            self.omegaSerial = serial.Serial(port[0], 9600)
            #self.connected = True
        
        if self.readThread is None:
            self.readThread = Thread(target=self.omegaReadThread, args=(self.omegaSerial,))
            self.readThread.daemon = True
            self.readThread.start()
        if self.writeThread is None:
            self.writeThread = Thread(target=self.omegaWriteThread, args=(self.omegaSerial,))
            self.writeThread.daemon = True
            self.writeThread.start()
        while self.writeQueue is None:
            pass

        self.enqueueLine("O99\n")
        

    def disconnect(self):
        self.omegaSerial.close()
        self.stop = True
        self.connected = False
        self._logger.info("Disconnected from Omega")
        self._plugin._plugin_manager.send_plugin_message(self._plugin._identifier, "UI:Con=%s" % self.connected)

    def setActiveDrive(self, drive):
        self.activeDrive = drive
        self._logger.info("Omega: active drive set to: %s" % self.activeDrive)

    def setFilepath(self, filepath):
        self.currentFilepath = filepath
        self._logger.info("Omega: current file set to: %s" % self.currentFilepath)

    def sendUIUpdate(self):
        self._plugin._plugin_manager.send_plugin_message(self._plugin._identifier, "UI:nSplices=%s" % int(self.msfNS, 16))
        self._plugin._plugin_manager.send_plugin_message(self._plugin._identifier, "UI:S=%s" % self.currentSplice)
        self._plugin._plugin_manager.send_plugin_message(self._plugin._identifier, "UI:Con=%s" % self.connected)
        if self.inPong:
            self._plugin._plugin_manager.send_plugin_message(self._plugin._identifier, "UI:Ponging")
        else:
            self._plugin._plugin_manager.send_plugin_message(self._plugin._identifier, "UI:Finished Pong")       

    def resetPrintValues(self):
        self._logger.info("Omega: Resetting print values")
        self.sentCounter = 0
        self.msfCU = ""
        self.msfNS = "0"
        self.msfNA = "0"
        self.currentSplice = "0"
        self.inPong = False
        self.splices = []
        self.algorithms = []
        self.nAlgorithms = 0
        
    def startSingleColor(self):
        self._logger.info("Omega: start Single Color Mode with drive %s" % self.activeDrive)
        cmdStr = "O4 D%s\n" % self.activeDrive
        self.omegaSerial.write(cmdStr.encode())
        self._logger.info("Omega: Sent %s" % cmdStr)

    def startSpliceDemo(self, withPrinter):
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

        if withPrinter is True:
            self._logger.info("Omega: start Splice Demo w/ Printer")
            if self.connected:
                self.omegaSerial.write("O2\n")
        else:
            self._logger.info("Omega: start Splice Demo w/o printer")
            if self.connected:
                self.omegaSerial.write("O3\n")

    def sendPrintStart(self):
        #self._logger.info("Omega: Sending 'O31'")
        #self.omegaSerial.write("O31\n")
        self._logger.info("Omega toggle pause")
        self._plugin._printer.toggle_pause_print()

    def jog(self, drive, dist):
        distBinary = bin(int(dist) & 0xffff)
        distHex = "%04X" % int(distBinary, 2)
        # figure out the drive number
        jogCmd = "O%s D%s" % (drive, distHex)
        self._logger.info(jogCmd)
        self.gotOmegaCmd(jogCmd)

    def cut(self):
        self._logger.info("Omega: Sending Cut command") 
        self.gotOmegaCmd("O19")

    def gotOmegaCmd(self, cmd):
        if "O25" in cmd:
            self.msfCU = cmd[5:]
            #self.msfCU = cmd
            self._logger.info("Omega: Got CU: %s" % self.msfCU) 
        elif "O26" in cmd:
            self.msfNS = cmd[5:]
            self._logger.info("Omega: Got NS: %s" % self.msfNS)
        elif "O28" in cmd:
            self.msfNA = cmd[5:]
            self.nAlgorithms = int(self.msfNA)
            self._logger.info("Omega: Got NA: %d" % self.nAlgorithms)
        elif "O29" in cmd:
            self.algorithms.append(cmd)
            self._logger.info("Omega: Got algorithm: %s" % cmd[4:])
        elif "O21" in cmd or "O22" in cmd or "O23" in cmd or "O24" in cmd:
            splice = (int(cmd[2:3]) - 1, cmd[5:13])
            self.splices.append(splice)
            self._logger.info("Omega: Got splice D: %s, dist: %s" % (splice[0], splice[1]))
        elif "O9" in cmd and "O99" not in cmd:
            #reset values
            self.resetPrintValues()
            self.enqueueLine(cmd)
        else:
            self._logger.info("Omega: Got an Omega command '%s'" % cmd)
            self.enqueueLine(cmd)

    def sendCmd(self, cmd):
        self._logger.info("Omega: Sending '%s'" % cmd)
        try:
            self.omegaSerial.write(cmd.encode() + "\n")
        except:
            self._logger.info("Omega: Error sending cmd")
            self.omegaSerial.close()

    def sendAutoloadOn(self):
        self.omegaSerial.write("O38\n")

    def sendAutoloadOff(self):
        self.omegaSerial.write("O37\n")

    def printerTest(self):
        self._plugin._logger.info("Sending commands from Omega")
        #self._plugin._printer.commands(["G28", "G1 X150 Y150 Z10 F6000"])
        #self._plugin._printer.commands(["M109 S220", "M83", "G1 E50.00"])
        self._plugin._printer.commands(["M83", "G1 E50.00 F200"])

    def sendNextData(self):
        if self.sentCounter == 0:
            #cmdStr = "O25 D%s\n" % self.msfCU.replace(':', ';')
            cmdStr = "O25 K%s\n" % self.msfCU.replace(':', ';')
            #self.omegaSerial.write(cmdStr.encode())
            #self.enqueueLine("%s\n" % self.msfCU)
            #self.enqueueLine("O25 D1111\n")
            #self.enqueueLine("O25 K1;")
            self.enqueueLine(cmdStr)
            self._logger.info("Omega: Sent '%s'" % cmdStr)
            self.sentCounter = self.sentCounter + 1
        elif self.sentCounter == 1:
            cmdStr = "O26 D%s\n" % self.msfNS
            #self.omegaSerial.write(cmdStr.encode())
            self.enqueueLine(cmdStr)
            self._logger.info("Omega: Sent '%s'" % cmdStr)
            self.sentCounter = self.sentCounter + 1
        elif self.sentCounter == 2:
            cmdStr = "O28 D%s\n" % self.msfNA
            self.enqueueLine(cmdStr)
            self._logger.info("Omega: Sent '%s'" % cmdStr)
            self.sentCounter = self.sentCounter + 1
        elif self.sentCounter <= (2 + self.nAlgorithms):
            self._logger.info("Omega: send algo")
            self.enqueueLine(self.algorithms[self.sentCounter - 3])
            self._logger.info("Omega: Sent '%s'" % self.algorithms[self.sendCounter - 3])
            self.sentCounter = self.sentCounter + 1
        elif self.sentCounter > (2 + self.nAlgorithms):
            self._logger.info("Omega: send splice")
            splice = self.splices[self.sentCounter - 3 - self.nAlgorithms]
            cmdStr = "O2%d D%s\n" % ((int(splice[0]) + 1), splice[1])
            #self.omegaSerial.write(cmdStr.encode())
            self.enqueueLine(cmdStr)
            self._logger.info("Omega: Sent '%s'" % cmdStr)
            self.sentCounter = self.sentCounter + 1

    def omegaReadThread(self, ser):
        self._logger.info("Omega Read Thread: Starting thread")
        while self.stop is not True:
            line = ser.readline()
            line = line.strip()
            self._logger.info("Omega: read in line: %s" % line)
            if 'O20' in line:
                self._logger.info("need to send next line")
                self.sendNextData()
            elif 'O30' in line:
                #send gcode command
                dist = line.strip()[5:]
                extrudeCmd = "G1 X1 E%s F10" % dist
                self._plugin._printer.commands(["G91", extrudeCmd, "G90", "G92 E0"])
                #self._plugin._printer.commands(["M109 S220", "M83", "G1 E50.00 F2000"])
            elif "O32" in line:
                #resume print
                self._logger.info("Omega: resuming print")
                self._plugin._printer.toggle_pause_print()
            elif "UI:" in line:
                #send a message to the front end
                self._logger.info(line)
                if "Ponging" in line:
                    self.inPong = True
                elif "Finished Pong" in line:
                    self.inPong = False
                elif "S=" in line:
                    self.currentSplice = line[5:]
                self._plugin._plugin_manager.send_plugin_message(self._plugin._identifier, line)
            elif "Connection Okay" in line:
                self.connected = True
		self._plugin._plugin_manager.send_plugin_message(self._plugin._identifier, "UI:Con=%s" % self.connected)

        ser.close()

    def enqueueLine(self, line):
	if self.writeThread is not None and self.writeQueue is not None:
            self.writeQueue.put(line)

    def omegaWriteThread(self, ser):
        self._logger.info("Omega Write Thread: Starting Thread")
        self.writeQueue = Queue()
        while self.stop is not True:
            line = self.writeQueue.get()
            line = line.strip()
            line = line + "\n"
            self._logger.info("Omega Write Thread: Sending: %s" % line)
            self.omegaSerial.write(line.encode())

    def shutdown(self):
        self.stop = True
        self.omegaSerial.close()
