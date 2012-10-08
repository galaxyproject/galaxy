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
/**
 * Adds logging capabilities to your Models/Views
 *  can be used with plain browser console (or something more complex like an AJAX logger)
 *
 *  add to your models/views at the definition using chaining:
 *      var MyModel = BaseModel.extend( LoggableMixin ).extend({ // ... });
 * 
 *  or - more explicitly AFTER the definition:
 *      var MyModel = BaseModel.extend({
 *          logger  : console
 *          // ...
 *          this.log( '$#%& it! - broken already...' );
 *      })
 *      _.extend( MyModel.prototype, LoggableMixin )
 *
 * NOTE: currently only uses the console.debug log function (as opposed to debug, error, warn, etc.)
 */
var LoggableMixin = {
    // replace null with console (if available) to see all logs
    logger      : null,
    
    log : function(){
        return ( this.logger )?( this.logger.log.apply( this, arguments ) )
                              :( undefined );
    }
};


// =============================================================================
/** Global string localization object (and global short form alias)
 *      set with either:
 *          GalaxyLocalization.setLocalizedString( original, localized )
 *          GalaxyLocalization.setLocalizedString({ original1 : localized1, original2 : localized2 })
 *      get with either:
 *          _l( original )
 */
//TODO: move to Galaxy.Localization (maybe galaxy.base.js)
var GalaxyLocalization = jQuery.extend( {}, {
    ALIAS_NAME : '_l',
    localizedStrings : {},
    
    setLocalizedString : function( str_or_obj, localizedString ){
        // pass in either two strings (english, translated) or an obj (map) of english : translated attributes
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
    
    localize : function( strToLocalize ){
        //console.debug( this + '.localize:', strToLocalize );
        // return the localized version if it's there, the strToLocalize if not
        var retStr = strToLocalize;
        if( _.has( this.localizedStrings, strToLocalize ) ){
            //console.debug( 'found' );
            retStr = this.localizedStrings[ strToLocalize ];
        }
        //console.debug( 'returning:', retStr );
        return retStr;
    },
    
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
 *  @class PersistantStorage
 *      persistant storage adapter to:
 *          provide an easy interface to object based storage using method chaining
 *          allow easy change of the storage engine used (h5's local storage?)
 *
 *  @param {String} storageKey : the key the storage engine will place the storage object under
 *  @param {Object} storageDefaults : [optional] initial object to set up storage with
 *
 *  @example :
 *  HistoryPanel.storage = new PersistanStorage( HistoryPanel.toString(), { visibleItems, {} })
 *  itemView.bind( 'toggleBodyVisibility', function( id, visible ){
 *      if( visible ){
 *          HistoryPanel.storage.get( 'visibleItems' ).set( id, true );
 *      } else {
 *          HistoryPanel.storage.get( 'visibleItems' ).deleteKey( id );
 *      }
 *  });
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

    // recursion helper for method chaining access
    var StorageRecursionHelper = function( data, parent ){
        //console.debug( 'new StorageRecursionHelper. data:', data );
        data = data || {};
        parent = parent || null;
        return {
            // get a value from the storage obj named 'key',
            //  if it's an object - return a new StorageRecursionHelper wrapped around it
            //  if it's something simpler - return the value
            //  if this isn't passed a key - return the data at this level of recursion
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
            // set a value on the current data - then pass up to top to save current entire object in storage
            set : function( key, value ){
                //TODO: add parameterless variation setting the data somehow
                //  ??: difficult bc of obj by ref, closure
                //console.debug( this + '.set', key, value );
                data[ key ] = value;
                this.save();
                return this;
            },
            // remove a key at this level - then save entire (as 'set' above)
            deleteKey : function( key ){
                //console.debug( this + '.deleteKey', key );
                delete data[ key ];
                this.save();
                return this;
            },
            // pass up the recursion chain (see below for base case)
            save : function(){
                //console.debug( this + '.save', parent );
                return parent.save();
            },
            toString : function(){
                return ( 'StorageRecursionHelper(' + data + ')' );
            }
        };
    };

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
    // the base case for save()'s upward recursion - save everything to storage
    returnedStorage.save = function( newData ){
        //console.debug( returnedStorage, '.save:', JSON.stringify( returnedStorage.get() ) );
        STORAGE_ENGINE_SETTER( storageKey, returnedStorage.get() );
    };
    // delete function to remove the base data object from the storageEngine
    returnedStorage.destroy = function(){
        //console.debug( returnedStorage, '.destroy:' );
        STORAGE_ENGINE_KEY_DELETER( storageKey );
    };
    returnedStorage.toString = function(){ return 'PersistantStorage(' + data + ')'; };
    
    return returnedStorage;
};

