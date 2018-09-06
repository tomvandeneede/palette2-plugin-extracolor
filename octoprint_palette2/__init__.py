# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.filemanager
import flask
from . import Omega


class P2Plugin(  octoprint.plugin.StartupPlugin, 
                    octoprint.plugin.TemplatePlugin, 
                    octoprint.plugin.SettingsPlugin, 
                    octoprint.plugin.AssetPlugin, 
                    octoprint.plugin.SimpleApiPlugin, 
                    octoprint.plugin.EventHandlerPlugin,
                    octoprint.plugin.ShutdownPlugin):

    def on_after_startup(self):
        self.palette = Omega.Omega(self)
    
    def get_settings_defaults(self):
        return dict(autoconnect=0)
    
    def get_template_configs(self):
        return [ 
            dict(type="navbar", custom_bindings=False), 
            dict(type="settings", custom_bindings=False) 
        ]

    def get_assets(self):
        return dict(
            js=["js/omega.js"],
            css=["css/omega.css"]
        )

    def get_api_commands(self):
        return dict (
            cancelPalette2 = [],
            clearPalette2 = [],
            connectOmega = ["port"],
            disconnectPalette2 = [],
            printStart = [],
            sdwpStart = [],
            sendCutCmd = [],
            sendOmegaCmd = ["cmd"],
            sendJogCmd = ["drive", "dist"],
            setActiveDrive = ["drive"],
            startSingleColor = [],
            startSpliceDemo = ["file", "withPrinter"],
            stopIndefJog = [],
            testPrinterCommands = [],
            uiUpdate = [],
            connectWifi = ["wifiSSID", "wifiPASS"],
        )

    def on_api_command(self, command, data):
        self._logger.info("Got a command %s" % command)

        if command == "cancelPalette2":
            self._logger.info("Cancelling print")
            self.palette.gotOmegaCmd("O0")
        elif command == "clearPalette2":
            self.palette.clear()
        elif command == "connectOmega":
            self._logger.info("Command recieved")
            self.palette.connectOmega(data["port"])
        elif command == "disconnectPalette2":
            self.palette.disconnect()
        elif command == "printStart":
            self.palette.sendPrintStart()
        elif command == "sendCutCmd":
            self.palette.cut()
        elif command == "sendOmegaCmd":
            self.palette.enqueueCmd(data["cmd"])
        elif command == "sendJogCmd":
            self._logger.info("Sending jog command")
            self.palette.startJog(data["drive"], data["dist"])
        elif command == "setActiveDrive":
            self._logger.info("Setting active drive to %s" % data["drive"])
            #set the active drive in the Omega class to the drive that was passed
            self.palette.setActiveDrive(data["drive"])
        elif command == "startSingleColor":
            self._logger.info("Got Start Single Color Mode command")
            if "drive" in data:
                self._logger.info("Starting single color with drive %s" % data["drive"])
                self.palette.setActiveDrive(data["drive"])
            self.palette.startSingleColor()
        elif command == "startSpliceDemo":
            self._logger.info("Starting a splice demo")
            # pass the file path to Omega
            path = self._settings.getBaseFolder("uploads") + "/" + data["file"]
            #self.palette.setFilepath(data["file"]) 
            self.palette.startSpliceDemo(data["file"],path , data["withPrinter"])
        elif command == "stopIndefJog":
            self._logger.info("Stopping indef jog")
            self.palette.stopIndefJog()
        elif command == "testPrinterCommands":
            self.palette.printerTest()
        elif command == "connectWifi":
            self.palette.connectWifi(data["wifiSSID"], data["wifiPASS"])
        elif command == "uiUpdate":
            self.palette.updateUI()
        return flask.jsonify(foo="bar")

    def on_api_get(self, request):
        self._plugin_manager.send_plugin_message(self._identifier, "Omega Message")
        return flask.jsonify(foo="bar") 

    def on_event(self, event, payload):
        if "ClientOpened" in event:
            self.palette.updateUI()
        elif "PrintStarted" in event:
            if ".oem" in payload["filename"]:
                self.palette.setFilename(payload["filename"].split('.')[0])
                self._logger.info("Filename: %s" % payload["filename"].split('.')[0])
        elif "FileAdded" in event:
            #User uploads a new file to Octoprint, we should update the demo list of files
            self._plugin_manager.send_plugin_message(self._identifier, "UI:Refresh Demo List")
        elif "FileRemoved" in event:
            #User removed a file from Octoprint, we should update the demo list of files
            self._plugin_manager.send_plugin_message(self._identifier, "UI:Refresh Demo List")
        elif "SettingsUpdated" in event:
            if self._settings.get(["autoconnect"]):
                self.palette.startConnectionThread()
            else:
                self.palette.stopConnectionThread()

    def on_shutdown(self):
        self.palette.shutdown()
    
    def sending_gcode(self, comm_instance, phase, cmd, cmd_type, gcode, subcode, tags=None):
        if "O31" in cmd:
            self.palette.enqueueCmd(cmd.strip())
            return "G4 P10",
        elif 'O' in cmd[0]:
            self.palette.gotOmegaCmd(cmd)
            return None,
        elif 'M0' in cmd[0]:
            return None,
        #return gcode

    def support_msf_machinecode(*args, **kwargs):
        return dict(
            machinecode=dict(
                msf=["msf"]
            )
        )


    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
        # for details.
        return dict(
	    palette2=dict(
	        displayName="Palette 2 Plugin",
                displayVersion=self._plugin_version,
                current=self._plugin_version,
	        type="commandline",
	        command="/home/pi/test-version.sh",

	        # update method: pip
	        pip="https://gitlab.com/mosaic-mfg/palette-2-plugin/-/archive/plugin-refactor/palette-2-plugin-plugin-refactor.zip"
	    )
        )


__plugin_name__ = "Palette 2"
__plugin_version__ = "0.1.0"
__plugin_description__ = "A Palette 2 plugin for OctoPrint (Beta)"
def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = P2Plugin()
    
    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.gcode.sending": __plugin_implementation__.sending_gcode,
        "octoprint.filemanager.extension_tree":  __plugin_implementation__.support_msf_machinecode,
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
