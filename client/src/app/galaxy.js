import Backbone from "backbone";
import $ from "jquery";
import _ from "underscore";
import { create, dialog } from "utils/data";
import { _getUserLocale, _setUserLocale, localize } from "utils/localization";

import { getGalaxyInstance } from "./singleton";
import userModel from "./user-model";

// ============================================================================
/** Base galaxy client-side application.
 *      Iniitializes:
 *          localize    : the string localizer
 *          config      : the current configuration (any k/v in
 *              galaxy.ini available from the configuration API)
 *          user        : the current user (as a mvc/user/user-model)
 */
export function GalaxyApp(options = {}, bootstrapped = {}) {
    this._init(options, bootstrapped);
}

/** initalize options and sub-components */
GalaxyApp.prototype._init = function (options, bootstrapped) {
    _.extend(this, Backbone.Events);

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

    this._initLocale();

    this.config = options.config || {};

    this._initUser(options.user || {});

    _setUserLocale(this.user, this.config);
    _getUserLocale();
    console.debug("currentLocale: ", sessionStorage.getItem("currentLocale"));

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

    return this;
};

// TODO: Remove this behavior when we can, it is kind of non-intuitive
GalaxyApp.prototype._patchGalaxy = function _patchGalaxy(patchWith) {
    // in case req or plain script tag order has created a prev. version of the Galaxy obj...
    if (this.options.patchExisting && patchWith) {
        // console.debug( 'found existing Galaxy object:', patchWith );
        // ...(for now) monkey patch any added attributes that the previous Galaxy may have had
        //TODO: move those attributes to more formal assignment in GalaxyApp
        for (const k in patchWith) {
            if (Object.prototype.hasOwnProperty.call(patchWith, k)) {
                // console.debug( '\t patching in ' + k + ' to Galaxy:', this[ k ] );
                this[k] = patchWith[k];
            }
        }
    }
};

/** add the localize fn to this object and the window namespace (as '_l') */
GalaxyApp.prototype._initLocale = function _initLocale() {
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
    console.debug("_initUser:", userJSON);
    this.user = new userModel.User(userJSON);
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

/** string rep */
GalaxyApp.prototype.toString = function toString() {
    const userEmail = this.user ? this.user.get("email") || "(anonymous)" : "uninitialized";
    return `GalaxyApp(${userEmail})`;
};

// ============================================================================
export default {
    GalaxyApp: GalaxyApp,
};
