/**
 * Simple base model for any visible element. Includes useful attributes and ability 
 * to set and track visibility.
 */
var BaseModel = Backbone.RelationalModel.extend({
    defaults: {
        name: null,
        hidden: false
    },
    
    show: function() {
        this.set("hidden", false);
    },
    
    hide: function() {
        this.set("hidden", true);
    },
    
    is_visible: function() {
        return !this.attributes.hidden;
    }
});


/**
 * Base view that handles visibility based on model's hidden attribute.
 */
var BaseView = Backbone.View.extend({
    
    initialize: function() {
        this.model.on("change:hidden", this.update_visible, this);
        this.update_visible();
    },
    
    update_visible: function() {
        if( this.model.attributes.hidden ){
            this.$el.hide();
        } else {
            this.$el.show();
        }
    }    
});


//==============================================================================
/** @class Mixin to add logging capabilities to an object.
 *      Designed to allow switching an objects log output off/on at one central
 *      statement. Can be used with plain browser console (or something more
 *      complex like an AJAX logger).
 *  <br />NOTE: currently only uses the console.debug log function
 *  (as opposed to debug, error, warn, etc.)
 *  @name LoggableMixin
 *
 *  @example
 *  // Add to your models/views at the definition using chaining:
 *      var MyModel = BaseModel.extend( LoggableMixin ).extend({ // ... });
 * 
 *  // or - more explicitly AFTER the definition:
 *      var MyModel = BaseModel.extend({
 *          logger  : console
 *          // ...
 *          this.log( '$#%& it! - broken already...' );
 *      })
 *      _.extend( MyModel.prototype, LoggableMixin )
 *
 */
var LoggableMixin =  /** @lends LoggableMixin# */{

    /** The logging object whose log function will be used to output
     *      messages. Null will supress all logging. Commonly set to console.
     */
    // replace null with console (if available) to see all logs
    logger      : null,
    
    /** Output log messages/arguments to logger.
     *  @param {Arguments} ... (this function is variadic)
     *  @returns undefined if not this.logger
     */
    log : function(){
        if( this.logger ){
            return this.logger.log.apply( this.logger, arguments );
        }
        return undefined;
    }
};


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
    
    /** String representation. */
    toString : function(){ return 'GalaxyLocalization'; }
});

// global localization alias
window[ GalaxyLocalization.ALIAS_NAME ] = function( str ){ return GalaxyLocalization.localize( str ); };

//TEST: setLocalizedString( string, string ), _l( string )
//TEST: setLocalizedString( hash ), _l( string )
//TEST: setLocalizedString( string === string ), _l( string )
//TEST: _l( non assigned string )


//==============================================================================
/**
 *  @class persistant storage adapter.
 *      Provides an easy interface to object based storage using method chaining.
 *      Allows easy change of the storage engine used (h5's local storage?).
 *  @augments StorageRecursionHelper
 *
 *  @param {String} storageKey : the key the storage engine will place the storage object under
 *  @param {Object} storageDefaults : [optional] initial object to set up storage with
 *
 *  @example
 *  // example of construction and use
 *  HistoryPanel.storage = new PersistanStorage( HistoryPanel.toString(), { visibleItems, {} });
 *  itemView.bind( 'toggleBodyVisibility', function( id, visible ){
 *      if( visible ){
 *          HistoryPanel.storage.get( 'visibleItems' ).set( id, true );
 *      } else {
 *          HistoryPanel.storage.get( 'visibleItems' ).deleteKey( id );
 *      }
 *  });
 *  @constructor
 */
var PersistantStorage = function( storageKey, storageDefaults ){
    if( !storageKey ){
        throw( "PersistantStorage needs storageKey argument" );
    }
    storageDefaults = storageDefaults || {};

    // ~constants for the current engine
    //TODO:?? this would be greatly simplified if we're IE9+ only (setters/getters)
    var STORAGE_ENGINE_GETTER       = jQuery.jStorage.get,
        STORAGE_ENGINE_SETTER       = jQuery.jStorage.set,
        STORAGE_ENGINE_KEY_DELETER  = jQuery.jStorage.deleteKey;

    /** Inner, recursive, private class for method chaining access.
     *  @name StorageRecursionHelper
     *  @constructor
     */
    function StorageRecursionHelper( data, parent ){
        //console.debug( 'new StorageRecursionHelper. data:', data );
        data = data || {};
        parent = parent || null;

        return /** @lends StorageRecursionHelper.prototype */{
            /** get a value from the storage obj named 'key',
             *  if it's an object - return a new StorageRecursionHelper wrapped around it
             *  if it's something simpler - return the value
             *  if this isn't passed a key - return the data at this level of recursion
             */
            get : function( key ){
                //console.debug( this + '.get', key );
                if( key === undefined ){
                    return data;
                } else if( data.hasOwnProperty( key ) ){
                    return ( jQuery.type( data[ key ] ) === 'object' )?
                        ( new StorageRecursionHelper( data[ key ], this ) )
                        :( data[ key ] );
                }
                return undefined;
            },
            /** get the underlying data based on this key */
            // set a value on the current data - then pass up to top to save current entire object in storage
            set : function( key, value ){
                //TODO: add parameterless variation setting the data somehow
                //  ??: difficult bc of obj by ref, closure
                //console.debug( this + '.set', key, value );
                data[ key ] = value;
                this._save();
                return this;
            },
            // remove a key at this level - then save entire (as 'set' above)
            deleteKey : function( key ){
                //console.debug( this + '.deleteKey', key );
                delete data[ key ];
                this._save();
                return this;
            },
            // pass up the recursion chain (see below for base case)
            _save : function(){
                //console.debug( this + '.save', parent );
                return parent._save();
            },
            toString : function(){
                return ( 'StorageRecursionHelper(' + data + ')' );
            }
        };
    }

    //??: more readable to make another class?
    var returnedStorage = {};
        // attempt to get starting data from engine...
        data = STORAGE_ENGINE_GETTER( storageKey );

    // ...if that fails, use the defaults (and store them)
    if( data === null ){
        //console.debug( 'no previous data. using defaults...' );
        data = jQuery.extend( true, {}, storageDefaults );
        STORAGE_ENGINE_SETTER( storageKey, data );
    }

    // the object returned by this constructor will be a modified StorageRecursionHelper
    returnedStorage = new StorageRecursionHelper( data );

    jQuery.extend( returnedStorage, /**  @lends PersistantStorage.prototype */{
        /** The base case for save()'s upward recursion - save everything to storage.
         *  @private
         *  @param {Any} newData data object to save to storage
         */
        _save : function( newData ){
            //console.debug( returnedStorage, '._save:', JSON.stringify( returnedStorage.get() ) );
            return STORAGE_ENGINE_SETTER( storageKey, returnedStorage.get() );
        },
        /** Delete function to remove the entire base data object from the storageEngine.
         */
        destroy : function(){
            //console.debug( returnedStorage, '.destroy:' );
            return STORAGE_ENGINE_KEY_DELETER( storageKey );
        },
        /** String representation.
         */
        toString : function(){ return 'PersistantStorage(' + storageKey + ')'; }
    });
    
    return returnedStorage;
};
