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
 *      var MyModel = Backbone.Model.extend( LoggableMixin ).extend({ // ... });
 * 
 *  // or - more explicitly AFTER the definition:
 *      var MyModel = Backbone.Model.extend({
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
            var log = this.logger.log;
            if( typeof this.logger.log === 'object' ){
                log = Function.prototype.bind.call( this.logger.log, this.logger );
            }
            return log.apply( this.logger, arguments );
        }
        return undefined;
    }
};


//==============================================================================
/** Backbone model that syncs to the browser's sessionStorage API.
 */
var SessionStorageModel = Backbone.Model.extend({
    initialize : function( initialAttrs ){
        // create unique id if none provided
        initialAttrs.id = ( !_.isString( initialAttrs.id ) )?( _.uniqueId() ):( initialAttrs.id );
        this.id = initialAttrs.id;

        // load existing from storage (if any), clear any attrs set by bbone before init is called,
        //  layer initial over existing and defaults, and save
        var existing = ( !this.isNew() )?( this._read( this ) ):( {} );
        this.clear({ silent: true });
        this.save( _.extend( {}, this.defaults, existing, initialAttrs ), { silent: true });

        // save on any change to it immediately
        this.on( 'change', function(){
            this.save();
        });
    },

    /** override of bbone sync to save to sessionStorage rather than REST
     *      bbone options (success, errror, etc.) should still apply
     */
    sync : function( method, model, options ){
        if( !options.silent ){
            model.trigger( 'request', model, {}, options );
        }
        var returned;
        switch( method ){
            case 'create'   : returned = this._create( model ); break;
            case 'read'     : returned = this._read( model );   break;
            case 'update'   : returned = this._update( model ); break;
            case 'delete'   : returned = this._delete( model ); break;
        }
        if( returned !== undefined || returned !== null ){
            if( options.success ){ options.success(); }
        } else {
            if( options.error ){ options.error(); }
        }
        return returned;
    },

    /** set storage to the stringified item */
    _create : function( model ){
        var json = model.toJSON(),
            set = sessionStorage.setItem( model.id, JSON.stringify( json ) );
        return ( set === null )?( set ):( json );
    },

    /** read and parse json from storage */
    _read : function( model ){
        return JSON.parse( sessionStorage.getItem( model.id ) );
    },

    /** set storage to the item (alias to create) */
    _update : function( model ){
        return model._create( model );
    },

    /** remove the item from storage */
    _delete : function( model ){
        return sessionStorage.removeItem( model.id );
    },

    /** T/F whether sessionStorage contains the model's id (data is present) */
    isNew : function(){
        return !sessionStorage.hasOwnProperty( this.id );
    },

    _log : function(){
        return JSON.stringify( this.toJSON(), null, '  ' );
    },
    toString : function(){
        return 'SessionStorageModel(' + this.id + ')';
    }

});
(function(){
    SessionStorageModel.prototype = _.omit( SessionStorageModel.prototype, 'url', 'urlRoot' );
}());


//==============================================================================
var HiddenUntilActivatedViewMixin = /** @lends hiddenUntilActivatedMixin# */{
//TODO: since this is a mixin, consider moving toggle, hidden into HUAVOptions

    /** */
    hiddenUntilActivated : function( $activator, options ){
        // call this in your view's initialize fn
        options = options || {};
        this.HUAVOptions = {
            $elementShown   : this.$el,
            showFn          : jQuery.prototype.toggle,
            showSpeed       : 'fast'
        };
        _.extend( this.HUAVOptions, options || {});
        /** has this been shown already (and onshowFirstTime called)? */
        this.HUAVOptions.hasBeenShown = this.HUAVOptions.$elementShown.is( ':visible' );
        this.hidden = this.isHidden();

        if( $activator ){
            var mixin = this;
            $activator.on( 'click', function( ev ){
                mixin.toggle( mixin.HUAVOptions.showSpeed );
            });
        }
    },

    isHidden : function(){
        return ( this.HUAVOptions.$elementShown.is( ':hidden' ) );
    },

    /** */
    toggle : function(){
        // can be called manually as well with normal toggle arguments
        //TODO: better as a callback (when the show/hide is actually done)
        // show
        if( this.hidden ){
            // fire the optional fns on the first/each showing - good for render()
            if( !this.HUAVOptions.hasBeenShown ){
                if( _.isFunction( this.HUAVOptions.onshowFirstTime ) ){
                    this.HUAVOptions.hasBeenShown = true;
                    this.HUAVOptions.onshowFirstTime.call( this );
                }
            }
            if( _.isFunction( this.HUAVOptions.onshow ) ){
                this.HUAVOptions.onshow.call( this );
                this.trigger( 'hiddenUntilActivated:shown', this );
            }
            this.hidden = false;

        // hide
        } else {
            if( _.isFunction( this.HUAVOptions.onhide ) ){
                this.HUAVOptions.onhide.call( this );
                this.trigger( 'hiddenUntilActivated:hidden', this );
            }
            this.hidden = true;
        }
        return this.HUAVOptions.showFn.apply( this.HUAVOptions.$elementShown, arguments );
    }
};
