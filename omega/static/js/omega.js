$(function() {
    function OmegaViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];

		self.omegaDialog = $('#omega_dialog');

        // this will hold the URL currently displayed by the iframe
        self.currentUrl = ko.observable();

		self.activeDriveTest = function(param) {
			console.log(param);
		}

			// this will hold the URL entered in the text field
		self.newUrl = ko.observable();
		self.activeDrive = ko.observable();
		self.omegaCommand = ko.observable();
		self.omegaPort = ko.observable();
		self.currentSplice = ko.observable();
		self.nSplices = ko.observable();
		self.loadingDrive = ko.observable();
		self.loadingColor = ko.observable();
		self.connectionStateMsg = ko.observable();
		self.jogDistance = ko.observable();
		self.jogWithOutgoing = ko.observable(false);

		self.jogDrive = 0;
		self.jogDriveObs = ko.observable("1");
		self.spliceNumber = 0;

		self.jogDrives = ko.observableArray(['1', '2', '3', '4', 'Out']);
		self.jogDists = ko.observableArray(['1', '10', '100', '-1', '-10', '-100']);

		self.connectOmega = function() {
			console.log("Connect omega")
			var payload = {
				command: "connectOmega",
				port: ""
			}

			$.ajax({
				url: API_BASEURL + "plugin/omega",
				type: "POST",
				dataType: "json",
				data: JSON.stringify(payload),
				contentType: "application/json; charset=UTF-8",
				success: self.fromResponse
			});
		}

		self.disconnectPalette2 = function() {
			var payload = {
				command: "disconnectPalette2",
			}
			$.ajax({
				url: API_BASEURL + "plugin/omega",
				type: "POST",
				dataType: "json",
				data: JSON.stringify(payload),
				contentType: "application/json; charset=UTF-8",
				success: self.fromResponse
			});
		}

		self.sendOmegaCmd = function() {
			var payload = {
				command: "sendOmegaCmd",
				cmd: self.omegaCommand()
			}
			$.ajax({
				url: API_BASEURL + "plugin/omega",
				type: "POST",
				dataType: "json",
				data: JSON.stringify(payload),
				contentType: "application/json; charset=UTF-8",
				success: self.fromResponse
			});
		}
     
		self.sendJogCmd = function () {
			console.log("Send jog command called")
			var distance = self.jogDistance();
			var drive = parseInt(self.jogDriveObs());
			var dist = parseInt(self.jogDistance());

			if (self.jogDriveObs().includes('Out')) {
				drive = 18;
			}
			else if (self.jogWithOutgoing()) {
				drive += 13;
			}
			else {
				drive += 9;
			}
			console.log(drive);
			console.log(dist);
			if (dist) {
				var payload = {
					command: "sendJogCmd",
					drive: drive,
					dist: dist 
				}
				$.ajax({
					url: API_BASEURL + "plugin/omega",
					type: "POST",
					dataType: "json",
					data: JSON.stringify(payload),
					contentType: "application/json; charset=UTF-8",
					success: self.fromResponse
				});
			}
		}

		self.sendCutCmd = function () {
			console.log("Sending cut command");
			var payload = {
				command: "sendCutCmd",
			}
			$.ajax({
				url: API_BASEURL + "plugin/omega",
				type: "POST",
				dataType: "json",
				data: JSON.stringify(payload),
				contentType: "application/json; charset=UTF-8",
				success: self.fromResponse
			});
		}

		self.sendClearOutCmd = function () {
			var payload = {
				command: "sendJogCmd",
				drive: 18,
				dist: 150 
			}

			$.ajax({
				url: API_BASEURL + "plugin/omega",
				type: "POST",
					dataType: "json",
					data: JSON.stringify(payload),
					contentType: "application/json; charset=UTF-8",
					success: self.fromResponse
			});
		}

		self.sendCancelCmd = function () {
			self.omegaCommand("O0");
			self.sendOmegaCmd();
			self.omegaCommand("");
		}

        self.sendSDWPrinterStart = function() {
			var payload = {
				command: "sdwpStart"
			}
			$.ajax({
				url: API_BASEURL + "plugin/omega",
				type: "POST",
				dataType: "json",
				data: JSON.stringify(payload),
				contentType: "application/json; charset=UTF-8",
				success: self.fromResponse
			});

        }

        self.sendPrintStart = function() {
			var payload = {
				command: "printStart",
			}
			$.ajax({
				url: API_BASEURL + "plugin/omega",
				type: "POST",
				dataType: "json",
				data: JSON.stringify(payload),
				contentType: "application/json; charset=UTF-8",
				success: self.fromResponse
			});
        }	

		self.setJogDrive = function () {
			console.log(self.jogDriveObs());	
		}

		self.sendFilamentLoaded = function () {
			self.omegaCommand("O39");
			self.sendOmegaCmd();
		} 

        self.setAD = function() {
			var activeDrive = $("#omega-ad button.active").innerHTML;
			console.log("Active Drive " + activeDrive);
		}

        self.fromResponse = function () {
			console.log("SUCCESS");
		}

        self.onAllBound = function(allViewModels) {
			console.log(allViewModels);
		}
		
		self.onEventPrintStarted = function(payload) {
			//self.showOmegaDialog();
			console.log(payload.filename);
			if (payload.filename.includes(".oem")) {
				self.showOmegaDialog();
			}
		}

		self.showOmegaDialog = function() {
			//self.currentSplice(self.spliceNumber);
			self.loadingColor("Blue");
			self.omegaDialog.modal({
						minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 80, 250); }
					}).css({
						width: 'auto',
						'margin-left': function() { return -($(this).width() /2); }
					});
		}

		self.startSingleColor = function() {
			var activeDrive = $("#omega-mod-ad button.active")[0].innerHTML;
			activeDrive = activeDrive - 1;
			console.log(activeDrive);
			var payload = {
				command: "startSingleColor",
				drive: activeDrive
			}
	
			$.ajax({
				url: API_BASEURL + "plugin/omega",
				type: "POST",
				dataType: "json",
				data: JSON.stringify(payload),
				contentType: "application/json; charset=UTF-8",
				success: self.fromResponse
			});
		}

		self.onDataUpdaterPluginMessage = function (pluginIdent, message) {
			console.log("Message from " + pluginIdent + ": " + message);
			if (message.includes("UI:S=")) {
				var num = message.substring(5);
				console.log("Current splice " + num);
				self.currentSplice(num);
			}
			else if (message.includes("UI:Load")) {
				var colors = ["", "filament", "Red", "Orange", "Yellow", "Green", "Blue", 
					"Pink", "Purple", "Brown", "Transparent", "White", 
					"Grey", "Black", "User 1", "User 2" ];

				var drive = message.substring(9, 10);
				var colorHex = message.substring(11, 12);
				var colorDec = parseInt("0x" + colorHex);
				var color = colors[colorDec];
				console.log("loading drive #:" + drive + " with " + color);

				if ($('#loading-span').hasClass("hide")) {
					$('#loading-span').removeClass("hide");
				}

				self.loadingDrive(drive);
				self.loadingColor(color);
			}
			else if (message.includes("UI:FINISHED LOADING")) {
				$('#loading-span').addClass("hide");
			}
			else if (message.includes("UI:nSplices")) {
				var ns = message.substring(12);
				self.nSplices(ns);
			}
			else if (message.includes("UI:Ponging")) {
				self.updatePongMsg(true);
			}
			else if (message.includes("UI:Finished Pong")) {
				self.updatePongMsg(false);
			}
			else if (message.includes("UI:Con=")) {
				console.log("Checking connection state")
				if (message.includes("True")) {
					$('#connection-state-msg').removeClass("text-muted");
					$('#connection-state-msg').addClass("text-success");
					self.connectionStateMsg("Connected");
				}
				else {
					$('#connection-state-msg').removeClass("text-success");
					$('#connection-state-msg').addClass("text-muted");
					self.connectionStateMsg("Not Connected");
				}
			}
		}

		self.updatePongMsg = function(isPonging) {
			if (isPonging) {
				$('#ponging-span').removeClass("hide");
			}
			else {
				$('#ponging-span').addClass("hide");
			}
		}

		self.onAfterBinding = function() {
			var payload = {
				command: "uiUpdate",
			}

			$.ajax({
				url: API_BASEURL + "plugin/omega",
				type: "POST",
				dataType: "json",
				data: JSON.stringify(payload),
				contentType: "application/json; charset=UTF-8",
				success: self.fromResponse
			});
		}

		self.startSpliceDemo = function() {
			console.log("Starting Splice Demo");
			var payload = {
				command: "startSpliceDemo"
			};

			$.ajax({
				url: API_BASEURL + "plugin/omega",
				type: "POST",
				dataType: "json",
				data: JSON.stringify(payload),
				contentType: "application/json; charset=UTF-8",
				success: self.fromResponse
			});

		}

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
        }
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
        ["#tab_plugin_omega"]
    ]);
});
