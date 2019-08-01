function OmegaViewModel(parameters) {
  var self = this;

  /* OTHER VIEWMODELS */
  self.settings = parameters[0];
  self.control = parameters[1];
  self.printerState = parameters[2];
  self.files = parameters[3];

  /* GLOBAL VARIABLES */
  self.notificationId = "";
  self.displaySetupAlerts = true;
  self.tryingToConnect = false;
  self.firstTime = false;
  self.actualPrintStarted = false;
  self.autoconnect = false;

  /* KNOCKOUT DATA-BINDINGS */
  self.omegaCommand = ko.observable();
  self.wifiSSID = ko.observable();
  self.wifiPASS = ko.observable();
  self.omegaPort = ko.observable();

  self.currentSplice = ko.observable();
  self.nSplices = ko.observable();
  self.totalSplicesDisplay = ko.computed(function () {
    return " / " + self.nSplices() + " Splices";
  });
  self.connected = ko.observable(false);
  self.connectPaletteText = ko.computed(function () {
    return self.connected() ? "Connected" : "Connect to Palette 2";
  });
  self.disconnectPaletteText = ko.computed(function () {
    return self.connected() ? "Disconnect" : "Disconnected";
  });

  self.currentStatus = ko.observable();
  self.amountLeftToExtrude = ko.observable();
  self.palette2SetupStarted = ko.observable();
  self.connectionStateMsg = ko.computed(function () {
    if (self.connected()) {
      return "Connected";
    } else {
      return self.autoconnect ? "Not Connected - Trying To Connect..." : "Not Connected";
    }
  });
  self.filaLength = ko.observable();
  self.filaLengthDisplay = ko.computed(function () {
    return (Number(self.filaLength()) / 1000.0).toFixed(2) + "m";
  });

  self.ports = ko.observableArray([]);
  self.selectedPort = ko.observable();
  self.pings = ko.observableArray([]);
  self.pingsDisplay = ko.computed(function () {
    if (self.pings()) {
      return self.pings().map(ping => {
        if (ping.percent !== "MISSED") {
          ping.percent = ping.percent + "%";
        }
        return ping;
      });
    } else {
      return [];
    }
  });
  self.latestPing = ko.computed(function () {
    return self.pingsDisplay()[0] ? self.pingsDisplay()[0].number : 0;
  });
  self.latestPingPercent = ko.computed(function () {
    return self.pingsDisplay()[0] ? self.pingsDisplay()[0].percent : "%";
  });
  self.pongs = ko.observableArray([]);
  self.pongsDisplay = ko.computed(function () {
    if (self.pongs()) {
      return self.pongs().map(pong => {
        pong.percent = pong.percent + "%";
        return pong;
      });
    } else {
      return [];
    }
  });
  self.latestPong = ko.computed(function () {
    return self.pongsDisplay()[0] ? self.pongsDisplay()[0].number : 0;
  });
  self.latestPongPercent = ko.computed(function () {
    return self.pongsDisplay()[0] ? self.pongsDisplay()[0].percent : "%";
  });

  self.autoCancelPing = ko.observable(true);
  self.showPingOnPrinter = ko.observable(true);
  self.feedRateControl = ko.observable(true);
  self.feedRateSlowed = ko.observable(false);
  self.feedRateSlowedText = ko.computed(function () {
    return self.feedRateSlowed() && self.printerState.isPrinting() ? "Yes" : "No";
  });
  self.feedRateNormalPct = ko.observable(100);
  self.feedRateSlowPct = ko.observable(50);
  self.feedRateStatus = ko.observable("Awaiting Update...");
  self.advancedOptions = ko.observable();

  self.autoLoad = ko.observable(false);
  self.isAutoLoading = ko.observable(false);
  self.autoLoadButtonText = ko.computed(function () {
    return self.isAutoLoading() ? "Loading..." : "Smart Load";
  });
  self.amountLeftToExtrudeText = ko.computed(function () {
    if (self.amountLeftToExtrude() > 0 || self.amountLeftToExtrude() < 0) {
      return `${self.amountLeftToExtrude()}mm`;
    } else if (self.amountLeftToExtrude() === 0) {
      return "Loading complete";
    } else {
      return "No loading offset detected";
    }
  });

  /* COMMUNICATION TO BACK-END FUNCTIONS */
  self.displayPorts = () => {
    const condition = $(".serial-ports-list").is(":visible") ? "closing" : "opening";
    const payload = {
      command: "displayPorts",
      condition: condition
    };
    self.ajaxRequest(payload).then(() => {
      self.settings.requestData();
    });
  };

  self.connectOmega = () => {
    self.tryingToConnect = true;
    UI.loadingOverlay(true, "connect");
    const payload = {
      command: "connectOmega",
      port: self.selectedPort() || ""
    }
    self.ajaxRequest(payload).always(value => {
      self.tryingToConnect = false;
      UI.loadingOverlay(false);
    });
  };

  self.disconnectPalette2 = () => {
    UI.loadingOverlay(true, "disconnect");
    self.connected(false);
    self.removeNotification();
    const payload = { command: "disconnectPalette2" };
    self.ajaxRequest(payload).always(value => {
      UI.loadingOverlay(false);
    });
  };

  self.changeAlertSettings = condition => {
    self.displaySetupAlerts = !condition;
    const payload = {
      command: "changeAlertSettings",
      condition: self.displaySetupAlerts
    };
    self.ajaxRequest(payload).then(() => {
      self.settings.requestData();
    });
  };

  self.sendOmegaCmd = (command) => {
    const payload = {
      command: "sendOmegaCmd",
      cmd: command,
    };
    self.ajaxRequest(payload);
  };

  self.uiUpdate = () => {
    console.log("Requesting BE to update UI");
    const payload = { command: "uiUpdate" };
    self.ajaxRequest(payload);
  };

  self.connectWifi = () => {
    const payload = {
      command: "connectWifi",
      wifiSSID: self.wifiSSID(),
      wifiPASS: self.wifiPASS()
    };
    self.ajaxRequest(payload);
  };

  self.sendCutCmd = () => {
    const payload = { command: "sendCutCmd" };
    self.ajaxRequest(payload);
  };

  self.sendClearOutCmd = () => {
    const payload = { command: "clearPalette2" };
    self.ajaxRequest(payload);
  };

  self.sendErrorReport = (errorNumber, description) => {
    const payload = {
      command: "sendErrorReport",
      errorNumber: errorNumber,
      description: description
    };
    self.ajaxRequest(payload);
  };

  self.startPrintFromHub = () => {
    const payload = { command: "startPrint" };
    self.ajaxRequest(payload);
  };

  self.downloadPingHistory = (data, event) => {
    event.stopPropagation();
    self.ajaxRequest({ command: "downloadPingHistory" }).then(result => {
      const filename = result.data.filename;
      const data = result.data.data;

      const blob = new Blob([data], { type: "text/plain" });
      if (window.navigator.msSaveOrOpenBlob) {
        window.navigator.msSaveBlob(blob, filename);
      } else {
        const elem = window.document.createElement("a");
        elem.href = window.URL.createObjectURL(blob);
        elem.download = filename;
        document.body.appendChild(elem);
        elem.click();
        elem.href = window.URL.revokeObjectURL(blob);
        document.body.removeChild(elem);
      }
    });
  };

  self.startAutoLoad = () => {
    self.ajaxRequest({ command: "startAutoLoad" });
  };

  self.feedRateControl.subscribe(function () {
    self.ajaxRequest({ command: "changeFeedRateControl", condition: self.feedRateControl() });
  });
  self.autoCancelPing.subscribe(function () {
    self.ajaxRequest({ command: "changeAutoCancelPing", condition: self.autoCancelPing() });
  });
  self.showPingOnPrinter.subscribe(function () {
    self.ajaxRequest({ command: "changeShowPingOnPrinter", condition: self.showPingOnPrinter() });
  });
  self.feedRateNormalPct.subscribe(function () {
    self.ajaxRequest({ command: "changeFeedRateNormalPct", value: self.feedRateNormalPct() });
  });
  self.feedRateSlowPct.subscribe(function () {
    self.ajaxRequest({ command: "changeFeedRateSlowPct", value: self.feedRateSlowPct() });
  });

  self.ajaxRequest = payload => {
    return $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8"
    });
  };

  self.handleAdvancedOptions = (subCommand, data) => {
    switch (subCommand) {
      case "displayAdvancedOptions":
        self.advancedOptions(data);
        break;
      case "feedRateControl":
        self.feedRateControl(data);
        break;
      case "feedRateSlowed":
        self.feedRateSlowed(data);
        break;
      case "autoCancelPing":
        self.autoCancelPing(data);
        break;
      case "showPingOnPrinter":
        self.showPingOnPrinter(data);
        break;
      case "feedRateNormalPct":
        self.feedRateNormalPct(data);
        break;
      case "feedRateSlowPct":
        self.feedRateSlowPct(data);
        break;
      case "advancedStatus":
        self.feedRateStatus(data);
        break;
      case "isAutoLoading":
        self.isAutoLoading(data);
        self.toggleSmallLoader();
        self.toggleAutoLoadText();
        break;
      default:
      //Do Nothing
    }
  };

  self.fromResponse = () => { };

  /* UI FUNCTIONS */

  self.checkIfCountdownExists = () => {
    if ($("body").find("#load-filament-notification").length === 0) {
      self.displayFilamentCountdown();
    }
  };

  self.smartLoadInfoListener = () => {
    $("body").find(".smart-load-icon").on("click", () => {
      self.toggleSmartLoadInfo();
    });
  };

  self.removePopupListener = () => {
    $(".remove-button").on("click", () => {
      self.removeNotification();
    });
  };

  self.autoLoadListener = () => {
    $(".autoload-button").on("click", () => {
      self.startAutoLoad();
    });
  };

  self.displayFilamentCountdown = () => {
    const notification = $(`
    <li id="load-filament-notification" class="popup-notification">
		  <i class="material-icons remove-button">clear</i>
		  <h6 class="load-filament-title">Remaining Length To Extrude:</h6>
      <div class="value-container">
        <span class="load-filament-value">${self.amountLeftToExtrudeText()}</span>
        <span class="small-loader-autoload"></span>
      </div>
      <div class="smart-load-container">
        <button class="btn btn-primary autoload-button">${self.autoLoadButtonText()}</button>
        <div class="smart-load-info-container">
          <i class="material-icons smart-load-icon">info_outline</i>
          <div class="smart-load-text" id="autoload-filament-text">
            <h6 class="smart-load-heading">Smart Loading makes starting a print easier</h6>
            <div class="smart-load-body"><p>Securely load your filament into your printer's extruder, insert the Outgoing Tube into the clip, then click "Smart Load". CANVAS Hub will automatically load the correct amount of filament into your printer and begin the print automatically.</p></div>
          </div>
        </div>
      </div>
    </li>`).hide();
    self.notificationId = "#load-filament-notification";
    $(".side-notifications-list").append(notification);

    self.smartLoadInfoListener();
    self.removePopupListener();
    self.autoLoadListener();
    self.toggleSmallLoader();
  };

  self.updateFilamentCountdown = firstValue => {
    if (self.amountLeftToExtrude() < 0) {
      UI.closeAlert();
      $(self.notificationId)
        .find(".load-filament-value")
        .addClass("negative-number");
    } else {
      $(self.notificationId)
        .find(".load-filament-value")
        .removeClass("negative-number");
    }
    if (firstValue) {
      $(self.notificationId)
        .fadeIn(200)
        .find(".load-filament-value")
        .text(`${self.amountLeftToExtrudeText()}`);
    } else {
      $(self.notificationId)
        .find(".load-filament-value")
        .text(`${self.amountLeftToExtrudeText()}`);
    }
  };

  self.removeNotification = () => {
    $(self.notificationId).fadeOut(500, function () {
      this.remove();
    });
  };

  self.showAlert = (command, condition) => {
    if (command === "temperature") {
      if (self.displaySetupAlerts) {
        const base_url = window.location.origin;
        window.location.href = `${base_url}/#temp`;
        UI.temperatureHighlight();
        Alerts.preheatAlert();
      }
    } else if (command === "extruder") {
      if (self.displaySetupAlerts) {
        const base_url = window.location.origin;
        window.location.href = `${base_url}/#control`;
        UI.extrusionHighlight();
        Alerts.extrusionAlert(self.firstTime);
      }
    } else if (command === "cancelling") {
      self.removeNotification();
      Alerts.printCancellingAlert();
    } else if (command === "printStarted") {
      // if user presses start from P2
      UI.closeAlert();
    } else if (command === "cancelled") {
      self.removeNotification();
      Alerts.printCancelledAlert();
    } else if (command === "startPrint") {
      if (self.displaySetupAlerts) {
        $("body").on("click", ".setup-checkbox input", event => {
          self.changeAlertSettings(event.target.checked);
        });
      }
      Alerts.readyToStartAlert(self.displaySetupAlerts).then(result => {
        if (result.hasOwnProperty("value")) {
          self.startPrintFromHub();
        }
      });
    } else if (command === "cannotConnect") {
      Alerts.cannotConnectAlert();
    } else if (command === "heartbeat") {
      UI.loadingOverlay(false);
      if (condition === "P2NotConnected") {
        Alerts.displayHeartbeatAlert();
      } else if (condition === "P2Responded") {
        Alerts.palette2PrintStartAlert()
      }
    } else if (command === "error") {
      Alerts.errorAlert(condition).then(result => {
        // if user clicks yes
        if (result.value) {
          Alerts.errorTextAlert().then(result => {
            if (result.dismiss === Swal.DismissReason.cancel) {
            } else {
              description = "";
              if (result.value) {
                description = result.value;
              }
              self.sendErrorReport(condition, description);
            }
          });
        }
        // if user clicks no
        else if (result.dismiss === Swal.DismissReason.cancel) {
        }
      });
    } else if (command === "noSerialPorts") {
      Alerts.noSerialPortsAlert();
    } else if (command === "turnOnP2") {
      Alerts.palette2NotConnectedAlert();
    } else if (command === "autoLoadIncomplete") {
      Alerts.autoLoadFailAlert();
    } else if (command === "threadError") {
      Alerts.P2SerialConnectionErrorAlert()
    }
  };

  self.toggleAdvancedOptionInfo = (data, event) => {
    const targetId = `#${event.target.nextElementSibling.id}`;
    if ($(`.advanced-info-text:not(${targetId})`).is(":visible")) {
      $(".advanced-info-text").hide(50);
    }
    $(targetId).toggle(50);
  };

  self.toggleSmartLoadInfo = (data, event) => {
    $(".smart-load-text").toggle(50);
  };

  self.toggleSmallLoader = () => {
    if (self.isAutoLoading()) {
      $(".small-loader-autoload").show();
    } else {
      $(".small-loader-autoload").fadeOut(200);
    }
  };

  self.toggleAutoLoadText = () => {
    if (self.isAutoLoading() || self.amountLeftToExtrude() <= 0 || self.firstTime) {
      $(self.notificationId)
        .find(".autoload-button")
        .text(`${self.autoLoadButtonText()}`)
        .attr("disabled", "disabled");
    } else {
      $(self.notificationId)
        .find(".autoload-button")
        .text(`${self.autoLoadButtonText()}`)
        .removeAttr("disabled");
    }
  };

  self.togglePingHistory = (data, event) => {
    if (self.pingsDisplay().length) {
      $(".ping-history").slideToggle();
    }
  };

  self.togglePongHistory = () => {
    if (self.pongsDisplay().length) {
      $(".pong-history").slideToggle();
    }
  };

  /* VIEWMODELS MODIFICATIONS FOR P2 PLUGIN */

  self.modifyPrinterStateVM = () => {
    self.printerState.enablePrint = ko.pureComputed(function () {
      if (self.printerState.filename() && self.printerState.filename().includes(".mcf.gcode")) {
        return (
          self.printerState.isOperational() &&
          self.printerState.isReady() &&
          !self.printerState.isPrinting() &&
          !self.printerState.isCancelling() &&
          !self.printerState.isPausing() &&
          self.printerState.loginState.isUser() &&
          self.printerState.filename() &&
          self.connected()
        );
      } else {
        return (
          self.printerState.isOperational() &&
          self.printerState.isReady() &&
          !self.printerState.isPrinting() &&
          !self.printerState.isCancelling() &&
          !self.printerState.isPausing() &&
          self.printerState.loginState.isUser() &&
          self.printerState.filename()
        );
      }
    });

    self.printerState.enablePause = ko.pureComputed(function () {
      if (
        self.printerState.filename() &&
        self.printerState.filename().includes(".mcf.gcode") &&
        self.palette2SetupStarted()
      ) {
        return false;
      } else {
        return (
          self.printerState.isOperational() &&
          (self.printerState.isPrinting() || self.printerState.isPaused()) &&
          !self.printerState.isCancelling() &&
          !self.printerState.isPausing() &&
          self.printerState.loginState.isUser()
        );
      }
    });
  };

  self.modifyFilesVM = () => {
    self.files.enablePrint = function (data) {
      if (data.name.includes(".mcf.gcode")) {
        return (
          self.files.loginState.isUser() &&
          self.files.isOperational() &&
          !(self.files.isPrinting() || self.files.isPaused() || self.files.isLoading()) &&
          self.connected()
        );
      } else {
        return (
          self.files.loginState.isUser() &&
          self.files.isOperational() &&
          !(self.files.isPrinting() || self.files.isPaused() || self.files.isLoading())
        );
      }
    };

    self.files.enableSelect = function (data, printAfterSelect) {
      if (
        data.name.includes(".mcf.gcode") &&
        self.files.isOperational() &&
        !(self.files.isPrinting() || self.files.isPaused() || self.files.isLoading())
      ) {
        return true && !self.files.listHelper.isSelected(data);
      } else {
        return self.files.enablePrint(data) && !self.files.listHelper.isSelected(data);
      }
    };
  };

  /* OCTOPRINT-SPECIFIC EVENT HANDLERS */

  self.onBeforeBinding = () => {
    self.uiUpdate();
    self.modifyPrinterStateVM();
    self.modifyFilesVM();

    self.currentSplice(0);
    self.nSplices(0);
    self.filaLength(0);
    self.connected(false);
  };

  self.onAfterBinding = () => {
    self.uiUpdate();
  };

  self.onEventFileSelected = payload => {
    if (payload.name.includes(".mcf.gcode") && !self.connected()) {
      self.showAlert("turnOnP2");
    }
  };

  self.onEventPrintStarted = payload => {
    if (payload.name.includes(".mcf.gcode") && self.connected()) {
      UI.loadingOverlay(true, "heartbeat");
    }
  };

  self.onEventPrintCancelling = payload => {
    self.removeNotification();
  };

  self.onEventPrintCancelled = payload => {
    self.removeNotification();
  };

  self.onDataUpdaterPluginMessage = (pluginIdent, message) => {
    if (pluginIdent === "palette2") {
      if (message.command === "error") {
        self.showAlert("error", message.data);
      } else if (message.command === "printHeartbeatCheck") {
        if (message.data === "P2NotConnected") {
          const base_url = window.location.origin;
          window.location.href = `${base_url}/#tab_plugin_palette2`;
        }
        self.showAlert("heartbeat", message.data);
      } else if (message.command === "pings") {
        self.pings(message.data.reverse());
      } else if (message.command === "pongs") {
        self.pongs(message.data.reverse());
      } else if (message.command === "selectedPort") {
        selectedPort = message.data;
        if (selectedPort) {
          self.selectedPort(selectedPort);
        }
      } else if (message.command === "ports") {
        allPorts = message.data;
        if (allPorts.length === 0) {
          self.showAlert("noSerialPorts");
          $(".serial-ports-list").hide(125);
        } else {
          self.ports(allPorts);
          $(".serial-ports-list").toggle(125);
        }
      } else if (message.command === "currentSplice") {
        self.currentSplice(message.data);
      } else if (message.command === "displaySetupAlerts") {
        self.displaySetupAlerts = message.data;
      } else if (message.command === "totalSplices") {
        self.nSplices(message.data);
      } else if (message.command === "p2Connection") {
        self.connected(message.data);
        if (self.tryingToConnect && !self.connected()) {
          self.showAlert("cannotConnect");
        }
      } else if (message.command === "filamentLength") {
        self.filaLength(message.data);
      } else if (message.command === "currentStatus") {
        if (message.data && message.data !== self.currentStatus()) {
          self.currentStatus(message.data);
          if (self.currentStatus() === "Loading filament into extruder") {
            UI.addNotificationList();
            self.checkIfCountdownExists();
          } else if (self.currentStatus() === "Print started: preparing splices") {
            self.removeNotification();
          }
        } else if (!message.data) {
          self.currentStatus("No ongoing Palette 2 print");
        }
      } else if (message.command === "amountLeftToExtrude") {
        if (!self.actualPrintStarted) {
          self.amountLeftToExtrude(message.data);
          if (!$("#load-filament-notification").is(":visible")) {
            self.updateFilamentCountdown(true);
          } else if ($("#load-filament-notification").is(":visible")) {
            self.updateFilamentCountdown(false);
          }
        }
      } else if (message.command === "printPaused") {
        self.printPaused = message.data;
      } else if (message.command === "firstTime") {
        self.firstTime = message.data;
      } else if (message.command === "autoConnect") {
        self.autoconnect = message.data;
      } else if (message.command === "palette2SetupStarted") {
        self.palette2SetupStarted(message.data);
      } else if (message.command === "actualPrintStarted") {
        self.actualPrintStarted = message.data;
      } else if (message.command === "alert") {
        self.showAlert(message.data);
      } else if (message.command === "advanced") {
        self.handleAdvancedOptions(message.subCommand, message.data);
      }
    }
  };
}

/* ======================
  RUN
  ======================= */

$(function () {
  OCTOPRINT_VIEWMODELS.push({
    // This is the constructor to call for instantiating the plugin
    construct: OmegaViewModel,
    dependencies: ["settingsViewModel", "controlViewModel", "printerStateViewModel", "filesViewModel"],
    elements: ["#tab_plugin_palette2"]
  }); // This is a list of dependencies to inject into the plugin. The order will correspond to the "parameters" arguments above // Finally, this is the list of selectors for all elements we want this view model to be bound to.
});
