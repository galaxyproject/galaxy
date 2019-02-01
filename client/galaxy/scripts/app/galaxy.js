import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
import BASE_MVC from "mvc/base-mvc";
import userModel from "mvc/user/user-model";
import metricsLogger from "utils/metrics-logger";
import addLogging from "utils/add-logging";
import localize from "utils/localization";
import { getGalaxyInstance } from "app";

// ============================================================================
/** Base galaxy client-side application.
 *      Iniitializes:
 *          logger      : the logger/metrics-logger
 *          localize    : the string localizer
 *          config      : the current configuration (any k/v in
 *              galaxy.ini available from the configuration API)
 *          user        : the current user (as a mvc/user/user-model)
 */
export function GalaxyApp(options = {}, bootstrapped = {}) {
    // console.warn("GalaxyApp constructor", serverPath());
    this._init(options, bootstrapped);
}

// add logging shortcuts for this object
addLogging(GalaxyApp, "GalaxyApp");

// a debug flag can be set via local storage and made available during script/page loading
var DEBUGGING_KEY = "galaxy:debug";

var NAMESPACE_KEY = `${DEBUGGING_KEY}:namespaces`;
var FLATTEN_LOG_MESSAGES_KEY = `${DEBUGGING_KEY}:flatten`;

var localDebugging = false;
try {
    localDebugging = localStorage.getItem(DEBUGGING_KEY) == "true";
} catch (storageErr) {
    console.log(localize("localStorage not available for debug flag retrieval"));
}

/** initalize options and sub-components */
GalaxyApp.prototype._init = function(options, bootstrapped) {
    var self = this;
    _.extend(self, Backbone.Events);
    if (localDebugging) {
        self.logger = console;
        console.debug("debugging galaxy:", "options:", options, "bootstrapped:", bootstrapped);
    }

    self._processOptions(options);
    self._initConfig(options.config || {});

    // Patch if this galaxy instance is replacing an existing one
    // _patchGalaxy depends on options.patchExisting
    // TODO: rethink this behavior
    let existingGalaxy = getGalaxyInstance();
    if (existingGalaxy) {
        self._patchGalaxy(existingGalaxy);
    }

    // add root and url parameters
    self.root = options.root || "/";
    self.params = options.params || {};
    self.session_csrf_token = options.session_csrf_token || null;

    self._initLogger(self.options.loggerOptions || {});
    // at this point, either logging or not and namespaces are enabled - chat it up
    self.debug("GalaxyApp.options: ", self.options);
    self.debug("GalaxyApp.config: ", self.config);
    self.debug("GalaxyApp.logger: ", self.logger);

    self._initLocale();
    self.debug("GalaxyApp.localize: ", self.localize);

    self.config = options.config || {};
    self.debug("GalaxyApp.config: ", self.config);

    self._initUser(options.user || {});
    self.debug("GalaxyApp.user: ", self.user);

    self._initUserLocale();
    self.debug("currentLocale: ", sessionStorage.getItem("currentLocale"));

    self._setUpListeners();
    self.trigger("ready", self);

    return self;
};

/** default options */
GalaxyApp.prototype.defaultOptions = {
    /** monkey patch attributes from existing Galaxy object? */
    patchExisting: true,
    /** root url of this app */
    root: "/",
    session_csrf_token: null
};

/** filter to options present in defaultOptions (and default to them) */
GalaxyApp.prototype._processOptions = function _processOptions(options) {
    var self = this;
    var defaults = self.defaultOptions;

    self.options = {};
    for (var k in defaults) {
        if (defaults.hasOwnProperty(k)) {
            self.options[k] = options.hasOwnProperty(k) ? options[k] : defaults[k];
        }
    }
    return self;
};

/** parse the config and any extra info derived from it */
GalaxyApp.prototype._initConfig = function _initConfig(config) {
    var self = this;
    self.config = config;

    // give precendence to localdebugging for this setting
    self.config.debug = localDebugging || self.config.debug;

    return self;
};

// TODO: Remove this behavior when we can, it is kind of non-intuitive
GalaxyApp.prototype._patchGalaxy = function _patchGalaxy(patchWith) {
    var self = this;
    // in case req or plain script tag order has created a prev. version of the Galaxy obj...
    if (self.options.patchExisting && patchWith) {
        // self.debug( 'found existing Galaxy object:', patchWith );
        // ...(for now) monkey patch any added attributes that the previous Galaxy may have had
        //TODO: move those attributes to more formal assignment in GalaxyApp
        for (var k in patchWith) {
            if (patchWith.hasOwnProperty(k)) {
                // self.debug( '\t patching in ' + k + ' to Galaxy:', self[ k ] );
                self[k] = patchWith[k];
            }
        }
    }
};

/** set up the metrics logger (utils/metrics-logger) and pass loggerOptions */
GalaxyApp.prototype._initLogger = function _initLogger(loggerOptions) {
    var self = this;

    // default to console logging at the debug level if the debug flag is set
    if (self.config.debug) {
        loggerOptions.consoleLogger = loggerOptions.consoleLogger || console;
        loggerOptions.consoleLevel = loggerOptions.consoleLevel || metricsLogger.MetricsLogger.ALL;
        // load any logging namespaces from localStorage if we can
        try {
            loggerOptions.consoleNamespaceWhitelist = localStorage.getItem(NAMESPACE_KEY).split(",");
        } catch (storageErr) {
            console.debug(storageErr);
        }
        try {
            loggerOptions.consoleFlattenMessages = localStorage.getItem(FLATTEN_LOG_MESSAGES_KEY) == "true";
        } catch (storageErr) {
            console.debug(storageErr);
        }
        console.log(loggerOptions.consoleFlattenMessages);
    }

    self.logger = new metricsLogger.MetricsLogger(loggerOptions);
    self.emit = {};
    ["log", "debug", "info", "warn", "error", "metric"].map(i => {
        self.emit[i] = function(data) {
            self.logger.emit(i, arguments[0], Array.prototype.slice.call(arguments, 1));
        };
    });

    if (self.config.debug) {
        // add this logger to mvc's loggable mixin so that all models can use the logger
        BASE_MVC.LoggableMixin.logger = self.logger;
    }
    return self;
};

/** add the localize fn to this object and the window namespace (as '_l') */
GalaxyApp.prototype._initLocale = function _initLocale(options) {
    var self = this;
    self.debug("_initLocale:", options);
    self.localize = localize;
    // add to window as global shortened alias
    // TODO: temporary - remove when can require for plugins
    window._l = self.localize;
    return self;
};

/** add the localize fn to this object and the window namespace (as '_l') */
GalaxyApp.prototype._initUserLocale = function _initUserLocale(options) {
    var self = this;

    // Choose best locale
    var global_locale = self.config.default_locale ? self.config.default_locale.toLowerCase() : false;

    var extra_user_preferences = {};
    if (self.user && self.user.attributes.preferences && "extra_user_preferences" in self.user.attributes.preferences) {
        extra_user_preferences = JSON.parse(self.user.attributes.preferences.extra_user_preferences);
    }

    var user_locale =
        "localization|locale" in extra_user_preferences
            ? extra_user_preferences["localization|locale"].toLowerCase()
            : false;

    if (user_locale == "auto") {
        user_locale = false;
    }

    var nav_locale =
        typeof navigator === "undefined"
            ? "__root"
            : (navigator.language || navigator.userLanguage || "__root").toLowerCase();

    let locale = user_locale || global_locale || nav_locale;

    sessionStorage.setItem("currentLocale", locale);
};

/** set up the current user as a Backbone model (mvc/user/user-model) */
GalaxyApp.prototype._initUser = function _initUser(userJSON) {
    var self = this;
    self.debug("_initUser:", userJSON);
    self.user = new userModel.User(userJSON);
    self.user.logger = self.logger;
    return self;
};

/** Set up DOM/jQuery/Backbone event listeners enabled for all pages */
GalaxyApp.prototype._setUpListeners = function _setUpListeners() {
    var self = this;

    // hook to jq beforeSend to record the most recent ajax call and cache some data about it
    /** cached info about the last ajax call made through jQuery */
    self.lastAjax = {};
    $(document).bind("ajaxSend", (ev, xhr, options) => {
        var data = options.data;
        try {
            data = JSON.parse(data);
        } catch (err) {
            // data isn't JSON, skip.
        }

        self.lastAjax = {
            url: location.href.slice(0, -1) + options.url,
            data: data
        };
        //TODO:?? we might somehow manage to *retry* ajax using either this hook or Backbone.sync
    });
    return self;
};

/** Turn debugging/console-output on/off by passing boolean. Pass nothing to get current setting. */
GalaxyApp.prototype.debugging = function _debugging(setting) {
    var self = this;
    try {
        if (setting === undefined) {
            return localStorage.getItem(DEBUGGING_KEY) === "true";
        }
        if (setting) {
            localStorage.setItem(DEBUGGING_KEY, true);
            return true;
        }

        localStorage.removeItem(DEBUGGING_KEY);
        // also remove all namespaces
        self.debuggingNamespaces(null);
    } catch (storageErr) {
        console.log(localize("localStorage not available for debug flag retrieval"));
    }
    return false;
};

/** Add, remove, or clear namespaces from the debugging filters
 *  Pass no arguments to retrieve the existing namespaces as an array.
 *  Pass in null to clear all namespaces (all logging messages will show now).
 *  Pass in an array of strings or single string of the namespaces to filter to.
 *  Returns the new/current namespaces as an array;
 */
GalaxyApp.prototype.debuggingNamespaces = function _debuggingNamespaces(namespaces) {
    var self = this;
    try {
        if (namespaces === undefined) {
            var csv = localStorage.getItem(NAMESPACE_KEY);
            return typeof csv === "string" ? csv.split(",") : [];
        } else if (namespaces === null) {
            localStorage.removeItem(NAMESPACE_KEY);
        } else {
            localStorage.setItem(NAMESPACE_KEY, namespaces);
        }
        var newSettings = self.debuggingNamespaces();
        if (self.logger) {
            self.logger.options.consoleNamespaceWhitelist = newSettings;
        }
        return newSettings;
    } catch (storageErr) {
        console.log(localize("localStorage not available for debug namespace retrieval"));
    }
};

/** string rep */
GalaxyApp.prototype.toString = function toString() {
    var userEmail = this.user ? this.user.get("email") || "(anonymous)" : "uninitialized";
    return `GalaxyApp(${userEmail})`;
};

// ============================================================================
export default {
    GalaxyApp: GalaxyApp
};
