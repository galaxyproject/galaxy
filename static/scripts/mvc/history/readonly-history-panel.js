define([
    "mvc/history/history-model",
    "mvc/collection/dataset-collection-base",
    "mvc/dataset/hda-base",
    "mvc/user/user-model",
    "mvc/base-mvc",
    "utils/localization"
], function( historyModel, datasetCollectionBase, hdaBase, userModel, baseMVC, _l ){
// ============================================================================
/** session storage for individual history preferences */
var HistoryPrefs = baseMVC.SessionStorageModel.extend({
    defaults : {
//TODO:?? expandedHdas to array?
        expandedHdas : {},
        //TODO:?? move to user?
        show_deleted : false,
        show_hidden  : false
        //TODO: add scroll position?
    },
    /** add an hda id to the hash of expanded hdas */
    addExpandedHda : function( model ){
        var key = 'expandedHdas';
        this.save( key, _.extend( this.get( key ), _.object([ model.id ], [ model.get( 'id' ) ]) ) );
    },
    /** remove an hda id from the hash of expanded hdas */
    removeExpandedHda : function( id ){
        var key = 'expandedHdas';
        this.save( key, _.omit( this.get( key ), id ) );
    },
    toString : function(){
        return 'HistoryPrefs(' + this.id + ')';
    }
});
// class lvl for access w/o instantiation
HistoryPrefs.storageKeyPrefix = 'history:';

/** key string to store each histories settings under */
HistoryPrefs.historyStorageKey = function historyStorageKey( historyId ){
    if( !historyId ){
        throw new Error( 'HistoryPrefs.historyStorageKey needs valid id: ' + historyId );
    }
    // single point of change
    return ( HistoryPrefs.storageKeyPrefix + historyId );
};
/** return the existing storage for the history with the given id (or create one if it doesn't exist) */
HistoryPrefs.get = function get( historyId ){
    return new HistoryPrefs({ id: HistoryPrefs.historyStorageKey( historyId ) });
};
/** clear all history related items in sessionStorage */
HistoryPrefs.clearAll = function clearAll( historyId ){
    for( var key in sessionStorage ){
        if( key.indexOf( HistoryPrefs.storageKeyPrefix ) === 0 ){
            sessionStorage.removeItem( key );
        }
    }
};


/* =============================================================================
TODO:

============================================================================= */
/** @class  non-editable, read-only View/Controller for a history model.
 *  @name HistoryPanel
 *
 *  Allows:
 *      changing the loaded history
 *      searching hdas
 *      displaying data, info, and download
 *  Does not allow:
 *      changing the name
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var ReadOnlyHistoryPanel = Backbone.View.extend( baseMVC.LoggableMixin ).extend(
/** @lends ReadOnlyHistoryPanel.prototype */{

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,

    /** class to use for constructing the HDA views */
    HDAViewClass : hdaBase.HDABaseView,

    tagName             : 'div',
    className           : 'history-panel',

    /** (in ms) that jquery effects will use */
    fxSpeed             : 'fast',

    /** string to display when the model has no hdas */
    emptyMsg            : _l( 'This history is empty' ),
    /** string to no hdas match the search terms */
    noneFoundMsg        : _l( 'No matching datasets found' ),

    // ......................................................................... SET UP
    /** Set up the view, set up storage, bind listeners to HDACollection events
     *  @param {Object} attributes optional settings for the panel
     */
    initialize : function( attributes ){
        attributes = attributes || {};
        // set the logger if requested
        if( attributes.logger ){
            this.logger = attributes.logger;
        }
        this.log( this + '.initialize:', attributes );

        // ---- instance vars
        // control contents/behavior based on where (and in what context) the panel is being used
        /** where should pages from links be displayed? (default to new tab/window) */
        this.linkTarget = attributes.linkTarget || '_blank';
        /** how quickly should jquery fx run? */
        this.fxSpeed = _.has( attributes, 'fxSpeed' )?( attributes.fxSpeed ):( this.fxSpeed );

        /** filters for displaying hdas */
        this.filters = [];
        this.searchFor = '';

        /** a function to locate the container to scroll to effectively scroll the panel */
//TODO: rename
        this.findContainerFn = attributes.findContainerFn;
        // generally this is $el.parent() - but may be $el or $el.parent().parent() depending on the context

        // ---- sub views and saved elements
        /** map of hda model ids to hda views */
        this.hdaViews = {};
        /** loading indicator */
        this.indicator = new LoadingIndicator( this.$el );

        // ----- set up panel listeners, handle models passed on init, and call any ready functions
        this._setUpListeners();
        // don't render when setting the first time
        var modelOptions = _.pick( attributes, 'initiallyExpanded', 'show_deleted', 'show_hidden' );
        this.setModel( this.model, modelOptions, false );
//TODO: remove?
        if( attributes.onready ){
            attributes.onready.call( this );
        }
    },

    /** create any event listeners for the panel
     *  @fires: rendered:initial    on the first render
     *  @fires: empty-history       when switching to a history with no HDAs or creating a new history
     */
    _setUpListeners : function(){
        this.on( 'error', function( model, xhr, options, msg, details ){
            this.errorHandler( model, xhr, options, msg, details );
        });

        this.on( 'loading-history', function(){
            // show the loading indicator when loading a new history starts...
            this._showLoadingIndicator( 'loading history...', 40 );
        });
        this.on( 'loading-done', function(){
            // ...hiding it again when loading is done (or there's been an error)
            this._hideLoadingIndicator( 40 );
            if( _.isEmpty( this.hdaViews ) ){
                this.trigger( 'empty-history', this );
            }
        });

        // throw the first render up as a diff namespace using once (for outside consumption)
        this.once( 'rendered', function(){
            this.trigger( 'rendered:initial', this );
            return false;
        });

        // debugging
        if( this.logger ){
            this.on( 'all', function( event ){
                this.log( this + '', arguments );
            }, this );
        }
        return this;
    },

    //TODO: see base-mvc
    //onFree : function(){
    //    _.each( this.hdaViews, function( view, modelId ){
    //        view.free();
    //    });
    //    this.hdaViews = null;
    //},

    // ........................................................................ error handling
    /** Event handler for errors (from the panel, the history, or the history's HDAs)
     *  @param {Model or View} model    the (Backbone) source of the error
     *  @param {XMLHTTPRequest} xhr     any ajax obj. assoc. with the error
     *  @param {Object} options         the options map commonly used with bbone ajax
     *  @param {String} msg             optional message passed to ease error location
     *  @param {Object} msg             optional object containing error details
     */
    errorHandler : function( model, xhr, options, msg, details ){
        console.error( model, xhr, options, msg, details );
//TODO: getting JSON parse errors from jq migrate

        // interrupted ajax
        if( xhr && xhr.status === 0 && xhr.readyState === 0 ){

        // bad gateway
        } else if( xhr && xhr.status === 502 ){
//TODO: gmail style 'reconnecting in Ns'

        // otherwise, show an error message inside the panel
        } else {
            var parsed = this._parseErrorMessage( model, xhr, options, msg, details );
            // it's possible to have a triggered error before the message container is rendered - wait for it to show
            if( !this.$messages().is( ':visible' ) ){
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
                    user    : ( user instanceof userModel.User )?( user.toJSON() ):( user + '' ),
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
        return msg + '. ' + _l( 'Please contact a Galaxy administrator if the problem persists' ) + '.';
    },

    // ------------------------------------------------------------------------ loading history/hda models
    //NOTE: all the following fns replace the existing history model with a new model
    // (in the following 'details' refers to the full set of hda api data (urls, display_apps, misc_info, etc.)
    //  - hdas w/o details will have summary data only (name, hid, deleted, visible, state, etc.))

    /** loads a history & hdas w/ details (but does not make them the current history) */
    loadHistoryWithHDADetails : function( historyId, attributes, historyFn, hdaFn ){
        //console.info( 'loadHistoryWithHDADetails:', historyId, attributes, historyFn, hdaFn );
        var hdaDetailIds = function( historyData ){
                // will be called to get hda ids that need details from the api
//TODO: non-visible HDAs are getting details loaded... either stop loading them at all or filter ids thru isVisible
                return _.values( HistoryPrefs.get( historyData.id ).get( 'expandedHdas' ) );
            };
        return this.loadHistory( historyId, attributes, historyFn, hdaFn, hdaDetailIds );
    },

    /** loads a history & hdas w/ NO details (but does not make them the current history) */
    loadHistory : function( historyId, attributes, historyFn, hdaFn, hdaDetailIds ){
        var panel = this;
        attributes = attributes || {};

        panel.trigger( 'loading-history', panel );
        //console.info( 'loadHistory:', historyId, attributes, historyFn, hdaFn, hdaDetailIds );
        var xhr = historyModel.History.getHistoryData( historyId, {
                historyFn       : historyFn,
                hdaFn           : hdaFn,
                hdaDetailIds    : attributes.initiallyExpanded || hdaDetailIds
            });

        return panel._loadHistoryFromXHR( xhr, attributes )
            .fail( function( xhr, where, history ){
                // throw an error up for the error handler
//TODO: difficult to localize - use template
                panel.trigger( 'error', panel, xhr, attributes, _l( 'An error was encountered while ' + where ),
                    { historyId: historyId, history: history || {} });
            })
            .always( function(){
                // bc _hideLoadingIndicator relies on this firing
                panel.trigger( 'loading-done', panel );
            });
    },

    /** given an xhr that will provide both history and hda data, pass data to set model or handle xhr errors */
    _loadHistoryFromXHR : function( xhr, attributes ){
        var panel = this;
        xhr.then( function( historyJSON, hdaJSON ){
            panel.JSONToModel( historyJSON, hdaJSON, attributes );
        });
        xhr.fail( function( xhr, where ){
            // always render - whether we get a model or not
            panel.render();
        });
        return xhr;
    },


    /** create a new history model from JSON and call setModel on it */
    JSONToModel : function( newHistoryJSON, newHdaJSON, attributes ){
        this.log( 'JSONToModel:', newHistoryJSON, newHdaJSON, attributes );
//TODO: Maybe better in History?
        attributes = attributes || {};
        //this.log( 'JSONToModel:', newHistoryJSON, newHdaJSON.length, attributes );

//        // set up the new model and render
//        if( Galaxy && Galaxy.currUser ){
////TODO: global
//            newHistoryJSON.user = Galaxy.currUser.toJSON();
//        }
        var model = new historyModel.History( newHistoryJSON, newHdaJSON, attributes );
        this.setModel( model );
        return this;
    },

    /** release/free/shutdown old models and set up panel for new models
     *  @fires new-model with the panel as parameter
     */
    setModel : function( model, attributes, render ){
        attributes = attributes || {};
        render = ( render !== undefined )?( render ):( true );
        this.log( 'setModel:', model, attributes, render );

        this.freeModel();
        this.selectedHdaIds = [];

        if( model ){
            // set up the new model with user, logger, storage, events
//            if( Galaxy && Galaxy.currUser ){
////TODO: global
//                model.user = Galaxy.currUser.toJSON();
//            }
            this.model = model;
            if( this.logger ){
                this.model.logger = this.logger;
            }
            this._setUpWebStorage( attributes.initiallyExpanded, attributes.show_deleted, attributes.show_hidden );
            this._setUpModelEventHandlers();
            this.trigger( 'new-model', this );
        }

        if( render ){
//TODO: remove?
            this.render();
        }
        return this;
    },

    /** free the current model and all listeners for it, free any hdaViews for the model */
    freeModel : function(){
        // stop/release the previous model, and clear cache to hda sub-views
        if( this.model ){
            this.model.clearUpdateTimeout();
            this.stopListening( this.model );
            this.stopListening( this.model.hdas );
            //TODO: see base-mvc
            //this.model.free();
        }
        this.freeHdaViews();
        return this;
    },

    /** free any hdaViews the panel has */
    freeHdaViews : function(){
        this.hdaViews = {};
        return this;
    },

    // ------------------------------------------------------------------------ browser stored prefs
    /** Set up client side storage. Currently PersistanStorage keyed under 'HistoryPanel.<id>'
     *  @param {Object} initiallyExpanded
     *  @param {Boolean} show_deleted whether to show deleted HDAs (overrides stored)
     *  @param {Boolean} show_hidden
     *  @see PersistentStorage
     */
    _setUpWebStorage : function( initiallyExpanded, show_deleted, show_hidden ){
        //this.log( '_setUpWebStorage', initiallyExpanded, show_deleted, show_hidden );
        this.storage = new HistoryPrefs({
            id: HistoryPrefs.historyStorageKey( this.model.get( 'id' ) )
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
        return this;
    },

    // ------------------------------------------------------------------------ history/hda event listening
    /** listening for history and HDA events */
    _setUpModelEventHandlers : function(){
        // ---- hdas
        // bind events from the model's hda collection
        // note: don't listen to the hdas for errors, history will pass that to us
        //this.model.hdas.on( 'reset', this.addAll, this );
        this.model.hdas.on( 'add', this.addContentView, this );

        // on a model error - bounce it up to the panel and remove it from the model
        this.model.on( 'error error:hdas', function( model, xhr, options, msg ){
            this.errorHandler( model, xhr, options, msg );
        }, this );
        return this;
    },

    // ------------------------------------------------------------------------ panel rendering
    /** Render urls, historyPanel body, and hdas (if any are shown)
     *  @fires: rendered    when the panel is attached and fully visible
     *  @see Backbone.View#render
     */
    render : function( speed, callback ){
        this.log( 'render:', speed, callback );
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

    /** render without history data
     *  @returns {jQuery} dom fragment with message container only
     */
    renderWithoutModel : function( ){
        // we'll always need the message container
        var $newRender = $( '<div/>' ),
            $msgContainer = $( '<div/>' ).addClass( 'message-container' )
                .css({ 'margin': '4px' });
        return $newRender.append( $msgContainer );
    },

    /** render with history data
     *  @returns {jQuery} dom fragment as temporary container to be swapped out later
     */
    renderModel : function( ){
        // tmp div for final swap in render
        var $newRender = $( '<div/>' );

        // render based on anonymity, set up behaviors
        $newRender.append( ReadOnlyHistoryPanel.templates.historyPanel( this.model.toJSON() ) );
        this.$emptyMessage( $newRender ).text( this.emptyMsg );
        // search and select available to both anon/logged-in users
        $newRender.find( '.history-secondary-actions' ).prepend( this._renderSearchButton() );

        this._setUpBehaviours( $newRender );

        // render hda views (if any and any shown (show_deleted/hidden)
        this.renderHdas( $newRender );
        return $newRender;
    },

    /** render the empty/none-found message */
    _renderEmptyMsg : function( $whereTo ){
        var panel = this,
            $emptyMsg = panel.$emptyMessage( $whereTo );

        if( !_.isEmpty( panel.hdaViews ) ){
            $emptyMsg.hide();

        } else if( panel.searchFor ){
            $emptyMsg.text( panel.noneFoundMsg ).show();

        } else {
            $emptyMsg.text( panel.emptyMsg ).show();
        }
        return this;
    },

    /** button for opening search */
    _renderSearchButton : function( $where ){
        return faIconButton({
            title   : _l( 'Search datasets' ),
            classes : 'history-search-btn',
            faIcon  : 'fa-search'
        });
    },

    /** Set up HistoryPanel js/widget behaviours */
    _setUpBehaviours : function( $where ){
        //TODO: these should be either sub-MVs, or handled by events
        $where = $where || this.$el;
        $where.find( '[title]' ).tooltip({ placement: 'bottom' });
        this._setUpSearchInput( $where.find( '.history-search-controls .history-search-input' ) );
        return this;
    },

    // ------------------------------------------------------------------------ sub-$element shortcuts
    /** the scroll container for this panel - can be $el, $el.parent(), or grandparent depending on context */
    $container : function(){
        return ( this.findContainerFn )?( this.findContainerFn.call( this ) ):( this.$el.parent() );
    },
    /** where hdaViews are attached */
    $datasetsList : function( $where ){
        return ( $where || this.$el ).find( '.datasets-list' );
    },
    /** container where panel messages are attached */
    $messages     : function( $where ){
        return ( $where || this.$el ).find( '.message-container' );
    },
    /** the message displayed when no hdaViews can be shown (no hdas, none matching search) */
    $emptyMessage : function( $where ){
        return ( $where || this.$el ).find( '.empty-history-message' );
    },

    // ------------------------------------------------------------------------ hda sub-views
    /** Set up/render a view for each HDA to be shown, init with model and listeners.
     *      HDA views are cached to the map this.hdaViews (using the model.id as key).
     *  @param {jQuery} $whereTo what dom element to prepend the HDA views to
     *  @returns the number of visible hda views
     */
    renderHdas : function( $whereTo ){
        $whereTo = $whereTo || this.$el;
        var panel = this,
            newHdaViews = {},
            // only render the shown hdas
            //TODO: switch to more general filtered pattern
            visibleHdas = this.model.hdas.getVisible(
                this.storage.get( 'show_deleted' ),
                this.storage.get( 'show_hidden' ),
                this.filters
            );
        //this.log( 'renderHdas, visibleHdas:', visibleHdas, $whereTo );
//TODO: prepend to sep div, add as one

        this.$datasetsList( $whereTo ).empty();

        if( visibleHdas.length ){
            visibleHdas.each( function( hda ){
                // render it (NOTE: reverse order, newest on top (prepend))
                var hdaId = hda.id,
                    hdaView = panel._createContentView( hda );
                newHdaViews[ hdaId ] = hdaView;
                // persist selection
                if( _.contains( panel.selectedHdaIds, hdaId ) ){
                    hdaView.selected = true;
                }
                panel.attachContentView( hdaView.render(), $whereTo );
            });
        }
        this.hdaViews = newHdaViews;
        this._renderEmptyMsg( $whereTo );
        return this.hdaViews;
    },

    /** Create an HDA view for the given HDA and set up listeners (but leave attachment for addHdaView)
     *  @param {HistoryDatasetAssociation} hda
     */
    _createContentView : function( hda ){
        var hdaId = hda.id,
            historyContentType = hda.get( "history_content_type" ),
            hdaView = null;
        if( historyContentType === "dataset" ){
            hdaView = new this.HDAViewClass({
                model           : hda,
                linkTarget      : this.linkTarget,
                expanded        : this.storage.get( 'expandedHdas' )[ hdaId ],
                //draggable       : true,
                hasUser         : this.model.ownedByCurrUser(),
                logger          : this.logger
            });
        } else {
            hdaView = new datasetCollectionBase.DatasetCollectionBaseView({
                model           : hda,
                linkTarget      : this.linkTarget,
                expanded        : this.storage.get( 'expandedHdas' )[ hdaId ],
                //draggable       : true,
                hasUser         : this.model.ownedByCurrUser(),
                logger          : this.logger
            });
        }
        this._setUpHdaListeners( hdaView );
        return hdaView;
    },

    /** Set up HistoryPanel listeners for HDAView events. Currently binds:
     *      HDAView#body-visible, HDAView#body-hidden to store expanded states
     *  @param {HDAView} hdaView HDAView (base or edit) to listen to
     */
    _setUpHdaListeners : function( hdaView ){
        var panel = this;
        hdaView.on( 'error', function( model, xhr, options, msg ){
            panel.errorHandler( model, xhr, options, msg );
        });
        // maintain a list of hdas whose bodies are expanded
        hdaView.on( 'body-expanded', function( model ){
            panel.storage.addExpandedHda( model );
        });
        hdaView.on( 'body-collapsed', function( id ){
            panel.storage.removeExpandedHda( id );
        });
        return this;
    },

    /** attach an hdaView to the panel */
    attachContentView : function( hdaView, $whereTo ){
        $whereTo = $whereTo || this.$el;
        var $datasetsList = this.$datasetsList( $whereTo );
        $datasetsList.prepend( hdaView.$el );
        return this;
    },

    /** Add an hda view to the panel for the given hda
     *  @param {HistoryDatasetAssociation} hda
     */
    addContentView : function( hda ){
        this.log( 'add.' + this, hda );
        var panel = this;

        // don't add the view if it wouldn't be visible accrd. to current settings
        if( !hda.isVisible( this.storage.get( 'show_deleted' ), this.storage.get( 'show_hidden' ) ) ){
            return panel;
        }

        // create and prepend to current el, if it was empty fadeout the emptyMsg first
        $({}).queue([
            function fadeOutEmptyMsg( next ){
                var $emptyMsg = panel.$emptyMessage();
                if( $emptyMsg.is( ':visible' ) ){
                    $emptyMsg.fadeOut( panel.fxSpeed, next );
                } else {
                    next();
                }
            },
            function createAndPrepend( next ){
                var hdaView = panel._createContentView( hda );
                panel.hdaViews[ hda.id ] = hdaView;
                hdaView.render().$el.hide();
                panel.scrollToTop();
                panel.attachContentView( hdaView );
                hdaView.$el.slideDown( panel.fxSpeed );
            }
        ]);
        return panel;
    },

    //TODO: removeHdaView?

    /** convenience alias to the model. Updates the hda list only (not the history) */
    refreshContents : function( detailIds, options ){
        if( this.model ){
            return this.model.refresh( detailIds, options );
        }
        // may have callbacks - so return an empty promise
        return $.when();
    },

    ///** use underscore's findWhere to find a view where the model matches the terms
    // *  note: finds and returns the _first_ matching
    // */
    //findHdaView : function( terms ){
    //    if( !this.model || !this.model.hdas.length ){ return undefined; }
    //    var model = this.model.hdas.findWhere( terms );
    //    return ( model )?( this.hdaViews[ model.id ] ):( undefined );
    //},

    hdaViewRange : function( viewA, viewB ){
        //console.debug( 'a: ', viewA, viewA.model );
        //console.debug( 'b: ', viewB, viewB.model );
        if( viewA === viewB ){ return [ viewA ]; }
        //TODO: would probably be better if we cache'd the views as an ordered list (as well as a map)
        var panel = this,
            withinSet = false,
            set = [];
        this.model.hdas.getVisible(
            this.storage.get( 'show_deleted' ),
            this.storage.get( 'show_hidden' ),
            this.filters
        ).each( function( hda ){
            //console.debug( 'checking: ', hda.get( 'name' ) );
            if( withinSet ){
                //console.debug( '\t\t adding: ', hda.get( 'name' ) );
                set.push( panel.hdaViews[ hda.id ] );
                if( hda === viewA.model || hda === viewB.model ){
                    //console.debug( '\t found last: ', hda.get( 'name' ) );
                    withinSet = false;
                }
            } else {
                if( hda === viewA.model || hda === viewB.model ){
                    //console.debug( 'found first: ', hda.get( 'name' ) );
                    withinSet = true;
                    set.push( panel.hdaViews[ hda.id ] );
                }
            }
        });
        return set;
    },

    // ------------------------------------------------------------------------ panel events
    /** event map */
    events : {
        // allow (error) messages to be clicked away
//TODO: switch to common close (X) idiom
        'click .message-container'      : 'clearMessages',
        'click .history-search-btn'     : 'toggleSearchControls'
    },

    /** Collapse all hda bodies and clear expandedHdas in the storage */
    collapseAllHdaBodies : function(){
        _.each( this.hdaViews, function( item ){
            item.toggleBodyVisibility( null, false );
        });
        this.storage.set( 'expandedHdas', {} );
        return this;
    },

    /** Handle the user toggling the deleted visibility by:
     *      (1) storing the new value in the persistent storage
     *      (2) re-rendering the history
     * @returns {Boolean} new show_deleted setting
     */
    toggleShowDeleted : function( show ){
        show = ( show !== undefined )?( show ):( !this.storage.get( 'show_deleted' ) );
        this.storage.set( 'show_deleted', show );
        this.renderHdas();
        return this.storage.get( 'show_deleted' );
    },

    /** Handle the user toggling the deleted visibility by:
     *      (1) storing the new value in the persistent storage
     *      (2) re-rendering the history
     * @returns {Boolean} new show_hidden setting
     */
    toggleShowHidden : function( show ){
        show = ( show !== undefined )?( show ):( !this.storage.get( 'show_hidden' ) );
        this.storage.set( 'show_hidden', show );
        this.renderHdas();
        return this.storage.get( 'show_hidden' );
    },

    // ........................................................................ hda search & filters
    /** render a search input for filtering datasets shown
     *      (see the search section in the HDA model for implementation of the actual searching)
     *      return will start the search
     *      esc will clear the search
     *      clicking the clear button will clear the search
     *      uses searchInput in ui.js
     */
    _setUpSearchInput : function( $where ){
        var panel = this,
            inputSelector = '.history-search-input';

        function onFirstSearch( searchFor ){
            //this.log( 'onFirstSearch', searchFor, panel );
            if( panel.model.hdas.haveDetails() ){
                panel.searchHdas( searchFor );
                return;
            }
            panel.$el.find( inputSelector ).searchInput( 'toggle-loading' );
            panel.model.hdas.fetchAllDetails({ silent: true })
                .always( function(){
                    panel.$el.find( inputSelector ).searchInput( 'toggle-loading' );
                })
                .done( function(){
                    panel.searchHdas( searchFor );
                });
        }
        $where.searchInput({
                initialVal      : panel.searchFor,
                name            : 'history-search',
                placeholder     : 'search datasets',
                classes         : 'history-search',
                onfirstsearch   : onFirstSearch,
                onsearch        : _.bind( this.searchHdas, this ),
                onclear         : _.bind( this.clearHdaSearch, this )
            });
        return $where;
    },
    /** toggle showing/hiding the search controls (rendering first on the initial show)
     *  @param {Event or Number} eventOrSpeed   variadic - if number the speed of the show/hide effect
     *  @param {boolean} show                   force show/hide with T/F
     */
    toggleSearchControls : function( eventOrSpeed, show ){
        var $searchControls = this.$el.find( '.history-search-controls' ),
            speed = ( jQuery.type( eventOrSpeed ) === 'number' )?( eventOrSpeed ):( this.fxSpeed );
        show = ( show !== undefined )?( show ):( !$searchControls.is( ':visible' ) );
        if( show ){
            $searchControls.slideDown( speed, function(){
                $( this ).find( 'input' ).focus();
            });
        } else {
            $searchControls.slideUp( speed );
        }
        return show;
    },

    /** filter hda view list to those that contain the searchFor terms
     *      (see the search section in the HDA model for implementation of the actual searching)
    */
    searchHdas : function( searchFor ){
        //note: assumes hda details are loaded
        //this.log( 'onSearch', searchFor, this );
        var panel = this;
        this.searchFor = searchFor;
        this.filters = [ function( hda ){ return hda.matchesAll( panel.searchFor ); } ];
        this.trigger( 'search:searching', searchFor, this );
        this.renderHdas();
        return this;
    },

    /** clear the search filters and show all views that are normally shown */
    clearHdaSearch : function( searchFor ){
        //this.log( 'onSearchClear', this );
        this.searchFor = '';
        this.filters = [];
        this.trigger( 'search:clear', this );
        this.renderHdas();
        return this;
    },

    // ........................................................................ loading indicator
    /** hide the panel and display a loading indicator (in the panel's parent) when history model's are switched */
    _showLoadingIndicator : function( msg, speed, callback ){
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
    _hideLoadingIndicator : function( speed, callback ){
        speed = ( speed !== undefined )?( speed ):( this.fxSpeed );
        if( this.indicator ){
            this.indicator.hide( speed, callback );
        }
    },

    // ........................................................................ (error) messages
    /** Display a message in the top of the panel.
     *  @param {String} type    type of message ('done', 'error', 'warning')
     *  @param {String} msg     the message to display
     *  @param {Object or HTML} modal contents displayed when the user clicks 'details' in the message
     */
    displayMessage : function( type, msg, details ){
        //precondition: msgContainer must have been rendered even if there's no model
        var panel = this;
        //this.log( 'displayMessage', type, msg, details );

        this.scrollToTop();
        var $msgContainer = this.$messages(),
            $msg = $( '<div/>' ).addClass( type + 'message' ).html( msg );
        //this.log( '  ', $msgContainer );

        if( !_.isEmpty( details ) ){
            var $detailsLink = $( '<a href="javascript:void(0)">Details</a>' )
                .click( function(){
                    Galaxy.modal.show( panel._messageToModalOptions( type, msg, details ) );
                    return false;
                });
            $msg.append( ' ', $detailsLink );
        }
        return $msgContainer.html( $msg );
    },

    /** convert msg and details into modal options usable by Galaxy.modal */
    _messageToModalOptions : function( type, msg, details ){
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
        this.$messages().empty();
        return this;
    },

    // ........................................................................ scrolling
    /** get the current scroll position of the panel in its parent */
    scrollPosition : function(){
        return this.$container().scrollTop();
    },

    /** set the current scroll position of the panel in its parent */
    scrollTo : function( pos ){
        this.$container().scrollTop( pos );
        return this;
    },

    /** Scrolls the panel to the top. */
    scrollToTop : function(){
        this.$container().scrollTop( 0 );
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
        var view = this.hdaViews[ id ];
        //this.scrollIntoView( $viewEl.offset().top );
        this.scrollTo( view.el.offsetTop );
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

    // ........................................................................ misc
    /** Return a string rep of the history */
    toString    : function(){
        return 'ReadOnlyHistoryPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});
//------------------------------------------------------------------------------ TEMPLATES
var _panelTemplate = [
    '<div class="history-controls">',
        '<div class="history-search-controls">',
            '<div class="history-search-input"></div>',
        '</div>',

        '<div class="history-title">',
            '<% if( history.name ){ %>',
                '<div class="history-name"><%= history.name %></div>',
            '<% } %>',
        '</div>',

        '<div class="history-subtitle clear">',
            '<% if( history.nice_size ){ %>',
                '<div class="history-size"><%= history.nice_size %></div>',
            '<% } %>',
            '<div class="history-secondary-actions"></div>',
        '</div>',

        '<% if( history.deleted ){ %>',
            '<div class="warningmessagesmall"><strong>',
                _l( 'You are currently viewing a deleted history!' ),
            '</strong></div>',
        '<% } %>',

        '<div class="message-container">',
            '<% if( history.message ){ %>',
                // should already be localized
                '<div class="<%= history.status %>message"><%= history.message %></div>',
            '<% } %>',
        '</div>',

        '<div class="quota-message errormessage">',
            _l( 'You are over your disk quota' ), '. ',
            _l( 'Tool execution is on hold until your disk usage drops below your allocated quota' ), '.',
        '</div>',

        '<div class="tags-display"></div>',
        '<div class="annotation-display"></div>',
        '<div class="history-dataset-actions">',
            '<div class="btn-group">',
                '<button class="history-select-all-datasets-btn btn btn-default"',
                        'data-mode="select">', _l( 'All' ), '</button>',
                '<button class="history-deselect-all-datasets-btn btn btn-default"',
                        'data-mode="select">', _l( 'None' ), '</button>',
            '</div>',
            '<button class="history-dataset-action-popup-btn btn btn-default">',
                _l( 'For all selected' ), '...</button>',
        '</div>',
    '</div>',
    // end history controls

    // where the datasets/hdas are added
    '<div class="datasets-list"></div>',
    '<div class="empty-history-message infomessagesmall">',
        _l( 'This history is empty' ),
    '</div>'
].join( '' );

ReadOnlyHistoryPanel.templates = {
    historyPanel : function( historyJSON ){
        return _.template( _panelTemplate, historyJSON, { variable: 'history' });
    }
};


//==============================================================================
    return {
        ReadOnlyHistoryPanel: ReadOnlyHistoryPanel
    };
});
