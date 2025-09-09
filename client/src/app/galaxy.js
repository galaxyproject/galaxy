import { create, dialog } from "utils/data";
import { _getUserLocale, _setUserLocale, localize } from "utils/localization";

import { getGalaxyInstance } from "./singleton";
import userModel from "./user-model";

// ============================================================================
/** Base galaxy client-side application. */
export function GalaxyApp(options = {}, bootstrapped = {}) {
    this._init(options, bootstrapped);
}

/** initalize options and sub-components */
GalaxyApp.prototype._init = function (options, bootstrapped) {
    this._processOptions(options);
    this._initConfig(options.config || {});

    const existingGalaxy = getGalaxyInstance();
    if (existingGalaxy) {
        this._patchGalaxy(existingGalaxy);
    }

    this.root = options.root || "/";
    this.params = options.params || {};
    this.session_csrf_token = options.session_csrf_token || null;

    this._initLocale();
    this.config = options.config || {};
    this._initUser(options.user || {});

    _setUserLocale(this.user, this.config);
    _getUserLocale();
    console.debug("currentLocale: ", sessionStorage.getItem("currentLocale"));

    this.data = {};
    const galaxy = this;
    /* These shouldn't probably be here, but they need to be right now for
     * compatibility with external plugins */
    this.data.create = (...args) => create(galaxy, ...args);
    this.data.dialog = (...args) => dialog(galaxy, ...args);

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
GalaxyApp.prototype._processOptions = function (options) {
    const defaults = this.defaultOptions;
    this.options = {};
    for (const k in defaults) {
        if (Object.prototype.hasOwnProperty.call(defaults, k)) {
            this.options[k] = Object.prototype.hasOwnProperty.call(options, k) ? options[k] : defaults[k];
        }
    }
    return this;
};

/** parse the config */
GalaxyApp.prototype._initConfig = function (config) {
    this.config = config;
    return this;
};

GalaxyApp.prototype._patchGalaxy = function (patchWith) {
    if (this.options.patchExisting && patchWith) {
        for (const k in patchWith) {
            if (Object.prototype.hasOwnProperty.call(patchWith, k)) {
                this[k] = patchWith[k];
            }
        }
    }
};

GalaxyApp.prototype._initLocale = function () {
    this.localize = localize;
    window._l = this.localize;
    return this;
};

GalaxyApp.prototype._initUserLocale = function () {
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

GalaxyApp.prototype._initUser = function (userJSON) {
    console.debug("_initUser:", userJSON);
    this.user = new userModel.User(userJSON);
    return this;
};

GalaxyApp.prototype.toString = function () {
    const userEmail = this.user ? this.user.get("email") || "(anonymous)" : "uninitialized";
    return `GalaxyApp(${userEmail})`;
};

// ============================================================================
export default {
    GalaxyApp: GalaxyApp,
};
