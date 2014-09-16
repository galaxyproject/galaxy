define([
    'i18n!nls/locale'
], function( localeStrings ){
// =============================================================================
/** Attempt to get a localized string for strToLocalize. If not found, return
 *      the original strToLocalize.
 * @param {String} strToLocalize the string to localize
 * @returns either the localized string if found or strToLocalize if not found
 */
var localize = function( strToLocalize ){
    //console.debug( this + '.localize:', strToLocalize );

    // cache strings that need to be localized but haven't been?
    if( localize.cacheNonLocalized && !localeStrings.hasOwnProperty( strToLocalize ) ){
        //console.debug( 'localization NOT found:', strToLocalize );
        // add nonCached as hash directly to this function
        if( !localize.nonLocalized ){ localize.nonLocalized = {}; }
        localize.nonLocalized[ strToLocalize ] = navigator.language;
    }
    // return the localized version from the closure if it's there, the strToLocalize if not
    return localeStrings[ strToLocalize ] || strToLocalize;
};
localize.cacheNonLocalized = false;


// =============================================================================
    return localize;
});
