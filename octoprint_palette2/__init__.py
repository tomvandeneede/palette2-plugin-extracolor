# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.filemanager
import flask
import requests
import os.path
from distutils.version import LooseVersion
from . import constants
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
        self._logger.info("%s Plugin STARTED" % self._plugin_info)
        if os.path.isdir("/home/pi/OctoPrint/venv/lib/python2.7/site-packages/Canvas-0.1.0-py2.7.egg-info/") and os.path.isdir("/home/pi/.mosaicdata/turquoise/"):
            call(["sudo rm -rf /home/pi/OctoPrint/venv/lib/python2.7/site-packages/Canvas-0.1.0-py2.7.egg-info/"], shell=True)
            call(["sudo chown -R pi:pi /home/pi/OctoPrint/venv/lib/python2.7/site-packages/"], shell=True)
        self.palette = Omega.Omega(self)
        self.palette.isHubS = self.palette.determineHubVersion()
        self.palette.startLedThread()
        self.palette.checkForRuamelVersion()
        self.palette.ports = self.palette.getAllPorts()
        self.palette.updateHubSLedScript()

    def get_settings_defaults(self):
        return dict(autoconnect=False,
                    palette2Alerts=True,
                    baudrate=115200,
                    selectedPort=None,
                    advancedOptions=False,
                    feedRateControl=False,
                    feedRateNormalPct=100,
                    feedRateSlowPct=75,
                    autoVariationCancelPing=False,
                    variationPct=8,
                    showPingOnPrinter=False
                    )

    def get_template_configs(self):
        return [
            dict(type="navbar", custom_bindings=False),
            dict(type="settings", custom_bindings=False)
        ]

    def get_assets(self):
        return dict(
            js=["js/palette2.js", "js/utils/alerts.js", "js/utils/ui.js"],
            css=["css/palette2.css"],
            less=["less/palette2.less"]
        )

    def get_api_commands(self):
        return dict(
            clearPalette2=[],
            connectOmega=["port"],
            disconnectPalette2=[],
            sendCutCmd=[],
            sendOmegaCmd=["cmd"],
            uiUpdate=[],
            changeAlertSettings=["condition"],
            displayPorts=["condition"],
            sendErrorReport=["errorNumber", "description"],
            startPrint=[],
            changeAutoVariationCancelPing=["condition"],
            changeVariationPct=["value"],
            changeShowPingOnPrinter=["condition"],
            changeFeedRateControl=["condition"],
            changeFeedRateSlowed=["condition"],
            changeFeedRateNormalPct=["value"],
            changeFeedRateSlowPct=["value"],
            startAutoLoad=[],
            downloadPingHistory=[]
        )

    def on_api_command(self, command, payload):
        self._logger.info("Got a command %s" % command)
        try:
            data = None
            if command == "connectOmega":
                self.palette.connectOmega(payload["port"])
            elif command == "disconnectPalette2":
                self.palette.disconnect()
            elif command == "sendCutCmd":
                self.palette.cut()
            elif command == "clearPalette2":
                self.palette.clear()
            elif command == "sendOmegaCmd":
                self.palette.enqueueCmd(payload["cmd"])
            elif command == "uiUpdate":
                self.palette.updateUIAll()
            elif command == "changeAlertSettings":
                self.palette.changeAlertSettings(payload["condition"])
            elif command == "displayPorts":
                self.palette.displayPorts(payload["condition"])
            elif command == "sendErrorReport":
                self.palette.sendErrorReport(payload["errorNumber"], payload["description"])
            elif command == "startPrint":
                self.palette.startPrintFromHub()
            elif command == "startAutoLoad":
                self.palette.startAutoLoadThread()
                self.palette.enqueueCmd("O102 D0")
            elif command == "changeAutoVariationCancelPing":
                self.palette.changeAutoVariationCancelPing(payload["condition"])
            elif command == "changeVariationPct":
                self.palette.changeVariationPct(payload["value"])
            elif command == "changeShowPingOnPrinter":
                self.palette.changeShowPingOnPrinter(payload["condition"])
            elif command == "changeFeedRateControl":
                self.palette.changeFeedRateControl(payload["condition"])
            elif command == "changeFeedRateNormalPct":
                self.palette.changeFeedRateNormalPct(payload["value"])
            elif command == "changeFeedRateSlowPct":
                self.palette.changeFeedRateSlowPct(payload["value"])
            elif command == "downloadPingHistory":
                data = self.palette.downloadPingHistory()
            response = "POST request (%s) successful" % command
            return flask.jsonify(response=response, data=data, status=constants.API_SUCCESS), constants.API_SUCCESS
        except Exception as e:
            error = str(e)
            self._logger.info("Exception message: %s" % str(e))
            return flask.jsonify(error=error, status=constants.API_FAILURE), constants.API_FAILURE

    def on_event(self, event, payload):
        try:
            if "ClientOpened" in event:
                self.palette.updateUIAll()
            elif "PrintPaused" in event:
                if ".mcf.gcode" in payload["name"]:
                    self.palette.printPaused = True
                    self.palette.updateUI({"command": "printPaused", "data": self.palette.printPaused})
            elif "PrintResumed" in event:
                if ".mcf.gcode" in payload["name"]:
                    self.palette.palette2SetupStarted = False
                    self.palette.updateUI({"command": "palette2SetupStarted", "data": self.palette.palette2SetupStarted})
                    self.palette.printPaused = False
                    self.palette.updateUI({"command": "printPaused", "data": self.palette.printPaused})
            elif "PrintDone" in event:
                if ".mcf.gcode" in payload["name"]:
                    self.palette.actualPrintStarted = False
                    self.palette.updateUI({"command": "actualPrintStarted", "data": self.palette.actualPrintStarted})
            elif "PrintFailed" in event:
                if ".mcf.gcode" in payload["name"]:
                    self.palette.actualPrintStarted = False
                    self.palette.updateUI({"command": "actualPrintStarted", "data": self.palette.actualPrintStarted})
            elif "PrintCancelled" in event:
                if ".mcf.gcode" in payload["name"] and self.palette.connected:
                    self.palette.actualPrintStarted = False
                    self.palette.updateUI({"command": "actualPrintStarted", "data": self.palette.actualPrintStarted})
                    if not self.palette.cancelFromP2:
                        self._logger.info("Cancelling print from Hub")
                        self.palette.cancelFromHub = True
                        self.palette.cancel()
                    else:
                        self._logger.info("Cancel already done from P2.")
            elif "FileAdded" in event:
                self.palette.getAllMCFFilenames()
            elif "FileRemoved" in event:
                self.palette.getAllMCFFilenames()
            elif "SettingsUpdated" in event:
                self._logger.info("Auto-reconnect: %s" % str(self._settings.get(["autoconnect"])))
                self._logger.info("Display Alerts: %s" % str(self._settings.get(["palette2Alerts"])))
                self._logger.info("Display Advanced Options: %s" % str(self._settings.get(["advancedOptions"])))
                self.palette.updateUI({"command": "autoConnect", "data": self._settings.get(["autoconnect"])})
                self.palette.updateUI({"command": "displaySetupAlerts", "data": self._settings.get(["palette2Alerts"])})
                self.palette.updateUI({"command": "advanced", "subCommand": "displayAdvancedOptions", "data": self._settings.get(["advancedOptions"])})
                if not self._settings.get(["advancedOptions"]):
                    self.palette.changeAutoVariationCancelPing(False)
                    self.palette.changeShowPingOnPrinter(False)
                    self.palette.changeFeedRateControl(False)
                self.palette.advanced_update_variables()
                if self._settings.get(["autoconnect"]):
                    self.palette.startConnectionThread()
                else:
                    self.palette.stopConnectionThread()
        except Exception as e:
            self._logger.info(e)

    def on_shutdown(self):
        self.palette.shutdown()

    def sending_gcode(self, comm_instance, phase, cmd, cmd_type, gcode, subcode=None, tags=None):
        if cmd is not None and len(cmd) > 1:
            # pings in GCODE
            if "O31" in cmd:
                self.palette.savePing(cmd.strip())
                return "G4 P10",
            # header information
            elif 'O' in cmd[0]:
                self.palette.gotOmegaCmd(cmd)
                return None,
            # pause print locally
            elif 'M0' in cmd[0:2]:
                self.palette.printPaused = True
                self.palette.updateUI({"command": "printPaused", "data": self.palette.printPaused})
                return None,
                # return gcode

    def support_msf_machinecode(*args, **kwargs):
        return dict(
            machinecode=dict(
                msf=["msf"]
            )
        )

    def get_latest(self, target, check, full_data=False, online=True):
        resp = requests.get("http://emerald.mosaicmanufacturing.com/canvas-hub-palette/latest")
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
