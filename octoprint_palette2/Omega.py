import serial
import serial.tools.list_ports
import glob
import time
import threading
import subprocess
import os
import binascii
import sys
import json
import requests
from ruamel.yaml import YAML
yaml = YAML(typ="safe")
from dotenv import load_dotenv
env_path = os.path.abspath(".") + "/.env"
if os.path.abspath(".") is "/":
    env_path = "/home/pi/.env"
load_dotenv(env_path)
BASE_URL_API = os.getenv("DEV_BASE_URL_API", "api.canvas3d.io/")
from subprocess import call
from Queue import Queue, Empty


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
            self._settings.save(force=True)
            self.updateUI({"command": "autoConnect", "data": self._settings.get(["autoconnect"])})
        self.ports = self.getAllPorts()
        self._logger.info("All ports: %s" % self.ports)
        if self.ports and not self.selectedPort:
            self.selectedPort = self.ports[0]
        self._logger.info("Selected port: %s" % self.selectedPort)
        self.updateUI({"command": "ports", "data": self.ports})
        self.updateUI({"command": "selectedPort", "data": self.selectedPort})

    def getRealPaths(self, ports):
        self._logger.info("Paths: %s" % ports)
        for index, port in enumerate(ports):
            port = os.path.realpath(port)
            ports[index] = port
        return ports

    def isPrinterPort(self, selected_port):
        selected_port = os.path.realpath(selected_port)
        printer_port = self._printer.get_current_connection()[1]
        self._logger.info("Trying port: %s" % selected_port)
        self._logger.info("Printer port: %s" % printer_port)
        # because ports usually have a second available one (.tty or .cu)
        printer_port_alt = ""
        if printer_port == None:
            return False
        else:
            if "tty." in printer_port:
                printer_port_alt = printer_port.replace("tty.", "cu.", 1)
            elif "cu." in printer_port:
                printer_port_alt = printer_port.replace("cu.", "tty.", 1)
            self._logger.info("Printer port alt: %s" % printer_port_alt)
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
                    self._logger.info("This is the printer port. Will not connect to this.")
                    self.updateUIAll()
                else:
                    default_baudrate = self._settings.get(["baudrate"])
                    second_baudrate = self.getSecondBaudrate(default_baudrate)
                    try:
                        self.omegaSerial = serial.Serial(port, default_baudrate, timeout=0.5)
                        if not self.tryHeartbeat(port, default_baudrate):
                            self._logger.info("Not the %s baudrate" % default_baudrate)
                            self.omegaSerial = serial.Serial(port, second_baudrate, timeout=0.5)
                            if not self.tryHeartbeat(port, second_baudrate):
                                self._logger.info("Not the %s baudrate" % second_baudrate)
                                self.updateUIAll()
                    except:
                        self._logger.info("Another resource is connected to port")
                        self.updateUIAll()
            else:
                self._logger.info("Unable to find port")
                self.updateUIAll()
        else:
            self._logger.info("Already Connected")
            self.updateUIAll()

    def getSecondBaudrate(self, default_baudrate):
        if default_baudrate == 115200:
            return 250000
        elif default_baudrate == 250000:
            return 115200

    def tryHeartbeat(self, port, baudrate):
        self._logger.info("Trying baudrate: %s" % baudrate)
        self.startReadThread()
        self.startWriteThread()
        self.enqueueCmd("\n")
        self.enqueueCmd("O99")

        timeout = 3
        timeout_start = time.time()
        # Wait for Palette to respond with a handshake within 3 seconds
        while time.time() < timeout_start + timeout:
            if self.heartbeat:
                self.connected = True
                self._logger.info("Connected to Omega")
                self.selectedPort = port
                self._settings.set(["baudrate"], baudrate, force=True)
                self._settings.save(force=True)
                self.updateUI({"command": "selectedPort", "data": self.selectedPort})
                self.updateUIAll()
                return True
            else:
                time.sleep(0.01)
        if not self.heartbeat:
            self._logger.info("Palette is not turned on OR this is not the serial port for Palette OR this is the wrong baudrate.")
            self.resetOmega()
            return False

    def tryHeartbeatBeforePrint(self):
        self.heartbeat = False
        self.enqueueCmd("\n")
        self.enqueueCmd("O99")
        self.printHeartbeatCheck = "Checking"

    def setFilename(self, name):
        self.filename = name

    def connectWifi(self, wifiSSID, wifiPASS):
        lines = open('/etc/wpa_supplicant/wpa_supplicant.conf').readlines()
        open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w').writelines(lines[0:-5])

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
        while self.readThreadStop is False:
            try:
                line = serialConnection.readline()
                if line:
                    command = self.parseLine(line)
                    if command != None:
                        self._logger.info("Omega: read in line: %s" % command)
                        if command["command"] == 20:
                            if command["total_params"] > 0:
                                if command["params"][0] == "D5":
                                    self._logger.info("FIRST TIME USE WITH PALETTE")
                                    self.firstTime = True
                                    self.updateUI({"command": "firstTime", "data": self.firstTime})
                                else:
                                    try:
                                        param_1 = int(command["params"][0][1:])
                                        # send next line of data
                                        self.sendNextData(param_1)
                                    except:
                                        self._logger.info("Error occured with: %s" % command)
                        elif command["command"] == 34:
                            if command["total_params"] == 1:
                                # if reject ping
                                if command["params"][0] == "D0":
                                    self._logger.info("REJECTING PING")
                            elif command["total_params"] > 2:
                                # if ping
                                if command["params"][0] == "D1":
                                    percent = command["params"][1][1:]
                                    try:
                                        number = int(command["params"][2][1:], 16)
                                        current = {"number": number, "percent": percent}
                                        self.pings.append(current)
                                        self.updateUI({"command": "pings", "data": self.pings})
                                    except:
                                        self._logger.info("Ping number invalid: %s" % command)
                                # else pong
                                elif command["params"][0] == "D2":
                                    percent = command["params"][1][1:]
                                    try:
                                        number = int(command["params"][2][1:], 16)
                                        current = {"number": number, "percent": percent}
                                        self.pongs.append(current)
                                        self.updateUI({"command": "pongs", "data": self.pongs})
                                    except:
                                        self._logger.info("Pong number invalid: %s" % command)
                        elif command["command"] == 40:
                            self.currentStatus = "Preparing splices"
                            self.actualPrintStarted = True
                            self.printPaused = False
                            self.updateUI({"command": "currentStatus", "data": self.currentStatus})
                            self.updateUI({"command": "actualPrintStarted", "data": self.actualPrintStarted})
                            self.updateUI({"command": "alert", "data": "printStarted"})
                            self._printer.toggle_pause_print()
                            self.updateUI({"command": "printPaused", "data": self.printPaused})
                            self._logger.info("Splices being prepared.")
                        elif command["command"] == 50:
                            self.sendAllMCFFilenamesToOmega()
                        elif command["command"] == 53:
                            if command["total_params"] > 1:
                                if command["params"][0] == "D1":
                                    try:
                                        index_to_print = int(command["params"][1][1:], 16)
                                        file = self.allMCFFiles[index_to_print]
                                        self.startPrintFromP2(file)
                                    except:
                                        self._logger.info("Print from P2 command invalid: %s" % command)
                        elif command["command"] == 88:
                            if command["total_params"] > 0:
                                try:
                                    error = int(command["params"][0][1:], 16)
                                    self._logger.info("ERROR %d DETECTED" % error)
                                    if os.path.isdir(os.path.expanduser('~') + "/.mosaicdata/"):
                                        self._printer.pause_print()
                                        self.updateUI({"command": "error", "data": error})
                                except:
                                    self._logger.info("Error command invalid: %s" % command)
                        elif command["command"] == 97:
                            if command["total_params"] > 0:
                                if command["params"][0] == "U0":
                                    if command["total_params"] > 1:
                                        if command["params"][1] == "D0":
                                            self.currentStatus = "Palette work completed: all splices prepared"
                                            self.updateUI({"command": "currentStatus", "data": self.currentStatus})
                                            self._logger.info("Palette work is done.")
                                        elif command["params"][1] == "D2":
                                            self._logger.info("P2 CANCELLING START")
                                            if not self.cancelFromHub and not self.cancelFromP2:
                                                self.cancelFromP2 = True
                                                self._printer.cancel_print()
                                            self.currentStatus = "Cancelling print"
                                            self.updateUI({"command": "currentStatus", "data": self.currentStatus})
                                            self.updateUI({"command": "alert", "data": "cancelling"})
                                        elif command["params"][1] == "D3":
                                            self._logger.info("P2 CANCELLING END")
                                            self.currentStatus = "Print cancelled"
                                            self.updateUI({"command": "currentStatus", "data": self.currentStatus})
                                            self.updateUI({"command": "alert", "data": "cancelled"})
                                            self.cancelFromHub = False
                                            self.cancelFromP2 = False
                                elif command["params"][0] == "U25":
                                    if command["total_params"] > 2:
                                        if command["params"][1] == "D1":
                                            try:
                                                self.currentSplice = int(command["params"][2][1:], 16)
                                                self._logger.info("Current splice: %s" % self.currentSplice)
                                                self.updateUI({"command": "currentSplice", "data": self.currentSplice})
                                            except:
                                                self._logger.info("Splice command invalid: %s" % command)
                                elif command["params"][0] == "U26":
                                    if command["total_params"] > 1:
                                        try:
                                            self.filamentLength = int(command["params"][1][1:], 16)
                                            self._logger.info("%smm used" % self.filamentLength)
                                            self.updateUI({"command": "filamentLength", "data": self.filamentLength})
                                        except:
                                            self._logger.info("Filament length update invalid: %s" % command)
                                elif command["params"][0] == "U39":
                                    if command["total_params"] == 1:
                                        self.currentStatus = "Loading filament into extruder"
                                        self.updateUI({"command": "alert", "data": "extruder"})
                                        self.updateUI({"command": "currentStatus", "data": self.currentStatus})
                                        self._logger.info("Filament must be loaded into extruder by user")
                                    elif command["params"][1][0:2] == "D-":
                                        try:
                                            self.amountLeftToExtrude = int(command["params"][1][2:])
                                            self._logger.info("%s mm left to extrude." % self.amountLeftToExtrude)
                                            self.updateUI({"command": "amountLeftToExtrude", "data": self.amountLeftToExtrude})
                                        except:
                                            self._logger.info("Filament extrusion update invalid: %s" % command)
                                    elif command["params"][1][0:2] == "D0":
                                        self.amountLeftToExtrude = 0
                                        self._logger.info("0" + "mm left to extrude.")
                                        self.updateUI({"command": "amountLeftToExtrude", "data": self.amountLeftToExtrude})
                                        if not self.cancelFromHub and not self.cancelFromP2:
                                            self.updateUI({"command": "alert", "data": "startPrint"})
                                        self.amountLeftToExtrude = ""
                                elif self.drivesInUse and command["params"][0] == self.drivesInUse[0]:
                                    if command["total_params"] > 1 and command["params"][1] == "D0":
                                        self.currentStatus = "Loading ingoing drives"
                                        self.updateUI({"command": "currentStatus", "data": self.currentStatus})
                                        self._logger.info("STARTING TO LOAD FIRST DRIVE")
                                elif self.drivesInUse and command["params"][0] == self.drivesInUse[-1]:
                                    if command["total_params"] > 1 and command["params"][1] == "D1":
                                        self.currentStatus = "Loading filament through outgoing tube"
                                        self.updateUI({"command": "currentStatus", "data": self.currentStatus})
                                        self.updateUI({"command": "alert", "data": "temperature"})
                                        self._logger.info("FINISHED LOADING LAST DRIVE")
            except Exception as e:
                # Something went wrong with the connection to Palette2
                self._logger.info("Palette 2 Read Thread error")
                self._logger.info(e)

    def omegaWriteThread(self, serialConnection):
        self._logger.info("Omega Write Thread: Starting Thread")
        while self.writeThreadStop is False:
            try:
                line = self.writeQueue.get(True, 0.5)
                if line:
                    self.lastCommandSent = line
                    line = line.strip()
                    line = line + "\n"
                    self._logger.info("Omega Write Thread: Sending: %s" % line)
                    serialConnection.write(line.encode())
                    self._logger.info(line.encode())
                    if "O99" in line:
                        self._logger.info("O99 sent to P2")
                        while self.printHeartbeatCheck == "Checking":
                            self._logger.info("WAITING FOR HEARTBEAT...")
                            time.sleep(1)
                else:
                    self._logger.info("Line is NONE")
            except Empty:
                pass
            except Exception as e:
                self._logger.info("Palette 2 Write Thread Error")
                self._logger.info(e)

    def omegaConnectionThread(self):
        while self.connectionThreadStop is False:
            if self.connected is False and not self._printer.is_printing():
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

    def cancel(self):
        self.enqueueCmd("O0")

    def updateUIAll(self):
        self._logger.info("Updating all UI variables")
        self.updateUI({"command": "printHeartbeatCheck", "data": self.printHeartbeatCheck}, True)
        self.updateUI({"command": "pings", "data": self.pings}, True)
        self.updateUI({"command": "pongs", "data": self.pongs}, True)
        self.updateUI({"command": "actualPrintStarted", "data": self.actualPrintStarted}, True)
        self.updateUI({"command": "palette2SetupStarted", "data": self.palette2SetupStarted}, True)
        self.updateUI({"command": "displaySetupAlerts", "data": self._settings.get(["palette2Alerts"])}, True)
        self.updateUI({"command": "autoConnect", "data": self._settings.get(["autoconnect"])}, True)
        self.updateUI({"command": "firstTime", "data": self.firstTime}, True)
        self.updateUI({"command": "currentStatus", "data": self.currentStatus}, True)
        self.updateUI({"command": "totalSplices", "data": self.msfNS}, True)
        self.updateUI({"command": "currentSplice", "data": self.currentSplice}, True)
        self.updateUI({"command": "p2Connection", "data": self.connected}, True)
        self.updateUI({"command": "filamentLength", "data": self.filamentLength}, True)
        self.updateUI({"command": "amountLeftToExtrude", "data": self.amountLeftToExtrude}, True)
        self.updateUI({"command": "printPaused", "data": self._printer.is_paused()}, True)

    def updateUI(self, data, log=None):
        if not log:
            self._logger.info("Updating UI")
        self._plugin_manager.send_plugin_message(self._identifier, data)

    def sendNextData(self, dataNum):
        if dataNum == 0:
            try:
                self.enqueueCmd(self.header[self.sentCounter])
                self._logger.info("Omega: Sent '%s'" % self.sentCounter)
                self.sentCounter = self.sentCounter + 1
            except:
                self._logger.info("Incorrect header information: %s" % self.header)
                self._logger.info("Sent counter: %s" % self.sentCounter)
        elif dataNum == 1:
            try:
                self._logger.info("Omega: send splice")
                splice = self.splices[self.spliceCounter]
                cmdStr = "O30 D%d D%s\n" % (int(splice[0]), splice[1])
                self.enqueueCmd(cmdStr)
                self.spliceCounter = self.spliceCounter + 1
            except:
                self._logger.info("Incorrect splice information: %s" % self.splices)
                self._logger.info("Splice counter: %s" % self.spliceCounter)
        elif dataNum == 2:
            self._logger.info("Sending ping: %s to Palette on request" % self.currentPingCmd)
            self.enqueueCmd(self.currentPingCmd)
        elif dataNum == 4:
            try:
                self._logger.info("Omega: send algo")
                self.enqueueCmd(self.algorithms[self.algoCounter])
                self._logger.info("Omega: Sent '%s'" % self.algorithms[self.algoCounter])
                self.algoCounter = self.algoCounter + 1
            except:
                self._logger.info("Incorrect algo information: %s" % self.algorithms)
                self._logger.info("Algo counter: %s" % self.algoCounter)
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
        self.header = [None] * 9
        self.splices = []
        self.algorithms = []
        self.filamentLength = 0
        self.currentStatus = ""
        self.drivesInUse = []
        self.amountLeftToExtrude = ""
        self.printPaused = ""
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
        self.cancelFromHub = False
        self.cancelFromP2 = False

        self.filename = ""

        self.connected = False
        self.readThread = None
        self.writeThread = None
        self.connectionThread = None
        self.connectionStop = False
        self.heartbeat = False

    def resetPrintValues(self):
        self.sentCounter = 0
        self.algoCounter = 0
        self.spliceCounter = 0

        self.msfCU = ""
        self.msfNS = "0"
        self.msfNA = "0"
        self.nAlgorithms = 0
        self.currentSplice = "0"
        self.header = [None] * 9
        self.splices = []
        self.algorithms = []
        self.filamentLength = 0
        self.currentStatus = ""
        self.drivesInUse = []
        self.amountLeftToExtrude = ""
        self.printPaused = ""
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
        self.cancelFromHub = False
        self.cancelFromP2 = False

        self.filename = ""

    def resetOmega(self):
        self.resetConnection()
        self.resetVariables()

    def shutdown(self):
        self._logger.info("Shutdown")
        self.disconnect()

    def disconnect(self):
        self._logger.info("Disconnecting from Palette")
        self.resetOmega()
        self.updateUIAll()

    def gotOmegaCmd(self, cmd):
        if "O1" not in cmd:
            if "O21" in cmd:
                self.header[0] = cmd
                self._logger.info("Omega: Got Version: %s" % self.header[0])
            elif "O22" in cmd:
                self.header[1] = cmd
                self._logger.info("Omega: Got Printer Profile: %s" % self.header[1])
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
                    if not "D0" in drive:
                        if index == 0:
                            drives[index] = "U60"
                        elif index == 1:
                            drives[index] = "U61"
                        elif index == 2:
                            drives[index] = "U62"
                        elif index == 3:
                            drives[index] = "U63"
                self.drivesInUse = list(filter(lambda drive: drive != "D0", drives))
                self._logger.info("Used Drives: %s" % self.drivesInUse)
            elif "O26" in cmd:
                self.header[5] = cmd
                try:
                    self.msfNS = int(cmd[5:], 16)
                    self._logger.info("Omega: Got NS: %s" % self.header[5])
                    self.updateUI({"command": "totalSplices", "data": self.msfNS})
                except:
                    self._logger.info("NS information not properly formatted: %s" % cmd)
            elif "O27" in cmd:
                self.header[6] = cmd
                try:
                    self.totalPings = int(cmd[5:], 16)
                    self._logger.info("Omega: Got NP: %s" % self.header[6])
                    self._logger.info("TOTAL PINGS: %s" % self.totalPings)
                except:
                    self._logger.info("NP information not properly formatted: %s" % cmd)
            elif "O28" in cmd:
                self.header[7] = cmd
                try:
                    self.msfNA = cmd[5:]
                    self.nAlgorithms = int(self.msfNA, 16)
                    self._logger.info("Omega: Got NA: %s" % self.header[7])
                except:
                    self._logger.info("NA information not properly formatted: %s" % cmd)
            elif "O29" in cmd:
                self.header[8] = cmd
                self._logger.info("Omega: Got NH: %s" % self.header[8])
            elif "O30" in cmd:
                try:
                    splice = (int(cmd[5:6]), cmd[8:])
                    self.splices.append(splice)
                    self._logger.info("Omega: Got splice D: %s, dist: %s" % (splice[0], splice[1]))
                except:
                    self._logger.info("Splice information not properly formatted: %s" % cmd)
            elif "O32" in cmd:
                self.algorithms.append(cmd)
                self._logger.info("Omega: Got algorithm: %s" % cmd[4:])
        elif "O1" in cmd:
            timeout = 4
            timeout_start = time.time()
            # Wait for Palette to respond with a handshake within 4 seconds
            while not self.heartbeat and time.time() < timeout_start + timeout:
                time.sleep(0.01)
            if self.heartbeat:
                self._logger.info("Palette did respond to O99")
                self.enqueueCmd(cmd)
                self.currentStatus = "Initializing ..."
                self.palette2SetupStarted = True
                self.printHeartbeatCheck = "P2Responded"
                self.printPaused = True
                self.updateUI({"command": "currentStatus", "data": self.currentStatus})
                self.updateUI({"command": "palette2SetupStarted", "data": self.palette2SetupStarted})
                self.updateUI({"command": "printHeartbeatCheck", "data": self.printHeartbeatCheck})
                self.updateUI({"command": "printPaused", "data": self.printPaused})
                self.printHeartbeatCheck = ""
            else:
                self._logger.info("Palette did not respond to O99")
                self.printHeartbeatCheck = "P2NotConnected"
                self.updateUI({"command": "printHeartbeatCheck", "data": self.printHeartbeatCheck})
                self.disconnect()
                self._logger.info("NO P2 detected. Cancelling print")
                self._printer.cancel_print()
        elif cmd == "O9":
            # reset values
            # self.resetOmega()
            self._logger.info("Omega: Soft resetting P2: %s" % cmd)
            self.enqueueCmd(cmd)
        else:
            self._logger.info("Omega: Got another Omega command '%s'" % cmd)
            self.enqueueCmd(cmd)

    def changeAlertSettings(self, condition):
        self._settings.set(["palette2Alerts"], condition, force=True)
        self._settings.save(force=True)
        self.updateUI({"command": "displaySetupAlerts", "data": self._settings.get(["palette2Alerts"])})

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
        self._logger.info("Received print command from P2")
        self._printer.select_file(file, False, printAfterSelect=True)

    def sendErrorReport(self, error_number, description):
        self._logger.info("SENDING ERROR REPORT TO MOSAIC")
        log_content = self.prepareErroReport(error_number, description)

        hub_id, hub_token = self.getHubData()
        url = "https://" + BASE_URL_API + "hubs/" + hub_id + "/log"
        payload = {
            "log": log_content
        }
        authorization = "Bearer " + hub_token
        headers = {"Authorization": authorization}
        try:
            response = requests.post(url, json=payload, headers=headers).json()
            if response.get("status") >= 300:
                self._logger.info(response)
            else:
                self._logger.info("Email sent successfully")
        except requests.exceptions.RequestException as e:
            self._logger.info(e)

    def prepareErroReport(self, error_number, description):
        error_report_path = os.path.expanduser('~') + "/.mosaicdata/error_report.log"

        # error number
        error_report_log = open(error_report_path, "w")
        error_report_log.write("===== ERROR %s =====\n\n" % error_number)

        # plugins + versions
        error_report_log.write("=== PLUGINS ===\n")
        plugins = self._plugin_manager.plugins.keys()
        for plugin in plugins:
            error_report_log.write("%s: %s\n" % (plugin, self._plugin_manager.get_plugin_info(plugin).version))

        # Hub or DIY
        error_report_log.write("\n=== TYPE ===\n")
        if os.path.isdir("/home/pi/.mosaicdata/turquoise/"):
            error_report_log.write("CANVAS HUB\n")
        else:
            error_report_log.write("DIY HUB\n")

        # description
        if description:
            error_report_log.write("\n=== USER ADDITIONAL DESCRIPTION ===\n")
            error_report_log.write(description + "\n")

        error_report_log.write("\n=== OCTOPRINT LOG ===\n")
        error_report_log.close()

        # OctoPrint log
        octoprint_log_path = os.path.expanduser('~') + "/.octoprint/logs/octoprint.log"
        linux_command = "tail -n 1000 %s >> %s" % (octoprint_log_path, error_report_path)
        call([linux_command], shell=True)

        data = ""
        with open(error_report_path, "r") as myfile:
            data = myfile.read()

        return data

    def startPrintFromHub(self):
        self._logger.info("Hub command to start print received")
        self.enqueueCmd("O39 D1")

    def getHubData(self):
        hub_file_path = os.path.expanduser('~') + "/.mosaicdata/canvas-hub-data.yml"

        hub_data = open(hub_file_path, "r")
        hub_yaml = yaml.load(hub_data)
        hub_data.close()

        hub_id = hub_yaml["canvas-hub"]["id"]
        hub_token = hub_yaml["canvas-hub"]["token"]

        return hub_id, hub_token

    def parseLine(self, line):
        line = line.strip()

        # is the first character O?
        if line[0] == "O":
            tokens = [token.strip() for token in line.split(" ")]
            # make command object
            command = {
                "command": tokens[0],
                "total_params": len(tokens) - 1,
                "params": tokens[1:]
            }
            # verify command validity
            try:
                command["command"] = int(command["command"][1:])
            except:
                # command should be a number, otherwise invalid command
                self._logger.info("%s is not a valid command: %s" % (command["command"], line))
                return None
            # verify tokens' validity
            if command["total_params"] > 0:
                for param in command["params"]:
                    # params should start with D or U, otherwise invalid param
                    if param[0] != "D" and param[0] != "U":
                        self._logger.info("%s is not a valid parameter: %s" % (param, line))
                        return None
            return command
        # otherwise, is this line the heartbeat response?
        elif line == "Connection Okay":
            self.heartbeat = True
            return None
        else:
            # Invalid first character (IFC). Don't need to do anything, but log out for potential troubleshooting.
            self._logger.info("IFC: %s" % line)
            return None
