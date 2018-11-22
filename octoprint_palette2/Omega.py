import serial
import glob
import time
import threading
import subprocess
import os
from Queue import Queue


class Omega():
    def __init__(self, plugin):
        self._logger = plugin._logger
        self._printer = plugin._printer
        self._plugin_manager = plugin._plugin_manager
        self._identifier = plugin._identifier
        self._settings = plugin._settings

        self.writeQueue = Queue()

        self.resetVariables()
        self.resetConnection()

        # Trys to automatically connect to palette first
        if self._settings.get(["autoconnect"]):
            self.startConnectionThread()

    def connectOmega(self, port=300):
        self._logger.info("Trying to connect to Omega")
        if self.connected is False:
            omegaPort = glob.glob('/dev/serial/by-id/*FTDI*')
            omegaPort += glob.glob('/dev/*usbserial*')
            if len(omegaPort) > 0:
                try:
                    self.omegaSerial = serial.Serial(
                        omegaPort[0], 250000, timeout=0.5)
                    self.connected = True
                except:
                    self._logger.info(
                        "Another resource is connected to Palette")
                    self.updateUI()
            else:
                self._logger.info("Unable to find Omega port")
                self.updateUI()
        else:
            self._logger.info("Already Connected")
            self.updateUI()

        if self.connected:
            self.startReadThread()
            self.startWriteThread()
            # send an O99 to handshake
            self.enqueueCmd("O99")

            timeout = 5   # [seconds]
            timeout_start = time.time()
            # Wait for Palette to respond with a handshake within 5 seconds
            while time.time() < timeout_start + timeout:
                if self.heartbeat:
                    self._logger.info("Connected to Omega")
                    self.updateUI()
                    break
                else:
                    pass
            if not self.heartbeat:
                self._logger.info("Palette is not turned on.")
                self.resetVariables()
                self.resetConnection()
                self.updateUI()

    def setFilename(self, name):
        self.filename = name

    def connectWifi(self, wifiSSID, wifiPASS):
        lines = open('/etc/wpa_supplicant/wpa_supplicant.conf').readlines()
        open('/etc/wpa_supplicant/wpa_supplicant.conf',
             'w').writelines(lines[0:-5])

        with open("/etc/wpa_supplicant/wpa_supplicant.conf", "a") as myfile:
            myfile.write('network={\n        ssid="' + wifiSSID +
                         '"\n        psk="' + wifiPASS + '"\n        key_mgmt=WPA-PSK\n}\n')

        os.system("sudo reboot")

    def startReadThread(self):
        if self.readThread is None:
            self.readThreadStop = False
            self.readThread = threading.Thread(
                target=self.omegaReadThread, args=(self.omegaSerial,))
            self.readThread.daemon = True
            self.readThread.start()

    def startWriteThread(self):
        if self.writeThread is None:
            self.writeThreadStop = False
            self.writeThread = threading.Thread(
                target=self.omegaWriteThread, args=(self.omegaSerial,))
            self.writeThread.daemon = True
            self.writeThread.start()

    def startConnectionThread(self):
        if self.connectionThread is None:
            self.connectionThreadStop = False
            self.connectionThread = threading.Thread(
                target=self.omegaConnectionThread)
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
                    # send next line of data
                    self.sendNextData(int(line[5]))
                    if "D5" in line:
                        self._logger.info("FIRST TIME USE WITH PALETTE")
                        self.firstTime = True
                        self.updateUI()
                elif "O40" in line:
                    self.printPaused = False
                    self.currentStatus = "Preparing splices"
                    self.updateUI()
                    self._printer.toggle_pause_print()
                    self._logger.info("Splices being prepared.")
                elif "O50" in line:
                    # get file list
                    pass
                elif "O97" in line:
                    if "U26" in line:
                        self.filamentLength = int(line[9:], 16)
                        self._logger.info(self.filamentLength)
                        self.updateUI()
                    elif "U25" in line:
                        if "D1" in line:
                            self.currentSplice = int(line[12:], 16)
                            self._logger.info(self.currentSplice)
                            self.updateUI()
                    elif "U39" in line:
                        if "D-" in line:
                            self.amountLeftToExtrude = int(line[10:])
                            self._logger.info(
                                line[10:] + "mm left to extrude.")
                            self.updateUI()
                        elif "D" not in line:
                            self.currentStatus = "Loading filament into extruder"
                            self.updateUI()
                            self._logger.info(
                                "Filament must be loaded into extruder by user")
                        elif "D0" in line:
                            self.amountLeftToExtrude = 0
                            self._logger.info("0" + "mm left to extrude.")
                            self.updateUI()
                            self.amountLeftToExtrude = ""
                    elif self.drivesInUse[0] in line:
                        if "D0" in line:
                            self.currentStatus = "Loading ingoing drives"
                            self.updateUI()
                            self._logger.info("STARTING TO LOAD FIRST DRIVE")
                    elif self.drivesInUse[-1] in line:
                        if "D1" in line:
                            self.currentStatus = "Loading filament through outgoing tube"
                            self.updateUI()
                            self._logger.info("FINISHED LOADING LAST DRIVE")
                    elif "U0" in line:
                        if "D0" in line:
                            self._logger.info("CANCELLING START")
                            self._printer.cancel_print()
                            self.currentStatus = "Cancelling Print"
                            self.updateUI()
                        elif "D1" in line:
                            self._logger.info("CANCELLING END")
                            self.currentStatus = "Print Cancelled"
                            self.updateUI()
                        else:
                            self.currentStatus = "Palette work completed: all splices prepared"
                            self.updateUI()
                            self._logger.info("Palette work is done.")
                elif "Connection Okay" in line:
                    self.heartbeat = True
                elif "UI:" in line:
                    # send a message to the front end
                    self._logger.info(line)
                    if "Ponging" in line:
                        self.inPong = True
                    elif "Finished Pong" in line:
                        self.inPong = False
                    # elif "S=" in line:
                    #     self.currentSplice = line[5:]
                    # self.updateUI()
            serialConnection.close()
        except Exception as e:
            # Something went wrong with the connection to Palette2
            # self.disconnect()
            print e

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
                self._logger.info(
                    "Omega: Adding Splice D: %s, Dist: %s" % (splice[0], splice[1]))
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

        if dist == 999:  # drive indef inwards
            jogCmd = "O%s D1 D1" % (drive)
        elif dist == -999:  # drive indef outwards
            jogCmd = "O%s D1 D0" % (drive)
        else:  # drive a certain distance
            jogCmd = "O%s D0 D%s" % (drive, distHex)

        self.enqueueCmd(jogCmd)

    def stopIndefJog(self):
        self._logger.info("Stop indef jog")
        jogCmd = "O10 D1 D2"
        self.enqueueCmd(jogCmd)

    def cut(self):
        self._logger.info("Omega: Sending Cut command")
        cutCmd = "O10 D5"
        self.enqueueCmd(cutCmd)

    def clear(self):
        self._logger.info("Omega: Sending Clear command")
        clearCmds = ["O10 D5", "O10 D0 D0 D0 DFFE1", "O10 D1 D0 D0 DFFE1",
                     "O10 D2 D0 D0 DFFE1", "O10 D3 D0 D0 DFFE1", "O10 D4 D0 D0 D0069"]
        for command in clearCmds:
            self.enqueueCmd(command)

    def sendCmd(self, cmd):
        self._logger.info("Omega: Sending '%s'" % cmd)
        try:
            self.enqueueCmd(cmd)
        except:
            self._logger.info("Omega: Error sending cmd")
            self.omegaSerial.close()

    def updateUI(self):

        self._logger.info("Sending UIUpdate from Palette")
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:FirstTime=%s" % self.firstTime)
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:PrinterCon=%s" % self.printerConnection)
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:DisplayAlerts=%s" % self.displayAlerts)
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:currentStatus=%s" % self.currentStatus)
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:nSplices=%s" % self.msfNS)
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:currentSplice=%s" % self.currentSplice)
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:Con=%s" % self.connected)
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:FilamentLength=%s" % self.filamentLength)
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:AmountLeftToExtrude=%s" % self.amountLeftToExtrude)
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:PalettePausedPrint=%s" % self.printPaused)
        if self.inPong:
            self._plugin_manager.send_plugin_message(
                self._identifier, "UI:Ponging")
        else:
            self._plugin_manager.send_plugin_message(
                self._identifier, "UI:Finished Pong")

    def sendNextData(self, dataNum):
        # self._logger.info("Sending next line, dataNum: " + str(dataNum) + " sentCount : " + str(self.sentCounter))
        # self._logger.info(self.sentCounter)

        if dataNum == 0:
            # cmdStr = "O25 D%s\n" % self.msfCU.replace(':', ';')
            self.enqueueCmd(self.header[self.sentCounter])
            self._logger.info("Omega: Sent '%s'" % self.sentCounter)
            self.sentCounter = self.sentCounter + 1
        elif dataNum == 4:
            self._logger.info("Omega: send algo")
            self.enqueueCmd(self.algorithms[self.algoCounter])
            self._logger.info("Omega: Sent '%s'" %
                              self.algorithms[self.algoCounter])
            self.algoCounter = self.algoCounter + 1
        elif dataNum == 1:
            self._logger.info("Omega: send splice")
            splice = self.splices[self.spliceCounter]
            cmdStr = "O30 D%d D%s\n" % (int(splice[0]), splice[1])
            self.enqueueCmd(cmdStr)
            self.spliceCounter = self.spliceCounter + 1

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
        self.algoCounter = 0
        self.spliceCounter = 0

        self.msfCU = ""
        self.msfNS = "0"
        self.msfNA = "0"
        self.nAlgorithms = 0
        self.currentSplice = "0"
        self.inPong = False
        self.header = [None] * 9
        self.splices = []
        self.algorithms = []
        self.filamentLength = 0
        self.currentStatus = ""
        self.drivesInUse = []
        self.amountLeftToExtrude = ""
        self.printPaused = ""
        self.printerConnection = ""
        self.firstTime = False

        self.displayAlerts = self._settings.get(["palette2Alerts"])

        self.filename = ""

        self.connected = False
        self.readThread = None
        self.writeThread = None
        self.connectionThread = None
        self.connectionStop = False
        self.heartbeat = False

    def resetOmega(self):
        self.resetConnection()
        self.resetVariables()

    def shutdown(self):
        self._logger.info("Shutdown")
        self.disconnect()

    def disconnect(self):
        self._logger.info("Disconnecting from Palette")
        self.resetOmega()
        self.updateUI()

    def setActiveDrive(self, drive):
        self.activeDrive = drive
        self._logger.info("Omega: active drive set to: %s" % self.activeDrive)

    def startSingleColor(self):
        self._logger.info(
            "Omega: start Single Color Mode with drive %s" % self.activeDrive)
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
        if "O21" in cmd:
            self.header[0] = cmd
            self._logger.info("Omega: Got Version: %s" % self.header[0])
        elif "O22" in cmd:
            self.header[1] = cmd
            self._logger.info("Omega: Got Printer Profile: %s" %
                              self.header[1])
        elif "O23" in cmd:
            self.header[2] = cmd
            self._logger.info("Omega: Got Slicer Profile: %s" % self.header[2])
        elif "O24" in cmd:
            self.header[3] = cmd
            self._logger.info("Omega: Got PPM Adjustment: %s" % self.header[3])
        elif "O25" in cmd:
            self.header[4] = cmd
            self._logger.info("Omega: Got MU: %s" % self.header[4])
            drives = self.header[4][4:].split(" ")
            for index, drive in enumerate(drives):
                if "D1" in drive:
                    if index == 0:
                        drives[index] = "U60"
                    elif index == 1:
                        drives[index] = "U61"
                    elif index == 2:
                        drives[index] = "U62"
                    elif index == 3:
                        drives[index] = "U63"
            self.drivesInUse = list(
                filter(lambda drive: drive != "D0", drives))
            self._logger.info("Used Drives: %s" % self.drivesInUse)
        elif "O26" in cmd:
            self.header[5] = cmd
            self.msfNS = int(cmd[5:], 16)
            self._logger.info("Omega: Got NS: %s" % self.header[5])
            self.updateUI()
        elif "O27" in cmd:
            self.header[6] = cmd
            self._logger.info("Omega: Got NP: %s" % self.header[6])
        elif "O28" in cmd:
            self.msfNA = cmd[5:]
            self.nAlgorithms = int(self.msfNA)
            self.header[7] = cmd
            self._logger.info("Omega: Got NA: %s" % self.header[7])
        elif "O29" in cmd:
            self.header[8] = cmd
            self._logger.info("Omega: Got NH: %s" % self.header[8])
        elif "O30" in cmd:
            splice = (int(cmd[5:6]), cmd[8:])
            self.splices.append(splice)
            self._logger.info("Omega: Got splice D: %s, dist: %s" %
                              (splice[0], splice[1]))
        elif "O32" in cmd:
            self.algorithms.append(cmd)
            self._logger.info("Omega: Got algorithm: %s" % cmd[4:])
        elif "O9" in cmd and "O99" not in cmd:
            # reset values
            self.resetOmega()
            self.enqueueCmd(cmd)
        else:
            self._logger.info("Omega: Got an Omega command '%s'" % cmd)
            self.enqueueCmd(cmd)

    def changeAlertSettings(self, condition):
        self._settings.set(["palette2Alerts"], condition)
        self._settings.save()
