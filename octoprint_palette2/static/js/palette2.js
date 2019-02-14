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

omegaApp.extrusionAlert = firstTime => {
  if (firstTime) {
    return swal({
      title: "Follow instructions on Palette 2 ",
      text: `Use the "Extrude" button in the Controls tab to drive filament into the extruder until you see the desired color. To accurately load, we recommend setting the extrusion amount to a low number.`,
      type: "info"
    });
  } else {
    return swal({
      title: "Follow instructions on Palette 2 ",
      text: `Use the "Extrude" button in the Controls tab to drive filament into the extruder. To accurately load, we recommend setting the extrusion amount to a low number.`,
      type: "info"
    });
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

/* 3.1 CLOSE ALERT */
omegaApp.closeAlert = () => {
  if (Swal.isVisible()) {
    Swal.close();
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
  self.amountLeftToExtrude = "";
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

  self.latestPing = ko.observable(0);
  self.latestPingPercent = ko.observable();
  self.latestPong = ko.observable(0);
  self.latestPongPercent = ko.observable();
  self.pings = ko.observableArray([]);
  self.pongs = ko.observableArray([]);

  // SKELLATORE
  self.ShowPingPongOnPrinter = ko.observable(true);
  self.FeedrateControl = ko.observable(true);
  self.FeedrateSlowed = ko.observable(false);
  self.FeedrateNormalPct = ko.observable(100);
  self.FeedrateSlowPct = ko.observable(80);
  self.Advanced_Status = ko.observable("Awaiting Update...");
  self.Advanced_Switches = ko.observable("Awaiting Update...");
  // /SKELLATORE

  /* COMMUNICATION TO BACK-END FUNCTIONS */

  self.togglePingHistory = () => {
    if (self.pings().length) {
      $(".ping-history").slideToggle();
    }
  };

  self.togglePongHistory = () => {
    if (self.pongs().length) {
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

  // SKELLATORE

  self.FeedrateControl.subscribe(function() {
    self.ajax_payload({ command: "changeFeedrateControl", condition: self.FeedrateControl() });
  });
  self.ShowPingPongOnPrinter.subscribe(function() {
    self.ajax_payload({ command: "changeShowPingPongOnPrinter", condition: self.ShowPingPongOnPrinter() });
  });
  self.FeedrateNormalPct.subscribe(function() {
    self.ajax_payload({ command: "changeFeedrateNormalPct", value: self.FeedrateNormalPct() });
  });
  self.FeedrateSlowPct.subscribe(function() {
    self.ajax_payload({ command: "changeFeedrateSlowPct", value: self.FeedrateSlowPct() });
  });

  self.ajax_payload = payload => {
    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8"
    });
  };

  self.update_from_plugin_message = message => {
    if (!message.command) {
      if (message.includes("ADVANCED:")) {
        value_ary = message.split("=");
        switch (value_ary[0]) {
          case "ADVANCED:DisplayAdvancedOptions":
            if (value_ary[1].includes("True")) {
              $(".advanced_options").show();
            } else {
              $(".advanced_options").hide();
            }
            break;
          case "ADVANCED:FEEDRATECONTROL":
            if (value_ary[1].includes("True")) {
              self.FeedrateControl(true);
            } else {
              self.FeedrateControl(false);
            }
            break;
          case "ADVANCED:FEEDRATESLOWED=":
            if (value_ary[1].includes("True")) {
              self.FeedrateSlowed(true);
            } else {
              self.FeedrateSlowed(false);
            }
            break;
          case "ADVANCED:SHOWPINGPONGONPRINTER":
            if (value_ary[1].includes("True")) {
              self.ShowPingPongOnPrinter(true);
            } else {
              self.ShowPingPongOnPrinter(false);
            }
            break;
          case "ADVANCED:FEEDRATENORMALPCT":
            self.FeedrateNormalPct(value_ary[1]);
            break;
          case "ADVANCED:FEEDRATESLOWPCT":
            self.FeedrateSlowPct(value_ary[1]);
            break;
          case "ADVANCED:UIMESSAGE":
            self.Advanced_Status(value_ary[1]);
            break;
          case "ADVANCED:UISWITCHES":
            self.update_switches(value_ary[1]);
            break;
          default:
          //Do Nothing
        }
      }
    }
  };

  self.update_switches = values => {
    switch_values = values.split(",");
    switch_string =
      "<b>Switch Status:</b><br/><b>Splice Core: </b>" +
      switch_values[0].toString() +
      "<br/><b>Buffer: </b>" +
      switch_values[1] +
      "<br/><b>Filament 1: </b>" +
      switch_values[2] +
      "<br/><b>Filament 2: </b>" +
      switch_values[3] +
      "<br/><b>Filament 3: </b>" +
      switch_values[4] +
      "<br/><b>Filament 4: </b>" +
      switch_values[5] +
      "<br/><b>Cutting Wheel: </b>" +
      switch_values[6];
    $(".switch_status").html(switch_string);
    self.Advanced_Switches = switch_string;
  };
  // /SKELLATORE

  self.fromResponse = () => {};

  /* UI FUNCTIONS */

  self.displayFilamentCountdown = () => {
    let notification = $(`<li id="jog-filament-notification" class="popup-notification">
              <i class="material-icons remove-popup">clear</i>
              <h6>Remaining Length To Extrude:</h6>
              <p class="jog-filament-value">${self.amountLeftToExtrude}mm</p>
              </li>`).hide();
    self.jogId = "#jog-filament-notification";
    $(".side-notifications-list").append(notification);
  };

  self.updateFilamentCountdown = firstValue => {
    if (firstValue) {
      $(self.jogId)
        .fadeIn(200)
        .find(".jog-filament-value")
        .text(`${self.amountLeftToExtrude}mm`);
    } else {
      $(self.jogId)
        .find(".jog-filament-value")
        .text(`${self.amountLeftToExtrude}mm`);
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
        if (self.firstTime) {
          omegaApp.extrusionAlert(true);
        } else {
          omegaApp.extrusionAlert(false);
        }
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
      self.removeNotification();
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
    }
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

  self.sendErrorReport = send => {
    var payload = {
      command: "sendErrorReport",
      send: send
    };
    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8"
    });
  };

  self.readyToStartAlert = () => {
    return swal({
      title: "Filament in place and ready to go",
      text: `Please go back to your Palette 2 and press "Finished". On the next screen, press "Start Print". Your print will begin automatically.`,
      type: "info",
      input: "checkbox",
      inputPlaceholder: "Don't show me these setup alerts anymore",
      confirmButtonText: "START PRINT"
    });
  };

  self.onDataUpdaterPluginMessage = (pluginIdent, message) => {
    if (pluginIdent === "palette2") {
      // SKELLATORE
      self.update_from_plugin_message(message);
      // /SKELLATORE
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
          self.latestPing(self.pings()[0].number);
          self.latestPingPercent(self.pings()[0].percent);
        } else {
          self.latestPing(0);
          self.latestPingPercent("");
          self.pings([]);
          $(".ping-history").hide();
        }
      } else if (message.command === "pongs") {
        if (message.data.length) {
          self.pongs(message.data.reverse());
          self.latestPong(self.pongs()[0].number);
          self.latestPongPercent(self.pongs()[0].percent);
        } else {
          self.latestPong(0);
          self.latestPongPercent("");
          self.pongs([]);
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
            self.displayFilamentCountdown();
          }
        } else if (!message.data) {
          self.currentStatus("No ongoing Palette 2 print");
        }
      } else if (message.command === "amountLeftToExtrude") {
        self.amountLeftToExtrude = message.data;
        if (!self.actualPrintStarted && self.amountLeftToExtrude) {
          if (!$("#jog-filament-notification").is(":visible")) {
            self.updateFilamentCountdown(true);
            // self.control.extrusionAmount(self.amountLeftToExtrude);
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
