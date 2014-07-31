define([
    'utils/add-logging'
], function( addLogging ){
//ASSUMES: backbone
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
    logger       : null,
    _logNamespace : '?',
    
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
addLogging( LoggableMixin );


//==============================================================================
/** Backbone model that syncs to the browser's sessionStorage API.
 */
var SessionStorageModel = Backbone.Model.extend({
    initialize : function( initialAttrs ){
        // check for sessionStorage and error if no id is provided
        this._checkEnabledSessionStorage();
        if( !initialAttrs.id ){
            throw new Error( 'SessionStorageModel requires an id in the initial attributes' );
        }
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

    _checkEnabledSessionStorage : function(){
        try {
            return sessionStorage.length;
        } catch( err ){
            alert( 'Please enable cookies in your browser for this Galaxy site' );
            return false;
        }
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

//==============================================================================
function mixin( mixinHash1, /* mixinHash2, etc: ... variadic */ propsHash ){
    // usage: var NewModel = Something.extend( mixin( MyMixinA, MyMixinB, { ... }) );
    //NOTE: this does not combine any hashes (like events, etc.) and you're expected to handle that

    // simple reversal of param order on _.defaults() - to show mixins in top of definition
    var args = Array.prototype.slice.call( arguments, 0 ),
        lastArg = args.pop();
    args.unshift( lastArg );
    return _.defaults.apply( _, args );
}


//==============================================================================
var ExpandableView = Backbone.View.extend( LoggableMixin ).extend({
//TODO: Although the reasoning behind them is different, this shares a lot with HiddenUntilActivated above: combine them
    //PRECONDITION: model must have method hasDetails

    initialize : function( attributes ){
        /** are the details of this view expanded/shown or not? */
        this.expanded   = attributes.expanded || false;
        this.log( '\t expanded:', this.expanded );
    },

    // ........................................................................ render main
//TODO: for lack of a better place, add rendering logic here
    fxSpeed : 'fast',

    /** Render this content, set up ui.
     *  @param {Integer} speed   the speed of the render
     *  @fires rendered when rendered
     *  @fires rendered:ready when first rendered and NO running HDAs
     *  @returns {Object} this HDABaseView
     */
    render : function( speed ){
        var $newRender = this._buildNewRender();
        this._queueNewRender( $newRender, speed );
        return this;
    },

    _buildNewRender : function(){
        // create a new render using a skeleton template, render title buttons, render body, and set up events, etc.
        var $newRender = $( this.templates.skeleton( this.model.toJSON() ) );
        if( this.expanded ){
            $newRender.children( '.details' ).replaceWith( this._renderDetails() );
        }
        this._setUpBehaviors( $newRender );
        return $newRender;
    },

    /** Fade out the old el, replace with new dom, then fade in.
     *  @param {Boolean} fade   whether or not to fade out/in when re-rendering
     *  @fires rendered when rendered
     *  @fires rendered:ready when first rendered and NO running HDAs
     */
    _queueNewRender : function( $newRender, speed ) {
        speed = ( speed === undefined )?( this.fxSpeed ):( speed );
        var view = this;

        $( view ).queue( 'fx', [
            function( next ){ this.$el.fadeOut( speed, next ); },
            function( next ){
                view._swapNewRender( $newRender );
                next();
            },
            function( next ){ this.$el.fadeIn( speed, next ); },
            function( next ){
                this.trigger( 'rendered', view );
                next();
            }
        ]);
    },

    _swapNewRender : function( $newRender ){
        return this.$el.empty().attr( 'class', this.className ).append( $newRender.children() );
    },

    /** set up js behaviors, event handlers for elements within the given container
     *  @param {jQuery} $container jq object that contains the elements to process (defaults to this.$el)
     */
    _setUpBehaviors : function( $container ){
        $container = $container || this.$el;
        // set up canned behavior on children (bootstrap, popupmenus, editable_text, etc.)
        make_popup_menus( $container );
        $container.find( '[title]' ).tooltip({ placement : 'bottom' });
    },

    // ......................................................................... details
    _renderDetails : function(){
        // override this
        return null;
    },

    // ......................................................................... expansion/details
    /** Show or hide the body/details of history content.
     *  @param {Boolean} expand if true, expand; if false, collapse
     */
    toggleExpanded : function( expand ){
        expand = ( expand === undefined )?( !this.expanded ):( expand );
        if( expand ){
            this.expand();
        } else {
            this.collapse();
        }
        return this;
    },

    /** Render and show the full, detailed body of this view including extra data and controls.
     *      note: if the model does not have detailed data, fetch that data before showing the body
     *  @fires expanded when a body has been expanded
     */
    expand : function(){
        var view = this;

        function _renderDetailsAndExpand(){
            view.$( '.details' ).replaceWith( view._renderDetails() );
            // needs to be set after the above or the slide will not show
            view.expanded = true;
            view.$( '.details' ).slideDown( view.fxSpeed, function(){
                    view.trigger( 'expanded', view );
                });
        }
//TODO:?? remove
        // fetch first if no details in the model
        if( !view.model.hasDetails() ){
            // we need the change event on HDCA's for the elements to be processed - so silent == false
            view.model.fetch().always( function( model ){
                _renderDetailsAndExpand();
            });
//TODO: no error handling
        } else {
            _renderDetailsAndExpand();
        }
    },

    /** Hide the body/details of an HDA.
     *  @fires collapsed when a body has been collapsed
     */
    collapse : function(){
        var view = this;
        view.expanded = false;
        this.$( '.details' ).slideUp( view.fxSpeed, function(){
            view.trigger( 'collapsed', view );
        });
    }

});

//==============================================================================
    return {
        LoggableMixin                   : LoggableMixin,
        SessionStorageModel             : SessionStorageModel,
        HiddenUntilActivatedViewMixin   : HiddenUntilActivatedViewMixin,
        mixin                           : mixin,
        ExpandableView                  : ExpandableView
    };
});
