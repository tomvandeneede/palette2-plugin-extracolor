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

        self.connectOmega = function() {
		var payload = {
			command: "connectOmega",
			port: self.omegaPort()
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

        self.setAD = function() {
		var activeDrive = $("#omega-ad button.active").innerHTML;
		console.log("Active Drive " + activeDrive);
	}

        self.fromResponse = function () {
		console.log("SUCCESS");
	}

        self.onAllBound = function(allViewModels) {
            // do something with them
		console.log(allViewModels);
		
        }
	self.onEventPrintStarted = function(payload) {
		self.showOmegaDialog();
		
	}

	self.showOmegaDialog = function() {
		self.omegaDialog.modal({
               	 	minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 80, 250); }
            	}).css({
               		width: 'auto',
                	'margin-left': function() { return -($(this).width() /2); }
            	});
	
	}

        self.startSingleColor = function() {
		var activeDrive = $("#omega-mod-ad button.active")[0].innerHTML;
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
	}

//        self.onAfterBinding = function() {
//		console.log("AFTER BINDING");
//		self.activeDrive("1");
//		console.log(self.activeDrive());
//	}

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

        // this will be called when the user clicks the "Go" button and set the iframe's URL to
        // the entered URL
        self.goToUrl = function() {
            //self.currentUrl(self.newUrl());
            $.ajax({
                url: API_BASEURL + "plugin/omega",
                type: "GET",
                dataType: "json",
                success: self.fromResponse
            });
        };

        // This will get called before the HelloWorldViewModel gets bound to the DOM, but after its
        // dependencies have already been initialized. It is especially guaranteed that this method
        // gets called _after_ the settings have been retrieved from the OctoPrint backend and thus
        // the SettingsViewModel been properly populated.
        self.onBeforeBinding = function() {
            self.newUrl(self.settings.settings.plugins.omega.url());
            self.goToUrl();
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
