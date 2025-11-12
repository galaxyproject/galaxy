import { create, dialog } from "@/utils/data";
import { _getUserLocale, _setUserLocale, localize } from "@/utils/localization";

import userModel from "./user-model";

const DEFAULT_OPTIONS = {
    patchExisting: true,
    root: "/",
    session_csrf_token: null,
};

export class GalaxyApp {
    constructor(options = {}, bootstrapped = {}) {
        this._processOptions(options);
        this._initConfig(options.config || {});

        this.root = options.root || "/";
        this.params = options.params || {};
        this.session_csrf_token = options.session_csrf_token || null;

        this._initLocale();
        this.config = options.config || {};
        this._initUser(options.user || {});

        _setUserLocale(this.user, this.config);
        _getUserLocale();
        console.debug("currentLocale:", sessionStorage.getItem("currentLocale"));

        this.data = {};
        this.data.create = (...args) => create(this, ...args);
        this.data.dialog = (...args) => dialog(this, ...args);
    }

    _processOptions(options) {
        const defaults = DEFAULT_OPTIONS;
        this.options = {};
        for (const k in defaults) {
            if (Object.prototype.hasOwnProperty.call(defaults, k)) {
                this.options[k] = Object.prototype.hasOwnProperty.call(options, k) ? options[k] : defaults[k];
            }
        }
    }

    _initConfig(config) {
        this.config = config;
    }

    _initLocale() {
        this.localize = localize;
        window._l = this.localize;
    }

    _initUserLocale() {
        const globalLocale =
            this.config.default_locale && this.config.default_locale != "auto"
                ? this.config.default_locale.toLowerCase()
                : false;

        let extraUserPrefs = {};
        if (
            this.user &&
            this.user.attributes.preferences &&
            "extra_user_preferences" in this.user.attributes.preferences
        ) {
            extraUserPrefs = JSON.parse(this.user.attributes.preferences.extra_user_preferences);
        }

        let userLocale =
            "localization|locale" in extraUserPrefs ? extraUserPrefs["localization|locale"].toLowerCase() : false;

        if (userLocale == "auto") {
            userLocale = false;
        }

        const navLocale =
            typeof navigator === "undefined"
                ? "__root"
                : (navigator.language || navigator.userLanguage || "__root").toLowerCase();

        const locale = userLocale || navLocale || globalLocale;
        sessionStorage.setItem("currentLocale", locale);
    }

    _initUser(userJSON) {
        console.debug("_initUser:", userJSON);
        this.user = new userModel.User(userJSON);
    }

    toString() {
        const email = this.user ? this.user.get("email") || "(anonymous)" : "uninitialized";
        return `GalaxyApp(${email})`;
    }
}
