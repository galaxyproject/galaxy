define([ "libs/underscore", "libs/backbone", "mvc/base-mvc", "mvc/user/user-model", "utils/metrics-logger", "utils/add-logging", "utils/localization" ], function(_, Backbone, BASE_MVC, userModel, metricsLogger, addLogging, localize) {
    function GalaxyApp(options, bootstrapped) {
        console.debug("GalaxyApp:", options, bootstrapped);
        var self = this;
        return self._init(options || {}, bootstrapped || {});
    }
    addLogging(GalaxyApp, "GalaxyApp");
    var DEBUGGING_KEY = "galaxy:debug", NAMESPACE_KEY = DEBUGGING_KEY + ":namespaces", localDebugging = !1;
    try {
        localDebugging = "true" == localStorage.getItem(DEBUGGING_KEY);
    } catch (storageErr) {
        console.log(localize("localStorage not available for debug flag retrieval"));
    }
    return GalaxyApp.prototype._init = function(options, bootstrapped) {
        var self = this;
        return _.extend(self, Backbone.Events), localDebugging && (self.logger = console), 
        self._processOptions(options), self.debug("GalaxyApp.options: ", self.options), 
        self.root = options.root || "/", self._initConfig(options.config || bootstrapped.config || {}), 
        self.debug("GalaxyApp.config: ", self.config), self._patchGalaxy(window.Galaxy), 
        self._initLogger(self.options.loggerOptions || {}), self.debug("GalaxyApp.logger: ", self.logger), 
        self._initLocale(), self.debug("GalaxyApp.localize: ", self.localize), self.config = options.config || {}, 
        self.debug("GalaxyApp.config: ", self.config), self._initUser(options.user || {}), 
        self.debug("GalaxyApp.user: ", self.user), self._setUpListeners(), self.trigger("ready", self), 
        self;
    }, GalaxyApp.prototype.defaultOptions = {
        patchExisting: !0,
        root: "/"
    }, GalaxyApp.prototype._processOptions = function(options) {
        var self = this, defaults = self.defaultOptions;
        self.debug("_processOptions: ", options), self.options = {};
        for (var k in defaults) defaults.hasOwnProperty(k) && (self.options[k] = options.hasOwnProperty(k) ? options[k] : defaults[k]);
        return self;
    }, GalaxyApp.prototype._initConfig = function(config) {
        var self = this;
        return self.debug("_initConfig: ", config), self.config = config, self.config.debug = localDebugging || self.config.debug, 
        self;
    }, GalaxyApp.prototype._patchGalaxy = function(patchWith) {
        var self = this;
        if (self.options.patchExisting && patchWith) {
            self.debug("found existing Galaxy object:", patchWith);
            for (var k in patchWith) patchWith.hasOwnProperty(k) && (self.debug("	 patching in " + k + " to Galaxy"), 
            self[k] = patchWith[k]);
        }
    }, GalaxyApp.prototype._initLogger = function(loggerOptions) {
        var self = this;
        if (self.config.debug) {
            loggerOptions.consoleLogger = loggerOptions.consoleLogger || console, loggerOptions.consoleLevel = loggerOptions.consoleLevel || metricsLogger.MetricsLogger.ALL;
            try {
                loggerOptions.consoleNamespaceWhitelist = localStorage.getItem(NAMESPACE_KEY).split(",");
            } catch (storageErr) {}
        }
        return self.debug("_initLogger:", loggerOptions), self.logger = new metricsLogger.MetricsLogger(loggerOptions), 
        self.config.debug && (BASE_MVC.LoggableMixin.logger = self.logger), self;
    }, GalaxyApp.prototype._initLocale = function(options) {
        var self = this;
        return self.debug("_initLocale:", options), self.localize = localize, window._l = self.localize, 
        self;
    }, GalaxyApp.prototype._initUser = function(userJSON) {
        var self = this;
        return self.debug("_initUser:", userJSON), self.user = new userModel.User(userJSON), 
        self.user.logger = self.logger, self.currUser = self.user, self;
    }, GalaxyApp.prototype._setUpListeners = function() {
        var self = this;
        return self.lastAjax = {}, $(document).bind("ajaxSend", function(ev, xhr, options) {
            var data = options.data;
            try {
                data = JSON.parse(data);
            } catch (err) {}
            self.lastAjax = {
                url: location.href.slice(0, -1) + options.url,
                data: data
            };
        }), self;
    }, GalaxyApp.prototype.debugging = function(setting) {
        var self = this;
        try {
            if (void 0 === setting) return "true" === localStorage.getItem(DEBUGGING_KEY);
            if (setting) return localStorage.setItem(DEBUGGING_KEY, !0), !0;
            localStorage.removeItem(DEBUGGING_KEY), self.debuggingNamespaces(null);
        } catch (storageErr) {
            console.log(localize("localStorage not available for debug flag retrieval"));
        }
        return !1;
    }, GalaxyApp.prototype.debuggingNamespaces = function(namespaces) {
        var self = this;
        try {
            if (void 0 === namespaces) {
                var csv = localStorage.getItem(NAMESPACE_KEY);
                return "string" == typeof csv ? csv.split(",") : [];
            }
            null === namespaces ? localStorage.removeItem(NAMESPACE_KEY) : localStorage.setItem(NAMESPACE_KEY, namespaces);
            var newSettings = self.debuggingNamespaces();
            return self.logger && (self.logger.options.consoleNamespaceWhitelist = newSettings), 
            newSettings;
        } catch (storageErr) {
            console.log(localize("localStorage not available for debug namespace retrieval"));
        }
    }, GalaxyApp.prototype.toString = function() {
        var userEmail = this.user ? this.user.get("email") || "(anonymous)" : "uninitialized";
        return "GalaxyApp(" + userEmail + ")";
    }, {
        GalaxyApp: GalaxyApp
    };
});