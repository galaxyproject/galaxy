define([
    "mvc/history/history-model",
    "mvc/dataset/hda-base",
    "mvc/dataset/hda-edit"
], function( historyModel, hdaBase, hdaEdit ){


// ============================================================================
/** session storage for individual history preferences
 */
var HistoryPanelPrefs = SessionStorageModel.extend({
    defaults : {
        //TODO:?? expandedHdas to array?
        expandedHdas : {},
        //TODO:?? move to user?
        show_deleted : false,
        show_hidden  : false
        //TODO: add scroll position?
    },
    /** add an hda id to the hash of expanded hdas */
    addExpandedHda : function( id ){
        this.save( 'expandedHdas', _.extend( this.get( 'expandedHdas' ), _.object([ id ], [ true ]) ) );
    },
    /** remove an hda id from the hash of expanded hdas */
    removeExpandedHda : function( id ){
        this.save( 'expandedHdas', _.omit( this.get( 'expandedHdas' ), id ) );
    },
    toString : function(){
        return 'HistoryPanelPrefs(' + this.id + ')';
    }
});

/** key string to store each histories settings under */
HistoryPanelPrefs.historyStorageKey = function historyStorageKey( historyId ){
    // class lvl for access w/o instantiation
    if( !historyId ){
        throw new Error( 'HistoryPanelPrefs.historyStorageKey needs valid id: ' + historyId );
    }
    // single point of change
    return ( 'history:' + historyId );
};


/* =============================================================================
Backbone.js implementation of history panel

r.js optimizer cline:
r.js -o baseUrl=. name=./mvc/history/history-panel.js out=history-panel.min.js

TODO:
    tags & annotations -> out
    use model.save instead of urls

    feature creep:
        lineage
        hide button
        show permissions in info
        show shared/sharing status on ds, history
        selection, multi-select (and actions common to selected (ugh))
        searching
        sorting, re-shuffling
    
============================================================================= */
/** @class View/Controller for the history model as used in the history
 *      panel (current right hand panel).
 *  @name HistoryPanel
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HistoryPanel = Backbone.View.extend( LoggableMixin ).extend(
/** @lends HistoryPanel.prototype */{
    
    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,

    /** which class to use for constructing the HDA views */
    //HDAView             : hdaBase.HDABaseView,
    HDAView             : hdaEdit.HDAEditView,

    tagName             : 'div',
    className           : 'history-panel',

    /** (in ms) that jquery effects will use */
    fxSpeed             : 'fast',

    datasetsSelector : '.datasets-list',
    emptyMsgSelector : '.empty-history-message',
    msgsSelector     : '.message-container',
    
    // ......................................................................... SET UP
    /** Set up the view, set up storage, bind listeners to HDACollection events
     *  @param {Object} attributes
     *  @config {Object} urlTemplates.hda       nested object containing url templates for HDAViews
     *  @throws 'needs urlTemplates' if urlTemplates.history or urlTemplates.hda aren't present
     *  @see PersistentStorage
     *  @see Backbone.View#initialize
     */
    initialize : function( attributes ){
        attributes = attributes || {};
        // set the logger if requested
        if( attributes.logger ){
            this.logger = attributes.logger;
        }
        this.log( this + '.initialize:', attributes );
//TODO: pass show_del'd/hidden through

        this._setUpListeners();

        // ---- set up instance vars
        /** map of hda model ids to hda views */
        this.hdaViews = {};
        /** loading indicator */
        this.indicator = new LoadingIndicator( this.$el );

        /** filters for displaying hdas */
        this.filters = [];

        // ---- handle models passed on init
        if( this.model ){
            this._setUpWebStorage( attributes.initiallyExpanded, attributes.show_deleted, attributes.show_hidden );
            this._setUpModelEventHandlers();
        }
//TODO: remove?
        // ---- and any run functions
        if( attributes.onready ){
            attributes.onready.call( this );
        }
    },

    /** create any event listeners for the panel
     *  @fires: rendered:initial    on the first render
     *  @fires: empty-history       when switching to a history with no HDAs or creating a new history
     */
    _setUpListeners : function(){
        // ---- event handlers for self
        this.on( 'error', function( model, xhr, options, msg, details ){
            this.errorHandler( model, xhr, options, msg, details );
        });

        this.on( 'loading-history', function(){
            // show the loading indicator when loading a new history starts...
            this.showLoadingIndicator( 'loading history...' );
        });
        this.on( 'loading-done', function(){
            // ...hiding it again when loading is done (or there's been an error)
            this.hideLoadingIndicator();
        });

        // throw the first render up as a diff namespace using once
        //  (for outside consumption)
        this.once( 'rendered', function(){
            this.trigger( 'rendered:initial', this );
            return false;
        });

        // trigger an event when there are no visible hdas
        //  (for outside consumption)
        this.on( 'switched-history current-history new-history', function(){
            if( _.isEmpty( this.hdaViews ) ){
                this.trigger( 'empty-history', this );
            }
        });

        // debugging
        if( this.logger ){
            this.on( 'all', function( event ){
                this.log( this + '', arguments );
            }, this );
        }
    },

    //TODO: see base-mvc
    //onFree : function(){
    //    _.each( this.hdaViews, function( view, modelId ){
    //        view.free();
    //    });
    //    this.hdaViews = null;
    //},

    // ........................................................................ error handling
    /** Event listener to handle errors (from the panel, the history, or the history's HDAs)
     *  @param {Model or View} model    the (Backbone) source of the error
     *  @param {XMLHTTPRequest} xhr     any ajax obj. assoc. with the error
     *  @param {Object} options         the options map commonly used with bbone ajax
     *  @param {String} msg             optional message passed to ease error location
     *  @param {Object} msg             optional object containing error details
     */
    errorHandler : function( model, xhr, options, msg, details ){
        var parsed = this._parseErrorMessage( model, xhr, options, msg, details );

        // interrupted ajax
        if( xhr && xhr.status === 0 && xhr.readyState === 0 ){

        // bad gateway
        } else if( xhr && xhr.status === 502 ){
//TODO: gmail style 'reconnecting in Ns'

        // otherwise, show an error message inside the panel
        } else {
            // it's possible to have a triggered error before the message container is rendered - wait for it to show
            if( !this.$el.find( this.msgsSelector ).is( ':visible' ) ){
                this.once( 'rendered', function(){
                    this.displayMessage( 'error', parsed.message, parsed.details );
                });
            } else {
                this.displayMessage( 'error', parsed.message, parsed.details );
            }
        }
    },

    /** Parse an error event into an Object usable by displayMessage based on the parameters
     *      note: see errorHandler for more info on params
     */
    _parseErrorMessage : function( model, xhr, options, msg, details ){
        var user = Galaxy.currUser,
            // add the args (w/ some extra info) into an obj
            parsed = {
                message : this._bePolite( msg ),
                details : {
                    user    : ( user instanceof User )?( user.toJSON() ):( user + '' ),
                    source  : ( model instanceof Backbone.Model )?( model.toJSON() ):( model + '' ),
                    xhr     : xhr,
                    options : ( xhr )?( _.omit( options, 'xhr' ) ):( options )
                }
            };
        // add any extra details passed in
        _.extend( parsed.details, details || {} );
        // fancy xhr.header parsing (--> obj)
        if( xhr &&  _.isFunction( xhr.getAllResponseHeaders ) ){
            var responseHeaders = xhr.getAllResponseHeaders();
            responseHeaders = _.compact( responseHeaders.split( '\n' ) );
            responseHeaders = _.map( responseHeaders, function( header ){
                return header.split( ': ' );
            });
            parsed.details.xhr.responseHeaders = _.object( responseHeaders );
        }
        return parsed;
    },

    /** Modify an error message to be fancy and wear a monocle. */
    _bePolite : function( msg ){
        msg = msg || _l( 'An error occurred while getting updates from the server' );
        return msg + '. ' + _l( 'Please contact a Galaxy administrator if the problem persists.' );
    },

    // ------------------------------------------------------------------------ loading history/hda models

    //NOTE: all the following fns replace the existing history model with a new model
    // (in the following 'details' refers to the full set of hda api data (urls, display_apps, misc_info, etc.)
    //  - hdas w/o details will have summary data only (name, hid, deleted, visible, state, etc.))

    /** (re-)loads the user's current history & hdas w/ details */
    loadCurrentHistory : function( attributes ){
        // implemented as a 'fresh start' or for when there is no model (intial panel render)
        var panel = this;
        return this.loadHistoryWithHDADetails( 'current', attributes )
            .then(function( historyData, hdaData ){
                panel.trigger( 'current-history', panel );
            });
    },

    /** loads a history & hdas w/ details and makes them the current history */
    switchToHistory : function( historyId, attributes ){
        //console.info( 'switchToHistory:', historyId, attributes );
        var panel = this,
            historyFn = function(){
                // make this current and get history data with one call
                return jQuery.post( galaxy_config.root + 'api/histories/' + historyId + '/set_as_current' );
            };
        return this.loadHistoryWithHDADetails( historyId, attributes, historyFn )
            .then(function( historyData, hdaData ){
                panel.trigger( 'switched-history', panel );
            });
    },

    /** creates a new history on the server and sets it as the user's current history */
    createNewHistory : function( attributes ){
        if( !Galaxy || !Galaxy.currUser || Galaxy.currUser.isAnonymous() ){
            this.displayMessage( 'error', _l( 'You must be logged in to create histories' ) );
            return $.when();
        }
        var panel = this,
            historyFn = function(){
                // get history data from posting a new history (and setting it to current)
                return jQuery.post( galaxy_config.root + 'api/histories', { current: true });
            };
        // id undefined bc there is no historyId yet - the server will provide
        //  (no need for details - nothing expanded in new history)
        return this.loadHistory( undefined, attributes, historyFn )
            .then(function( historyData, hdaData ){
                panel.trigger( 'new-history', panel );
            });
    },

    /** loads a history & hdas w/ details (but does not make them the current history) */
    loadHistoryWithHDADetails : function( historyId, attributes, historyFn, hdaFn ){
        //console.info( 'loadHistoryWithHDADetails:', historyId, attributes, historyFn, hdaFn );
        var panel = this,
            // will be called to get hda ids that need details from the api
            hdaDetailIds = function( historyData ){
//TODO: non-visible HDAs are getting details loaded... either stop loading them at all or filter ids thru isVisible
                return panel.getExpandedHdaIds( historyData.id );
            };
        return this.loadHistory( historyId, attributes, historyFn, hdaFn, hdaDetailIds );
    },

    /** loads a history & hdas w/ NO details (but does not make them the current history) */
    loadHistory : function( historyId, attributes, historyFn, hdaFn, hdaDetailIds ){
        this.trigger( 'loading-history', this );
        attributes = attributes || {};
        var panel = this;
        //console.info( 'loadHistory:', historyId, attributes, historyFn, hdaFn, hdaDetailIds );
        var xhr = historyModel.History.getHistoryData( historyId, {
                historyFn       : historyFn,
                hdaFn           : hdaFn,
                hdaDetailIds    : attributes.initiallyExpanded || hdaDetailIds
            });
        return this._loadHistoryFromXHR( xhr, attributes )
            .fail( function( xhr, where, history ){
                // throw an error up for the error handler
                panel.trigger( 'error', panel, xhr, attributes, _l( 'An error was encountered while ' + where ),
                    { historyId: historyId, history: history || {} });
            })
            .always( function(){
                // bc hideLoadingIndicator relies on this firing
                panel.trigger( 'loading-done', panel );
            });
    },

    /** given an xhr that will provide both history and hda data, pass data to set model or handle xhr errors */
    _loadHistoryFromXHR : function( xhr, attributes ){
        var panel = this;
        xhr.then( function( historyJSON, hdaJSON ){
            panel.setModel( historyJSON, hdaJSON, attributes );
        });
        xhr.fail( function( xhr, where ){
            // always render - whether we get a model or not
            panel.render();
        });
        return xhr;
    },

    /** release/free/shutdown old models and set up panel for new models */
    setModel : function( newHistoryJSON, newHdaJSON, attributes ){
        attributes = attributes || {};
        //console.info( 'setModel:', newHistoryJSON, newHdaJSON.length, attributes );

        // stop/release the previous model, and clear cache to hda sub-views
        if( this.model ){
            this.model.clearUpdateTimeout();
            this.stopListening( this.model );
            this.stopListening( this.model.hdas );
            //TODO: see base-mvc
            //this.model.free();
        }
        this.hdaViews = {};

        // set up the new model and render
        if( Galaxy && Galaxy.currUser ){
//TODO: global
            newHistoryJSON.user = Galaxy.currUser.toJSON();
        }
        this.model = new historyModel.History( newHistoryJSON, newHdaJSON, attributes );
        this._setUpWebStorage( attributes.initiallyExpanded, attributes.show_deleted, attributes.show_hidden );
        this._setUpModelEventHandlers();
        this.trigger( 'new-model', this );
        this.render();
        return this;
    },

    /** alias to the model. Updates the hda list only (not the history) */
    refreshHdas : function( detailIds, options ){
        if( this.model ){
            return this.model.refresh( detailIds, options );
        }
        // may have callbacks - so return an empty promise
        return $.when();
    },

    // ------------------------------------------------------------------------ browser stored prefs
    /** Set up client side storage. Currently PersistanStorage keyed under 'HistoryPanel.<id>'
     *  @param {Object} initiallyExpanded
     *  @param {Boolean} show_deleted whether to show deleted HDAs (overrides stored)
     *  @param {Boolean} show_hidden
     *  @see PersistentStorage
     */
    _setUpWebStorage : function( initiallyExpanded, show_deleted, show_hidden ){
        //console.debug( '_setUpWebStorage', initiallyExpanded, show_deleted, show_hidden );
        this.storage = new HistoryPanelPrefs({
            id: HistoryPanelPrefs.historyStorageKey( this.model.get( 'id' ) )
        });

        // expanded Hdas is a map of hda.ids -> a boolean repr'ing whether this hda's body is already expanded
        // store any pre-expanded ids passed in
        if( _.isObject( initiallyExpanded ) ){
            this.storage.set( 'exandedHdas', initiallyExpanded );
        }

        // get the show_deleted/hidden settings giving priority to values passed in, using web storage otherwise
        // if the page has specifically requested show_deleted/hidden, these will be either true or false
        //  (as opposed to undefined, null) - and we give priority to that setting
        if( _.isBoolean( show_deleted ) ){
            this.storage.set( 'show_deleted', show_deleted );
        }
        if( _.isBoolean( show_hidden ) ){
            this.storage.set( 'show_hidden', show_hidden );
        }

        this.trigger( 'new-storage', this.storage, this );
        this.log( this + ' (init\'d) storage:', this.storage.get() );
    },

    /** clear all stored history panel data */
    clearWebStorage : function(){
        for( var key in sessionStorage ){
            if( key.indexOf( 'history:' ) === 0 ){
                sessionStorage.removeItem( key );
            }
        }
    },

    /** get all stored data as an Object for a history with the given id */
    getStoredOptions : function( historyId ){
        if( !historyId || historyId === 'current' ){
            return ( this.storage )?( this.storage.get() ):( {} );
        }
        //TODO: make storage engine generic
        var item = sessionStorage.getItem( HistoryPanelPrefs.historyStorageKey( historyId ) );
        return ( item === null )?( {} ):( JSON.parse( item ) );
    },

    /** get an array of expanded hda ids for the given history id */
    getExpandedHdaIds : function( historyId ){
        var expandedHdas = this.getStoredOptions( historyId ).expandedHdas;
        return (( _.isEmpty( expandedHdas ) )?( [] ):( _.keys( expandedHdas ) ));
    },

    // ------------------------------------------------------------------------ history/hda event listening
    /** listening for history and HDA events */
    _setUpModelEventHandlers : function(){
        // ---- history
        // on a model error - bounce it up to the panel and remove it from the model
        this.model.on( 'error error:hdas', function( model, xhr, options, msg ){
            this.errorHandler( model, xhr, options, msg );
        }, this );

        // don't need to re-render entire model on all changes, just render disk size when it changes
        this.model.on( 'change:nice_size', this.updateHistoryDiskSize, this );

        // update the quota meter when current history changes size
        if( Galaxy && Galaxy.quotaMeter ){
            this.listenTo( this.model, 'change:nice_size', function(){
                //console.info( '!! model size changed:', this.model.get( 'nice_size' ) )
//TODO: global
                Galaxy.quotaMeter.update();
            });
        }

        // ---- hdas
        // bind events from the model's hda collection
        // note: don't listen to the hdas for errors, history will pass that to us
        //this.model.hdas.on( 'reset', this.addAll, this );
        this.model.hdas.on( 'add', this.addHdaView, this );

        this.model.hdas.on( 'change:deleted', this.handleHdaDeletionChange, this );
        this.model.hdas.on( 'change:visible', this.handleHdaVisibleChange, this );
        // when an hda is purged the disk size changes
        this.model.hdas.on( 'change:purged', function( hda ){
            // hafta get the new nice-size w/o the purged hda
            this.model.fetch();
        }, this );

        // if an a hidden hda is created (gen. by a workflow), moves thru the updater to the ready state,
        //  then: remove it from the collection if the panel is set to NOT show hidden datasets
        this.model.hdas.on( 'state:ready', function( hda, newState, oldState ){
            if( ( !hda.get( 'visible' ) )
            &&  ( !this.storage.get( 'show_hidden' ) ) ){
                this.removeHdaView( this.hdaViews[ hda.id ] );
            }
        }, this );

    },

    // ------------------------------------------------------------------------ adding/removing hda sub-views
    /** Add an hda view to the panel for the given hda
     *  @param {HistoryDatasetAssociation} hda
     */
    addHdaView : function( hda ){
        this.log( 'add.' + this, hda );
        var panel = this;

        // don't add the view if it wouldn't be visible accrd. to current settings
        if( !hda.isVisible( this.storage.get( 'show_deleted' ), this.storage.get( 'show_hidden' ) ) ){
            return;
        }

        // create and prepend to current el, if it was empty fadeout the emptyMsg first
        $({}).queue([
            function fadeOutEmptyMsg( next ){
                var $emptyMsg = panel.$el.find( panel.emptyMsgSelector );
                if( $emptyMsg.is( ':visible' ) ){
                    $emptyMsg.fadeOut( panel.fxSpeed, next );
                } else {
                    next();
                }
            },
            function createAndPrepend( next ){
                panel.scrollToTop();
                var $whereTo = panel.$el.find( panel.datasetsSelector );
                panel.createHdaView( hda ).$el.hide().prependTo( $whereTo ).slideDown( panel.fxSpeed );
            }
        ]);
    },

    /** Create an HDA view for the given HDA (but leave attachment for addHdaView above)
     *  @param {HistoryDatasetAssociation} hda
     */
    createHdaView : function( hda ){
        var hdaId = hda.get( 'id' ),
            expanded = this.storage.get( 'expandedHdas' )[ hdaId ],
            hdaView = new this.HDAView({
                    model           : hda,
                    expanded        : expanded,
                    hasUser         : this.model.hasUser(),
                    logger          : this.logger
                });
        this._setUpHdaListeners( hdaView );
        this.hdaViews[ hdaId ] = hdaView;
        return hdaView.render();
    },

    /** Set up HistoryPanel listeners for HDAView events. Currently binds:
     *      HDAView#body-visible, HDAView#body-hidden to store expanded states
     *  @param {HDAView} hdaView HDAView (base or edit) to listen to
     */
    _setUpHdaListeners : function( hdaView ){
        var historyView = this;
        // maintain a list of hdas whose bodies are expanded
        hdaView.on( 'body-expanded', function( id ){
            historyView.storage.addExpandedHda( id );
        });
        hdaView.on( 'body-collapsed', function( id ){
            historyView.storage.removeExpandedHda( id );
        });
//TODO: remove?
        hdaView.on( 'error', function( model, xhr, options, msg ){
            historyView.errorHandler( model, xhr, options, msg );
        });
    },

    /** If this hda is deleted and we're not showing deleted hdas, remove the view
     *  @param {HistoryDataAssociation} the hda to check
     */
    handleHdaDeletionChange : function( hda ){
        if( hda.get( 'deleted' ) && !this.storage.get( 'show_deleted' ) ){
            this.removeHdaView( this.hdaViews[ hda.id ] );
        } // otherwise, the hdaView rendering should handle it
    },

    /** If this hda is hidden and we're not showing hidden hdas, remove the view
     *  @param {HistoryDataAssociation} the hda to check
     */
    handleHdaVisibleChange : function( hda ){
        if( hda.hidden() && !this.storage.get( 'show_hidden' ) ){
            this.removeHdaView( this.hdaViews[ hda.id ] );
        } // otherwise, the hdaView rendering should handle it
    },

    /** Remove a view from the panel and if the panel is now empty, re-render
     *  @param {Int} the id of the hdaView to remove
     */
    removeHdaView : function( hdaView ){
        if( !hdaView ){ return; }

        var panel = this;
        hdaView.$el.fadeOut( panel.fxSpeed, function(){
            hdaView.off();
            hdaView.remove();
            delete panel.hdaViews[ hdaView.model.id ];
            if( _.isEmpty( panel.hdaViews ) ){
                panel.$el.find( panel.emptyMsgSelector ).fadeIn( panel.fxSpeed, function(){
                    panel.trigger( 'empty-history', panel );
                });
            }
        });
    },

    // ------------------------------------------------------------------------ panel rendering
    /** Render urls, historyPanel body, and hdas (if any are shown)
     *  @fires: rendered    when the panel is attached and fully visible
     *  @see Backbone.View#render
     */
    render : function( speed, callback ){
        // send a speed of 0 to have no fade in/out performed
        speed = ( speed === undefined )?( this.fxSpeed ):( speed );
        var panel = this,
            $newRender;

        // handle the possibility of no model (can occur if fetching the model returns an error)
        if( this.model ){
            $newRender = this.renderModel();
        } else {
            $newRender = this.renderWithoutModel();
        }

        // fade out existing, swap with the new, fade in, set up behaviours
        $( panel ).queue( 'fx', [
            function( next ){
                //panel.$el.fadeTo( panel.fxSpeed, 0.0001, next );
                if( speed && panel.$el.is( ':visible' ) ){
                    panel.$el.fadeOut( speed, next );
                } else {
                    next();
                }
            },
            function( next ){
                // swap over from temp div newRender
                panel.$el.empty();
                if( $newRender ){
                    panel.$el.append( $newRender.children() );
                }
                next();
            },
            function( next ){
                if( speed && !panel.$el.is( ':visible' ) ){
                    panel.$el.fadeIn( speed, next );
                } else {
                    next();
                }
            },
            function( next ){
                //TODO: ideally, these would be set up before the fade in (can't because of async save text)
                if( callback ){ callback.call( this ); }
                panel.trigger( 'rendered', this );
                next();
            }
        ]);
        return this;
    },

    /** render with no history data */
    renderWithoutModel : function( ){
        // we'll always need the message container
        var $newRender = $( '<div/>' ),
            $msgContainer = $( '<div/>' ).addClass( 'message-container' )
                .css({ 'margin-left': '4px', 'margin-right': '4px' });
        return $newRender.append( $msgContainer );
    },

    /** render with history data */
    renderModel : function( ){
        var $newRender = $( '<div/>' );

        // render based on anonymity, set up behaviors
        if( !Galaxy || !Galaxy.currUser || Galaxy.currUser.isAnonymous() ){
            $newRender.append( HistoryPanel.templates.anonHistoryPanel( this.model.toJSON() ) );

        } else {
            $newRender.append( HistoryPanel.templates.historyPanel( this.model.toJSON() ) );
            this._renderTags( $newRender );
            this._renderAnnotation( $newRender );
        }
        this._setUpBehaviours( $newRender );

        // render hda views (if any and any shown (show_deleted/hidden)
        this.renderHdas( $newRender );
        return $newRender;
    },

    _renderTags : function( $where ){
        this.tagsEditor = new TagsEditor({
            model           : this.model,
            el              : $where.find( '.history-controls .tags-display' ),
            onshowFirstTime : function(){ this.render(); },
            $activator      : faIconButton({
                title   : _l( 'Edit history tags' ),
                classes : 'history-tag-btn',
                faIcon  : 'fa-tags'
            }).appendTo( $where.find( '.history-secondary-actions' ) )
        });
    },
    _renderAnnotation : function( $where ){
        this.annotationEditor = new AnnotationEditor({
            model           : this.model,
            el              : $where.find( '.history-controls .annotation-display' ),
            onshowFirstTime : function(){ this.render(); },
            $activator      : faIconButton({
                title   : _l( 'Edit history tags' ),
                classes : 'history-annotate-btn',
                faIcon  : 'fa-comment'
            }).appendTo( $where.find( '.history-secondary-actions' ) )
        });
    },

    /** Set up HistoryPanel js/widget behaviours
     */
    //TODO: these should be either sub-MVs, or handled by events
    _setUpBehaviours : function( $where ){
        $where = $where || this.$el;
        $where.find( '[title]' ).tooltip({ placement: 'bottom' });

        // anon users shouldn't have access to any of the following
        if( !this.model || !Galaxy.currUser || Galaxy.currUser.isAnonymous() ){ return; }

        var panel = this;//,
        $where.find( '.history-name' ).make_text_editable({
            on_finish: function( newName ){
                $where.find( '.history-name' ).text( newName );
                panel.model.save({ name: newName })
                    .fail( function(){
                        $where.find( '.history-name' ).text( panel.model.previous( 'name' ) );
                    });
            }
        });
    },

    /** Set up/render a view for each HDA to be shown, init with model and listeners.
     *      HDA views are cached to the map this.hdaViews (using the model.id as key).
     *  @param {jQuery} $whereTo what dom element to prepend the HDA views to
     *  @returns the number of visible hda views
     */
    renderHdas : function( $whereTo ){
        $whereTo = $whereTo || this.$el;
        this.hdaViews = {};
        var historyView = this,
            $datasetsList = $whereTo.find( this.datasetsSelector ),
            // only render the shown hdas
            //TODO: switch to more general filtered pattern
            visibleHdas  = this.model.hdas.getVisible(
                this.storage.get( 'show_deleted' ),
                this.storage.get( 'show_hidden' ),
                this.filters
            );
        //console.debug( 'renderHdas, visibleHdas:', visibleHdas, $whereTo );
        $datasetsList.empty();

        if( visibleHdas.length ){
            visibleHdas.each( function( hda ){
                // render it (NOTE: reverse order, newest on top (prepend))
                $datasetsList.prepend( historyView.createHdaView( hda ).$el );
            });
            $whereTo.find( this.emptyMsgSelector ).hide();
            
        } else {
            //console.debug( 'emptyMsg:', $whereTo.find( this.emptyMsgSelector ) )
            $whereTo.find( this.emptyMsgSelector ).show();
        }
        return this.hdaViews;
    },

    // ------------------------------------------------------------------------ panel events
    /** event map */
    events : {
        // allow (error) messages to be clicked away
        //TODO: switch to common close (X) idiom
        'click .message-container'   : 'clearMessages'
    },

    /** Update the history size display (curr. upper right of panel).
     */
    updateHistoryDiskSize : function(){
        this.$el.find( '.history-size' ).text( this.model.get( 'nice_size' ) );
    },
    
    /** Collapse all hda bodies and clear expandedHdas in the storage
     */
    collapseAllHdaBodies : function(){
        _.each( this.hdaViews, function( item ){
            item.toggleBodyVisibility( null, false );
        });
        this.storage.set( 'expandedHdas', {} );
    },

    /** Handle the user toggling the deleted visibility by:
     *      (1) storing the new value in the persistent storage
     *      (2) re-rendering the history
     * @returns {Boolean} new show_deleted setting
     */
    toggleShowDeleted : function(){
        this.storage.set( 'show_deleted', !this.storage.get( 'show_deleted' ) );
        this.render();
        return this.storage.get( 'show_deleted' );
    },

    /** Handle the user toggling the deleted visibility by:
     *      (1) storing the new value in the persistent storage
     *      (2) re-rendering the history
     * @returns {Boolean} new show_hidden setting
     */
    toggleShowHidden : function(){
        this.storage.set( 'show_hidden', !this.storage.get( 'show_hidden' ) );
        this.render();
        return this.storage.get( 'show_hidden' );
    },

    // ........................................................................ filters
    /** render a search input for filtering datasets shown
     *      (see the search section in the HDA model for implementation of the actual searching)
     *      return will start the search
     *      esc will clear the search
     *      clicking the clear button will clear the search
     *      uses searchInput in ui.js
     */
    renderSearchControls : function(){
        var panel = this;
        //TODO: needs proper async
        panel.model.hdas.fetchAllDetails({ silent: true });

        function onSearch( searchFor ){
            //console.debug( 'onSearch', searchFor, panel );
            panel.searchFor = searchFor;
            panel.filters = [ function( hda ){ return hda.matchesAll( panel.searchFor ); } ];
            panel.trigger( 'search:searching', searchFor, panel );
            panel.renderHdas();
        }
        function onSearchClear(){
            //console.debug( 'onSearchClear', panel );
            panel.searchFor = '';
            panel.filters = [];
            panel.trigger( 'search:clear', panel );
            panel.renderHdas();
        }
        return searchInput({
                initialVal      : panel.searchFor,
                name            : 'history-search',
                placeholder     : 'search datasets',
                classes         : 'history-search',
                onsearch        : onSearch,
                onclear         : onSearchClear
            })
            .addClass( 'history-search-controls' )
            .css( 'padding', '0px 0px 8px 0px' );
    },

    /** toggle showing/hiding the search controls (rendering first on the initial show) */
    toggleSearchControls : function(){
        var $searchInput = this.$el.find( '.history-search-controls' );
        if( !$searchInput.size() ){
            $searchInput = this.renderSearchControls().hide();
            this.$el.find( '.history-title' ).before( $searchInput );
        }
        $searchInput.slideToggle( this.fxSpeed );
    },

    // ........................................................................ multi-select of hdas
    showSelect : function( speed ){
        _.each( this.hdaViews, function( view ){
            view.showSelect( speed );
        });
    },

    hideSelect : function( speed ){
        _.each( this.hdaViews, function( view ){
            view.hideSelect( speed );
        });
    },

    getSelectedHdaViews : function(){
        return _.filter( this.hdaViews, function( v ){
            return v.selected;
        });
    },

    // ........................................................................ loading indicator
    /** hide the panel and display a loading indicator (in the panel's parent) when history model's are switched */
    showLoadingIndicator : function( msg, speed, callback ){
        speed = ( speed !== undefined )?( speed ):( this.fxSpeed );
        if( !this.indicator ){
            this.indicator = new LoadingIndicator( this.$el, this.$el.parent() );
        }
        if( !this.$el.is( ':visible' ) ){
            this.indicator.show( 0, callback );
        } else {
            this.$el.fadeOut( speed );
            this.indicator.show( msg, speed, callback );
        }
    },

    /** hide the loading indicator */
    hideLoadingIndicator : function( speed, callback ){
        speed = ( speed !== undefined )?( speed ):( this.fxSpeed );
        if( this.indicator ){
            this.indicator.hide( speed, callback );
        }
    },

    // ........................................................................ (error) messages
    /** Display a message in the top of the panel.
     *  @param {String} type    type of message ('done', 'error', 'warning')
     *  @param {String} msg     the message to display
     */
    displayMessage : function( type, msg, details ){
        //precondition: msgContainer must have been rendered even if there's no model
        var panel = this;
        //console.debug( 'displayMessage', type, msg, details );

        this.scrollToTop();
        var $msgContainer = this.$el.find( this.msgsSelector ),
            $msg = $( '<div/>' ).addClass( type + 'message' ).html( msg );
        //console.debug( '  ', $msgContainer );

        if( !_.isEmpty( details ) ){
            var $detailsLink = $( '<a href="javascript:void(0)">Details</a>' )
                .click( function(){
                    Galaxy.modal.show( panel.messageToModalOptions( type, msg, details ) );
                    return false;
                });
            $msg.append( ' ', $detailsLink );
        }
        return $msgContainer.html( $msg );
    },

    /** convert msg and details into modal options usable by Galaxy.modal */
    messageToModalOptions : function( type, msg, details ){
        // only error is fleshed out here
        var panel = this,
            $modalBody = $( '<div/>' ),
            options = { title: 'Details' };

        //TODO: to some util library
        function objToTable( obj ){
            obj = _.omit( obj, _.functions( obj ) );
            return [
                '<table>',
                    _.map( obj, function( val, key ){
                        val = ( _.isObject( val ) )?( objToTable( val ) ):( val );
                        return '<tr><td style="vertical-align: top; color: grey">' + key + '</td>'
                                 + '<td style="padding-left: 8px">' + val + '</td></tr>';
                    }).join( '' ),
                '</table>'
            ].join( '' );
        }

        if( _.isObject( details ) ){
            options.body = $modalBody.append( objToTable( details ) );

        } else {
            options.body = $modalBody.html( details );
        }
        options.buttons = {
            'Ok': function(){
                Galaxy.modal.hide();
                panel.clearMessages();
            }
            //TODO: if( type === 'error' ){ options.buttons[ 'Report this error' ] = function(){} }
        };
        return options;
    },

    /** Remove all messages from the panel.
     */
    clearMessages : function(){
        var $msgContainer = this.$el.find( this.msgsSelector );
        $msgContainer.empty();
    },

    // ........................................................................ scrolling
    /** get the current scroll position of the panel in its parent */
    scrollPosition : function(){
        return this.$el.parent().scrollTop();
    },

    /** set the current scroll position of the panel in its parent */
    scrollTo : function( pos ){
        this.$el.parent().scrollTop( pos );
    },

    /** Scrolls the panel to the top.
     *  @returns {HistoryPanel} the panel
     */
    scrollToTop : function(){
        this.$el.parent().scrollTop( 0 );
        return this;
    },

    /** Scrolls the panel (the enclosing container - in gen., the page) so that some object
     *      is displayed in the vertical middle.
     *      NOTE: if no size is given the panel will scroll to objTop (putting it at the top).
     *  @param {Number} objTop  the top offset of the object to view
     *  @param {Number} objSize the size of the object to view
     *  @returns {HistoryPanel} the panel
     */
    scrollIntoView : function( where, size ){
        if( !size ){
            this.$el.parent().parent().scrollTop( where );
            return this;
        }
        // otherwise, place the object in the vertical middle
        var viewport = window,
            panelContainer = this.$el.parent().parent(),
            containerHeight = $( viewport ).innerHeight(),
            middleOffset = ( containerHeight / 2 ) - ( size / 2 );

        $( panelContainer ).scrollTop( where - middleOffset );
        return this;
    },

    /** Scrolls the panel to show the HDA with the given id.
     *  @param {String} id  the id of HDA to scroll into view
     *  @returns {HistoryPanel} the panel
     */
    scrollToId : function( id ){
        // do nothing if id not found
        if( ( !id ) || ( !this.hdaViews[ id ] ) ){
            return this;
        }
        var $viewEl = this.hdaViews[ id ].$el;
        this.scrollIntoView( $viewEl.offset().top, $viewEl.outerHeight() );
        return this;
    },

    /** Scrolls the panel to show the HDA with the given hid.
     *  @param {Integer} hid    the hid of HDA to scroll into view
     *  @returns {HistoryPanel} the panel
     */
    scrollToHid : function( hid ){
        var hda = this.model.hdas.getByHid( hid );
        // do nothing if hid not found
        if( !hda ){ return this; }
        return this.scrollToId( hda.id );
    },

    // ........................................................................ external objects/MVC
    //TODO: remove quota meter from panel and remove this
    /** add listeners to an external quota meter (mvc/user/user-quotameter.js) */
    connectToQuotaMeter : function( quotaMeter ){
        if( !quotaMeter ){
            return this;
        }
        // show/hide the 'over quota message' in the history when the meter tells it to
        this.listenTo( quotaMeter, 'quota:over',  this.showQuotaMessage );
        this.listenTo( quotaMeter, 'quota:under', this.hideQuotaMessage );

        // having to add this to handle re-render of hview while overquota (the above do not fire)
        this.on( 'rendered rendered:initial', function(){
            if( quotaMeter && quotaMeter.isOverQuota() ){
                this.showQuotaMessage();
            }
        });
        return this;
    },

//TODO: this seems more like a per user message than a history message; IOW, this doesn't belong here
    /** Show the over quota message (which happens to be in the history panel).
     */
    showQuotaMessage : function(){
        var msg = this.$el.find( '.quota-message' );
        //this.log( this + ' showing quota message:', msg, userData );
        if( msg.is( ':hidden' ) ){ msg.slideDown( this.fxSpeed ); }
    },

//TODO: this seems more like a per user message than a history message
    /** Hide the over quota message (which happens to be in the history panel).
     */
    hideQuotaMessage : function(){
        var msg = this.$el.find( '.quota-message' );
        //this.log( this + ' hiding quota message:', msg, userData );
        if( !msg.is( ':hidden' ) ){ msg.slideUp( this.fxSpeed ); }
    },

//TODO: move show_deleted/hidden into panel from opt menu and remove this
    /** add listeners to an external options menu (templates/webapps/galaxy/root/index.mako) */
    connectToOptionsMenu : function( optionsMenu ){
        if( !optionsMenu ){
            return this;
        }
        // set a visible indication in the popupmenu for show_hidden/deleted based on the currHistoryPanel's settings
        this.on( 'new-storage', function( storage, panel ){
            if( optionsMenu && storage ){
                optionsMenu.findItemByHtml( _l( 'Include Deleted Datasets' ) ).checked = storage.get( 'show_deleted' );
                optionsMenu.findItemByHtml( _l( 'Include Hidden Datasets' ) ).checked = storage.get( 'show_hidden' );
            }
        });
        return this;
    },

    /** Return a string rep of the history
     */
    toString    : function(){
        return 'HistoryPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});

//------------------------------------------------------------------------------ TEMPLATES
HistoryPanel.templates = {
    historyPanel     : Handlebars.templates[ 'template-history-historyPanel' ],
    anonHistoryPanel : Handlebars.templates[ 'template-history-historyPanel-anon' ]
};

//==============================================================================
    return {
        HistoryPanel     : HistoryPanel
    };
});
