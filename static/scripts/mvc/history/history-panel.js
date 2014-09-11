define([
    "mvc/list/list-panel",
    "mvc/history/history-model",
    "mvc/history/history-contents",
    "mvc/history/hda-li",
    "mvc/history/hdca-li",
    "mvc/collection/collection-panel",
    "mvc/user/user-model",
    "mvc/base-mvc",
    "utils/localization"
], function(
    LIST_PANEL,
    HISTORY_MODEL,
    HISTORY_CONTENTS,
    HDA_LI,
    HDCA_LI,
    COLLECTION_PANEL,
    USER,
    BASE_MVC,
    _l
){
// ============================================================================
/** session storage for individual history preferences */
var HistoryPrefs = BASE_MVC.SessionStorageModel.extend(
/** @lends HistoryPrefs.prototype */{
//TODO:?? possibly mark as current T/F - have History.currId() (a class method) return that value
    defaults : {
//TODO:?? expandedIds to array?
        expandedIds : {},
        //TODO:?? move to user?
        show_deleted : false,
        show_hidden  : false
        //TODO: add scroll position?
    },
    /** add an hda id to the hash of expanded hdas */
    addExpanded : function( model ){
        var key = 'expandedIds';
//TODO:?? is this right anymore?
        this.save( key, _.extend( this.get( key ), _.object([ model.id ], [ model.get( 'id' ) ]) ) );
    },
    /** remove an hda id from the hash of expanded hdas */
    removeExpanded : function( model ){
        var key = 'expandedIds';
        this.save( key, _.omit( this.get( key ), model.id ) );
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
 *  Allows:
 *      changing the loaded history
 *      displaying data, info, and download
 *      tracking history attrs: size, tags, annotations, name, etc.
 *  Does not allow:
 *      changing the name
 */
var _super = LIST_PANEL.ModelListPanel;
var HistoryPanel = _super.extend(
/** @lends HistoryPanel.prototype */{

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    /** class to use for constructing the HDA views */
    HDAViewClass        : HDA_LI.HDAListItemView,
    /** class to use for constructing the HDCA views */
    HDCAViewClass       : HDCA_LI.HDCAListItemView,
    /** class to used for constructing collection of sub-view models */
    collectionClass     : HISTORY_CONTENTS.HistoryContents,
    /** key of attribute in model to assign to this.collection */
    modelCollectionKey  : 'contents',

    tagName             : 'div',
    className           : _super.prototype.className + ' history-panel',

    /** string to display when the collection is empty */
    emptyMsg            : _l( 'This history is empty' ),
    /** displayed when no items match the search terms */
    noneFoundMsg        : _l( 'No matching datasets found' ),
    /** string used for search placeholder */
    searchPlaceholder   : _l( 'search datasets' ),

    // ......................................................................... SET UP
    /** Set up the view, bind listeners.
     *  @param {Object} attributes optional settings for the panel
     */
    initialize : function( attributes ){
        _super.prototype.initialize.call( this, attributes );
        // ---- instance vars
        // control contents/behavior based on where (and in what context) the panel is being used
        /** where should pages from links be displayed? (default to new tab/window) */
        this.linkTarget = attributes.linkTarget || '_blank';
    },

    /** In this override, clear the update timer on the model */
    freeModel : function(){
        _super.prototype.freeModel.call( this );
//TODO: move to History.free()
        if( this.model ){
            this.model.clearUpdateTimeout();
        }
        return this;
    },

    /** create any event listeners for the panel
     *  @fires: rendered:initial    on the first render
     *  @fires: empty-history       when switching to a history with no contents or creating a new history
     */
    _setUpListeners : function(){
        _super.prototype._setUpListeners.call( this );

        this.on( 'error', function( model, xhr, options, msg, details ){
            this.errorHandler( model, xhr, options, msg, details );
        });

        this.on( 'loading-done', function(){
            //TODO:?? if( this.collection.length ){
            if( !this.views.length ){
                this.trigger( 'empty-history', this );
            }
        });
    },

    // ------------------------------------------------------------------------ loading history/hda models
    //NOTE: all the following fns replace the existing history model with a new model
    // (in the following 'details' refers to the full set of contents api data (urls, display_apps, misc_info, etc.)
    //  - contents w/o details will have summary data only (name, hid, deleted, visible, state, etc.))
//TODO: too tangled...

    /** loads a history & contents, getting details of any contents whose ids are stored in sessionStorage
     *      (but does not make them the current history)
     */
    loadHistoryWithDetails : function( historyId, attributes, historyFn, contentsFn ){
        this.info( 'loadHistoryWithDetails:', historyId, attributes, historyFn, contentsFn );
        var detailIdsFn = function( historyData ){
                // will be called to get content ids that need details from the api
//TODO:! non-visible contents are getting details loaded... either stop loading them at all or filter ids thru isVisible
                return _.values( HistoryPrefs.get( historyData.id ).get( 'expandedIds' ) );
            };
        return this.loadHistory( historyId, attributes, historyFn, contentsFn, detailIdsFn );
    },

    /** loads a history & contents (but does not make them the current history) */
    loadHistory : function( historyId, attributes, historyFn, contentsFn, detailIdsFn ){
        this.info( 'loadHistory:', historyId, attributes, historyFn, contentsFn, detailIdsFn );
        var panel = this;
        attributes = attributes || {};

        panel.trigger( 'loading', panel );
        //this.info( 'loadHistory:', historyId, attributes, historyFn, contentsFn, detailIdsFn );
        var xhr = HISTORY_MODEL.History.getHistoryData( historyId, {
                historyFn       : historyFn,
                contentsFn      : contentsFn,
                detailIdsFn     : attributes.initiallyExpanded || detailIdsFn
            });

        return panel._loadHistoryFromXHR( xhr, attributes )
            .fail( function( xhr, where, history ){
                // throw an error up for the error handler
                panel.trigger( 'error', panel, xhr, attributes, _l( 'An error was encountered while ' + where ),
                    { historyId: historyId, history: history || {} });
            })
            .always( function(){
                // bc _hideLoadingIndicator relies on this firing
                panel.trigger( 'loading-done', panel );
            });
    },

    /** given an xhr that will provide both history and contents data, pass data to set model or handle xhr errors */
    _loadHistoryFromXHR : function( xhr, attributes ){
        var panel = this;
        xhr.then( function( historyJSON, contentsJSON ){
            panel.JSONToModel( historyJSON, contentsJSON, attributes );
            panel.render();
        });
        xhr.fail( function( xhr, where ){
            // render anyways - whether we get a model or not
            panel.render();
        });
        return xhr;
    },

    /** convenience alias to the model. Updates the item list only (not the history) */
    refreshContents : function( detailIds, options ){
        if( this.model ){
            return this.model.refresh( detailIds, options );
        }
        // may have callbacks - so return an empty promise
        return $.when();
    },

//TODO:?? seems unneccesary
//TODO: Maybe better in History?
    /** create a new history model from JSON and call setModel on it */
    JSONToModel : function( newHistoryJSON, newHdaJSON, attributes ){
        this.log( 'JSONToModel:', newHistoryJSON, newHdaJSON, attributes );
        attributes = attributes || {};
        //this.log( 'JSONToModel:', newHistoryJSON, newHdaJSON.length, attributes );

        var model = new HISTORY_MODEL.History( newHistoryJSON, newHdaJSON, attributes );
//TODO:?? here?
        this.setModel( model );
        return model;
    },

    /** release/free/shutdown old models and set up panel for new models
     *  @fires new-model with the panel as parameter
     */
    setModel : function( model, attributes ){
        attributes = attributes || {};
        _super.prototype.setModel.call( this, model, attributes );
        if( this.model ){
            this._setUpWebStorage( attributes.initiallyExpanded, attributes.show_deleted, attributes.show_hidden );
        }
    },

    // ------------------------------------------------------------------------ browser stored prefs
    /** Set up client side storage. Currently PersistanStorage keyed under 'HistoryPanel.<id>'
     *  @param {Object} initiallyExpanded
     *  @param {Boolean} show_deleted whether to show deleted contents (overrides stored)
     *  @param {Boolean} show_hidden
     *  @see PersistentStorage
     */
    _setUpWebStorage : function( initiallyExpanded, show_deleted, show_hidden ){
        //if( !this.model ){ return this; }
        //this.log( '_setUpWebStorage', initiallyExpanded, show_deleted, show_hidden );
        this.storage = new HistoryPrefs({
            id: HistoryPrefs.historyStorageKey( this.model.get( 'id' ) )
        });

        // expandedIds is a map of content.ids -> a boolean repr'ing whether that item's body is already expanded
        // store any pre-expanded ids passed in
        if( _.isObject( initiallyExpanded ) ){
            this.storage.set( 'expandedIds', initiallyExpanded );
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

    // ------------------------------------------------------------------------ panel rendering
    /** In this override, add a btn to toggle the selectors */
    _buildNewRender : function(){
        var $newRender = _super.prototype._buildNewRender.call( this );
        if( this.multiselectActions.length ){
            $newRender.find( '.controls .actions' ).prepend( this._renderSelectButton() );
        }
        return $newRender;
    },

    /** button for starting select mode */
    _renderSelectButton : function( $where ){
        return faIconButton({
            title   : _l( 'Operations on multiple datasets' ),
            classes : 'show-selectors-btn',
            faIcon  : 'fa-check-square-o'
        });
    },

    // ------------------------------------------------------------------------ sub-views
    /** In this override, since history contents are mixed,
     *      get the appropo view class based on history_content_type
     */
    _getItemViewClass : function( model ){
        var contentType = model.get( "history_content_type" );
        switch( contentType ){
            case 'dataset':
                return this.HDAViewClass;
            case 'dataset_collection':
                return this.HDCAViewClass;
        }
        throw new TypeError( 'Unknown history_content_type: ' + contentType );
    },

    /** in this override, check if the contents would also display based on show_deleted/hidden */
    _filterItem : function( model ){
        var panel = this;
        return ( _super.prototype._filterItem.call( panel, model )
            && ( !model.hidden() || panel.storage.get( 'show_hidden' ) )
            && ( !model.isDeletedOrPurged() || panel.storage.get( 'show_deleted' ) ) );
    },

    /** in this override, add a linktarget, and expand if id is in web storage */
    _getItemViewOptions : function( model ){
        var options = _super.prototype._getItemViewOptions.call( this, model );
        return _.extend( options, {
            linkTarget      : this.linkTarget,
            expanded        : !!this.storage.get( 'expandedIds' )[ model.id ],
            hasUser         : this.model.ownedByCurrUser()
        });
    },

    /** In this override, add/remove expanded/collapsed model ids to/from web storage */
    _setUpItemViewListeners : function( view ){
        var panel = this;
        _super.prototype._setUpItemViewListeners.call( panel, view );

        //TODO:?? could use 'view:expanded' here?
        // maintain a list of items whose bodies are expanded
        view.on( 'expanded', function( v ){
            panel.storage.addExpanded( v.model );
        });
        view.on( 'collapsed', function( v ){
            panel.storage.removeExpanded( v.model );
        });
        return this;
    },

    // ------------------------------------------------------------------------ selection
    /** Override to correctly set the historyId of the new collection */
    getSelectedModels : function(){
        var collection = _super.prototype.getSelectedModels.call( this );
        collection.historyId = this.collection.historyId;
        return collection;
    },

    // ------------------------------------------------------------------------ panel events
    /** event map */
    events : _.extend( _.clone( _super.prototype.events ), {
        // toggle list item selectors
        'click .show-selectors-btn'                 : 'toggleSelectors'
        // allow (error) messages to be clicked away
//TODO: switch to common close (X) idiom
        //'click .messages'               : 'clearMessages',
//TODO: remove
        //'click .history-search-btn'     : 'toggleSearchControls'
    }),

    /** Handle the user toggling the deleted visibility by:
     *      (1) storing the new value in the persistent storage
     *      (2) re-rendering the history
     * @returns {Boolean} new show_deleted setting
     */
    toggleShowDeleted : function( show ){
        show = ( show !== undefined )?( show ):( !this.storage.get( 'show_deleted' ) );
        this.storage.set( 'show_deleted', show );
        //TODO:?? to events on storage('change:show_deleted')
        this.renderItems();
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
        //TODO:?? to events on storage('change:show_hidden')
        this.renderItems();
        return this.storage.get( 'show_hidden' );
    },

    /** On the first search, if there are no details - load them, then search */
    _firstSearch : function( searchFor ){
        var panel = this,
            inputSelector = '.history-search-input';
        this.log( 'onFirstSearch', searchFor );

        if( panel.model.contents.haveDetails() ){
            panel.searchItems( searchFor );
            return;
        }

        panel.$el.find( inputSelector ).searchInput( 'toggle-loading' );
        panel.model.contents.fetchAllDetails({ silent: true })
            .always( function(){
                panel.$el.find( inputSelector ).searchInput( 'toggle-loading' );
            })
            .done( function(){
                panel.searchItems( searchFor );
            });
    },

//TODO: break this out
    // ........................................................................ error handling
    /** Event handler for errors (from the panel, the history, or the history's contents)
     *  @param {Model or View} model    the (Backbone) source of the error
     *  @param {XMLHTTPRequest} xhr     any ajax obj. assoc. with the error
     *  @param {Object} options         the options map commonly used with bbone ajax
     *  @param {String} msg             optional message passed to ease error location
     *  @param {Object} msg             optional object containing error details
     */
    errorHandler : function( model, xhr, options, msg, details ){
        this.error( model, xhr, options, msg, details );
//TODO: getting JSON parse errors from jq migrate

        // interrupted ajax
        if( xhr && xhr.status === 0 && xhr.readyState === 0 ){

        // bad gateway
        } else if( xhr && xhr.status === 502 ){
//TODO: gmail style 'reconnecting in Ns'

        // otherwise, show an error message inside the panel
        } else {
            // if sentry is available, attempt to get the event id
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
    _parseErrorMessage : function( model, xhr, options, msg, details, sentryId ){
        //if( xhr.responseText ){
        //    xhr.responseText = _.escape( xhr.responseText );
        //}
        var user = Galaxy.currUser,
            // add the args (w/ some extra info) into an obj
            parsed = {
                message : this._bePolite( msg ),
                details : {
                    message : msg,
                    raven   : ( window.Raven && _.isFunction( Raven.lastEventId) )?
                                    ( Raven.lastEventId() ):( undefined ),
                    agent   : navigator.userAgent,
                    // add ajax data from Galaxy object cache
                    url     : ( window.Galaxy )?( Galaxy.lastAjax.url ):( undefined ),
                    data    : ( window.Galaxy )?( Galaxy.lastAjax.data ):( undefined ),
                    options : ( xhr )?( _.omit( options, 'xhr' ) ):( options ),
                    xhr     : xhr,
                    source  : ( _.isFunction( model.toJSON ) )?( model.toJSON() ):( model + '' ),
                    user    : ( user instanceof USER.User )?( user.toJSON() ):( user + '' )
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
            options = { title: 'Details' };
        if( _.isObject( details ) ){

            details = _.omit( details, _.functions( details ) );
            var text = JSON.stringify( details, null, '  ' ),
                pre = $( '<pre/>' ).text( text );
            options.body = $( '<div/>' ).append( pre );

        } else {
            options.body = $( '<div/>' ).html( details );
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

    /** Remove all messages from the panel. */
    clearMessages : function( ev ){
        $( ev.currentTarget ).fadeOut( this.fxSpeed, function(){
            $( this ).remove();
        });
        //this.$messages().children().not( '.quota-message' ).remove();
        return this;
    },

    // ........................................................................ scrolling
    /** Scrolls the panel to show the content sub-view with the given hid.
     *  @param {Integer} hid    the hid of item to scroll into view
     *  @returns {HistoryPanel} the panel
     */
    scrollToHid : function( hid ){
        return this.scrollToItem( _.first( this.viewsWhereModel({ hid: hid }) ) );
    },

    // ........................................................................ misc
    /** Return a string rep of the history */
    toString : function(){
        return 'HistoryPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


//------------------------------------------------------------------------------ TEMPLATES
HistoryPanel.prototype.templates = (function(){

    var controlsTemplate = BASE_MVC.wrapTemplate([
        '<div class="controls">',
            '<div class="title">',
                '<div class="name"><%= history.name %></div>',
            '</div>',
            '<div class="subtitle">',
                //'<%= view.collection.length %>', _l( ' items' ),
            '</div>',
            '<div class="history-size"><%= history.nice_size %></div>',

            '<div class="actions"></div>',

            '<div class="messages">',
                '<% if( history.deleted ){ %>',
                    '<div class="deleted-msg warningmessagesmall">',
                        _l( 'This history has been deleted' ),
                    '</div>',
                '<% } %>',

                '<% if( history.message ){ %>',
                    // should already be localized
                    '<div class="<%= history.message.level || "info" %>messagesmall">',
                        '<%= history.message.text %>',
                    '</div>',
                '<% } %>',
            '</div>',

            // add tags and annotations
            '<div class="tags-display"></div>',
            '<div class="annotation-display"></div>',

            '<div class="search">',
                '<div class="search-input"></div>',
            '</div>',

            '<div class="list-actions">',
                '<div class="btn-group">',
                    '<button class="select-all btn btn-default"',
                            'data-mode="select">', _l( 'All' ), '</button>',
                    '<button class="deselect-all btn btn-default"',
                            'data-mode="select">', _l( 'None' ), '</button>',
                '</div>',
                '<button class="list-action-popup-btn btn btn-default">',
                    _l( 'For all selected' ), '...</button>',
            '</div>',
        '</div>'
    ], 'history' );

    return _.extend( _.clone( _super.prototype.templates ), {
        controls : controlsTemplate
    });
}());


//==============================================================================
    return {
        HistoryPanel: HistoryPanel
    };
});
