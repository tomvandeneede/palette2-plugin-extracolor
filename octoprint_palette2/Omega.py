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
try:
    from ruamel.yaml import YAML
except ImportError:
    from ruamel.yaml.main import YAML
from dotenv import load_dotenv
yaml = YAML(typ="safe")
env_path = os.path.abspath(".") + "/.env"
if os.path.abspath(".") is "/":
    env_path = "/home/pi/.env"
load_dotenv(env_path)
BASE_URL_API = os.getenv("DEV_BASE_URL_API", "api.canvas3d.io/")
from subprocess import call
from Queue import Queue, Empty
from . import constants


class Omega():
    def __init__(self, plugin):
        self._logger = plugin._logger
        self._printer = plugin._printer
        self._printer_profile_manager = plugin._printer_profile_manager
        self._plugin_manager = plugin._plugin_manager
        self._identifier = plugin._identifier
        self._settings = plugin._settings

        self.ports = []
        self.ledThread = None
        self.isHubS = False

        self.writeQueue = Queue()

        self.resetVariables()
        self.resetConnection()

        # Tries to automatically connect to palette first
        if self._settings.get(["autoconnect"]):
            self.startConnectionThread()

    def checkLedScriptFlag(self):
        led_script_flag = "/home/pi/.mosaicdata/led_flag"
        return os.path.isfile(led_script_flag)

    def updateHubSLedScript(self):
        if self.isHubS and not self.checkLedScriptFlag():
            self._logger.info("Updating LED script")
            updated_script_path = "/home/pi/OctoPrint/venv/lib/python2.7/site-packages/octoprint_palette2/led.py"
            led_script_path = "/home/pi/led.py"
            call(["cp %s %s" % (updated_script_path, led_script_path)], shell=True)

            script_flag_path = "/home/pi/.mosaicdata/led_flag"
            call(["touch %s" % script_flag_path], shell=True)
            self._logger.info("LED script updated. Please restart the CANVAS Hub S")

    def determineHubVersion(self):
        hub_file_path = os.path.expanduser('~') + "/.mosaicdata/canvas-hub-data.yml"

        if os.path.exists(hub_file_path):
            hub_data = open(hub_file_path, "r")
            hub_yaml = yaml.load(hub_data)
            hub_data.close()

            hub_rank = hub_yaml["versions"]["global"]
            if hub_rank == "0.2.0":
                return True
        return False

    def checkForRuamelVersion(self):
        paths = [
            "/home/pi/oprint/lib/python2.7/site-packages/_ruamel_yaml.so",
            "/home/pi/oprint/lib/python2.7/site-packages/ruamel.yaml.clib-0.1.0-py2.7-nspkg.pth",
            "/home/pi/oprint/lib/python2.7/site-packages/ruamel.yaml.clib-0.1.0-py2.7.egg-info",
        ]
        for path in paths:
            if os.path.exists(path):
                self._logger.info("Deleting file/directory")
                call(["rm -rf %s" % path], shell=True)

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
        self._logger.info("Selected port: %s" % self._settings.get(["selectedPort"]))
        self.updateUI({"command": "ports", "data": self.ports})
        self.updateUI({"command": "selectedPort", "data": self._settings.get(["selectedPort"])})
        if not self.ports:
            raise Exception(constants.P2_CONNECTION["NO_SERIAL_PORTS_FOUND"])

    def getRealPaths(self, ports):
        self._logger.info("Paths: %s" % ports)
        for index, port in enumerate(ports):
            port = os.path.realpath(port)
            ports[index] = port
        return ports

    def isPrinterPort(self, selected_port):
        selected_port = os.path.realpath(selected_port)
        printer_port = self._printer.get_current_connection()[1]
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
                # if manual port given, try that first
                if port:
                    self._logger.info("Attempting manually selected port")
                    if not self.isPrinterPort(port):
                        self.attemptSerialConnection(port)
                    else:
                        self.updateUIAll()
                        raise Exception(constants.P2_CONNECTION["PRINTER_ON_CURRENT_PORT"])
                else:
                    # try the last successfully connected port first, if any
                    lastConnectedP2Port = self._settings.get(["selectedPort"])
                    if lastConnectedP2Port:
                        self._logger.info("Attempting last successfully connected port")
                        self.attemptSerialConnection(lastConnectedP2Port)

                    # loop through all ports
                    for serialPort in self.ports:
                        if self.isPrinterPort(serialPort) or lastConnectedP2Port:
                            continue
                        if self.attemptSerialConnection(serialPort):
                            break
                if not self.connected:
                    self._settings.set(["selectedPort"], None, force=True)
                    self._settings.save(force=True)
                    self.updateUIAll()
                    raise Exception(constants.P2_CONNECTION["HEARTBEAT_CONNECT_FAILURE"])
            else:
                self.updateUIAll()
                raise Exception(constants.P2_CONNECTION["NO_SERIAL_PORTS_FOUND"])
        else:
            self.updateUIAll()
            raise Exception(constants.P2_CONNECTION["ALREADY_CONNECTED"])

    def attemptSerialConnection(self, port):
        default_baudrate = self._settings.get(["baudrate"])
        second_baudrate = self.getSecondBaudrate(default_baudrate)
        baudrates = [default_baudrate, second_baudrate]
        for baudrate in baudrates:
            try:
                if self.tryHeartbeatBeforeConnect(port, baudrate):
                    break
            except Exception as e:
                self._logger.info(e)
        return self.connected

    def getSecondBaudrate(self, default_baudrate):
        if default_baudrate == 115200:
            return 250000
        elif default_baudrate == 250000:
            return 115200

    def tryHeartbeatBeforeConnect(self, port, baudrate):
        self._logger.info("Trying: port (%s) and baudrate (%s)" %(port, baudrate))
        self.omegaSerial = serial.Serial(port, baudrate, timeout=0.5)
        self.startReadThread()
        self.startWriteThread()
        self.enqueueCmd("\n")
        self.enqueueCmd(constants.COMMANDS["HEARTBEAT"])

        timeout = 3
        timeout_start = time.time()
        # Wait for Palette to respond with a handshake within 3 seconds
        while time.time() < timeout_start + timeout:
            if self.heartbeat:
                self.connected = True
                self._logger.info("Connected to Omega")
                self._settings.set(["selectedPort"], port, force=True)
                self._settings.set(["baudrate"], baudrate, force=True)
                self._settings.save(force=True)
                self.enqueueCmd(constants.COMMANDS["GET_FIRMWARE_VERSION"])
                self.updateUI({"command": "selectedPort", "data": self._settings.get(["selectedPort"])})
                self.updateUIAll()
                return True
            else:
                time.sleep(0.01)
        if not self.heartbeat:
            self.resetOmega()
            self._logger.info("Not the %s baudrate" % baudrate)
            return False

    def tryHeartbeatBeforePrint(self):
        self.heartbeat = False
        self.enqueueCmd("\n")
        self.enqueueCmd(constants.COMMANDS["HEARTBEAT"])
        self.printHeartbeatCheck = "Checking"

    def setFilename(self, name):
        self.filename = name

    def startReadThread(self):
        if self.readThread is None:
            self.readThreadStop = False
            self.readThread = threading.Thread(
                target=self.omegaReadThread,
                args=(self.omegaSerial,)
            )
            self.readThread.daemon = True
            self.readThread.start()

    def startWriteThread(self):
        if self.writeThread is None:
            self.writeThreadStop = False
            self.writeThread = threading.Thread(
                target=self.omegaWriteThread,
                args=(self.omegaSerial,)
            )
            self.writeThread.daemon = True
            self.writeThread.start()

    def startConnectionThread(self):
        if self.connectionThread is None:
            self.connectionThreadStop = False
            self.connectionThread = threading.Thread(
                target=self.omegaConnectionThread
            )
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
                        if command["command"] != 99:
                            self._logger.info("Omega: read in line: %s" % line.strip())
                        if command["command"] == 20:
                            if command["total_params"] > 0:
                                if command["params"][0] == "D5":
                                    self.handleFirstTimePrint()
                                else:
                                    self.handleP2RequestForMoreInfo(command)
                        elif command["command"] == 34:
                            if command["total_params"] == 1:
                                # if reject ping
                                if command["params"][0] == "D0":
                                    self.handleRejectedPing()
                            elif command["total_params"] > 2:
                                # if ping
                                if command["params"][0] == "D1":
                                    self.handlePing(command)
                                # else pong
                                elif command["params"][0] == "D2":
                                    self.handlePong(command)
                        elif command["command"] == 40:
                            self.handleResumeRequest()
                        elif command["command"] == 50:
                            if command["total_params"] > 0:
                                firmware_version = command["params"][0].replace("D","")
                                if firmware_version >= "9.0.9":
                                    self.startHeartbeatThread()
                            else:
                                self.sendAllMCFFilenamesToOmega()
                        elif command["command"] == 53:
                            if command["total_params"] > 1:
                                if command["params"][0] == "D1":
                                    self.handleStartPrintFromP2(command)
                        elif command["command"] == 88:
                            if command["total_params"] > 0:
                                self.handleErrorDetected(command)
                        elif command["command"] == 97:
                            if command["total_params"] > 0:
                                if command["params"][0] == "U0":
                                    if command["total_params"] > 1:
                                        if command["params"][1] == "D0":
                                            self.handleSpliceCompletion()
                                        elif command["params"][1] == "D2":
                                            self.handlePrintCancelling()
                                        elif command["params"][1] == "D3":
                                            self.handlePrintCancelled()
                                elif command["params"][0] == "U25":
                                    if command["total_params"] > 2:
                                        if command["params"][1] == "D0":
                                            self.handleSpliceStart(command)
                                            self.feedRateControlStart()
                                        elif command["params"][1] == "D1":
                                            self.feedRateControlEnd()
                                elif command["params"][0] == "U26":
                                    if command["total_params"] > 1:
                                        self.handleFilamentUsed(command)
                                elif command["params"][0] == "U39":
                                    if command["total_params"] == 1:
                                        self.handleLoadingOffsetStart()
                                    # positive integer
                                    elif "-" in command["params"][1]:
                                        self.handleLoadingOffsetExtrude(command)
                                    # negative integer or 0
                                    elif "-" not in command["params"][1]:
                                        self.handleLoadingOffsetCompletion(command)
                                elif self.drivesInUse and command["params"][0] == self.drivesInUse[0]:
                                    if command["total_params"] > 1 and command["params"][1] == "D0":
                                        self.handleDrivesLoading()
                                elif self.drivesInUse and command["params"][0] == self.drivesInUse[-1]:
                                    if command["total_params"] > 1 and command["params"][1] == "D1":
                                        self.handleFilamentOutgoingTube()
                        elif command["command"] == 100:
                            self.handlePauseRequest()
                        elif command["command"] == 102:
                            if command["total_params"] > 0:
                                if command["params"][0] == "D0":
                                    self.handleSmartLoadRequest()
            except Exception as e:
                # Something went wrong with the connection to Palette2
                self._logger.info("Palette 2 Read Thread error")
                self._logger.info(e)
                self.readThreadError = True
                break
        if self.readThreadError:
            self.disconnect()
            self.updateUI({"command": "alert", "data": "threadError"})

    def omegaWriteThread(self, serialConnection):
        self._logger.info("Omega Write Thread: Starting Thread")
        while self.writeThreadStop is False:
            try:
                line = self.writeQueue.get(True, 0.5)
                if line:
                    self.lastCommandSent = line
                    line = line.strip()
                    if constants.COMMANDS["HEARTBEAT"] not in line and "\n" not in line:
                        self._logger.info("Omega Write Thread: Sending: %s" % line.strip())
                    line = line + "\n"
                    serialConnection.write(line.encode())
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
                try:
                    self.connectOmega("")
                except Exception as e:
                    self._logger.info(e)
            time.sleep(1)

    def startLedThread(self):
        if self.isHubS:
            if self.ledThread is not None:
                self.stopLedThread()
            self._logger.info("Starting Led Thread")
            self.ledThreadStop = False
            self.ledThread = threading.Thread(target=self.omegaLedThread)
            self.ledThread.daemon = True
            self.ledThread.start()

    def stopLedThread(self):
        if self.isHubS:
            self.ledThreadStop = True
            if self.ledThread and threading.current_thread() != self.ledThread:
                self.ledThread.join()
            self.ledThread = None

    def omegaLedThread(self):
        palette_flag_path = "/home/pi/.mosaicdata/palette_flag"
        printer_flag_path = "/home/pi/.mosaicdata/printer_flag"
        try:
            while not self.ledThreadStop:
                if self.connected:
                    if not os.path.exists(palette_flag_path):
                        call(["touch %s" % palette_flag_path], shell=True)
                else:
                    if os.path.exists(palette_flag_path):
                        call(["rm %s" % palette_flag_path], shell=True)
                if self._printer.get_state_id() in ["OPERATIONAL", "PRINTING", "PAUSED"]:
                    if not os.path.exists(printer_flag_path):
                        call(["touch %s" % printer_flag_path], shell=True)
                else:
                    if os.path.exists(printer_flag_path):
                        call(["rm %s" % printer_flag_path], shell=True)
                time.sleep(2)
        except Exception as e:
                self._logger.info("Palette 2 Led Thread Error")
                self._logger.info(e)

    def startHeartbeatThread(self):
        if self.heartbeatThread is not None:
            self.stopHeartbeatThread()
        self._logger.info("Starting Heartbeat Thread")
        self.heartbeatThreadStop = False
        self.heartbeatSent = False
        self.heartbeatReceived = False
        self.heartbeatThread = threading.Thread(target=self.omegaHeartbeatThread)
        self.heartbeatThread.daemon = True
        self.heartbeatThread.start()

    def stopHeartbeatThread(self):
        self.heartbeatThreadStop = True
        if self.heartbeatThread and threading.current_thread() != self.heartbeatThread:
            self.heartbeatThread.join()
        self.heartbeatThread = None

    def omegaHeartbeatThread(self):
        try:
            while not self.heartbeatThreadStop:
                if not self.palette2SetupStarted and not self.actualPrintStarted:
                    if self.heartbeatSent and not self.heartbeatReceived:
                        self._logger.info("Did not receive heartbeat response")
                        self.disconnect()
                        break
                    self.heartbeatSent = True
                    self.heartbeatReceived = False
                    self.enqueueCmd(constants.COMMANDS["HEARTBEAT"])
                time.sleep(2)
        except Exception as e:
                self._logger.info("Palette 2 Heartbeat Thread Error")
                self._logger.info(e)

    def enqueueCmd(self, line):
        self.writeQueue.put(line)

    def cut(self):
        self._logger.info("Omega: Sending Cut command")
        self.enqueueCmd(constants.COMMANDS["CUT"])

    def clear(self):
        self._logger.info("Omega: Sending Clear command")
        for command in constants.COMMANDS["CLEAR"]:
            self.enqueueCmd(command)

    def cancel(self):
        self.enqueueCmd(constants.COMMANDS["CANCEL"])

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
        self.updateUI({"command": "advanced", "subCommand": "displayAdvancedOptions", "data": self._settings.get(["advancedOptions"])}, True)
        self.updateUI({"command": "ports", "data": self.getAllPorts()}, True)
        self.advanced_updateUI()


    def updateUI(self, data, log=None):
        if not log:
            if data["command"] == "advanced":
                self._logger.info("Updating UI: %s" % data["subCommand"])
            else:
                self._logger.info("Updating UI: %s" % data["command"])
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
                cmdStr = "%s D%d D%s\n" % (constants.COMMANDS["SPLICE"], int(splice[0]), splice[1])
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

    def savePing(self, pingCmd):
        self.currentPingCmd = pingCmd
        self.enqueueCmd(constants.COMMANDS["PING"])
        self._logger.info("Got a ping cmd, saving it")

    def resetConnection(self):
        self._logger.info("Resetting read and write threads")

        self.stopReadThread()
        self.stopWriteThread()
        self.stopAutoLoadThread()
        self.stopHeartbeatThread()
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
        self._logger.info("Omega: Resetting all values - STARTED")

        self.omegaSerial = None
        self.sentCounter = 0
        self.algoCounter = 0
        self.spliceCounter = 0

        self.msfNS = 0
        self.msfNA = "0"
        self.nAlgorithms = 0
        self.currentSplice = 0
        self.header = [None] * 9
        self.splices = []
        self.algorithms = []
        self.filamentLength = 0
        self.currentStatus = ""
        self.drivesInUse = []
        self.amountLeftToExtrude = ""
        self.printPaused = False
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
        self.heartbeatSent = False
        self.heartbeatReceived = False

        self.filename = ""

        self.connected = False
        self.readThread = None
        self.writeThread = None
        self.readThreadError = None
        self.connectionThread = None
        self.heartbeatThread = None
        self.connectionStop = False
        self.heartbeat = False

        self.missedPings = 0
        self.advanced_reset_values()

        self.autoLoadThread = None
        self.isSplicing = False
        self._logger.info("Omega: Resetting all values - FINISHED")

    def resetPrintValues(self):
        self._logger.info("Omega: Resetting print values - STARTED")
        self.sentCounter = 0
        self.algoCounter = 0
        self.spliceCounter = 0

        self.msfNS = 0
        self.msfNA = "0"
        self.nAlgorithms = 0
        self.currentSplice = 0
        self.header = [None] * 9
        self.splices = []
        self.algorithms = []
        self.filamentLength = 0
        self.currentStatus = ""
        self.drivesInUse = []
        self.amountLeftToExtrude = ""
        self.printPaused = False
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
        self.heartbeatSent = False
        self.heartbeatReceived = False

        self.autoLoadingExtraFiliment = 0

        self.filename = ""

        self.missedPings = 0
        self.isSplicing = False
        self.advanced_reset_print_values()
        self._logger.info("Omega: Resetting print values - FINISHED")

    def resetOmega(self):
        self.resetConnection()
        self.resetVariables()

    def shutdown(self):
        self._logger.info("Shutdown")
        self.disconnect()
        self.stopLedThread()

    def disconnect(self):
        self._logger.info("Disconnecting from Palette")
        self.resetOmega()
        self.updateUIAll()

    def initializePrintVariables(self):
        self._logger.info("PRINT STARTED P2")
        self.resetPrintValues()
        self.tryHeartbeatBeforePrint()
        self.updateUIAll()
        self.printHeartbeatCheck = ""

    def gotOmegaCmd(self, cmd):
        if "O1" not in cmd:
            if "O21" in cmd:
                self.initializePrintVariables()
                self._logger.info("Starting Header Sequence")
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

            elif "O40" in cmd
                p = cmd.find("D")
                if (p>0):
                    self.autoLoadingExtraFiliment = int(cmd[p+1:],16)
                    self._logger.info("Omega:  Added %dmm of filament " % self.autoLoadingExtraFiliment)

        elif "O1" in cmd:
            timeout = 4
            timeout_start = time.time()
            # Wait for Palette to respond with a handshake within 4 seconds
            while not self.heartbeat and time.time() < timeout_start + timeout:
                time.sleep(0.01)
            if self.heartbeat:
                self._logger.info("Palette did respond to %s" % constants.COMMANDS["HEARTBEAT"])
                self.enqueueCmd(cmd)
                self.currentStatus = constants.STATUS["INITIALIZING"]
                self.palette2SetupStarted = True
                if self.heartbeatSent:
                    self.heartbeatReceived = True
                self.printHeartbeatCheck = "P2Responded"
                self.printPaused = True
                self.updateUI({"command": "currentStatus", "data": self.currentStatus})
                self.updateUI({"command": "palette2SetupStarted", "data": self.palette2SetupStarted})
                self.updateUI({"command": "printHeartbeatCheck", "data": self.printHeartbeatCheck})
                self.updateUI({"command": "printPaused", "data": self.printPaused})
                self.updateUI({"command": "advanced", "subCommand": "advancedStatus", "data": "Awaiting Update..."})
                self.printHeartbeatCheck = ""
                try:
                    filename = self._printer.get_current_job()["file"]["name"].replace(".mcf.gcode", "").strip()
                    self.setFilename(filename)
                except:
                    self._logger.info("Error getting filename")
            else:
                self._logger.info("Palette did not respond to %s" % constants.COMMANDS["HEARTBEAT"])
                self.printHeartbeatCheck = "P2NotConnected"
                self.updateUI({"command": "printHeartbeatCheck", "data": self.printHeartbeatCheck})
                self.disconnect()
                self._logger.info("NO P2 detected. Cancelling print")
                self._printer.cancel_print()
        elif cmd == "O9":
            # reset values
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
            self.enqueueCmd("%s D%s" % (constants.COMMANDS["FILENAME"], filename))
        self.enqueueCmd(constants.COMMANDS["FILENAMES_DONE"])

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

    def startPrintFromP2(self, file):
        self._logger.info("Received print command from P2")
        self._printer.select_file(file, False, printAfterSelect=True)

    def sendErrorReport(self, error_number, description):
        self._logger.info("SENDING ERROR REPORT TO MOSAIC")
        log_content = self.prepareErrorReport(error_number, description)

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

    def prepareErrorReport(self, error_number, description):
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
        self.enqueueCmd(constants.COMMANDS["START_PRINT_HUB"])

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
            self.heartbeatReceived = True
            self.heartbeatSent = False
            return None
        else:
            # Invalid first character (IFC). Don't need to do anything, but log out for potential troubleshooting.
            self._logger.info("IFC: %s" % line)
            return None

    def feedRateControlStart(self):
        self._logger.info('ADVANCED: SPLICE START')
        self.isSplicing = True
        if self.feedRateControl and self.actualPrintStarted:
            self._logger.info('ADVANCED: Feed-rate Control: ACTIVATED')
            advanced_status = 'Splice (%s) starting: speed -> SLOW (%s%%)' % (self.currentSplice, self.feedRateSlowPct)
            self.updateUI({"command": "advanced", "subCommand": "advancedStatus", "data": advanced_status})
            # Splice Start
            if self.feedRateSlowed:
                # Feedrate already slowed, set it again to be safe.
                try:
                    self._logger.info("ADVANCED: Feed-rate SLOW - ACTIVE* (%s)" % self.feedRateSlowPct)
                    self._printer.commands('M220 S%s' % self.feedRateSlowPct)
                except ValueError:
                    self._logger.info('ADVANCED: Unable to Update Feed-Rate -> SLOW :: ' + str(ValueError))
            else:
                self._logger.info('ADVANCED: Feed-rate SLOW - ACTIVE (%s)' % self.feedRateSlowPct)
                try:
                    self._printer.commands('M220 S%s B' % self.feedRateSlowPct)
                    self.feedRateSlowed = True
                except ValueError:
                    self._logger.info('ADVANCED: Unable to Update Feed-Rate -> SLOW :: ' + str(ValueError))
            self.updateUI({"command": "advanced", "subCommand": "feedRateSlowed", "data": self.feedRateSlowed}, True)
        else:
            self._logger.info('ADVANCED: Feed-rate Control: INACTIVE')

    def feedRateControlEnd(self):
        self._logger.info('ADVANCED: SPLICE END')
        self.isSplicing = False
        if self.feedRateControl and self.actualPrintStarted:
            self._logger.info('ADVANCED: Feed-rate NORMAL - ACTIVE (%s)' % self.feedRateNormalPct)
            advanced_status = 'Splice (%s) finished: speed -> NORMAL (%s%%)' % (self.currentSplice, self.feedRateNormalPct)
            self.updateUI({"command": "advanced", "subCommand": "advancedStatus", "data": advanced_status})
            try:
                self._printer.commands('M220 S%s' % self.feedRateNormalPct)
                self.feedRateSlowed = False
            except ValueError:
                self._logger.info('ADVANCED: Unable to Update Feed-Rate -> NORMAL :: ' + str(ValueError))
            self.updateUI({"command": "advanced", "subCommand": "feedRateSlowed", "data": self.feedRateSlowed}, True)
        else:
            self._logger.info('ADVANCED: Feed-Rate Control: INACTIVE')

    def sendPingToPrinter(self, ping_number, ping_percent):
        self._logger.info("ADVANCED: Ping!")
        self._logger.info("ADVANCED: Show on Printer: %s" % self.showPingOnPrinter)
        # filter out ping offset information
        if self.showPingOnPrinter:
            try:
                if ping_percent == "MISSED":
                    self._printer.commands("M117 Ping %s %s" % (ping_number, ping_percent))
                else:
                    self._printer.commands("M117 Ping %s %s%%" % (ping_number, ping_percent))
            except ValueError:
                self._logger.info("Printer cannot handle M117 commands.")

    def advanced_reset_values(self):
        self.feedRateControl = self._settings.get(["feedRateControl"])
        self.feedRateNormalPct = self._settings.get(["feedRateNormalPct"])
        self.feedRateSlowPct = self._settings.get(["feedRateSlowPct"])
        self.autoVariationCancelPing = self._settings.get(["autoVariationCancelPing"])
        self.showPingOnPrinter = self._settings.get(["showPingOnPrinter"])
        self.variationPct = self._settings.get(["variationPct"])
        self.advanced_reset_print_values()

    def advanced_reset_print_values(self):
        self.autoLoadThread = None
        self.feedRateSlowed = False
        self.isAutoLoading = False

    def advanced_updateUI(self):
        self._logger.info("ADVANCED UPDATE UI")
        try:
            self.updateUI({"command": "advanced", "subCommand": "autoVariationCancelPing", "data": self._settings.get(["autoVariationCancelPing"])}, True)
            self.updateUI({"command": "advanced", "subCommand": "showPingOnPrinter", "data": self._settings.get(["showPingOnPrinter"])}, True)
            self.updateUI({"command": "advanced", "subCommand": "feedRateControl", "data": self._settings.get(["feedRateControl"])}, True)
            self.updateUI({"command": "advanced", "subCommand": "feedRateSlowed", "data": self.feedRateSlowed}, True)
            self.updateUI({"command": "advanced", "subCommand": "feedRateNormalPct", "data": self._settings.get(["feedRateNormalPct"])}, True)
            self.updateUI({"command": "advanced", "subCommand": "feedRateSlowPct", "data": self._settings.get(["feedRateSlowPct"])}, True)
            self.updateUI({"command": "advanced", "subCommand": "variationPct", "data": self._settings.get(["variationPct"])}, True)
            self.updateUI({"command": "advanced", "subCommand": "isAutoLoading", "data": self.isAutoLoading}, True)
        except Exception as e:
            self._logger.info(e)

    def changeAutoVariationCancelPing(self, condition):
        try:
            self._settings.set(["autoVariationCancelPing"], condition, force=True)
            self._settings.save(force=True)
            self._logger.info("ADVANCED: autoVariationCancelPing -> '%s' '%s'" % (condition, self._settings.get(["autoVariationCancelPing"])))
            self.autoVariationCancelPing = self._settings.get(["autoVariationCancelPing"])
        except Exception as e:
            self._logger.info(e)

    def changeShowPingOnPrinter(self, condition):
        try:
            self._settings.set(["showPingOnPrinter"], condition, force=True)
            self._settings.save(force=True)
            self._logger.info("ADVANCED: showPingOnPrinter -> '%s' '%s'" % (condition, self._settings.get(["showPingOnPrinter"])))
            self.showPingOnPrinter = self._settings.get(["showPingOnPrinter"])
        except Exception as e:
            self._logger.info(e)

    def changeFeedRateControl(self, condition):
        try:
            self._settings.set(["feedRateControl"], condition, force=True)
            self._settings.save(force=True)
            self._logger.info("ADVANCED: feedRateControl -> '%s' '%s'" % (condition, self._settings.get(["feedRateControl"])))
            self.feedRateControl = self._settings.get(["feedRateControl"])
        except Exception as e:
            self._logger.info(e)

    def changeFeedRateNormalPct(self, value):
        if self.isPositiveInteger(value):
            clean_value = int(value)
            advanced_status = ""
            if clean_value == self.feedRateNormalPct:
                self._logger.info("Normal Feed Rate Speed did not change. Do nothing")
            elif clean_value > 150:
                self._logger.info("Cannot set normal feed rate above 150%.")
                advanced_status = 'Cannot set normal feed rate above 150%%. Keeping speed at (%s%%).' % self.feedRateNormalPct
                self.updateUI({"command": "advanced", "subCommand": "feedRateNormalPct", "data": self._settings.get(["feedRateNormalPct"])})
            else:
                try:
                    self._settings.set(["feedRateNormalPct"], clean_value)
                    self._settings.save(force=True)
                    self._logger.info("ADVANCED: feedRateNormalPct -> '%s' '%s'" % (clean_value, self._settings.get(["feedRateNormalPct"])))
                    self.feedRateNormalPct = self._settings.get(["feedRateNormalPct"])
                    if not self.actualPrintStarted:
                        advanced_status = 'Normal feed rate set to %s%%. Awaiting start of print to apply...' % self.feedRateNormalPct
                    else:
                        if not self.feedRateSlowed:
                            self._printer.commands('M220 S%s' % self.feedRateNormalPct)
                            advanced_status = 'Not currently splicing: speed -> NORMAL (%s%%)' % self.feedRateNormalPct
                        else:
                            advanced_status = 'Normal feed rate set to %s%%. Awaiting end of current splice to apply...' % self.feedRateNormalPct
                except Exception as e:
                    self._logger.info(e)
            if advanced_status != "":
                self.updateUI({"command": "advanced", "subCommand": "advancedStatus", "data": advanced_status})
        else:
            self._logger.info("Not positive integer")
            self.updateUI({"command": "advanced", "subCommand": "feedRateNormalPct", "data": self._settings.get(["feedRateNormalPct"])})


    def changeFeedRateSlowPct(self, value):
        if self.isPositiveInteger(value):
            clean_value = int(value)
            advanced_status = ""
            if clean_value == self.feedRateSlowPct:
                self._logger.info("Splice Feed Rate Speed did not change. Do nothing")
            elif clean_value > 100:
                self._logger.info("Cannot set splicing feed rate above 100%.")
                advanced_status = 'Cannot set splicing feed rate above 100%%. Keeping speed at (%s%%).' % self.feedRateSlowPct
                self.updateUI({"command": "advanced", "subCommand": "feedRateSlowPct", "data": self._settings.get(["feedRateSlowPct"])})
            else:
                try:
                    self._settings.set(["feedRateSlowPct"], clean_value)
                    self._settings.save(force=True)
                    self._logger.info("ADVANCED: feedRateSlowPct -> '%s' '%s'" % (clean_value, self._settings.get(["feedRateSlowPct"])))
                    self.feedRateSlowPct = self._settings.get(["feedRateSlowPct"])
                    if not self.actualPrintStarted:
                        advanced_status = 'Splicing feed rate set to %s%%. Awaiting start of print to apply...' % (self.feedRateSlowPct)
                    else:
                        if self.feedRateSlowed:
                            self._printer.commands('M220 S%s' % self.feedRateSlowPct)
                            advanced_status = 'Currently splicing (%s): speed -> SLOW (%s%%)' % (self.currentSplice, self.feedRateSlowPct)
                        else:
                            advanced_status = 'Splicing feed rate set to %s%%. Awaiting next splice to apply...' % (self.feedRateSlowPct)
                except Exception as e:
                    self._logger.info(e)
            if advanced_status != "":
                self.updateUI({"command": "advanced", "subCommand": "advancedStatus", "data": advanced_status})
        else:
            self._logger.info("Not positive integer")
            self.updateUI({"command": "advanced", "subCommand": "feedRateSlowPct", "data": self._settings.get(["feedRateSlowPct"])})

    def changeVariationPct(self, value):
        if self.isPositiveInteger(value):
            clean_value = int(value)
            advanced_status = ""
            if clean_value == self.variationPct:
                self._logger.info("Variation percent did not change. Do nothing")
            elif clean_value > 100:
                self._logger.info("Cannot set variation percent above 100%.")
                advanced_status = 'Cannot set variation percent above 100%%. Keeping variation range at +/- (%s%%).' % self.variationPct
                self.updateUI({"command": "advanced", "subCommand": "variationPct", "data": self._settings.get(["variationPct"])})
            else:
                try:
                    self._settings.set(["variationPct"], clean_value)
                    self._settings.save(force=True)
                    self._logger.info("ADVANCED: variationPct -> '%s' '%s'" % (clean_value, self._settings.get(["variationPct"])))
                    self.variationPct = self._settings.get(["variationPct"])
                except Exception as e:
                    self._logger.info(e)
        else:
            self._logger.info("Not positive integer")
            self.updateUI({"command": "advanced", "subCommand": "variationPct", "data": self._settings.get(["variationPct"])})

    def advanced_update_variables(self):
        self.autoVariationCancelPing = self._settings.get(["autoVariationCancelPing"])
        self.showPingOnPrinter = self._settings.get(["showPingOnPrinter"])
        self.feedRateControl = self._settings.get(["feedRateControl"])
        self.feedRateNormalPct = self._settings.get(["feedRateNormalPct"])
        self.feedRateSlowPct = self._settings.get(["feedRateSlowPct"])
        self.variationPct = self._settings.get(["variationPct"])
        self.advanced_updateUI()

    def isPositiveInteger(self, value):
        try:
            return int(value) > 0
        except Exception as e:
            self._logger.info(e)
            return False

    def startAutoLoadThread(self):
        if self.autoLoadThread is not None:
            self.stopAutoLoadThread()

        self._logger.info("Starting AutoLoad Thread")
        self.isAutoLoading = True
        self.updateUI({"command": "advanced", "subCommand": "isAutoLoading", "data": self.isAutoLoading})
        self.autoLoadThreadStop = False
        self.autoLoadThread = threading.Thread(target=self.omegaAutoLoadThread)
        self.autoLoadThread.daemon = True
        self.autoLoadThread.start()

    def stopAutoLoadThread(self):
        self.autoLoadThreadStop = True
        if self.autoLoadThread and threading.current_thread() != self.autoLoadThread:
            self.autoLoadThread.join()
        self.autoLoadThread = None

    def omegaAutoLoadThread(self):
        self._printer.extrude(0)
        self.autoLoadFilament(self.amountLeftToExtrude)

    def autoLoadFilament(self, amount_to_extrude):
        if not self.autoLoadThreadStop:

            amount_to_extrude += self.autoLoadingExtraFiliment
            self._logger.info("Amount to extrude: %s" % amount_to_extrude)

            if amount_to_extrude <= 0:
                self.isAutoLoading = False
                self.updateUI({"command": "advanced", "subCommand": "isAutoLoading", "data": self.isAutoLoading})
                return 0

            old_value = amount_to_extrude
            change_detected = False

            # if not splicing, send extrusion command to printer
            if not self.isSplicing:
                if amount_to_extrude > 70:
                    # do increments of 50mm for large loading offsets to minimize filament grinding, in case a splice occurs
                    self._logger.info("Amount above 70, sending 50 to printer.")
                    self._printer.extrude(50)
                elif amount_to_extrude > 5:
                    # half the amount to minimize risk of over-extrusion
                    self._logger.info("Amount above 5, sending half (%s) to printer." % (amount_to_extrude / 2))
                    self._printer.extrude(amount_to_extrude / 2)
                elif amount_to_extrude > 0:
                    self._logger.info("Amount 5 or below, sending %s to printer." % amount_to_extrude)
                    self._printer.extrude(amount_to_extrude)

            timeout = 6
            timeout_start = time.time()
            # check for change in remaining offset value after extrusion command was sent to know if smart load is working
            while time.time() < timeout_start + timeout:
                if self.amountLeftToExtrude != old_value:
                    old_value = self.amountLeftToExtrude
                    change_detected = True
                    # reset timeout
                    timeout = 3
                    timeout_start = time.time()
                time.sleep(0.01)

            if change_detected:
                # wait for current splice to finish before recursively continuing smart loading
                if self.isSplicing:
                    self._logger.info("Palette 2 is currently splicing. Waiting for end of splice before continuing...")
                    while self.isSplicing:
                        time.sleep(1)
                    self._logger.info("Resuming smart load.")
                self.autoLoadFilament(self.amountLeftToExtrude)
            else:
                self._logger.info("Loading offset at %smm did not change within %s seconds. Filament did not move. Must place filament again" % (self.amountLeftToExtrude, timeout))
                self.isAutoLoading = False
                self.updateUI({"command": "advanced", "subCommand": "isAutoLoading", "data": self.isAutoLoading})
                self.updateUI({"command": "alert", "data": "autoLoadIncomplete"})
                self.enqueueCmd(constants.COMMANDS["SMART_LOAD_STOP"])
                return None
        else:
            return None

    def downloadPingHistory(self):
        self._logger.info("DOWNLOADING PING HISTORY")
        return self.getPingHistory(self.pings, self.filename)

    def getPingHistory(self, pings, filename):
        data = ""
        data = data + "%s\n\nPING            (%%)\n===================\n" % filename

        # write out each ping
        for ping in pings:
            ping_number = "Ping %s" % ping["number"]
            ping_percent = "%s%%" % ping["percent"]
            if ping["percent"] == "MISSED":
                ping_percent = ping["percent"]
            space_length = (len("===================") - len(ping_number) - len(ping_percent)) * " "
            data = data + "%s%s%s\n" % (ping_number, space_length, ping_percent)

        download_filename = filename + ".txt"
        return {"filename": download_filename, "data": data}

    def handleResumeRequest(self):
        if self.actualPrintStarted:
            self._printer.resume_print()
            self.printPaused = False
            self.updateUI({"command": "printPaused", "data": self.printPaused})
        else:
            if self.currentStatus == constants.STATUS["LOADING_EXTRUDER"]:
                self._printer.resume_print()
                self.printPaused = False
                self.currentStatus = constants.STATUS["PRINT_STARTED"]
                self.actualPrintStarted = True
                self.updateUI({"command": "currentStatus", "data": self.currentStatus})
                self.updateUI({"command": "actualPrintStarted", "data": self.actualPrintStarted})
                self.updateUI({"command": "alert", "data": "printStarted"})
                self.updateUI({"command": "printPaused", "data": self.printPaused})
                self._logger.info("Splices being prepared.")

    def handlePing(self, command):
        try:
            percent = float(command["params"][1][1:])
            number = int(command["params"][2][1:], 16) + self.missedPings
            current = {"number": number, "percent": percent}
            self.pings.append(current)
            self.updateUI({"command": "pings", "data": self.pings})
            self.sendPingToPrinter(number, percent)
            self.handlePingVariation()
        except:
            self._logger.info("Ping number invalid: %s" % command)

    def handlePong(self, command):
        try:
            percent = float(command["params"][1][1:])
            number = int(command["params"][2][1:], 16)
            current = {"number": number, "percent": percent}
            self.pongs.append(current)
            self.updateUI({"command": "pongs", "data": self.pongs})
        except:
            self._logger.info("Pong number invalid: %s" % command)

    def handleRejectedPing(self):
        # as of P2 FW version 9.0.9, pings are no longer "rejected"
        # this method will be kept for backwards compatibility purposes
        self._logger.info("REJECTING PING")
        self.missedPings = self.missedPings + 1
        current = {"number": len(self.pings) + 1, "percent": "MISSED"}
        self.pings.append(current)
        self.updateUI({"command": "pings", "data": self.pings})
        self.sendPingToPrinter(current["number"], current["percent"])

    def handleFirstTimePrint(self):
        self._logger.info("FIRST TIME USE WITH PALETTE")
        self.firstTime = True
        self.updateUI({"command": "firstTime", "data": self.firstTime})

    def handleP2RequestForMoreInfo(self, command):
        try:
            param_1 = int(command["params"][0][1:])
            # send next line of data
            self.sendNextData(param_1)
        except:
            self._logger.info("Error occured with: %s" % command)

    def handleStartPrintFromP2(self, command):
        try:
            index_to_print = int(command["params"][1][1:], 16)
            self.allMCFFiles.reverse()
            file = self.allMCFFiles[index_to_print]
            self.startPrintFromP2(file)
        except:
            self._logger.info("Print from P2 command invalid: %s" % command)

    def handleErrorDetected(self, command):
        try:
            error = int(command["params"][0][1:], 16)
            self._logger.info("ERROR %d DETECTED" % error)
            if os.path.isdir(os.path.expanduser('~') + "/.mosaicdata/"):
                self._printer.cancel_print()
                self.updateUI({"command": "error", "data": error})
        except:
            self._logger.info("Error command invalid: %s" % command)

    def handleSpliceCompletion(self):
        self.currentStatus = constants.STATUS["SPLICES_DONE"]
        self.updateUI({"command": "currentStatus", "data": self.currentStatus})
        self._logger.info("Palette work is done.")

    def handlePrintCancelling(self):
        self._logger.info("P2 CANCELLING START")
        if not self.cancelFromHub and not self.cancelFromP2:
            self.cancelFromP2 = True
            self._printer.cancel_print()
        self.currentStatus = constants.STATUS["CANCELLING"]
        self.updateUI({"command": "currentStatus", "data": self.currentStatus})
        self.updateUI({"command": "alert", "data": "cancelling"})

    def handlePrintCancelled(self):
        self._logger.info("P2 CANCELLING END")
        self.currentStatus = constants.STATUS["CANCELLED"]
        self.updateUI({"command": "currentStatus", "data": self.currentStatus})
        self.updateUI({"command": "alert", "data": "cancelled"})
        self.cancelFromHub = False
        self.cancelFromP2 = False

    def handleSpliceStart(self, command):
        try:
            self.currentSplice = int(command["params"][2][1:], 16)
            self._logger.info("Current splice: %s" % self.currentSplice)
            self.updateUI({"command": "currentSplice", "data": self.currentSplice})
        except:
            self._logger.info("Splice command invalid: %s" % command)

    def handleFilamentUsed(self, command):
        try:
            self.filamentLength = int(command["params"][1][1:], 16)
            self._logger.info("%smm used" % self.filamentLength)
            self.updateUI({"command": "filamentLength", "data": self.filamentLength})
        except:
            self._logger.info("Filament length update invalid: %s" % command)

    def handleLoadingOffsetStart(self):
        self.currentStatus = constants.STATUS["LOADING_EXTRUDER"]
        self.updateUI({"command": "alert", "data": "extruder"})
        self.updateUI({"command": "currentStatus", "data": self.currentStatus})
        self._logger.info("Filament must be loaded into extruder by user")

    def handleLoadingOffsetExtrude(self, command):
        try:
            self.amountLeftToExtrude = int(command["params"][1][2:])
            self._logger.info("%s mm left to extrude." % self.amountLeftToExtrude)
            self.updateUI({"command": "amountLeftToExtrude", "data": self.amountLeftToExtrude})
        except:
            self._logger.info("Filament extrusion update invalid: %s" % command)

    def handleLoadingOffsetCompletion(self, command):
        # also handles cases of LO over-extrusion
        try:
            self.amountLeftToExtrude = int(command["params"][1][1:]) * -1
            self._logger.info("%s mm left to extrude." % self.amountLeftToExtrude)
            self.updateUI({"command": "amountLeftToExtrude", "data": self.amountLeftToExtrude})
        except:
            self._logger.info("Filament extrusion update invalid: %s" % command)
        if self.amountLeftToExtrude == 0:
            if not self.cancelFromHub and not self.cancelFromP2:
                if self.isAutoLoading:
                    while self.isAutoLoading:
                        time.sleep(0.01)
                    self.updateUI({"command": "alert", "data": "startPrint"})
                else:
                    self.updateUI({"command": "alert", "data": "startPrint"})

    def handleDrivesLoading(self):
        self.currentStatus = constants.STATUS["LOADING_DRIVES"]
        self.updateUI({"command": "currentStatus", "data": self.currentStatus})
        self._logger.info("STARTING TO LOAD FIRST DRIVE")

    def handleFilamentOutgoingTube(self):
        self.currentStatus = constants.STATUS["LOADING_TUBE"]
        self.updateUI({"command": "currentStatus", "data": self.currentStatus})
        self.updateUI({"command": "alert", "data": "temperature"})
        self._logger.info("FINISHED LOADING LAST DRIVE")

    def handlePauseRequest(self):
        self._printer.pause_print()
        self.printPaused = True
        self.updateUI({"command": "printPaused", "data": self.printPaused})

    def handleSmartLoadRequest(self):
        if not self.isAutoLoading:
            self.startAutoLoadThread()

    def handlePingVariation(self):
        if self.autoVariationCancelPing and len(self.pings) > 1:
            try:
                currentPing = self.pings[-1]["percent"]
                previousPing = self.pings[-2]["percent"]
                variation = abs(currentPing - previousPing)
                if variation > self.variationPct:
                    self._logger.info("Variation (%s%% - current: %s%% vs before: %s%%) is significantly greater than %s%%. Cancelling print" % (variation, currentPing, previousPing, self.variationPct))
                    self.cancel()
            except Exception as e:
                self._logger.info(e)
