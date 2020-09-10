import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
import BASE_MVC from "mvc/base-mvc";
import userModel from "mvc/user/user-model";
import metricsLogger from "utils/metrics-logger";
import addLogging from "utils/add-logging";
import localize from "utils/localization";
import { getGalaxyInstance } from "app";
import { create, dialog } from "utils/data";

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
    this._init(options, bootstrapped);
}

// add logging shortcuts for this object
addLogging(GalaxyApp, "GalaxyApp");

// a debug flag can be set via local storage and made available during script/page loading
const DEBUGGING_KEY = "galaxy:debug";

const NAMESPACE_KEY = `${DEBUGGING_KEY}:namespaces`;
const FLATTEN_LOG_MESSAGES_KEY = `${DEBUGGING_KEY}:flatten`;

let localDebugging = false;
try {
    localDebugging = localStorage.getItem(DEBUGGING_KEY) == "true";
} catch (storageErr) {
    console.log(localize("localStorage not available for debug flag retrieval"));
}

/** initalize options and sub-components */
GalaxyApp.prototype._init = function (options, bootstrapped) {
    _.extend(this, Backbone.Events);
    if (localDebugging) {
        this.logger = console;
        console.debug("debugging galaxy:", "options:", options, "bootstrapped:", bootstrapped);
    }

    this._processOptions(options);
    this._initConfig(options.config || {});

    // Patch if this galaxy instance is replacing an existing one
    // _patchGalaxy depends on options.patchExisting
    // TODO: rethink this behavior
    const existingGalaxy = getGalaxyInstance();
    if (existingGalaxy) {
        this._patchGalaxy(existingGalaxy);
    }

    // add root and url parameters
    this.root = options.root || "/";
    this.params = options.params || {};
    this.session_csrf_token = options.session_csrf_token || null;

    this._initLogger(this.options.loggerOptions || {});
    // at this point, either logging or not and namespaces are enabled - chat it up
    this.debug("GalaxyApp.options: ", this.options);
    this.debug("GalaxyApp.config: ", this.config);
    this.debug("GalaxyApp.logger: ", this.logger);

    this._initLocale();
    this.debug("GalaxyApp.localize: ", this.localize);

    this.config = options.config || {};
    this.debug("GalaxyApp.config: ", this.config);

    this._initUser(options.user || {});
    this.debug("GalaxyApp.user: ", this.user);

    this._initUserLocale();
    this.debug("currentLocale: ", sessionStorage.getItem("currentLocale"));

    this._setUpListeners();
    this.trigger("ready", this);

    /* These shouldn't probably be here, but they need to be right now for
     * compatibility with external plugins */
    this.data = {};
    this.data.create = create;
    this.data.dialog = dialog;

    return this;
};

/** default options */
GalaxyApp.prototype.defaultOptions = {
    /** monkey patch attributes from existing Galaxy object? */
    patchExisting: true,
    /** root url of this app */
    root: "/",
    session_csrf_token: null,
};

/** filter to options present in defaultOptions (and default to them) */
GalaxyApp.prototype._processOptions = function _processOptions(options) {
    const defaults = this.defaultOptions;

    this.options = {};
    for (const k in defaults) {
        if (Object.prototype.hasOwnProperty.call(defaults, k)) {
            this.options[k] = Object.prototype.hasOwnProperty.call(options, k) ? options[k] : defaults[k];
        }
    }
    return this;
};

/** parse the config and any extra info derived from it */
GalaxyApp.prototype._initConfig = function _initConfig(config) {
    this.config = config;

    // give precendence to localdebugging for this setting
    this.config.debug = localDebugging || this.config.debug;

    return this;
};

// TODO: Remove this behavior when we can, it is kind of non-intuitive
GalaxyApp.prototype._patchGalaxy = function _patchGalaxy(patchWith) {
    // in case req or plain script tag order has created a prev. version of the Galaxy obj...
    if (this.options.patchExisting && patchWith) {
        // this.debug( 'found existing Galaxy object:', patchWith );
        // ...(for now) monkey patch any added attributes that the previous Galaxy may have had
        //TODO: move those attributes to more formal assignment in GalaxyApp
        for (const k in patchWith) {
            if (Object.prototype.hasOwnProperty.call(patchWith, k)) {
                // this.debug( '\t patching in ' + k + ' to Galaxy:', this[ k ] );
                this[k] = patchWith[k];
            }
        }
    }
};

/** set up the metrics logger (utils/metrics-logger) and pass loggerOptions */
GalaxyApp.prototype._initLogger = function _initLogger(loggerOptions) {
    // default to console logging at the debug level if the debug flag is set
    if (this.config.debug) {
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

    this.logger = new metricsLogger.MetricsLogger(loggerOptions);
    this.emit = {};
    ["log", "debug", "info", "warn", "error", "metric"].map((i) => {
        this.emit[i] = (data) => {
            this.logger.emit(i, arguments[0], Array.prototype.slice.call(arguments, 1));
        };
    });

    if (this.config.debug) {
        // add this logger to mvc's loggable mixin so that all models can use the logger
        BASE_MVC.LoggableMixin.logger = this.logger;
    }
    return this;
};

/** add the localize fn to this object and the window namespace (as '_l') */
GalaxyApp.prototype._initLocale = function _initLocale(options) {
    this.debug("_initLocale:", options);
    this.localize = localize;
    // add to window as global shortened alias
    // TODO: temporary - remove when can require for plugins
    window._l = this.localize;
    return this;
};

/** add the localize fn to this object and the window namespace (as '_l') */
GalaxyApp.prototype._initUserLocale = function _initUserLocale(options) {
    // Choose best locale
    const global_locale =
        this.config.default_locale && this.config.default_locale != "auto"
            ? this.config.default_locale.toLowerCase()
            : false;

    let extra_user_preferences = {};
    if (this.user && this.user.attributes.preferences && "extra_user_preferences" in this.user.attributes.preferences) {
        extra_user_preferences = JSON.parse(this.user.attributes.preferences.extra_user_preferences);
    }

    let user_locale =
        "localization|locale" in extra_user_preferences
            ? extra_user_preferences["localization|locale"].toLowerCase()
            : false;

    if (user_locale == "auto") {
        user_locale = false;
    }

    const nav_locale =
        typeof navigator === "undefined"
            ? "__root"
            : (navigator.language || navigator.userLanguage || "__root").toLowerCase();

    const locale = user_locale || nav_locale || global_locale;

    sessionStorage.setItem("currentLocale", locale);
};

/** set up the current user as a Backbone model (mvc/user/user-model) */
GalaxyApp.prototype._initUser = function _initUser(userJSON) {
    this.debug("_initUser:", userJSON);
    this.user = new userModel.User(userJSON);
    this.user.logger = this.logger;
    return this;
};

/** Set up DOM/jQuery/Backbone event listeners enabled for all pages */
GalaxyApp.prototype._setUpListeners = function _setUpListeners() {
    // hook to jq beforeSend to record the most recent ajax call and cache some data about it
    /** cached info about the last ajax call made through jQuery */
    this.lastAjax = {};
    $(document).bind("ajaxSend", (ev, xhr, options) => {
        let data = options.data;
        try {
            data = JSON.parse(data);
        } catch (err) {
            // data isn't JSON, skip.
        }

        this.lastAjax = {
            url: location.href.slice(0, -1) + options.url,
            data: data,
        };
        //TODO:?? we might somehow manage to *retry* ajax using either this hook or Backbone.sync
    });
    return this;
};

/** Turn debugging/console-output on/off by passing boolean. Pass nothing to get current setting. */
GalaxyApp.prototype.debugging = function _debugging(setting) {
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
        this.debuggingNamespaces(null);
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
    try {
        if (namespaces === undefined) {
            const csv = localStorage.getItem(NAMESPACE_KEY);
            return typeof csv === "string" ? csv.split(",") : [];
        } else if (namespaces === null) {
            localStorage.removeItem(NAMESPACE_KEY);
        } else {
            localStorage.setItem(NAMESPACE_KEY, namespaces);
        }
        const newSettings = this.debuggingNamespaces();
        if (this.logger) {
            this.logger.options.consoleNamespaceWhitelist = newSettings;
        }
        return newSettings;
    } catch (storageErr) {
        console.log(localize("localStorage not available for debug namespace retrieval"));
    }
};

/** string rep */
GalaxyApp.prototype.toString = function toString() {
    const userEmail = this.user ? this.user.get("email") || "(anonymous)" : "uninitialized";
    return `GalaxyApp(${userEmail})`;
};

// ============================================================================
export default {
    GalaxyApp: GalaxyApp,
};
