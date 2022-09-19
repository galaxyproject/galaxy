// eslint-disable-next-line no-undef
define(["i18n!nls/locale"], function (localeStrings) {
    /**
     * @param {String} strToLocalize
     * @returns
     */
    var localize = function (strToLocalize) {
        return localeStrings[strToLocalize] || strToLocalize;
    };

    localize.cacheNonLocalized = false;

    localize._setUserLocale = function _setUserLocale(user, config) {
        const global_locale =
            config.default_locale && config.default_locale != "auto" ? config.default_locale.toLowerCase() : false;

        let extra_user_preferences = {};
        if (user && user.attributes.preferences && "extra_user_preferences" in user.attributes.preferences) {
            extra_user_preferences = JSON.parse(user.attributes.preferences.extra_user_preferences);
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

    localize._getUserLocale = function _getUserLocale(user, config) {
        let locale = null;
        if (Object.prototype.hasOwnProperty.call(localeStrings, "__root")) {
            locale = sessionStorage.getItem("currentLocale");
            if (locale) {
                localeStrings =
                    localeStrings["__" + locale] || localeStrings["__" + locale.split("-")[0]] || localeStrings.__root;
            }
        }
        return locale;
    };

    return localize;
});
