define([
    'i18n!nls/locale'
], function( localeStrings ){

// =============================================================================
/** Simple string replacement localization. Language data from galaxy/scripts/nls */

// support both requirejs and webpack from the same file
// if loaded via webpack, it will be a different format than via requirejs - convert
if( localeStrings.hasOwnProperty( '__root' ) ){
    //console.debug( 'amdi18n+webpack localization for ' + locale + ' loaded' );
    var locale = (
        typeof navigator === 'undefined' ? '__root'
            : ( navigator.language || navigator.userLanguage || '__root' ).toLowerCase()
    );
    localeStrings = localeStrings[ '__' + locale ] || localeStrings[ '__' + locale.split('-')[0] ] ||localeStrings.__root;

// } else {
//     console.debug( 'i18n+requirejs localization for ' + locale + ' loaded' );
}
// TODO: when this is no longer necessary remove this, i18n.js, and the resolveModule in config

// -----------------------------------------------------------------------------
/** Attempt to get a localized string for strToLocalize. If not found, return
 *      the original strToLocalize.
 * @param {String} strToLocalize the string to localize
 * @returns either the localized string if found or strToLocalize if not found
 */
var localize = function( strToLocalize ){
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
    return localeStrings[ strToLocalize ] || strToLocalize;
};
localize.cacheNonLocalized = false;


// =============================================================================
    return localize;
});
