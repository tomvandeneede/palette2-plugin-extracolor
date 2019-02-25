if (!document.getElementById("sweetalert2-styling")) {
  let link = document.createElement("link");
  link.id = "sweetalert2-styling";
  link.href = "https://cdnjs.cloudflare.com/ajax/libs/limonte-sweetalert2/7.29.0/sweetalert2.min.css";
  link.rel = "stylesheet";
  document.head.appendChild(link);
}
if (!document.getElementById("sweetalert2-script")) {
  let script = document.createElement("script");
  script.id = "sweetalert2-script";
  script.src = "https://cdnjs.cloudflare.com/ajax/libs/limonte-sweetalert2/7.29.0/sweetalert2.min.js";
  document.head.appendChild(script);
}

/* ======================
HELPER FUNCTIONS
======================= */
const omegaApp = {};

/* 1. LOADER */
omegaApp.loadingOverlay = (condition, status) => {
  if (condition) {
    if (status === "connect") {
      message = `<h1 class="loading-overlay-message">Trying to connect to Palette 2...</h1>`;
    } else if (status === "disconnect") {
      message = `<h1 class="loading-overlay-message">Disconnecting Palette 2...</h1>`;
    } else if (status === "heartbeat") {
      message = `<h1 class="loading-overlay-message">Verifying Palette 2 connection before starting print...</h1>`;
    }
    $("body").append(`<div class="loading-overlay-container">
    <div class="loader"></div>
    ${message}
    </div>`);
  } else {
    $("body")
      .find(".loading-overlay-container")
      .remove();
  }
};

/* 2. HIGHLIGHT TO HELP USER USE TEMP CONTROLS */
omegaApp.temperatureHighlight = () => {
  $("body")
    .find(`#temperature-table .input-mini.input-nospin:first`)
    .addClass("highlight-glow")
    .on("focus", event => {
      $(event.target).removeClass("highlight-glow");
    });
};

/* 2.1 HIGHLIGHT TO HELP USER USE EXTRUSION CONTROLS */
omegaApp.extrusionHighlight = () => {
  $("body")
    .find("#control-jog-extrusion .input-mini.text-right")
    .addClass("highlight-glow")
    .on("focus", event => {
      $(event.target).removeClass("highlight-glow");
    });
  $("body")
    .find("#control-jog-extrusion > div :nth-child(3)")
    .addClass("highlight-glow-border")
    .on("focus", event => {
      $(event.target).removeClass("highlight-glow-border");
    });
};

/* 3. ALERT TEXTS */
omegaApp.cannotConnectAlert = () => {
  return swal({
    title: "Could not connect to Palette 2",
    text: `Please make sure Palette 2 is turned on and that the selected port corresponds to it. Please wait 5 seconds before trying again.`,
    type: "error"
  });
};

omegaApp.palette2PrintStartAlert = () => {
  return swal({
    title: "You are about to print with Palette 2",
    text:
      "Your print will temporarily be paused. This is normal - please follow the instructions on Palette 2's screen. The print will resume automatically once everything is ready.",
    type: "info"
  });
};

omegaApp.preheatAlert = () => {
  return swal({
    title: "Pre-heat your printer",
    text:
      "Palette 2 is now making filament. In the meantime, please pre-heat your printer using the controls in the Temperature Tab.",
    type: "info"
  });
};

omegaApp.extrusionAlert = (firstTime, autoLoad) => {
  let text = `Use the "Extrude" button in the Controls tab to drive filament into the extruder. To accurately load, we recommend setting the extrusion amount to a low number.`;
  if (firstTime) {
    text = `Use the "Extrude" button in the Controls tab to drive filament into the extruder until you see the desired color. To accurately load, we recommend setting the extrusion amount to a low number.`;
    return swal({
      title: "Follow instructions on Palette 2 ",
      text: text,
      type: "info"
    });
  } else {
    if (autoLoad) {
      text = `Use the "Extrude" button in the Controls tab or the "Auto Load" button in the Palette 2 tab to drive filament into the extruder. If using "Auto Load", please place the filament at a proper angle to be inserted into the extruder before loading.`;
      return swal({
        title: "Follow instructions on Palette 2 ",
        text: text,
        type: "info",
        showConfirmButton: true,
        showCancelButton: true,
        confirmButtonText: "Go to Auto Load",
        cancelButtonText: "OK"
      });
    } else {
      return swal({
        title: "Follow instructions on Palette 2 ",
        text: text,
        type: "info"
      });
    }
  }
};

omegaApp.printCancellingAlert = () => {
  return swal({
    title: "Palette 2: Print cancelling",
    text: `Please remove filament from the extruder and from Palette 2.`,
    type: "info"
  });
};

omegaApp.printCancelledAlert = () => {
  return swal({
    title: "Palette 2: Print cancelled",
    text: `Palette 2 print successfully cancelled. Please make sure you have pressed "Finished" on Palette 2's screen before starting a new print.`,
    type: "info"
  });
};

omegaApp.palette2NotConnectedAlert = () => {
  return swal({
    title: "Palette 2 not connected",
    text: "You have selected an .mcf file. Please enable the connection to Palette 2 before printing.",
    type: "info"
  });
};

omegaApp.noSerialPortsAlert = () => {
  return swal({
    title: "No serial ports detected",
    text: `Please make sure all cables are inserted properly into your Hub.`,
    type: "error"
  });
};

omegaApp.errorAlert = errorNumber => {
  return swal({
    title: `Error ${errorNumber} detected`,
    text: `An error occured on Palette 2. Your print has been paused. Would you like to send a crash report to Mosaic for investigation?`,
    confirmButtonText: "Yes",
    showCancelButton: true,
    cancelButtonText: "No",
    reverseButtons: true,
    type: "error"
  });
};

omegaApp.errorTextAlert = () => {
  return swal({
    title: "Please provide additional details (OPTIONAL)",
    text:
      "(E.g: what part of the print you were at, what is displayed on your Palette 2 screen, is this the first time this has occured, etc)",
    customClass: "error-container",
    input: "textarea",
    inputClass: "error-textarea",
    width: "40rem",
    confirmButtonText: "Send"
  });
};

omegaApp.displayHeartbeatAlert = status => {
  if (status === "P2NotConnected") {
    omegaApp.loadingOverlay(false);
    return swal({
      title: "No response from Palette 2",
      text: `Please make sure Palette 2 is turned on and try reconnecting to it in the Palette 2 tab before starting another print.`,
      type: "error"
    });
  } else if (status === "P2Responded") {
    omegaApp.loadingOverlay(false);
    omegaApp.palette2PrintStartAlert();
  }
};

omegaApp.readyToStartAlert = setupAlertSetting => {
  if (setupAlertSetting) {
    return swal({
      title: "Filament in place and ready to go",
      text: `Please press "Start Print" below or directly on your Palette 2 screen to begin your print.`,
      type: "info",
      inputClass: "setup-checkbox",
      input: "checkbox",
      inputPlaceholder: "Don't show me these setup alerts anymore",
      confirmButtonText: "Start Print"
    });
  } else {
    return swal({
      title: "Filament in place and ready to go",
      text: `Please press "Start Print" below or directly on your Palette 2 screen to begin your print.`,
      type: "info",
      confirmButtonText: "Start Print"
    });
  }
};

omegaApp.autoLoadFailAlert = () => {
  return swal({
    title: "Auto load not completed",
    text: `Filament stopped moving. Please make sure the filament is properly placed in the extruder and then continue extruding, either with "Auto Load" again or with manual controls.`,
    type: "info"
  });
};

/* 3.1 CLOSE ALERT */
omegaApp.closeAlert = () => {
  if (Swal.isVisible()) {
    Swal.close();
  }
};

/* 4. Append Notification List to DOM */
omegaApp.addNotificationList = () => {
  if ($("body").find(".side-notifications-list").length === 0) {
    $("body")
      .css("position", "relative")
      .append(`<ul class="side-notifications-list"></ul>`);
  }
};

/* ======================
OMEGA VIEWMODEL FOR OCTOPRINT
======================= */

function OmegaViewModel(parameters) {
  var self = this;

  /* OTHER VIEWMODELS */
  self.settings = parameters[0];
  self.control = parameters[1];
  self.printerState = parameters[2];
  self.files = parameters[3];

  /* GLOBAL VARIABLES */
  self.omegaCommand = ko.observable();
  self.wifiSSID = ko.observable();
  self.wifiPASS = ko.observable();
  self.omegaPort = ko.observable();
  self.currentSplice = ko.observable();
  self.nSplices = ko.observable();
  self.totalSplicesDisplay = ko.computed(function() {
    return " / " + self.nSplices() + " Splices";
  });
  self.connected = ko.observable(false);
  self.connectPaletteText = ko.computed(function() {
    return self.connected() ? "Connected" : "Connect to Palette 2";
  });
  self.disconnectPaletteText = ko.computed(function() {
    return self.connected() ? "Disconnect" : "Disconnected";
  });
  self.demoWithPrinter = ko.observable(false);

  self.currentStatus = ko.observable();
  self.amountLeftToExtrude = ko.observable();
  self.jogId = "";
  self.displaySetupAlerts = true;
  self.tryingToConnect = false;
  self.firstTime = false;
  self.actualPrintStarted = false;
  self.autoconnect = false;
  self.connectionStateMsg = ko.computed(function() {
    if (self.connected()) {
      return "Connected";
    } else {
      return self.autoconnect ? "Not Connected - Trying To Connect..." : "Not Connected";
    }
  });
  self.filaLength = ko.observable();
  self.filaLengthDisplay = ko.computed(function() {
    return (Number(self.filaLength()) / 1000.0).toFixed(2) + "m";
  });
  self.palette2SetupStarted = ko.observable();

  // self.files = ko.observableArray([]);

  self.selectedDemoFile = ko.observable();

  self.ports = ko.observableArray([]);
  self.selectedPort = ko.observable();
  self.pings = ko.observableArray([]);
  self.pingsDisplay = ko.computed(function() {
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
  self.latestPing = ko.computed(function() {
    return self.pingsDisplay()[0] ? self.pingsDisplay()[0].number : 0;
  });
  self.latestPingPercent = ko.computed(function() {
    return self.pingsDisplay()[0] ? self.pingsDisplay()[0].percent : "%";
  });
  self.pongs = ko.observableArray([]);
  self.pongsDisplay = ko.computed(function() {
    if (self.pongs()) {
      return self.pongs().map(pong => {
        pong.percent = pong.percent + "%";
        return pong;
      });
    } else {
      return [];
    }
  });
  self.latestPong = ko.computed(function() {
    return self.pongsDisplay()[0] ? self.pongsDisplay()[0].number : 0;
  });
  self.latestPongPercent = ko.computed(function() {
    return self.pongsDisplay()[0] ? self.pongsDisplay()[0].percent : "%";
  });
  self.showPingOnPrinter = ko.observable(true);
  self.feedRateControl = ko.observable(true);
  self.feedRateSlowed = ko.observable(false);
  self.feedRateSlowedText = ko.computed(function() {
    return self.feedRateSlowed() && self.printerState.isPrinting() ? "Yes" : "No";
  });
  self.feedRateNormalPct = ko.observable(100);
  self.feedRateSlowPct = ko.observable(50);
  self.feedRateStatus = ko.observable("Awaiting Update...");
  self.advancedOptions = ko.observable();

  self.autoLoad = ko.observable(false);
  self.isAutoLoading = ko.observable(false);
  self.autoLoadButtonText = ko.computed(function() {
    return self.isAutoLoading() ? "Auto Loading..." : "Auto Load";
  });
  self.amountLeftToExtrudeText = ko.computed(function() {
    if (self.amountLeftToExtrude() > 0 || self.amountLeftToExtrude() < 0) {
      return `${self.amountLeftToExtrude()}mm`;
    } else if (self.amountLeftToExtrude() === 0) {
      return "Loading offset completed";
    } else {
      return "No loading offset detected";
    }
  });

  /* COMMUNICATION TO BACK-END FUNCTIONS */

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

  // window.onload = () => {
  //   self.refreshDemoList();
  // };

  // self.filterDemoFiles = ko.computed(function() {
  //   var filteredFiles = self.files().filter(f => {
  //     return f.match(/.msf$/i);
  //   });
  //   return filteredFiles;
  // });

  self.displayPorts = () => {
    let condition = "";
    // determine if user is opening or closing list of ports
    if ($(".serial-ports-list").is(":visible")) {
      condition = "closing";
    } else {
      condition = "opening";
    }

    var payload = {
      command: "displayPorts",
      condition: condition
    };
    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8"
    }).then(() => {
      self.settings.requestData();
    });
  };

  // self.refreshDemoList = () => {
  //   var payload = {};
  //   $.ajax({
  //     headers: {
  //       "X-Api-Key": UI_API_KEY
  //     },
  //     url: API_BASEURL + "files?recursive=true",
  //     type: "GET",
  //     dataType: "json",
  //     data: JSON.stringify(payload),
  //     contentType: "application/json; charset=UTF-8",
  //     success: function(d) {
  //       self.files(
  //         d.files.map(function(file, index) {
  //           return file.name;
  //         })
  //       );
  //     }
  //   });
  // };

  self.startSpliceDemo = () => {
    if (self.selectedDemoFile()) {
      var payload = {
        command: "startSpliceDemo",
        file: self.selectedDemoFile(),
        withPrinter: self.demoWithPrinter()
      };

      $.ajax({
        url: API_BASEURL + "plugin/palette2",
        type: "POST",
        dataType: "json",
        data: JSON.stringify(payload),
        contentType: "application/json; charset=UTF-8"
      });
    }
  };

  self.connectOmega = () => {
    self.tryingToConnect = true;
    omegaApp.loadingOverlay(true, "connect");

    if (self.selectedPort()) {
      var payload = {
        command: "connectOmega",
        port: self.selectedPort()
      };
    } else {
      var payload = { command: "connectOmega", port: "" };
    }

    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8"
    });
  };

  self.disconnectPalette2 = () => {
    omegaApp.loadingOverlay(true, "disconnect");
    self.connected(false);
    self.removeNotification();
    var payload = {
      command: "disconnectPalette2"
    };
    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8"
    });
  };

  self.changeAlertSettings = condition => {
    self.displaySetupAlerts = !condition;
    var payload = { command: "changeAlertSettings", condition: self.displaySetupAlerts };

    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8"
    }).then(() => {
      self.settings.requestData();
    });
  };

  self.sendOmegaCmd = (command, payload) => {
    var payload = {
      command: "sendOmegaCmd",
      cmd: self.omegaCommand()
    };
    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8",
      success: self.fromResponse
    });
  };

  self.uiUpdate = () => {
    console.log("Requesting BE to update UI");
    var payload = { command: "uiUpdate" };

    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8"
    });
  };

  self.connectWifi = () => {
    var payload = {
      command: "connectWifi",
      wifiSSID: self.wifiSSID(),
      wifiPASS: self.wifiPASS()
    };
    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8",
      success: self.fromResponse
    });
  };

  self.sendCutCmd = () => {
    var payload = {
      command: "sendCutCmd"
    };
    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8",
      success: self.fromResponse
    });
  };

  self.sendClearOutCmd = () => {
    var payload = {
      command: "clearPalette2"
    };

    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8",
      success: self.fromResponse
    });
  };

  self.sendErrorReport = (errorNumber, description) => {
    var payload = {
      command: "sendErrorReport",
      errorNumber: errorNumber,
      description: description
    };
    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8"
    });
  };

  self.startPrintFromHub = () => {
    var payload = {
      command: "startPrint"
    };
    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8"
    });
  };

  self.feedRateControl.subscribe(function() {
    self.ajax_payload({ command: "changeFeedRateControl", condition: self.feedRateControl() });
  });
  self.showPingOnPrinter.subscribe(function() {
    self.ajax_payload({ command: "changeShowPingOnPrinter", condition: self.showPingOnPrinter() });
  });
  self.feedRateNormalPct.subscribe(function() {
    self.ajax_payload({ command: "changeFeedRateNormalPct", value: self.feedRateNormalPct() });
  });
  self.feedRateSlowPct.subscribe(function() {
    self.ajax_payload({ command: "changeFeedRateSlowPct", value: self.feedRateSlowPct() });
  });
  self.autoLoad.subscribe(function() {
    self.ajax_payload({ command: "changeAutoLoad", condition: self.autoLoad() });
  });

  self.ajax_payload = payload => {
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
      case "autoLoad":
        self.autoLoad(data);
        break;
      case "isAutoLoading":
        self.isAutoLoading(data);
        break;
      default:
      //Do Nothing
    }
  };

  self.fromResponse = () => {};

  /* UI FUNCTIONS */

  self.checkIfCountdownExists = () => {
    if ($("body").find("#jog-filament-notification").length === 0) {
      self.displayFilamentCountdown();
    }
  };

  self.displayFilamentCountdown = () => {
    let notification = $(`<li id="jog-filament-notification" class="popup-notification">
              <i class="material-icons remove-popup">clear</i>
              <h6>Remaining Length To Extrude:</h6>
              <p class="jog-filament-value">${self.amountLeftToExtrude()}mm</p>
              </li>`).hide();
    self.jogId = "#jog-filament-notification";
    $(".side-notifications-list").append(notification);
  };

  self.updateFilamentCountdown = firstValue => {
    if (self.amountLeftToExtrude() < 0) {
      omegaApp.closeAlert();
      $(self.jogId)
        .find(".jog-filament-value")
        .addClass("negative-number");
    } else {
      $(self.jogId)
        .find(".jog-filament-value")
        .removeClass("negative-number");
    }
    if (firstValue) {
      $(self.jogId)
        .fadeIn(200)
        .find(".jog-filament-value")
        .text(`${self.amountLeftToExtrude()}mm`);
    } else {
      $(self.jogId)
        .find(".jog-filament-value")
        .text(`${self.amountLeftToExtrude()}mm`);
    }
  };

  self.removeNotification = () => {
    $(self.jogId).fadeOut(500, function() {
      this.remove();
    });
  };

  self.showAlert = (command, condition) => {
    if (command === "temperature") {
      if (self.displaySetupAlerts) {
        let base_url = window.location.origin;
        window.location.href = `${base_url}/#temp`;
        omegaApp.temperatureHighlight();
        omegaApp.preheatAlert();
      }
    } else if (command === "extruder") {
      if (self.displaySetupAlerts) {
        let base_url = window.location.origin;
        window.location.href = `${base_url}/#control`;
        omegaApp.extrusionHighlight();
        omegaApp.extrusionAlert(self.firstTime, self.autoLoad()).then(result => {
          if (result.value && !self.firstTime && self.autoLoad()) {
            let base_url = window.location.origin;
            window.location.href = `${base_url}/#tab_plugin_palette2`;
          }
        });
      }
    } else if (command === "cancelling") {
      self.removeNotification();
      omegaApp.printCancellingAlert();
    } else if (command === "printStarted") {
      // if user presses start from P2
      omegaApp.closeAlert();
    } else if (command === "cancelled") {
      self.removeNotification();
      omegaApp.printCancelledAlert();
    } else if (command === "startPrint") {
      if (self.displaySetupAlerts) {
        $("body").on("click", ".setup-checkbox input", event => {
          self.changeAlertSettings(event.target.checked);
        });
      }
      omegaApp.readyToStartAlert(self.displaySetupAlerts).then(result => {
        if (result.hasOwnProperty("value")) {
          self.startPrintFromHub();
        }
      });
    } else if (command === "cannotConnect") {
      omegaApp.cannotConnectAlert();
    } else if (command === "heartbeat") {
      omegaApp.displayHeartbeatAlert(condition);
    } else if (command === "error") {
      omegaApp.errorAlert(condition).then(result => {
        // if user clicks yes
        if (result.value) {
          omegaApp.errorTextAlert().then(result => {
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
      omegaApp.noSerialPortsAlert();
    } else if (command === "turnOnP2") {
      omegaApp.palette2NotConnectedAlert();
    } else if (command === "autoLoadIncomplete") {
      omegaApp.autoLoadFailAlert();
    }
  };

  self.toggleAdvancedOptionInfo = (data, event) => {
    let targetClass = `#${event.target.nextElementSibling.id}`;
    if ($(`.advanced-info-text:not(${targetClass})`).is(":visible")) {
      $(".advanced-info-text").hide(50);
    }
    $(targetClass).toggle(50);
  };

  /* VIEWMODELS MODIFICATIONS FOR P2 PLUGIN */

  self.modifyPrinterStateVM = () => {
    self.printerState.enablePrint = ko.pureComputed(function() {
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

    self.printerState.enablePause = ko.pureComputed(function() {
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
    self.files.enablePrint = function(data) {
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

    self.files.enableSelect = function(data, printAfterSelect) {
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
    // self.refreshDemoList();
    self.uiUpdate();
    omegaApp.addNotificationList();
  };

  self.downloadPingHistory = (data, event) => {
    event.stopPropagation();
    self.ajax_payload({ command: "downloadPingHistory" }).then(result => {
      let filename = result.response.filename;
      let data = result.response.data;

      let blob = new Blob([data], { type: "text/plain" });
      if (window.navigator.msSaveOrOpenBlob) {
        window.navigator.msSaveBlob(blob, filename);
      } else {
        let elem = window.document.createElement("a");
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
    self.isAutoLoading(true);
    self.ajax_payload({ command: "startAutoLoad" });
  };

  self.onEventFileSelected = payload => {
    if (payload.name.includes(".mcf.gcode") && !self.connected()) {
      self.showAlert("turnOnP2");
    }
  };

  self.onEventPrintStarted = payload => {
    if (payload.name.includes(".mcf.gcode") && self.connected()) {
      omegaApp.loadingOverlay(true, "heartbeat");
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
          let base_url = window.location.origin;
          window.location.href = `${base_url}/#tab_plugin_palette2`;
        }
        self.showAlert("heartbeat", message.data);
      } else if (message.command === "pings") {
        if (message.data.length) {
          self.pings(message.data.reverse());
        } else {
          $(".ping-history").hide();
        }
      } else if (message.command === "pongs") {
        if (message.data.length) {
          self.pongs(message.data.reverse());
        } else {
          $(".pong-history").hide();
        }
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
        if (self.tryingToConnect) {
          omegaApp.loadingOverlay(false);
        }
        self.connected(message.data);
        if (self.connected()) {
          self.tryingToConnect = false;
        } else {
          omegaApp.loadingOverlay(false);
          if (self.tryingToConnect) {
            self.tryingToConnect = false;
            self.showAlert("cannotConnect");
          }
        }
      }
      // else if (message.includes("UI:Refresh Demo List")) {
      //   self.refreshDemoList();
      // }
      else if (message.command === "filamentLength") {
        self.filaLength(message.data);
      } else if (message.command === "currentStatus") {
        if (message.data && message.data !== self.currentStatus()) {
          self.currentStatus(message.data);
          if (self.currentStatus() === "Loading filament into extruder") {
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
          if (!$("#jog-filament-notification").is(":visible")) {
            self.updateFilamentCountdown(true);
          } else if ($("#jog-filament-notification").is(":visible")) {
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

$(function() {
  OCTOPRINT_VIEWMODELS.push({
    // This is the constructor to call for instantiating the plugin
    construct: OmegaViewModel,
    dependencies: ["settingsViewModel", "controlViewModel", "printerStateViewModel", "filesViewModel"],
    elements: ["#tab_plugin_palette2"]
  }); // This is a list of dependencies to inject into the plugin. The order will correspond to the "parameters" arguments above // Finally, this is the list of selectors for all elements we want this view model to be bound to.
});
