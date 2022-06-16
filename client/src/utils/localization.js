// eslint-disable-next-line no-undef
define(["i18n!nls/locale"], function (localeStrings) {
    // -----------------------------------------------------------------------------
    /** Attempt to get a localized string for strToLocalize. If not found, return
     *      the original strToLocalize.
     * @param {String} strToLocalize the string to localize
     * @returns either the localized string if found or strToLocalize if not found
     */
    var localize = function (strToLocalize) {
        // console.debug( 'amdi18n.localize:', strToLocalize, '->', localeStrings[ strToLocalize ] || strToLocalize );

        // //TODO: conditional compile on DEBUG flag
        // // cache strings that need to be localized but haven't been?
        // if( localize.cacheNonLocalized && !Object.prototype.hasOwnProperty.call(localeStrings,  strToLocalize ) ){
        //     // console.debug( 'localization NOT found:', strToLocalize );
        //     // add nonCached as hash directly to this function
        //     localize.nonLocalized = localize.nonLocalized || {};
        //     localize.nonLocalized[ locale ] = localize.nonLocalized[ locale ] || {};
        //     localize.nonLocalized[ locale ][ strToLocalize ] = false;
        // }

        // return the localized version from the closure if it's there, the strToLocalize if not
        return localeStrings[strToLocalize] || strToLocalize;
    };
    localize.cacheNonLocalized = false;

    localize._setUserLocale = function _setUserLocale(user, config) {
        // Choose best locale
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
    // =============================================================================
    /** Simple string replacement localization. Language data from src/nls */

    localize._getUserLocale = function _getUserLocale(user, config) {
        let locale = null;
        if (Object.prototype.hasOwnProperty.call(localeStrings, "__root")) {
            //console.debug( 'amdi18n+webpack localization for ' + locale + ' loaded' );

            locale = sessionStorage.getItem("currentLocale");

            if (locale) {
                localeStrings =
                    localeStrings["__" + locale] || localeStrings["__" + locale.split("-")[0]] || localeStrings.__root;
            }

            // } else {
            //     console.debug( 'i18n+requirejs localization for ' + locale + ' loaded' );
        }
        return locale;
        // TODO: when this is no longer necessary remove this, i18n.js, and the resolveModule in config
    };

    // =============================================================================
    return localize;
});
