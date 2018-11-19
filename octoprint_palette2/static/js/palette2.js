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
      console.log("API KEY", UI_API_KEY);
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
          console.log("SUCCESS ~~~", d);
          self.files(
            d.files.map(function(file, index) {
              console.log(index, file);
              return file.name;
            })
          );
          console.log(self.files);
        }
      });
    };

    self.connectOmega = function() {
      console.log("Connect omega");
      var payload = {
        command: "connectOmega",
        port: ""
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

    self.disconnectPalette2 = function() {
      var payload = {
        command: "disconnectPalette2"
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

    self.sendOmegaCmd = function() {
      console.log("Sending omega command");
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
      console.log("Connecting to Wifi");
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
      console.log("Send jog command called");
      var drive = parseInt(self.selectedJogDriveObs());
      var dist = parseInt(self.selectedJogDistance());

      if (self.selectedJogDriveObs().includes("Out")) {
        drive = 18;
      } else if (self.jogWithOutgoing()) {
        drive += 13;
      } else {
        drive += 9;
      }

      console.log(drive);
      console.log(dist);

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
      console.log("Send stop indef jog command");
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
      console.log("Sending cut command");
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
        command: "sendJogCmd",
        drive: 18,
        dist: 150
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
      console.log("Active Drive " + activeDrive);
    };

    self.fromResponse = function() {
      console.log("SUCCESS");
    };

    self.onAllBound = function(allViewModels) {
      console.log(allViewModels);
      console.log(self.settings);
    };

    self.onEventPrintStarted = function(payload) {
      console.log(payload.name);
      if (payload.name.includes(".mcf.gcode")) {
        // self.showOmegaDialog();
        if (self.displayAlerts) {
          swal({
            title: "You are about to print a Multi-Material File",
            text:
              "Your print has temporarily been paused by the Palette 2 Plugin. This is normal - please go see your Palette 2 device and follow the instructions on its screen. The print will resume automatically once everything is ready.",
            type: "info"
          });
        }
      }
    };

    self.onEventPrintPaused = function(payload) {
      if (payload.name.includes(".mcf.gcode")) {
        if (self.printPaused === "True") {
          $("#job_pause").attr("disabled", true);
        }
      }
    };

    self.onEventPrintResumed = function(payload) {
      if (payload.name.includes(".mcf.gcode")) {
        if (self.printPaused === "False") {
          $("#job_pause").attr("disabled", false);
        }
      }
    };

    self.onEventPrintDone = function(payload) {
      if (payload.name.includes(".mcf.gcode")) {
        if (self.displayAlerts) {
          swal({
            title: "Print Completed",
            text: `Your Multi-Material Print for ${payload.name} is done.`,
            type: "success"
          });
        }
      }
    };

    self.showOmegaDialog = function() {
      //self.currentSplice(self.spliceNumber);
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
      console.log(activeDrive);
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
      let filament = (Number(self.filaLength) / 1000.0).toFixed(1) + "m";
      console.log(filament + "m");
      $(".filament-used span")
        .html("")
        .text(filament);
    };

    self.updateCurrentSplice = function() {
      $(".current-splice").text(self.currentSplice());
    };

    self.updateTotalSplices = function() {
      let totalSplices = " / " + self.nSplices() + " Splices";
      console.log(totalSplices);
      $(".total-splices").text(totalSplices);
    };

    self.updateConnection = function(condition) {
      if (condition) {
        $("#connection-state-msg")
          .removeClass("text-muted")
          .addClass("text-success")
          .css("color", "green");
        $(".connect-palette-button")
          .text("Connected")
          .addClass("disabled")
          .attr("disabled", true);
        self.connectionStateMsg("Connected");
        self.connected(true);
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
        self.connected(false);
      }
    };

    self.updateCurrentStatus = function() {
      $(".current-status").text(self.currentStatus);
      if (self.currentStatus === "Palette work completed: all splices prepared") {
        $(".current-status")
          .text(self.currentStatus)
          .addClass("completed");
        if (self.displayAlerts) {
          swal({
            title: "Palette work is completed",
            text: `All splices have been prepared. You may check on the progress of your print on the left sidebar. You will be notified when the print is completed. `,
            type: "success"
          });
        }
      } else if (self.currentStatus === "Loading filament through outgoing tube") {
        if (self.displayAlerts) {
          swal({
            title: "Drives Are Loaded",
            text:
              "Please wait while the filament is loaded through the outgoing tube. You will be notified when this is done. In the meanwhile, please pre-heat your printer in the Temperature Tab.",
            type: "info"
          });
        }
      } else if (self.currentStatus === "Loading filament into extruder") {
        if (self.displayAlerts) {
          swal({
            title: "Filament Is Ready",
            text:
              "Please follow the instructions on the Palette Screen. Press OK when you are at the filament jogging step.",
            type: "info"
          }).then(result => {
            if (result.value) {
              let base_url = window.location.origin;
              window.location.href = `${base_url}/#control`;
              if (self.displayAlerts) {
                swal({
                  title: "Slowly extrude until the filament is in place ",
                  text: `Use the "Extrude" button in this tab to push the filament to the appropriate start location. Please set small amounts (1mm - 5mm) to not extrude too far. `,
                  type: "info",
                  position: "bottom",
                  allowOutsideClick: false
                });
              }
              let notification = $(`<li id="jog-filament-notification" class="popup-notification">
            <h6>Remaining length to extrude:</h6>
            <p class="jog-filament-value">${self.amountLeftToExtrude}mm</p>
            </li>`).hide();
              $(".side-notifications-list").append(notification);
              notification.fadeIn(200);
              self.jogId = "#jog-filament-notification";
            }
          });
        } else {
          // let base_url = window.location.origin;
          // window.location.href = `${base_url}/#control`;
          let notification = $(`<li id="jog-filament-notification" class="popup-notification">
            <h6>Remaining length to extrude:</h6>
            <p class="jog-filament-value">${self.amountLeftToExtrude}mm</p>
            </li>`).hide();
          $(".side-notifications-list").append(notification);
          notification.fadeIn(200);
          self.jogId = "#jog-filament-notification";
        }
      }
    };

    self.onDataUpdaterPluginMessage = function(pluginIdent, message) {
      if (pluginIdent === "palette2") {
        console.log(message);
        // console.log("Message from " + pluginIdent + ": " + message);
        if (message.includes("UI:currentSplice")) {
          var num = message.substring(17);
          console.log("Current splice " + num);
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
          console.log("loading drive #:" + drive + " with " + color);

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
          console.log(self.nSplices());
          self.updateTotalSplices();
        } else if (message.includes("UI:Ponging")) {
          self.updatePongMsg(true);
        } else if (message.includes("UI:Finished Pong")) {
          self.updatePongMsg(false);
        } else if (message.includes("UI:Con=")) {
          console.log("Checking connection state");
          if (message.includes("True")) {
            self.updateConnection(true);
          } else {
            self.updateConnection(false);
          }
        } else if (message.includes("UI:Refresh Demo List")) {
          self.refreshDemoList();
        } else if (message.includes("UI:FilamentLength")) {
          self.filaLength = message.substring(18);
          console.log("Filament Length: " + self.filaLength);
          self.updateFilamentUsed();
        } else if (message.includes("UI:currentStatus")) {
          if (message.substring(17) !== self.currentStatus) {
            self.currentStatus = message.substring(17);
            self.updateCurrentStatus();
          }
        } else if (message.includes("UI:AmountLeftToExtrude")) {
          self.amountLeftToExtrude = message.substring(23);
          console.log(self.amountLeftToExtrude);
          if (self.amountLeftToExtrude === "0") {
            $(self.jogId).fadeOut(500, function() {
              this.remove();
            });
            if (self.displayAlerts) {
              swal({
                title: "Filament in place and ready to go",
                text: `Please go back to your Palette and press "Next". Once that is done, your print will restart automatically. You will be notified when Palette finishes preparing splices as well as when the print itself is completed.`,
                type: "info"
              });
            }
          } else if ($("#jog-filament-notification").length) {
            $(self.jogId)
              .find(".jog-filament-value")
              .text(`${self.amountLeftToExtrude}mm`);
          }
        } else if (message.includes("UI:PalettePausedPrint")) {
          self.printPaused = message.substring(22);
          console.log("PRINT PAUSED: " + self.printPaused);
        }
      }
    };

    self.updatePongMsg = function(isPonging) {
      if (isPonging) {
        $("#ponging-span").removeClass("hide");
      } else {
        $("#ponging-span").addClass("hide");
      }
    };

    self.onAfterBinding = function() {
      var payload = {
        command: "uiUpdate"
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

    self.startSpliceDemo = function() {
      if (self.selectedDemoFile()) {
        console.log("Starting Splice Demo");
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
          contentType: "application/json; charset=UTF-8",
          success: self.fromResponse
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
