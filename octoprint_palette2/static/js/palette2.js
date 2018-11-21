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

$(function() {
  function OmegaViewModel(parameters) {
    var self = this;

    function JogDistance(dvalue, distance) {
      this.dvalue = dvalue;
      this.distance = distance;
    }

    self.settings = parameters[0];
    self.omegaDialog = $("#omega_dialog");

    // this will hold the URL currently displayed by the iframe
    self.currentUrl = ko.observable();

    self.activeDriveTest = function(param) {
      console.log(param);
    };

    // this will hold the URL entered in the text field
    self.newUrl = ko.observable();
    self.activeDrive = ko.observable();
    self.omegaCommand = ko.observable();
    self.wifiSSID = ko.observable();
    self.wifiPASS = ko.observable();
    self.omegaPort = ko.observable();
    self.currentSplice = ko.observable();
    self.nSplices = ko.observable();
    self.loadingDrive = ko.observable();
    self.loadingColor = ko.observable();
    self.connectionStateMsg = ko.observable();
    self.connected = ko.observable(false);
    self.jogWithOutgoing = ko.observable(false);
    self.jogDrive = 0;
    self.selectedJogDriveObs = ko.observable("1");
    self.spliceNumber = 0;
    self.demoWithPrinter = ko.observable(false);
    self.currentStatus = "";
    self.amountLeftToExtrude = "";
    self.jogId = "";
    self.displayAlerts = true;
    self.tryingToConnect = false;
    self.currentFile = "";
    self.printerConnected = false;

    self.jogDrives = ko.observableArray(["1", "2", "3", "4", "Out"]);
    self.files = ko.observableArray([]);

    //self.jogDists = ko.observableArray(['1', '10', '100', '-1', '-10', '-100']);
    self.jogDists = ko.observableArray([
      new JogDistance(999, "∞"),
      new JogDistance(100, "100"),
      new JogDistance(10, "10"),
      new JogDistance(1, "1"),
      new JogDistance(null, "Distance (mm)"),
      new JogDistance(-1, "-1"),
      new JogDistance(-10, "-10"),
      new JogDistance(-100, "-100"),
      new JogDistance(-999, "-∞")
    ]);

    self.selectedJogDistance = ko.observable();
    self.selectedDemoFile = ko.observable();

    window.onload = function() {
      self.refreshDemoList();
    };

    self.filterDemoFiles = ko.computed(function() {
      var filteredFiles = self.files().filter(f => {
        return f.match(/.msf$/i);
      });
      return filteredFiles;
    });

    self.refreshDemoList = function() {
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

    self.loadingOverlay = condition => {
      if (condition) {
        $("body").append(`<div class="loading-overlay-container"><div class="loader"></div></div>`);
      } else {
        $("body")
          .find(".loading-overlay-container")
          .remove();
      }
    };

    self.connectOmega = function() {
      self.tryingToConnect = true;
      self.loadingOverlay(true);

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

    self.disconnectPalette2 = function() {
      self.loadingOverlay(true);
      self.connected(false);
      $(self.jogId).fadeOut(500, function() {
        this.remove();
      });
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

    self.sendOmegaCmd = function(command, payload) {
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

    self.connectWifi = function() {
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

    self.sendJogCmd = function() {
      var drive = parseInt(self.selectedJogDriveObs());
      var dist = parseInt(self.selectedJogDistance());

      if (self.selectedJogDriveObs().includes("Out")) {
        drive = 18;
      } else if (self.jogWithOutgoing()) {
        drive += 13;
      } else {
        drive += 9;
      }

      if (dist) {
        var payload = {
          command: "sendJogCmd",
          drive: drive,
          dist: dist
        };
        $.ajax({
          url: API_BASEURL + "plugin/palette2",
          type: "POST",
          dataType: "json",
          data: JSON.stringify(payload),
          contentType: "application/json; charset=UTF-8",
          success: self.fromResponse
        });
      }
    };

    self.sendStopIndefJogCmd = function() {
      var payload = {
        command: "stopIndefJog"
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

    self.sendCutCmd = function() {
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

    self.sendClearOutCmd = function() {
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

    self.sendCancelCmd = function() {
      self.omegaCommand("O0");
      self.sendOmegaCmd();
      self.omegaCommand("");
    };

    self.sendSDWPrinterStart = function() {
      var payload = {
        command: "sdwpStart"
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

    self.sendPrintStart = function() {
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

    self.setJogDrive = function() {
      console.log(self.selectedJogDriveObs());
    };

    self.sendFilamentLoaded = function() {
      self.omegaCommand("O39");
      self.sendOmegaCmd();
    };

    self.setAD = function() {
      var activeDrive = $("#omega-ad button.active").innerHTML;
    };

    self.fromResponse = function() {
      // console.log("SUCCESS");
    };

    self.onAllBound = function(allViewModels) {
      // self.removeFolderBinding();
      // self.handleGCODEFolders();
    };

    self.findCurrentFilename = function() {
      self.currentFile = $("#state_wrapper")
        .find(`strong[title]`)
        .text();
    };

    self.onStartupComplete = function() {
      self.findCurrentFilename();
      self.removeFolderBinding();
      self.handleGCODEFolders();
    };

    self.applyPaletteDisabling = function() {
      console.log("PRINTER: " + self.printerConnected);
      console.log("P2: " + self.connected());
      console.log(self.currentFile);
      if (self.printerConnected) {
        if (!self.connected()) {
          let count = 0;
          let applyDisabling = setInterval(function() {
            if (count > 20) {
              clearInterval(applyDisabling);
            }
            $(".palette-tag")
              .siblings(".action-buttons")
              .find(".btn:last-child")
              .css("pointer-events", "none")
              .attr("disabled", true);

            count++;
            if (self.currentFile.includes(".mcf.gcode")) {
              $("#job_print").attr("disabled", true);
            } else if (self.currentFile && !self.currentFile.includes(".mcf.gcode")) {
              $("#job_print").attr("disabled", false);
            }
          }, 100);
        } else if (!self.currentFile) {
          let count = 0;
          let applyDisabling3 = setInterval(function() {
            if (count > 20) {
              clearInterval(applyDisabling3);
            }
            $("#job_print").attr("disabled", true);
            count++;
          }, 100);
        } else {
          let count = 0;
          let applyDisabling2 = setInterval(function() {
            if (count > 20) {
              clearInterval(applyDisabling2);
            }
            $(".palette-tag")
              .siblings(".action-buttons")
              .find(".btn:last-child")
              .css("pointer-events", "auto")
              .attr("disabled", false);
            $("#job_print").attr("disabled", false);
            count++;
          }, 100);
        }
      } else {
        let count = 0;
        let applyDisabling3 = setInterval(function() {
          if (count > 20) {
            clearInterval(applyDisabling3);
          }
          $("#job_print").attr("disabled", true);
          count++;
        }, 100);
      }
    };

    self.handleGCODEFolders = function(payload) {
      self.removeFolderBinding();
      $("#files .gcode_files .entry.back.clickable").on("click", () => {
        self.applyPaletteDisabling();
      });
    };

    self.removeFolderBinding = function(payload) {
      $("#files .gcode_files")
        .find(".folder .title")
        .removeAttr("data-bind")
        .on("click", event => {
          self.applyPaletteDisabling();
        });
    };

    self.onEventConnected = function(payload) {
      self.printerConnected = true;
      self.findCurrentFilename();
      self.applyPaletteDisabling();
    };

    self.onEventDisconnected = function(payload) {
      self.printerConnected = false;
      self.applyPaletteDisabling();
    };

    self.onEventFileRemoved = function(payload) {
      self.applyPaletteDisabling();
    };

    self.onEventUpdatedFiles = function(payload) {
      self.applyPaletteDisabling();
    };

    self.onEventFileSelected = function(payload) {
      self.currentFile = payload.name;

      if (self.currentFile.includes(".mcf.gcode")) {
        self.applyPaletteDisabling();
        if (!self.connected()) {
          swal({
            title: "Palette 2 not connected",
            text: "You have selected an .mcf file. Please enable the connection to Palette 2 before printing.",
            type: "info"
          });
        }
      }
    };

    self.onEventFileDeselected = function(payload) {
      self.applyPaletteDisabling();
    };

    self.onEventPrintStarted = function(payload) {
      if (payload.name.includes(".mcf.gcode")) {
        if (self.connected()) {
          if (self.displayAlerts) {
            swal({
              title: "You are about to print with Palette 2",
              text:
                "Your print has temporarily been paused. This is normal - please follow the instructions on Palette 2's screen. The print will resume automatically once everything is ready.",
              type: "info"
            });
          }
        }
      }
    };

    self.onEventPrintPaused = function(payload) {
      if (self.connected() && payload.name.includes(".mcf.gcode")) {
        let count = 0;
        let applyDisablingResume = setInterval(function() {
          if (count > 50) {
            clearInterval(applyDisablingResume);
          }
          $("body")
            .find("#job_pause")
            .attr("disabled", true);
          count++;
        }, 100);
      }
    };

    self.onEventPrintResumed = function(payload) {
      console.log("GOT TO EVENT PRINT RESUMED");
      console.log(self.connected());
      console.log(payload.name);

      if (self.connected() && payload.name.includes(".mcf.gcode")) {
        console.log("GOT INSIDE IF");
        let count = 0;
        let applyDisablingResume2 = setInterval(function() {
          console.log("GOT LOOP");

          if (count > 50) {
            clearInterval(applyDisablingResume2);
          }
          $("body")
            .find("#job_pause")
            .attr("disabled", false);
          $("#job_print").attr("disabled", true);
          count++;
        }, 100);
      }
    };

    self.onEventPrintCancelled = function(payload) {
      if (payload.name.includes(".mcf.gcode")) {
        self.sendCancelCmd();
      }
    };

    self.showOmegaDialog = function() {
      self.loadingColor("Blue");
      self.omegaDialog
        .modal({
          minHeight: function() {
            return Math.max($.fn.modal.defaults.maxHeight() - 80, 250);
          }
        })
        .css({
          width: "auto",
          "margin-left": function() {
            return -($(this).width() / 2);
          }
        });
    };

    self.startSingleColor = function() {
      var activeDrive = $("#omega-mod-ad button.active")[0].innerHTML;
      activeDrive = activeDrive - 1;
      var payload = {
        command: "startSingleColor",
        drive: activeDrive
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

    self.updateFilamentUsed = function() {
      let filament = (Number(self.filaLength) / 1000.0).toFixed(2) + "m";
      $(".filament-used span")
        .html("")
        .text(filament);
    };

    self.updateCurrentSplice = function() {
      $(".current-splice").text(self.currentSplice());
    };

    self.updateTotalSplices = function() {
      let totalSplices = " / " + self.nSplices() + " Splices";
      $(".total-splices").text(totalSplices);
    };

    self.updateConnection = function() {
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
    };

    self.updateCurrentStatus = function() {
      $(".current-status").text(self.currentStatus);
      if (self.currentStatus === "Palette work completed: all splices prepared") {
        $(".current-status")
          .text(self.currentStatus)
          .addClass("completed");
      } else if (self.currentStatus === "Loading filament through outgoing tube") {
        if (self.displayAlerts) {
          let base_url = window.location.origin;
          window.location.href = `${base_url}/#temp`;
          swal({
            title: "Pre-heat your printer",
            text:
              "Palette 2 is now making filament. In the meantime, please pre-heat your printer using the controls in the Temperature Tab.",
            type: "info"
          }).then(res => {
            $("body")
              .find(`#temperature-table .input-mini.input-nospin`)
              .addClass("highlight-glow")
              .on("focus", event => {
                $(event.target).removeClass("highlight-glow");
              });
          });
        }
      } else if (self.currentStatus === "Loading filament into extruder") {
        if (self.displayAlerts) {
          let base_url = window.location.origin;
          window.location.href = `${base_url}/#control`;
          swal({
            title: "Follow instructions on Palette 2 ",
            text: `Use the "Extrude" button in the Controls tab to drive filament into the extruder. To accurately load, we recommend setting the extrusion amount to a low number (1mm - 5mm).`,
            type: "info"
          }).then(res => {
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
          });
        }
        let notification = $(`<li id="jog-filament-notification" class="popup-notification">
            <h6>Remaining length to extrude:</h6>
            <p class="jog-filament-value">${self.amountLeftToExtrude}mm</p>
            </li>`).hide();
        self.jogId = "#jog-filament-notification";
        $(".side-notifications-list").append(notification);
      }
    };

    self.changeAlertSettings = function(condition) {
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

    self.onDataUpdaterPluginMessage = function(pluginIdent, message) {
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
        } else if (message.includes("UI:Load")) {
          var colors = [
            "",
            "filament",
            "Red",
            "Orange",
            "Yellow",
            "Green",
            "Blue",
            "Pink",
            "Purple",
            "Brown",
            "Transparent",
            "White",
            "Grey",
            "Black",
            "User 1",
            "User 2"
          ];

          var drive = message.substring(9, 10);
          var colorHex = message.substring(11, 12);
          var colorDec = parseInt("0x" + colorHex);
          var color = colors[colorDec];

          if ($("#loading-span").hasClass("hide")) {
            $("#loading-span").removeClass("hide");
          }

          self.loadingDrive(drive);
          self.loadingColor(color);
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
          self.loadingOverlay(false);
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
              swal({
                title: "Could not connect to Palette 2",
                text: `Please make sure Palette 2 is turned on. Please wait 5 seconds before trying again.`,
                type: "error"
              });
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
            $(self.jogId).fadeOut(500, function() {
              this.remove();
            });
            if (self.displayAlerts) {
              swal({
                title: "Filament in place and ready to go",
                text: `Please go back to your Palette 2 and press "Finished". On the next screen, press "Start Print". Your print will begin automatically.`,
                type: "info",
                input: "checkbox",
                inputPlaceholder: "Don't show me these setup alerts anymore"
              });
            }
          } else if (self.amountLeftToExtrude.length && !$("#jog-filament-notification").is(":visible")) {
            $(self.jogId)
              .fadeIn(200)
              .find(".jog-filament-value")
              .text(`${self.amountLeftToExtrude}mm`);
          } else if ($("#jog-filament-notification").is(":visible")) {
            $(self.jogId)
              .find(".jog-filament-value")
              .text(`${self.amountLeftToExtrude}mm`);
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

    self.onAfterBinding = function() {
      var payload = { command: "uiUpdate" };

      $.ajax({
        url: API_BASEURL + "plugin/palette2",
        type: "POST",
        dataType: "json",
        data: JSON.stringify(payload),
        contentType: "application/json; charset=UTF-8"
      });

      // HAVE SOMETHING TO DISABLE THESE SETUP TUTORIALS
      // 1. No ongoing Palette 2 print
      // 2. Loading ingoing drives
      // 3. Loading filament through outgoing tube
      // 4. Loading filament into extruder
      // 5. Preparing splices
      // 6. Palette work completed: all splices prepared
    };

    self.startSpliceDemo = function() {
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

    // This will get called before the ViewModel gets bound to the DOM, but after its
    // dependencies have already been initialized. It is especially guaranteed that this method
    // gets called _after_ the settings have been retrieved from the OctoPrint backend and thus
    // the SettingsViewModel been properly populated.
    self.onBeforeBinding = function() {
      self.currentSplice("0");
      self.nSplices("0");
      self.loadingDrive("0");
      self.loadingColor("Black");
      self.connectionStateMsg("Not Connected");
      self.connected(false);
    };
  }

  // This is how our plugin registers itself with the application, by adding some configuration
  // information to the global variable OCTOPRINT_VIEWMODELS
  OCTOPRINT_VIEWMODELS.push([
    // This is the constructor to call for instantiating the plugin
    OmegaViewModel,

    // This is a list of dependencies to inject into the plugin, the order which you request
    // here is the order in which the dependencies will be injected into your view model upon
    // instantiation via the parameters argument
    ["settingsViewModel"],

    // Finally, this is the list of selectors for all elements we want this view model to be bound to.
    ["#tab_plugin_palette2"]
  ]);
});
