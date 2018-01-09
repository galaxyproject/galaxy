define(["i18n!nls/locale"], function(localeStrings) {
    // =============================================================================
    /** Simple string replacement localization. Language data from galaxy/scripts/nls */

    function onloadLocaleConfig() {
        // Wait until Galaxy.config is loaded.
        if (Galaxy.config && localeStrings.hasOwnProperty("__root")) {
            var global_locale = Galaxy.config.default_locale ? Galaxy.config.default_locale.toLowerCase() : false;

            var extra_user_preferences = {};
            if (Galaxy.user && Galaxy.user.attributes.preferences && 'extra_user_preferences' in Galaxy.user.attributes.preferences) {
                extra_user_preferences = JSON.parse(Galaxy.user.attributes.preferences.extra_user_preferences);
            }

            var user_locale = 'localization|locale' in extra_user_preferences ? extra_user_preferences['localization|locale'].toLowerCase() : false;

            var nav_locale =
                typeof navigator === "undefined"
                    ? "__root"
                    : (navigator.language || navigator.userLanguage || "__root").toLowerCase();

            console.debug('global_locale: ' + global_locale);
            console.debug('user_locale: ' + user_locale);
            console.debug('nav_locale: ' + nav_locale);

            localeStrings =
                localeStrings["__" + user_locale] || localeStrings["__" + global_locale] || localeStrings["__" + nav_locale] || localeStrings["__" + nav_locale.split("-")[0]] || localeStrings.__root;
        } else {
            setTimeout(onloadLocaleConfig, 100);
        }
    }
    onloadLocaleConfig();

    // TODO: when this is no longer necessary remove this, i18n.js, and the resolveModule in config

    // -----------------------------------------------------------------------------
    /** Attempt to get a localized string for strToLocalize. If not found, return
     *      the original strToLocalize.
     * @param {String} strToLocalize the string to localize
     * @returns either the localized string if found or strToLocalize if not found
     */
    var localize = function(strToLocalize) {
        // console.debug( 'amdi18n.localize:', strToLocalize, '->', localeStrings[ strToLocalize ] || strToLocalize );

        // //TODO: conditional compile on DEBUG flag
        // // cache strings that need to be localized but haven't been?
        // if( localize.cacheNonLocalized && !localeStrings.hasOwnProperty( strToLocalize ) ){
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

    // =============================================================================
    return localize;
});
