# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.filemanager
import flask
import requests
import os.path
from distutils.version import LooseVersion
from . import Omega
from subprocess import call


class P2Plugin(octoprint.plugin.StartupPlugin,
               octoprint.plugin.TemplatePlugin,
               octoprint.plugin.SettingsPlugin,
               octoprint.plugin.AssetPlugin,
               octoprint.plugin.SimpleApiPlugin,
               octoprint.plugin.EventHandlerPlugin,
               octoprint.plugin.ShutdownPlugin):

    def get_sorting_key(self, context):
        if context == "StartupPlugin.on_after_startup":
            return 1
        return None

    def on_after_startup(self):
        self._logger.info("Palette 2 Plugin STARTED")

        if os.path.isdir("/home/pi/OctoPrint/venv/lib/python2.7/site-packages/Canvas-0.1.0-py2.7.egg-info/") and os.path.isdir("/home/pi/.mosaicdata/turquoise/"):
            call(["sudo rm -rf /home/pi/OctoPrint/venv/lib/python2.7/site-packages/Canvas-0.1.0-py2.7.egg-info/"], shell=True)
            call(
                ["sudo chown -R pi:pi /home/pi/OctoPrint/venv/lib/python2.7/site-packages/"], shell=True)
        self.palette = Omega.Omega(self)

    def get_settings_defaults(self):
        return dict(autoconnect=False, palette2Alerts=True)

    def get_template_configs(self):
        return [
            dict(type="navbar", custom_bindings=False),
            dict(type="settings", custom_bindings=False)
        ]

    def get_assets(self):
        return dict(
            js=["js/palette2.js"],
            css=["css/palette2.css"],
            less=["less/palette2.less"]
        )

    def get_api_commands(self):
        return dict(
            cancelPalette2=[],
            clearPalette2=[],
            connectOmega=["port"],
            disconnectPalette2=[],
            printStart=[],
            sendCutCmd=[],
            sendOmegaCmd=["cmd"],
            uiUpdate=[],
            connectWifi=["wifiSSID", "wifiPASS"],
            changeAlertSettings=["condition"],
            displayPorts=["condition"],
            sendErrorReport=["send"],
            startPrint=[]
        )

    def on_api_command(self, command, data):
        self._logger.info("Got a command %s" % command)
        if command == "cancelPalette2":
            self._logger.info("Cancelling print")
            self.palette.enqueueCmd("O0")
        elif command == "clearPalette2":
            self.palette.clear()
        elif command == "connectOmega":
            self._logger.info("Command received")
            self.palette.connectOmega(data["port"])
        elif command == "disconnectPalette2":
            self.palette.disconnect()
        elif command == "printStart":
            self.palette.sendPrintStart()
        elif command == "sendCutCmd":
            self.palette.cut()
        elif command == "sendOmegaCmd":
            self.palette.enqueueCmd(data["cmd"])
        elif command == "connectWifi":
            self.palette.connectWifi(data["wifiSSID"], data["wifiPASS"])
        elif command == "uiUpdate":
            self.palette.updateUI()
        elif command == "changeAlertSettings":
            self.palette.changeAlertSettings(data["condition"])
        elif command == "displayPorts":
            self.palette.displayPorts(data["condition"])
        elif command == "sendErrorReport":
            self.palette.sendErrorReport(data["send"])
        elif command == "startPrint":
            self.palette.startPrintFromHub()
        return flask.jsonify(foo="bar")

    def on_api_get(self, request):
        self._plugin_manager.send_plugin_message(
            self._identifier, "Omega Message")
        return flask.jsonify(foo="bar")

    def on_event(self, event, payload):
        if "ClientOpened" in event:
            self.palette.printerConnection = self._printer.get_current_connection()[
                0]
            self.palette.updateUI()
            self.palette.printerConnection = ""
        elif "PrintStarted" in event:
            if ".mcf.gcode" in payload["name"]:
                self._logger.info("PRINT STARTED P2")
                self.palette.resetPrintValues()
                self.palette.tryHeartbeatBeforePrint()
                self._logger.info("Filename: %s" %
                                  payload["name"].split('.')[0])
                self.palette.setFilename(payload["name"].split(".")[0])
                self.palette.updateUI()
                self.palette.printHeartbeatCheck = ""
        elif "PrintPaused" in event:
            if ".mcf.gcode" in payload["name"]:
                self.palette.printPaused = True
                self.palette.updateUI()
        elif "PrintResumed" in event:
            if ".mcf.gcode" in payload["name"]:
                self.palette.palette2SetupStarted = False
                self.palette.printPaused = False
                self.palette.updateUI()
        elif "PrintDone" in event:
            if ".mcf.gcode" in payload["name"]:
                self.palette.actualPrintStarted = False
                self.palette.updateUI()
        elif "PrintFailed" in event:
            if ".mcf.gcode" in payload["name"]:
                self.palette.actualPrintStarted = False
                self.palette.updateUI()
        elif "PrintCancelled" in event:
            if ".mcf.gcode" in payload["name"]:
                self.palette.actualPrintStarted = False
                self.palette.updateUI()
        elif "FileAdded" in event:
            # User uploads a new file to Octoprint, we should update the demo list of files
            self.palette.getAllMCFFilenames()
            self._plugin_manager.send_plugin_message(
                self._identifier, "UI:Refresh Demo List")
        elif "FileRemoved" in event:
            # User removed a file from Octoprint, we should update the demo list of files
            self.palette.getAllMCFFilenames()
            self._plugin_manager.send_plugin_message(
                self._identifier, "UI:Refresh Demo List")
        elif "SettingsUpdated" in event:
            self._logger.info("Auto-reconnect: %s" %
                              str(self._settings.get(["autoconnect"])))
            self._logger.info("Display alerts: %s" % str(
                self._settings.get(["palette2Alerts"])))
            self.palette.updateUI()
            if self._settings.get(["autoconnect"]):
                self.palette.startConnectionThread()
            else:
                self.palette.stopConnectionThread()

    def on_shutdown(self):
        self.palette.shutdown()

    def sending_gcode(self, comm_instance, phase, cmd, cmd_type, gcode, subcode=None, tags=None):
        if "O31" in cmd:
            self.palette.handlePing(cmd.strip())
            return "G4 P10",
        elif 'O' in cmd[0]:
            self.palette.gotOmegaCmd(cmd)
            return None,
        elif 'M0' in cmd[0]:
            return None,
        # return gcode

    def support_msf_machinecode(*args, **kwargs):
        return dict(
            machinecode=dict(
                msf=["msf"]
            )
        )

    def get_latest(self, target, check, full_data=False, online=True):
        resp = requests.get(
            "http://emerald.mosaicmanufacturing.com/canvas-hub-palette/latest")
        version_data = resp.json()
        version = version_data["versions"][0]["version"]
        current_version = check.get("current")
        information = dict(
            local=dict(
                name=current_version,
                value=current_version,
            ),
            remote=dict(
                name=version,
                value=version
            )
        )
        self._logger.info("current version: %s" % current_version)
        self._logger.info("remote version: %s" % version)
        needs_update = LooseVersion(current_version) < LooseVersion(version)
        self._logger.info("needs update: %s" % needs_update)
        return information, not needs_update

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
        # for details.
        return dict(
            palette2=dict(
                displayName="Palette 2 Plugin",
                displayVersion=self._plugin_version,
                current=self._plugin_version,
                type="python_checker",
                python_checker=self,
                command="/home/pi/test-version.sh",

                # update method: pip
                pip="https://gitlab.com/mosaic-mfg/palette-2-plugin/-/archive/master/palette-2-plugin-master.zip"
            )
        )


__plugin_name__ = "Palette 2"
__plugin_description__ = "A plugin to handle communication with Palette 2"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = P2Plugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.gcode.sending": __plugin_implementation__.sending_gcode,
        "octoprint.filemanager.extension_tree":  __plugin_implementation__.support_msf_machinecode,
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
