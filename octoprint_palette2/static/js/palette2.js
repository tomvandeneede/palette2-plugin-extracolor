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
omegaApp.loadingOverlay = condition => {
  if (condition) {
    $("body").append(`<div class="loading-overlay-container"><div class="loader"></div></div>`);
  } else {
    $("body")
      .find(".loading-overlay-container")
      .remove();
  }
};

/* 2. DISABLE PRINT ICON SMALL */
omegaApp.disableSmallPrintIcon = condition => {
  if (condition) {
    $(".palette-tag")
      .siblings(".action-buttons")
      .find(".btn:last-child")
      .css("pointer-events", "none")
      .attr("disabled", true);
  } else {
    $(".palette-tag")
      .siblings(".action-buttons")
      .find(".btn:last-child")
      .css("pointer-events", "auto")
      .attr("disabled", false);
  }
};

/* 2.1 DISABLE PRINT ICON LARGE */
omegaApp.disableLargePrintIcon = condition => {
  $("#job_print").attr("disabled", condition);
};

/* 2.2 DISABLE PAUSE ICON LARGE */
omegaApp.disablePause = condition => {
  $("body")
    .find("#job_pause")
    .attr("disabled", condition);
};

/* 3. HIGHLIGHT TO HELP USER USE TEMP CONTROLS */
omegaApp.temperatureHighlight = () => {
  $("body")
    .find(`#temperature-table .input-mini.input-nospin:first`)
    .addClass("highlight-glow")
    .on("focus", event => {
      $(event.target).removeClass("highlight-glow");
    });
};

/* 3.1 HIGHLIGHT TO HELP USER USE EXTRUSION CONTROLS */
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

/* 4. ALERT TEXTS */
omegaApp.cannotConnectAlert = () => {
  return swal({
    title: "Could not connect to Palette 2",
    text: `Please make sure Palette 2 is turned on. Please wait 5 seconds before trying again.`,
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
      text: `Use the "Extrude" button in the Controls tab to drive filament into the extruder until you see the desired color. To accurately load, we recommend setting the extrusion amount to a low number (1mm - 5mm).`,
      type: "info"
    });
  } else {
    return swal({
      title: "Follow instructions on Palette 2 ",
      text: `Use the "Extrude" button in the Controls tab to drive filament into the extruder. To accurately load, we recommend setting the extrusion amount to a low number (1mm - 5mm).`,
      type: "info"
    });
  }
};

omegaApp.readyToStartAlert = () => {
  return swal({
    title: "Filament in place and ready to go",
    text: `Please go back to your Palette 2 and press "Finished". On the next screen, press "Start Print". Your print will begin automatically.`,
    type: "info",
    input: "checkbox",
    inputPlaceholder: "Don't show me these setup alerts anymore"
  });
};

omegaApp.printCancelAlert = () => {
  return swal({
    title: "Print cancelling ",
    text: `Please remove filament from the extruder.`,
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

/* ======================
OMEGA VIEWMODEL FOR OCTOPRINT
======================= */

function OmegaViewModel(parameters) {
  var self = this;

  /* GLOBAL VARIABLES */
  self.omegaCommand = ko.observable();
  self.wifiSSID = ko.observable();
  self.wifiPASS = ko.observable();
  self.omegaPort = ko.observable();
  self.currentSplice = ko.observable();
  self.nSplices = ko.observable();
  self.connectionStateMsg = ko.observable();
  self.connected = ko.observable(false);
  self.demoWithPrinter = ko.observable(false);

  self.currentStatus = "";
  self.amountLeftToExtrude = "";
  self.jogId = "";
  self.displayAlerts = true;
  self.tryingToConnect = false;
  self.currentFile = "";
  self.printerConnected = false;
  self.firstTime = false;
  self.actualPrintStarted = false;
  self.autoconnect = false;

  self.files = ko.observableArray([]);

  self.selectedDemoFile = ko.observable();

  /* COMMUNICATION TO BACK-END FUNCTIONS */

  window.onload = () => {
    self.refreshDemoList();
  };

  self.filterDemoFiles = ko.computed(function() {
    var filteredFiles = self.files().filter(f => {
      return f.match(/.msf$/i);
    });
    return filteredFiles;
  });

  self.refreshDemoList = () => {
    var payload = {};
    $.ajax({
      headers: {
        "X-Api-Key": UI_API_KEY
      },
      url: API_BASEURL + "files",
      type: "GET",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8",
      success: function(d) {
        self.files(
          d.files.map(function(file, index) {
            return file.name;
          })
        );
      }
    });
  };

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
    omegaApp.loadingOverlay(true);

    var payload = {
      command: "connectOmega",
      port: ""
    };

    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8"
    }).then(res => {
      self.applyPaletteDisabling();
    });
  };

  self.disconnectPalette2 = () => {
    omegaApp.loadingOverlay(true);
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
    }).then(res => {
      self.applyPaletteDisabling();
    });
  };

  self.changeAlertSettings = condition => {
    self.displayAlerts = !condition;
    $(".alert-input").prop("checked", self.displayAlerts);
    var payload = { command: "changeAlertSettings", condition: self.displayAlerts };

    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8"
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

  self.sendCancelCmd = () => {
    self.omegaCommand("O0");
    self.sendOmegaCmd();
    self.omegaCommand("");
  };

  self.sendPrintStart = () => {
    var payload = {
      command: "printStart"
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

  self.fromResponse = () => {};

  /* UI FUNCTIONS */

  self.findCurrentFilename = () => {
    self.currentFile = $("#state_wrapper")
      .find(`strong[title]`)
      .text();
  };

  self.resetValues = () => {
    self.amountLeftToExtrude = "";
    self.firstTime = false;
    self.actualPrintStarted = false;
  };

  self.applyPaletteDisabling = () => {
    if (self.printerConnected) {
      if (!self.connected()) {
        let count = 0;
        let applyDisabling = setInterval(function() {
          if (count > 20) {
            clearInterval(applyDisabling);
          }
          omegaApp.disableSmallPrintIcon(true);
          count++;
          if (self.currentFile.includes(".mcf.gcode")) {
            omegaApp.disableLargePrintIcon(true);
          } else if (self.currentFile && !self.currentFile.includes(".mcf.gcode")) {
            omegaApp.disableLargePrintIcon(false);
          }
        }, 100);
      } else if (!self.currentFile) {
        let count = 0;
        let applyDisabling3 = setInterval(function() {
          if (count > 20) {
            clearInterval(applyDisabling3);
          }
          omegaApp.disableLargePrintIcon(true);
          count++;
        }, 100);
      } else {
        let count = 0;
        let applyDisabling2 = setInterval(function() {
          if (count > 20) {
            clearInterval(applyDisabling2);
          }
          omegaApp.disableSmallPrintIcon(false);
          omegaApp.disableLargePrintIcon(false);
          count++;
        }, 100);
      }
    } else {
      let count = 0;
      let applyDisabling3 = setInterval(function() {
        if (count > 20) {
          clearInterval(applyDisabling3);
        }
        omegaApp.disableLargePrintIcon(true);
        count++;
      }, 100);
    }
  };

  self.handleGCODEFolders = payload => {
    self.removeFolderBinding();
    $("#files .gcode_files .entry.back.clickable").on("click", () => {
      self.applyPaletteDisabling();
    });
  };

  self.removeFolderBinding = payload => {
    $("#files .gcode_files")
      .find(".folder .title")
      .removeAttr("data-bind")
      .on("click", event => {
        self.applyPaletteDisabling();
      });
  };

  self.updateFilamentUsed = () => {
    let filament = (Number(self.filaLength) / 1000.0).toFixed(2) + "m";
    $(".filament-used span")
      .html("")
      .text(filament);
  };

  self.updateCurrentSplice = () => {
    $(".current-splice").text(self.currentSplice());
  };

  self.updateTotalSplices = () => {
    let totalSplices = " / " + self.nSplices() + " Splices";
    $(".total-splices").text(totalSplices);
  };

  self.updateConnection = () => {
    if (self.connected()) {
      $("#connection-state-msg")
        .removeClass("text-muted")
        .addClass("text-success")
        .css("color", "green");
      $(".connect-palette-button")
        .text("Connected")
        .addClass("disabled")
        .attr("disabled", true);
      self.connectionStateMsg("Connected");
      self.applyPaletteDisabling();
    } else {
      if (self.autoconnect) {
        $("#connection-state-msg")
          .removeClass("text-success")
          .addClass("text-muted")
          .css("color", "red");
        $(".connect-palette-button")
          .text("Connected")
          .addClass("disabled")
          .attr("disabled", true);
        self.connectionStateMsg("Not Connected - Trying To Connect...");
        self.applyPaletteDisabling();
      } else {
        $("#connection-state-msg")
          .removeClass("text-success")
          .addClass("text-muted")
          .css("color", "red");
        $(".connect-palette-button")
          .text("Connect to Palette 2")
          .removeClass("disabled")
          .attr("disabled", false);
        self.connectionStateMsg("Not Connected");
        self.applyPaletteDisabling();
      }
    }
  };

  self.updateCurrentStatus = () => {
    $(".current-status").text(self.currentStatus);
    if (self.currentStatus === "Palette work completed: all splices prepared") {
      $(".current-status").text(self.currentStatus);
      self.actualPrintStarted = false;
    } else if (self.currentStatus === "Loading filament through outgoing tube") {
      if (self.displayAlerts) {
        let base_url = window.location.origin;
        window.location.href = `${base_url}/#temp`;
        omegaApp.preheatAlert().then(res => {
          omegaApp.temperatureHighlight();
        });
      }
    } else if (self.currentStatus === "Loading filament into extruder") {
      if (self.displayAlerts) {
        let base_url = window.location.origin;
        window.location.href = `${base_url}/#control`;
        if (self.firstTime) {
          omegaApp.extrusionAlert(true).then(res => {
            omegaApp.extrusionHighlight();
          });
        } else {
          omegaApp.extrusionAlert(false).then(res => {
            omegaApp.extrusionHighlight();
          });
        }
        self.displayFilamentCountdown();
      }
    } else if (self.currentStatus === "Cancelling Print") {
      omegaApp.printCancelAlert();
    } else if (self.currentStatus === "Preparing splices") {
      self.actualPrintStarted = true;
    }
  };

  self.displayFilamentCountdown = () => {
    let notification = $(`<li id="jog-filament-notification" class="popup-notification">
              <i class="material-icons remove-popup">clear</i>
              <h6>Remaining length to extrude:</h6>
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

  /* OCTOPRINT-SPECIFIC EVENT HANDLERS */

  self.onBeforeBinding = () => {
    self.currentSplice("0");
    self.nSplices("0");
    self.connectionStateMsg("Not Connected");
    self.connected(false);
  };

  self.onAfterBinding = () => {
    self.settings = parameters[0];
    var payload = { command: "uiUpdate" };

    $.ajax({
      url: API_BASEURL + "plugin/palette2",
      type: "POST",
      dataType: "json",
      data: JSON.stringify(payload),
      contentType: "application/json; charset=UTF-8"
    });
  };

  self.onStartupComplete = () => {
    self.findCurrentFilename();
    self.removeFolderBinding();
    self.handleGCODEFolders();
  };

  self.onEventConnected = payload => {
    self.printerConnected = true;
    self.findCurrentFilename();
    self.applyPaletteDisabling();
  };

  self.onEventDisconnected = payload => {
    self.printerConnected = false;
    self.applyPaletteDisabling();
  };

  self.onEventFileRemoved = payload => {
    self.applyPaletteDisabling();
  };

  self.onEventUpdatedFiles = payload => {
    self.applyPaletteDisabling();
  };

  self.onEventFileSelected = payload => {
    self.currentFile = payload.name;

    if (self.currentFile.includes(".mcf.gcode")) {
      self.applyPaletteDisabling();
      if (!self.connected()) {
        omegaApp.palette2NotConnectedAlert();
      }
    }
  };

  self.onEventFileDeselected = payload => {
    self.applyPaletteDisabling();
  };

  self.onEventPrintStarted = payload => {
    if (payload.name.includes(".mcf.gcode")) {
      if (self.connected()) {
        if (self.displayAlerts) {
          omegaApp.palette2PrintStartAlert();
        }
      }
    }
  };

  self.onEventPrintPaused = payload => {
    if (self.connected() && payload.name.includes(".mcf.gcode") && !self.actualPrintStarted) {
      let count = 0;
      let applyDisablingResume = setInterval(function() {
        if (count > 50) {
          clearInterval(applyDisablingResume);
        }
        omegaApp.disablePause(true);
        count++;
      }, 100);
    }
  };

  self.onEventPrintResumed = payload => {
    if (self.connected() && payload.name.includes(".mcf.gcode") && self.actualPrintStarted) {
      let count = 0;
      let applyDisablingResume2 = setInterval(function() {
        if (count > 50) {
          clearInterval(applyDisablingResume2);
        }
        omegaApp.disablePause(false);
        omegaApp.disableLargePrintIcon(true);
        count++;
      }, 100);
    }
  };

  self.onEventPrintCancelled = payload => {
    if (payload.name.includes(".mcf.gcode")) {
      self.currentStatus = "Print cancelled";
      self.updateCurrentStatus();
      self.sendCancelCmd();
      self.resetValues();
    }
  };

  self.onEventPrintDone = payload => {
    if (payload.name.includes(".mcf.gcode")) {
      self.resetValues();
    }
  };

  self.onDataUpdaterPluginMessage = (pluginIdent, message) => {
    if (pluginIdent === "palette2") {
      if (message.includes("UI:currentSplice")) {
        var num = message.substring(17);
        self.currentSplice(num);
        self.updateCurrentSplice();
      } else if (message.includes("UI:DisplayAlerts")) {
        if (message.includes("True")) {
          self.displayAlerts = true;
        } else if (message.includes("False")) {
          self.displayAlerts = false;
        }
      } else if (message.includes("UI:FINISHED LOADING")) {
        $("#loading-span").addClass("hide");
      } else if (message.includes("UI:nSplices")) {
        var ns = message.substring(12);
        self.nSplices(ns);
        self.updateTotalSplices();
      } else if (message.includes("UI:Ponging")) {
        self.updatePongMsg(true);
      } else if (message.includes("UI:Finished Pong")) {
        self.updatePongMsg(false);
      } else if (message.includes("UI:Con=")) {
        omegaApp.loadingOverlay(false);
        if (message.includes("True")) {
          self.tryingToConnect = false;
          self.connected(true);
          self.updateConnection();
        } else {
          self.connected(false);
          self.updateConnection();
          if (self.tryingToConnect) {
            self.tryingToConnect = false;
            $("body").on("click", "#swal2-checkbox", event => {
              self.changeAlertSettings(event.target.checked);
            });
            omegaApp.cannotConnectAlert();
          }
        }
      } else if (message.includes("UI:Refresh Demo List")) {
        self.refreshDemoList();
      } else if (message.includes("UI:FilamentLength")) {
        self.filaLength = message.substring(18);
        self.updateFilamentUsed();
      } else if (message.includes("UI:currentStatus")) {
        if (message.substring(17) !== self.currentStatus) {
          self.currentStatus = message.substring(17);
          self.updateCurrentStatus();
        }
      } else if (message.includes("UI:AmountLeftToExtrude")) {
        self.amountLeftToExtrude = message.substring(23);
        if (self.amountLeftToExtrude === "0") {
          self.removeNotification();
          if (self.displayAlerts) {
            omegaApp.readyToStartAlert();
          }
        } else if (self.amountLeftToExtrude.length && !$("#jog-filament-notification").is(":visible")) {
          self.updateFilamentCountdown(true);
        } else if (self.amountLeftToExtrude.length && $("#jog-filament-notification").is(":visible")) {
          self.updateFilamentCountdown(false);
        }
      } else if (message.includes("UI:PalettePausedPrint")) {
        self.printPaused = message.substring(22);
      } else if (message.includes("UI:PrinterCon")) {
        let printerState = message.substring(14);
        if (printerState) {
          if (printerState === "Closed") {
            self.printerConnected = false;
          } else {
            self.printerConnected = true;
          }
        }
      } else if (message.includes("UI:FirstTime")) {
        let firstTime = message.substring(13);
        if (firstTime === "True") {
          self.firstTime = true;
        } else {
          self.firstTime = false;
        }
      } else if (message.includes("UI:AutoConnect=")) {
        self.autoconnect = message.substring(15);
        if (self.autoconnect === "True") {
          self.autoconnect = true;
        } else {
          self.autoconnect = false;
        }
      }
    }

    self.updatePongMsg = function(isPonging) {
      if (isPonging) {
        $("#ponging-span").removeClass("hide");
      } else {
        $("#ponging-span").addClass("hide");
      }
    };
  };
}

/* ======================
  RUN
  ======================= */

$(function() {
  OmegaViewModel();
  OCTOPRINT_VIEWMODELS.push({
    // This is the constructor to call for instantiating the plugin
    construct: OmegaViewModel,
    // This is a list of dependencies to inject into the plugin. The order will correspond to the "parameters" arguments above
    dependencies: ["settingsViewModel"],
    // Finally, this is the list of selectors for all elements we want this view model to be bound to.
    elements: ["#tab_plugin_palette2"]
  });
});
