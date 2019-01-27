import serial
import serial.tools.list_ports
import glob
import time
import threading
import subprocess
import os
import binascii
import sys
from subprocess import call
from Queue import Queue


class Omega():
    def __init__(self, plugin):
        self._logger = plugin._logger
        self._printer = plugin._printer
        self._plugin_manager = plugin._plugin_manager
        self._identifier = plugin._identifier
        self._settings = plugin._settings

        self.ports = []
        self.selectedPort = ""

        self.writeQueue = Queue()

        self.resetVariables()
        self.resetConnection()

        # Tries to automatically connect to palette first
        if self._settings.get(["autoconnect"]):
            self.startConnectionThread()

        # SKELLATORE
        self.ShowPingPongOnPrinter = self._settings.get(["ShowPingPongOnPrinter"]) or True
        self.FeedrateControl = self._settings.get(["FeedrateControl"]) or True
        self.FeedrateSlowed = self._settings.get(["FeedrateSlowed"]) or False
        self.FeedrateNormalPct = self._settings.get(["FeedrateNormalPct"]) or 100
        self.FeedrateSlowPct = self._settings.get(["FeedrateSlowPct"]) or 80

        self.splicecore_switch = False
        self.buffer_switch = False
        self.filament_input_1_switch = False
        self.filament_input_2_switch = False
        self.filament_input_3_switch = False
        self.filament_input_4_switch = False
        self.cutter_switch = False

        # /SKELLATORE

    def getAllPorts(self):
        baselist = []

        if 'win32' in sys.platform:
            # use windows com stuff
            self._logger.info("Using a windows machine")
            for port in serial.tools.list_ports.grep('.*0403:6015.*'):
                self._logger.info("got port %s" % port.device)
                baselist.append(port.device)

        baselist = baselist \
            + glob.glob('/dev/serial/by-id/*FTDI*') \
            + glob.glob('/dev/*usbserial*') \

        baselist = self.getRealPaths(baselist)
        # get unique values only
        baselist = list(set(baselist))
        return baselist

    def displayPorts(self, condition):
        # only change settings if user is opening the list of ports
        if "opening" in condition:
            self._settings.set(["autoconnect"], False, force=True)
        self.ports = self.getAllPorts()
        self._logger.info(self.ports)
        if self.ports and not self.selectedPort:
            self.selectedPort = self.ports[0]
        self._logger.info(self.selectedPort)
        self._plugin_manager.send_plugin_message(
            self._identifier, {"command": "ports", "data": self.ports})
        self._plugin_manager.send_plugin_message(
            self._identifier, {"command": "selectedPort", "data": self.selectedPort})

    def getRealPaths(self, ports):
        self._logger.info(ports)
        for index, port in enumerate(ports):
            port = os.path.realpath(port)
            ports[index] = port
        self._logger.info(ports)
        return ports

    def isPrinterPort(self, selected_port):
        selected_port = os.path.realpath(selected_port)
        printer_port = self._printer.get_current_connection()[1]
        self._logger.info("Trying %s" % selected_port)
        self._logger.info(printer_port)
        # because ports usually have a second available one (.tty or .cu)
        printer_port_alt = ""
        if printer_port == None:
            return False
        else:
            if "tty." in printer_port:
                printer_port_alt = printer_port.replace("tty.", "cu.", 1)
            elif "cu." in printer_port:
                printer_port_alt = printer_port.replace("cu.", "tty.", 1)
            self._logger.info(printer_port_alt)
            if selected_port == printer_port or selected_port == printer_port_alt:
                return True
            else:
                return False

    def connectOmega(self, port):
        if self.connected is False:
            self.ports = self.getAllPorts()
            self._logger.info("Potential ports: %s" % self.ports)
            if len(self.ports) > 0:
                if not port:
                    port = self.ports[0]
                if self.isPrinterPort(port):
                    self._logger.info(
                        "This is the printer port. Will not connect to this.")
                    self.updateUI()
                else:
                    try:
                        self.omegaSerial = serial.Serial(
                            port, 250000, timeout=0.5)
                        self.connected = True
                        self.tryHeartbeat(port)
                    except:
                        self._logger.info(
                            "Another resource is connected to port")
                        self.updateUI()
            else:
                self._logger.info("Unable to find port")
                self.updateUI()
        else:
            self._logger.info("Already Connected")
            self.updateUI()

    def tryHeartbeat(self, port):
        if self.connected:
            self.connected = False
            self.startReadThread()
            self.startWriteThread()
            self.enqueueCmd("O99")

            timeout = 5
            timeout_start = time.time()
            # Wait for Palette to respond with a handshake within 5 seconds
            while time.time() < timeout_start + timeout:
                if self.heartbeat:
                    self.connected = True
                    self._logger.info("Connected to Omega")
                    self.selectedPort = port
                    self._plugin_manager.send_plugin_message(
                        self._identifier, {"command": "selectedPort", "data": self.selectedPort})
                    self.updateUI()
                    break
                else:
                    time.sleep(0.01)
            if not self.heartbeat:
                self._logger.info(
                    "Palette is not turned on OR this is not the serial port for Palette.")
                self.resetVariables()
                self.resetConnection()
                self.updateUI()

    def tryHeartbeatBeforePrint(self):
        self.heartbeat = False
        self.enqueueCmd("O99")
        self.printHeartbeatCheck = "Checking"

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
                # SKELLATORE
                self.advanced_parse_line(line)
                # /SKELLATORE
                if line:
                    self._logger.info("Omega: read in line: %s" % line)
                if 'O20' in line:
                    # send next line of data
                    self.sendNextData(int(line[5]))
                    if "D5" in line:
                        self._logger.info("FIRST TIME USE WITH PALETTE")
                        self.firstTime = True
                        self.updateUI()
                elif "O34" in line:
                    commands = [command.strip() for command in line.split('D')]
                    nature = commands[1]
                    if nature == "0":
                        self._logger.info("REJECTING PING")
                    # if ping
                    elif nature == "1":
                        percent = commands[2]
                        number = int(commands[3], 16)
                        current = {"number": number, "percent": percent}
                        self.pings.append(current)
                    # else pong
                    elif nature == "2":
                        percent = commands[2]
                        number = int(commands[3], 16)
                        current = {"number": number, "percent": percent}
                        self.pongs.append(current)
                    self.updateUI()
                elif "O40" in line:
                    self.printPaused = False
                    self.currentStatus = "Preparing splices"
                    self.actualPrintStarted = True
                    self.updateUI()
                    self._printer.toggle_pause_print()
                    self._logger.info("Splices being prepared.")
                elif "O50" in line:
                    self.sendAllMCFFilenamesToOmega()
                elif "O53" in line:
                    if "D1" in line:
                        index_to_print = int(line[8:], 16)
                        file = self.allMCFFiles[index_to_print]
                        self.startPrintFromP2(file)
                elif "O88" in line:
                    error = int(line[5:], 16)
                    self._logger.info("ERROR %d DETECTED" % error)
                    self._printer.pause_print()
                    self._plugin_manager.send_plugin_message(
                        self._identifier, {"command": "error", "data": error})
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
                            self.currentStatus = "Palette work completed: all splices prepared"
                            self.updateUI()
                            self._logger.info("Palette work is done.")
                        elif "D2" in line:
                            self._logger.info("CANCELLING START")
                            self._printer.cancel_print()
                            self.currentStatus = "Cancelling print"
                            self.updateUI()
                        elif "D3" in line:
                            self._logger.info("CANCELLING END")
                            self.currentStatus = "Print cancelled"
                            self.updateUI()
                elif "Connection Okay" in line:
                    self.heartbeat = True
                elif "UI:" in line:
                    if "Ponging" in line:
                        self.inPong = True
                    elif "Finished Pong" in line:
                        self.inPong = False
            serialConnection.close()
        except Exception as e:
            # Something went wrong with the connection to Palette2
            print(e)

    def omegaWriteThread(self, serialConnection):
        self._logger.info("Omega Write Thread: Starting Thread")
        while self.writeThreadStop is False:
            try:
                line = self.writeQueue.get(True, 0.5)
                self.lastCommandSent = line
                line = line.strip()
                line = line + "\n"
                self._logger.info("Omega Write Thread: Sending: %s" % line)
                serialConnection.write(line.encode())
                self._logger.info(line.encode())
                if "O99" in line:
                    self._logger.info("GOT A O99")
                    while self.printHeartbeatCheck == "Checking":
                        self._logger.info("WAITING FOR HEARTBEAT")
                        time.sleep(1)
            except:
                pass
        self.writeThread = None

    def omegaConnectionThread(self):
        while self.connectionThreadStop is False:
            if self.connected is False:
                self.connectOmega(self.selectedPort)
            time.sleep(1)

    def enqueueCmd(self, line):
        self.writeQueue.put(line)

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

    def updateUI(self):
        self._logger.info("Sending UIUpdate from Palette")
        self._plugin_manager.send_plugin_message(
            self._identifier, {"command": "printHeartbeatCheck", "data": self.printHeartbeatCheck})
        self._plugin_manager.send_plugin_message(
            self._identifier, {"command": "pings", "data": self.pings})
        self._plugin_manager.send_plugin_message(
            self._identifier, {"command": "pongs", "data": self.pongs})
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:ActualPrintStarted=%s" % self.actualPrintStarted)
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:Palette2SetupStarted=%s" % self.palette2SetupStarted)
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:AutoConnect=%s" % self._settings.get(["autoconnect"]))
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:FirstTime=%s" % self.firstTime)
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:PrinterCon=%s" % self.printerConnection)
        self._plugin_manager.send_plugin_message(
            self._identifier, "UI:DisplayAlerts=%s" % self._settings.get(["palette2Alerts"]))
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
        # SKELLATORE
        self.advanced_updateUI()
        # /SKELLATORE


    def sendNextData(self, dataNum):
        if dataNum == 0:
            self.enqueueCmd(self.header[self.sentCounter])
            self._logger.info("Omega: Sent '%s'" % self.sentCounter)
            self.sentCounter = self.sentCounter + 1
        elif dataNum == 2:
            self._logger.info(
                "Sending ping: %s to Palette on request" % self.currentPingCmd)
            self.enqueueCmd(self.currentPingCmd)
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
        elif dataNum == 8:
            self._logger.info("Need to resend last line")
            self.enqueueCmd(self.lastCommandSent)

    def handlePing(self, pingCmd):
        self.currentPingCmd = pingCmd
        self.enqueueCmd("O31")
        self._logger.info("Got a ping cmd, saving it")

    def resetConnection(self):
        self._logger.info("Resetting read and write threads")

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
        self.lastCommandSent = ""
        self.currentPingCmd = ""
        self.palette2SetupStarted = False
        self.allMCFFiles = []
        self.actualPrintStarted = False
        self.totalPings = 0
        self.pings = []
        self.pongs = []
        self.printHeartbeatCheck = ""

        self.filename = ""

        self.connected = False
        self.readThread = None
        self.writeThread = None
        self.connectionThread = None
        self.connectionStop = False
        self.heartbeat = False

        # SKELLATORE
        self.advanced_reset_values()
        # /SKELLATORE

    def resetPrintValues(self):
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
        self.lastCommandSent = ""
        self.currentPingCmd = ""
        self.palette2SetupStarted = False
        self.allMCFFiles = []
        self.actualPrintStarted = False
        self.totalPings = 0
        self.pings = []
        self.pongs = []
        self.printHeartbeatCheck = ""

        self.filename = ""

        # SKELLATORE
        self.advanced_reset_print_values()
        # /SKELLATORE

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

    def sendPrintStart(self):
        self._logger.info("Omega toggle pause")
        self._printer.toggle_pause_print()

    def gotOmegaCmd(self, cmd):
        if "O0" in cmd:
            self.enqueueCmd("O0")
        elif "O1 " in cmd:
            timeout = 5
            timeout_start = time.time()
            # Wait for Palette to respond with a handshake within 5 seconds
            while not self.heartbeat and time.time() < timeout_start + timeout:
                pass
            if self.heartbeat:
                self._logger.info("Palette did respond to O99")
                self.enqueueCmd(cmd)
                self.currentStatus = "Initializing ..."
                self.palette2SetupStarted = True
                self.printHeartbeatCheck = "P2Responded"
                self.updateUI()
                self.printHeartbeatCheck = ""
            else:
                self._logger.info("Palette did not respond to O99")
                self.printHeartbeatCheck = "P2NotConnected"
                self.updateUI()
                self.printHeartbeatCheck = ""
                self.disconnect()
                self._logger.info("NO P2 detected. Cancelling print")
                self._printer.cancel_print()
        elif "O21" in cmd:
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
            self.totalPings = int(cmd[5:], 16)
            self._logger.info("Omega: Got NP: %s" % self.header[6])
            self._logger.info("TOTAL PINGS: %s" % self.totalPings)
            self.updateUI()
        elif "O28" in cmd:
            self.msfNA = cmd[5:]
            self.nAlgorithms = int(self.msfNA, 16)
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
        elif "O9" is cmd:
            # reset values
            self.resetOmega()
            self.enqueueCmd(cmd)
        else:
            self._logger.info("Omega: Got an Omega command '%s'" % cmd)
            self.enqueueCmd(cmd)

    def changeAlertSettings(self, condition):
        self._settings.set(["palette2Alerts"], condition, force=True)

    def sendAllMCFFilenamesToOmega(self):
        self.getAllMCFFilenames()
        for file in self.allMCFFiles:
            filename = file.replace(".mcf.gcode", "")
            self.enqueueCmd("O51 D" + filename)
        self.enqueueCmd("O52")

    def getAllMCFFilenames(self):
        self.allMCFFiles = []
        uploads_path = self._settings.global_get_basefolder("uploads")
        self.iterateThroughFolder(uploads_path, "")

    def iterateThroughFolder(self, folder_path, folder_name):
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            # If file is an .mcf.gcode file
            if os.path.isfile(file_path) and ".mcf.gcode" in file:
                if folder_name != "":
                    cumulative_folder_name = folder_name + "/" + file
                else:
                    cumulative_folder_name = file
                self.allMCFFiles.append(cumulative_folder_name)
            # If file is a folder, go through that folder again
            # elif os.path.isdir(file_path):
            #     if folder_name != "":
            #         cumulative_folder_name = folder_name + "/" + file
            #     else:
            #         cumulative_folder_name = file
            #     self.iterateThroughFolder(file_path, cumulative_folder_name)

    def startPrintFromP2(self, file):
        self._printer.select_file(file, False, printAfterSelect=True)

    def sendErrorReport(self, send):
        if send:
            self._logger.info("SENDING ERROR REPORT TO MOSAIC")
            call(["tail -n 200 ~/.octoprint/logs/octoprint.log > ~/.mosaicdata/error_report.log"], shell=True)
        else:
            self._logger.info("NOT SENDING ERROR REPORT TO MOSAIC")

    def startPrintFromHub(self):
        self._logger.info("START PRINT FROM HERE")
        self.enqueueCmd("O39")

    def sendErrorReport(self, send):
        if send:
            self._logger.info("SENDING ERROR REPORT TO MOSAIC")
            call(["tail -n 200 ~/.octoprint/logs/octoprint.log > ~/.mosaicdata/error_report.log"], shell=True)
        else:
            self._logger.info("NOT SENDING ERROR REPORT TO MOSAIC")

    def startPrintFromHub(self):
        self._logger.info("START PRINT FROM HERE")
        self.enqueueCmd("O39")

    # SKELLATORE
    def advanced_reset_values(self):
        self.FeedrateSlowed = False
        self.FeedrateControl = self._settings.get(["FeedrateControl"])
        self.FeedrateNormalPct = self._settings.get(["FeedrateNormalPct"])
        self.FeedrateSlowPct = self._settings.get(["FeedrateSlowPct"])
        self.ShowPingPongOnPrinter = self._settings.get(["ShowPingPongOnPrinter"])

    def advanced_reset_print_values(self):
        pass

    def advanced_parse_line(self, line):
        # self._logger.info('ADVANCED:' + line)
        last_status_received = False
        try:
            advanced_status = ''
            if 'O97 U25 D0' in line:
                self._logger.info('ADVANCED: SPLICE START')
                if self.FeedrateControl:
                    self._logger.info('ADVANCED: Feed-rate Control: ACTIVATED')
                    advanced_status = 'Slice Starting: Speed -> SLOW(%s)' % self.FeedrateSlowPct
                    # Splice Start
                    if self.FeedrateSlowed:
                        # Feedrate already slowed, set it again to be safe.
                        try:
                            self._logger.info("ADVANCED: Feed-rate SLOW - ACTIVE* (%s)" % self.FeedrateSlowPct)
                            self._printer.commands('M220 S%s' % self.FeedrateSlowPct)
                        except ValueError:
                            self._logger.info('ADVANCED: Unable to Update Feed-Rate -> SLOW :: ' + str(ValueError))
                    else:
                        self._logger.info('ADVANCED: Feed-rate SLOW - ACTIVE (%s)' % self.FeedrateSlowPct)
                        try:
                            self._printer.commands('M220 S%s B' % self.FeedrateSlowPct)
                            self.FeedrateSlowed = True
                        except ValueError:
                            self._logger.info('ADVANCED: Unable to Update Feed-Rate -> SLOW :: ' + str(ValueError))
                    self._plugin_manager.send_plugin_message(self._identifier, "ADVANCED:FEEDRATESLOWED=True")
                    self.updateUI()
                else:
                    self._logger.info('ADVANCED: Feed-rate Control: INACTIVE')
                    self.updateUI()
            if 'O97 U25 D1' in line:
                self._logger.info('ADVANCED: SPLICE END')
                if self.FeedrateControl:
                    self._logger.info('ADVANCED: Feed-rate NORMAL - ACTIVE (%s)' % self.FeedrateNormalPct)
                    advanced_status = 'Slice Finished: Speed -> NORMAL(%s) ' % self.FeedrateNormalPct
                    try:
                        self._printer.commands('M220 S%s' % self.FeedrateNormalPct)
                        self.FeedrateSlowed = False
                    except ValueError:
                        self._logger.info('ADVANCED: Unable to Update Feed-Rate -> NORMAL :: ' + str(ValueError))
                    self._plugin_manager.send_plugin_message(self._identifier, "ADVANCED:FEEDRATESLOWED=False")
                    self.updateUI()
                else:
                    self._logger.info('ADVANCED: Feed-Rate Control: INACTIVE')
                    self.updateUI()
            if 'O34 D1' in line:
                self._logger.info("ADVANCED: Ping! Pong!")
                self._logger.info("ADVANCED: Show on Printer: %s" % self.ShowPingPongOnPrinter)
                # filter out ping offset information
                if self.ShowPingPongOnPrinter:
                    idx = line.find("O34")
                    parms = line[idx+7:].split(" ")
                    try:
                        self._printer.commands("M117 Ping {} {}pct".format(str(int(parms[1][1:],16)), parms[0][1:]))
                        self.updateUI()
                    except ValueError:
                        self._printer.commands("M117 {}".format(line[idx+7:]))
                        self.updateUI()
            if 'O68 D2' in line:
                # Switch Status
                if 'O68 D2 D0' in line:
                    if 'D2 D0 D1' in line:
                        self.splicecore_switch = True
                    else:
                        self.splicecore_switch = False
                if 'O68 D2 D1' in line:
                    if 'D2 D1 D1' in line:
                        self.buffer_switch = True
                    else:
                        self.buffer_switch = False
                if 'O68 D2 D2' in line:
                    if 'D2 D2 D1' in line:
                        self.filament_input_1_switch = True
                    else:
                        self.filament_input_1_switch = False
                if 'O68 D2 D3' in line:
                    if 'D2 D3 D1' in line:
                        self.filament_input_2_switch = True
                    else:
                        self.filament_input_2_switch = False
                if 'O68 D2 D4' in line:
                    if 'D2 D4 D1' in line:
                        self.filament_input_3_switch = True
                    else:
                        self.filament_input_3_switch = False
                if 'O68 D2 D5' in line:
                    if 'D2 D5 D1' in line:
                        self.filament_input_4_switch = True
                    else:
                        self.filament_input_4_switch = False
                if 'O68 D2 D6' in line:
                    if 'D2 D6 D1' in line:
                        self.cutter_switch = True
                    else:
                        self.cutter_switch = False
                    last_status_received = True
                switch_status = (str(self.splicecore_switch) + ',' + str(self.buffer_switch) + ','
                                 + str(self.filament_input_1_switch) + ',' + str(self.filament_input_2_switch) + ','
                                 + str(self.filament_input_3_switch) + ',' + str(self.filament_input_4_switch) + ','
                                 + str(self.cutter_switch))
                if last_status_received:
                    self._logger.info("ADVANCED: SWITCHES: %s" % switch_status)
                    self._plugin_manager.send_plugin_message(self._identifier, "ADVANCED:UISWITCHES=%s" % switch_status)
            if advanced_status != '':
                self._plugin_manager.send_plugin_message(self._identifier, "ADVANCED:UIMESSAGE=%s" % advanced_status)
                self.enqueueCmd("O68 D2")  # Queue Switch Status

        except Exception as e:
            # Something went wrong with the connection to Palette2
            print(e)

    def advanced_updateUI(self):
        try:
            self._plugin_manager.send_plugin_message(self._identifier, "ADVANCED:SHOWPINGPONGONPRINTER=%s" %
                                                     self._settings.get(["ShowPingPongOnPrinter"]))
            self._plugin_manager.send_plugin_message(self._identifier, "ADVANCED:FEEDRATECONTROL=%s" %
                                                     self._settings.get(["FeedrateControl"]))
            self._plugin_manager.send_plugin_message(self._identifier, "ADVANCED:FEEDRATESLOWED=%s" %
                                                     self._settings.get(["FeedrateSlowed"]))
            self._plugin_manager.send_plugin_message(self._identifier, "ADVANCED:FEEDRATENORMALPCT=%s" %
                                                     self._settings.get(["FeedrateNormalPct"]))
            self._plugin_manager.send_plugin_message(self._identifier, "ADVANCED:FEEDRATESLOWPCT=%s" %
                                                     self._settings.get(["FeedrateSlowPct"]))
        except Exception as e:
            print(e)

    def changeShowPingPongOnPrinter(self, condition):
        try:
            self._settings.set(["ShowPingPongOnPrinter"], condition, force=True)
            self._settings.save(force=True)
            self._logger.info("ADVANCED: ShowPingPongOnPrinter -> '%s' '%s'" % (condition, self._settings.get(["ShowPingPongOnPrinter"])))
        except Exception as e:
            print(e)

    def changeFeedrateControl(self, condition):
        try:
            self._settings.set(["FeedrateControl"], condition, force=True)
            self._settings.save(force=True)
            self._logger.info("ADVANCED: FeedrateControl -> '%s' '%s'" % (condition, self._settings.get(["FeedrateControl"])))
        except Exception as e:
            print(e)

    def changeFeedrateSlowed(self, condition):
        try:
            self._settings.set(["FeedrateSlowed"], condition, force=True)
            self._settings.save(force=True)
            self._logger.info("ADVANCED: FeedrateSlowed -> '%s' '%s'" % (condition, self._settings.get(["FeedrateSlowed"])))
        except Exception as e:
            print(e)

    def changeFeedrateNormalPct(self, value):
        try:
            self._settings.set(["FeedrateNormalPct"], value)
            self._settings.save(force=True)
            self._logger.info("ADVANCED: FeedrateNormalPct -> '%s' '%s'" % (value, self._settings.get(["FeedrateNormalPct"])))
            if not self._settings.get(["FeedrateSlowed"]):
                self._printer.commands('M220 S%s' % value)
        except Exception as e:
            print(e)

    def changeFeedrateSlowPct(self, value):
        try:
            self._settings.set(["FeedrateSlowPct"], value)
            self._settings.save(force=True)
            self._logger.info("ADVANCED: FeedrateSlowPct -> '%s' '%s'" % (value, self._settings.get(["FeedrateSlowPct"])))
            if self._settings.get(["FeedrateSlowed"]):
                self._printer.commands('M220 S%s' % value)
        except Exception as e:
            print(e)

    def advanced_on_event(self, event, payload):
        try:
            if "ClientOpened" or "SettingsUpdated" in event:
                self.ShowPingPongOnPrinter = self._settings.get(["ShowPingPongOnPrinter"])
                self.FeedrateControl = self._settings.get(["FeedrateControl"])
                self.FeedrateSlowed = self._settings.get(["FeedrateSlowed"])
                self.FeedrateNormalPct = self._settings.get(["FeedrateNormalPct"])
                self.FeedrateSlowPct = self._settings.get(["FeedrateSlowPct"])
                self.enqueueCmd("O68 D2")  # Queue Switch Status
        except Exception as e:
            print(e)

    def advanced_api_command(self, command, data):
        try:
            if command == "changeShowPingPongOnPrinter":
                self.changeShowPingPongOnPrinter(data["condition"])
            if command == "changeFeedrateControl":
                self.changeFeedrateControl(data["condition"])
            if command == "changeFeedrateNormalPct":
                self.changeFeedrateNormalPct(data["value"])
            if command == "changeFeedrateSlowPct":
                self.changeFeedrateSlowPct(data["value"])
            self.palette.updateUI()
        except Exception as e:
            print(e)
    # /SKELLATORE
