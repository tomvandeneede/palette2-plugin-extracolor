# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import flask
from . import Omega

class OmegaPlugin(octoprint.plugin.StartupPlugin, 
                       octoprint.plugin.TemplatePlugin, 
                       octoprint.plugin.SettingsPlugin, 
                       octoprint.plugin.AssetPlugin, 
                       octoprint.plugin.SimpleApiPlugin, 
                       octoprint.plugin.EventHandlerPlugin,
                       octoprint.plugin.ShutdownPlugin):

    def on_after_startup(self):
        self.omega = Omega.Omega(self)

    def get_settings_defaults(self):
        pass

    def get_template_configs(self):
        return [ dict(type="navbar", custom_bindings=False), dict(type="settings", custom_bindings=False) ]

    def get_assets(self):
        return dict(
            js=["js/omega.js"],
            css=["css/omega.css"]
        )

    def get_api_commands(self):
        return dict (
            command1= [],
            setActiveDrive = ["drive"],
            startSingleColor = [],
            startSpliceDemo = [],
            connectOmega = ["port"],
            testPrinterCommands = [],
            sendOmegaCmd = ["cmd"],
            printStart = [],
            uiUpdate = [],
            sdwpStart = []
        )

    def on_api_command(self, command, data):
        self._logger.info("Got a command %s" % command)
        if command == "setActiveDrive":
            self._logger.info("Setting active drive to %s" % data["drive"])
            #set the active drive in the Omega class to the drive that was passed
            self.omega.setActiveDrive(data["drive"])
        elif command == "startSingleColor":
            self._logger.info("Got Start Single Color Mode command")
            if "drive" in data:
                self._logger.info("Starting single color with drive %s" % data["drive"])
                self.omega.setActiveDrive(data["drive"])
            self.omega.startSingleColor()
        elif command == "startSpliceDemo":
            self._logger.info("Starting a splice demo")
            # pass the file path to Omega
            #self.omega.setFilepath(data["filepath"]) 
            self.omega.startSpliceDemo(withPrinter = False)
        elif command == "connectOmega":
            self.omega.connectOmega(data["port"])
        elif command == "testPrinterCommands":
            self.omega.printerTest()
            #self._logger.info("Sending a G28")
            #self._printer.commands(["G28", "G1 X150 Y150 Z10 F6000"])
        elif command == "sendOmegaCmd":
            self.omega.sendCmd(data["cmd"])
        elif command == "printStart":
            self.omega.sendPrintStart()
        elif command == "sdwpStart":
            self.omega.startSpliceDemo(withPrinter = True)
        elif command == "uiUpdate":
            self.omega.sendUIUpdate()
        return flask.jsonify(foo="bar")

    def on_api_get(self, request):
        self._plugin_manager.send_plugin_message(self._identifier, "Omega Message")
        return flask.jsonify(foo="bar") 

    def on_event(self, event, payload):
        self._logger.info("Got event: %s" % event)
        if "ClientOpened" in event:
            self.omega.sendUIUpdate()

    def on_shutdown(self):
        self.omega.shutdown()
    
    def sending_gcode(self, comm_instance, cmd, cmd_type):
        if cmd and "O27 " in cmd:
            self.omega.sendCmd(cmd)
            self._logger.info("got a ping %s", cmd.strip())
        elif cmd and cmd[0] is 'O':
            self.omega.gotOmegaCmd(cmd.strip())
        return cmd

__plugin_name__ = "Omega"
__plugin_version__ = "0.1.0"
__plugin_description__ = "A Palette-2i plugin for OctoPrint (Beta)"
def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = OmegaPlugin()
    
    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.sending_gcode
    }
