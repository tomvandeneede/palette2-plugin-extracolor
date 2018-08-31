import serial
import glob
import time
import threading
import subprocess
import os
from Queue import Queue

class Omega():
    def __init__(self, plugin):
        plugin._logger.info("Hello from Omega!")
        self._logger = plugin._logger
        self._printer = plugin._printer
        self._plugin_manager = plugin._plugin_manager
        self._identifier = plugin._identifier
        self._settings = plugin._settings

        self.writeQueue = Queue()

        self.resetVariables()
        self.resetConnection()
        
        #Trys to automatically connect to palette first
        if self._settings.get(["autoconnect"]):
            self.startConnectionThread()

    def connectOmega(self, port = 300):
        self._logger.info("Trying to connect to Omega")
        if self.connected is False:
            omegaPort = glob.glob('/dev/serial/by-id/*D*')
            if len(omegaPort) > 0:
                try:
                    self.omegaSerial = serial.Serial(omegaPort[0], 250000, timeout=0.5)
                    self.connected = True
                    self._logger.info("Connected to Omega")
                    #Tells plugin to update UI
                    self._plugin_manager.send_plugin_message(self._identifier, "UI:Con=%s" % self.connected)
                except:
                    self._logger.info("Another resource is connected to Palette")
            else:
                self._logger.info("Unable to find Omega port")
        else:
            self._logger.info("Already Connected")

        if self.connected:
            self.startReadThread()
            self.startWriteThread()

    def connectWifi(self, wifiSSID, wifiPASS):
        lines = open('/etc/wpa_supplicant/wpa_supplicant.conf').readlines()
        open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w').writelines(lines[0:-5])
        
        with open("/etc/wpa_supplicant/wpa_supplicant.conf", "a") as myfile:
            myfile.write('network={\n        ssid="' + wifiSSID + '"\n        psk="' + wifiPASS + '"\n        key_mgmt=WPA-PSK\n}\n')
        
        os.system("sudo reboot")

    def startReadThread(self):
        if self.readThread is None:
            self.readThreadStop = False
            self.readThread = threading.Thread(target=self.omegaReadThread, args=(self.omegaSerial,))
            self.readThread.daemon = True
            self.readThread.start()

    def startWriteThread(self):
        if self.writeThread is None:
            self.writeThreadStop = False
            self.writeThread = threading.Thread(target=self.omegaWriteThread, args=(self.omegaSerial,))
            self.writeThread.daemon = True
            self.writeThread.start()
    
    def startConnectionThread(self):
        if self.connectionThread is None:
            self.connectionThreadStop = False
            self.connectionThread = threading.Thread(target=self.omegaConnectionThread)
            self.connectionThread.daemon = True
            self.connectionThread.start()
    
    def stopReadThread(self):
        self.readThreadStop = True
        if self.readThread and threading.current_thread() != self.readThread:
            self.readThread.join()
        self.readThread = None
    
    def stopWriteThread(self):
        self.writeThreadStop = True
        if self.writeThread and threading.current_thread() != self.writeThread:
            self.writeThread.join()
        self.writeThread = None

    def stopConnectionThread(self):
        self.connectionThreadStop = True
        if self.connectionThread and threading.current_thread() != self.connectionThread:
            self.connectionThread.join()
        self.connectionThread = None

    def omegaReadThread(self, serialConnection):
        self._logger.info("Omega Read Thread: Starting thread")
        try:
            while self.readThreadStop is False:
                line = serialConnection.readline()
                line = line.strip()
                if line:
                    self._logger.info("Omega: read in line: %s" % line)
                if 'O20' in line:
                    #send next line of data
                    self.sendNextData(int(line[5]))
                elif 'O30' in line:
                    #send gcode command
                    dist = line.strip()[5:]
                    extrudeCmd = "G1 X1 E%s F10" % dist
                    self._printer.commands(["G91", extrudeCmd, "G90", "G92 E0"])
                elif "O32" in line:
                    #resume print
                    self._printer.toggle_pause_print()
                elif "UI:" in line:
                    #send a message to the front end
                    self._logger.info(line)
                    if "Ponging" in line:
                        self.inPong = True
                    elif "Finished Pong" in line:
                        self.inPong = False
                    elif "S=" in line:
                        self.currentSplice = line[5:]
                    self.updateUI()
            serialConnection.close()
        except:
            #Something went wrong with the connection to Palette2
            self.disconnect()

    def omegaWriteThread(self, serialConnection):
        self._logger.info("Omega Write Thread: Starting Thread")
        while self.writeThreadStop is False:
            try:
                line = self.writeQueue.get(True, 0.5)
                line = line.strip()
                line = line + "\n"
                self._logger.info("Omega Write Thread: Sending: %s" % line)
                serialConnection.write(line.encode())
            except:
                pass
        self.writeThread = None

    def omegaConnectionThread(self):
        while self.connectionThreadStop is False:
            if self.connected is False:
                self.connectOmega()
            time.sleep(1)

    def enqueueCmd(self, line):
        self.writeQueue.put(line)

    def startSpliceDemo(self, fileName, path, withPrinter):
        self._logger.info("Starting splice demo")
        f = open(path, "r")
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
        print(withPrinter)
        if withPrinter is True:
            self._logger.info("Omega: start Splice Demo w/ Printer")
            if self.connected:
                cmd = "O3 D" + fileName + "\n"
                self.enqueueCmd(cmd)
        else:
            self._logger.info("Omega: start Splice Demo w/o printer")
            if self.connected:
                cmd = "O3 D" + fileName + "\n"
                self.enqueueCmd(cmd)

    def startJog(self, drive, dist):
        self._logger.info("Jog command received")
        jogCmd = None

        distBinary = bin(int(dist) & 0xffff)
        distHex = "%04X" % int(distBinary, 2)

        if dist == 999: # drive indef inwards
            jogCmd = "O%s D1 D1" % (drive)
        elif dist == -999: # drive indef outwards
            jogCmd = "O%s D1 D0" % (drive)
        else: # drive a certain distance
            jogCmd = "O%s D0 D%s" % (drive, distHex)

        self.enqueueCmd(jogCmd)

    def stopIndefJog(self):
        self._logger.info("Stop indef jog")
        jogCmd = "O10 D1 D2"
        self.enqueueCmd(jogCmd)

    def cut(self):
        self._logger.info("Omega: Sending Cut command") 
        cutCmd = "O19"
        self.enqueueCmd(cutCmd)

    def sendCmd(self, cmd):
        self._logger.info("Omega: Sending '%s'" % cmd)
        try:
            self.enqueueCmd(cmd)
        except:
            self._logger.info("Omega: Error sending cmd")
            self.omegaSerial.close()

    def updateUI(self):
        self._logger.info("Sending UIUpdate")
        #self._plugin_manager.send_plugin_message(self._identifier, "UI:nSplices=%s" % int(self.msfNS, 16))
        #self._plugin_manager.send_plugin_message(self._identifier, "UI:S=%s" % self.currentSplice)
        self._plugin_manager.send_plugin_message(self._identifier, "UI:Con=%s" % self.connected)
        #if self.inPong:
            #self._plugin_manager.send_plugin_message(self._identifier, "UI:Ponging")
        #else:
            #self._plugin_manager.send_plugin_message(self._identifier, "UI:Finished Pong")

    def sendNextData(self, dataNum):
        self._logger.info("Sending next line, dataNum: " + str(dataNum) + " sentCount : " + str(self.sentCounter))
        self._logger.info(self.sentCounter)
        if self.sentCounter == 0 and dataNum == 0:
            cmdStr = "O25 D%s\n" % self.msfCU.replace(':', ';')
            self.enqueueCmd(cmdStr)
            self._logger.info("Omega: Sent '%s'" % cmdStr)
            self.sentCounter = self.sentCounter + 1
        elif self.sentCounter == 1 and dataNum == 0:
            cmdStr = "O26 D%s\n" % self.msfNS
            self.enqueueCmd(cmdStr)
            self._logger.info("Omega: Sent '%s'" % cmdStr)
            self.sentCounter = self.sentCounter + 1
        elif self.sentCounter == 2 and dataNum == 0:
            cmdStr = "O28 D%s\n" % self.msfNA
            self.enqueueCmd(cmdStr)
            self._logger.info("Omega: Sent '%s'" % cmdStr)
            self.sentCounter = self.sentCounter + 1
        elif dataNum == 4:
            self._logger.info("Omega: send algo")
            self.enqueueCmd(self.algorithms[self.sentCounter - 3])
            self._logger.info("Omega: Sent '%s'" % self.algorithms[self.sendCounter - 3])
            self.sentCounter = self.sentCounter + 1
        elif dataNum == 1:
            self._logger.info("Omega: send splice")
            splice = self.splices[self.sentCounter - 3 - self.nAlgorithms]
            cmdStr = "O2%d D%s\n" % ((int(splice[0]) + 1), splice[1])
            self.enqueueCmd(cmdStr)
            self._logger.info("Omega: Sent '%s'" % cmdStr)
            self.sentCounter = self.sentCounter + 1

    def resetConnection(self):
        self._logger.info("Resetting read and write threads")
        # stop read and write threads
        
        self.stopReadThread()
        self.stopWriteThread()
        if not self._settings.get(["autoconnect"]):
            self.stopConnectionThread()

        if self.omegaSerial:
            self.omegaSerial.close()
            self.omegaSerial = None
        self.connectionStop = False

        # clear command queue
        while not self.writeQueue.empty():
            self.writeQueue.get()
    
    def resetVariables(self):
        self._logger.info("Omega: Resetting print values")
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
        self.readThread = None
        self.writeThread = None
        self.connectionThread = None
        self.connectionStop = False

    def resetOmega(self):
        self.resetConnection()
        self.resetVariables()

    def shutdown(self):
        self.disconnect()

    def disconnect(self):
        self._logger.info("Disconnecting from Palette")
        self.resetOmega()
        self.updateUI()

    def setActiveDrive(self, drive):
        self.activeDrive = drive
        self._logger.info("Omega: active drive set to: %s" % self.activeDrive)

    def startSingleColor(self):
        self._logger.info("Omega: start Single Color Mode with drive %s" % self.activeDrive)
        cmdStr = "O4 D%s\n" % self.activeDrive
        self.omegaSerial.write(cmdStr.encode())
        self._logger.info("Omega: Sent %s" % cmdStr)

    def sendPrintStart(self):
        self._logger.info("Omega toggle pause")
        self._printer.toggle_pause_print()
    
    def sendAutoloadOn(self):
        self.omegaSerial.write("O38\n")

    def sendAutoloadOff(self):
        self.omegaSerial.write("O37\n")

    def printerTest(self):
        self._logger.info("Sending commands from Omega")
        self._printer.commands(["M83", "G1 E50.00 F200"])

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
            self.resetOmega()
            self.enqueueCmd(cmd)
        elif "O1" in cmd:
            self.enqueueCmd("O1 D%s D0007 D0001" % self.filename)
        else:
            self._logger.info("Omega: Got an Omega command '%s'" % cmd)
            self.enqueueCmd(cmd)
