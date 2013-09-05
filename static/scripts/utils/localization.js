// =============================================================================
/** @class string localizer (and global short form alias)
 *
 *  @example
 *  // set with either:
 *      GalaxyLocalization.setLocalizedString( original, localized )
 *      GalaxyLocalization.setLocalizedString({ original1 : localized1, original2 : localized2 })
 *  // get with either:
 *      GalaxyLocalization.localize( string )
 *      _l( string )
 *
 *  @constructs
 */
//TODO: move to Galaxy.Localization (maybe galaxy.base.js)
var GalaxyLocalization = jQuery.extend( {}, {
    /** shortened, alias reference to GalaxyLocalization.localize */
    ALIAS_NAME : '_l',
    /** map of available localized strings (english -> localized) */
    localizedStrings : {},

    /** Set a single English string -> localized string association, or set an entire map of those associations
     *  @param {String or Object} str_or_obj english (key) string or a map of english -> localized strings
     *  @param {String} localized string if str_or_obj was a string
     */
    setLocalizedString : function( str_or_obj, localizedString ){
        //console.debug( this + '.setLocalizedString:', str_or_obj, localizedString );
        var self = this;

        // DRY non-duplicate assignment function
        var setStringIfNotDuplicate = function( original, localized ){
            // do not set if identical - strcmp expensive but should only happen once per page per word
            if( original !== localized ){
                self.localizedStrings[ original ] = localized;
            }
        };

        if( jQuery.type( str_or_obj ) === "string" ){
            setStringIfNotDuplicate( str_or_obj, localizedString );

        } else if( jQuery.type( str_or_obj ) === "object" ){
            jQuery.each( str_or_obj, function( key, val ){
                //console.debug( 'key=>val', key, '=>', val );
                // could recurse here but no reason
                setStringIfNotDuplicate( key, val );
            });

        } else {
            throw( 'Localization.setLocalizedString needs either a string or object as the first argument,' +
                   ' given: ' + str_or_obj );
        }
    },

    /** Attempt to get a localized string for strToLocalize. If not found, return the original strToLocalize.
     * @param {String} strToLocalize the string to localize
     * @returns either the localized string if found or strToLocalize if not found
     */
    localize : function( strToLocalize ){
        //console.debug( this + '.localize:', strToLocalize );

        //// uncomment this section to cache strings that need to be localized but haven't been
        //if( !_.has( this.localizedStrings, strToLocalize ) ){
        //    //console.debug( 'localization NOT found:', strToLocalize );
        //    if( !this.nonLocalized ){ this.nonLocalized = {}; }
        //    this.nonLocalized[ strToLocalize ] = false;
        //}

        // return the localized version if it's there, the strToLocalize if not
        return this.localizedStrings[ strToLocalize ] || strToLocalize;
    },

    /** Add the localization function alias (GalaxyLocalization.ALIAS_NAME) to the given namespace.
     * @param {Object} namespace    the object/namespace to add the alias to
     */
    addAliasToNamespace : function( namespace ){
        namespace[ GalaxyLocalization.ALIAS_NAME ] = function( str ){ return GalaxyLocalization.localize( str ); };
    },

    /** String representation. */
    toString : function(){ return 'GalaxyLocalization'; }
});

GalaxyLocalization.addAliasToNamespace( window );
