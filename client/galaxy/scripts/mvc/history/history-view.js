define([
    "mvc/list/list-view",
    "mvc/history/history-model",
    "mvc/history/history-contents",
    "mvc/history/history-preferences",
    "mvc/history/hda-li",
    "mvc/history/hdca-li",
    "mvc/user/user-model",
    "ui/fa-icon-button",
    "mvc/base-mvc",
    "utils/localization",
    "ui/search-input"
], function(
    LIST_VIEW,
    HISTORY_MODEL,
    HISTORY_CONTENTS,
    HISTORY_PREFS,
    HDA_LI,
    HDCA_LI,
    USER,
    faIconButton,
    BASE_MVC,
    _l
){
'use strict';

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
var _super = LIST_VIEW.ModelListPanel;
var HistoryView = _super.extend(
/** @lends HistoryView.prototype */{
    _logNamespace : 'history',

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
        if( this.model ){
//TODO: move to History.free()
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
        this.on({
            error : function( model, xhr, options, msg, details ){
                this.errorHandler( model, xhr, options, msg, details );
            },
            'loading-done' : function(){
                this.render();
                if( !this.views.length ){
                    this.trigger( 'empty-history', this );
                }
            },
            'views:ready view:attached view:removed' : function( view ){
                this._renderSelectButton();
            }
        });
        // this.on( 'all', function(){ console.debug( arguments ); });
    },

    // ------------------------------------------------------------------------ inf. scrolling
    /** @type {Number} ms to debounce scroll handler for infinite scrolling */
    INFINITE_SCROLL_DEBOUNCE_MS : 40,
    /** @type {Number} number of px (or less) from the bottom the scrollbar should be before fetching */
    INFINITE_SCROLL_FETCH_THRESHOLD_PX : 128,

    /** override to track the scroll container for this view */
    _setUpBehaviors : function( $where ){
        var self = this,
            $newRender = _super.prototype._setUpBehaviors.call( this, $where );
        // this needs to be handled outside the events hash since we're accessing the scollContainer
        // (rebind and debounce the method so we can cache for any later removal)
        self.scrollHandler = _.debounce( _.bind( this.scrollHandler, self ), self.INFINITE_SCROLL_DEBOUNCE_MS );
        self.$scrollContainer( $where ).on( 'scroll', self.scrollHandler );
        return self;
    },

    /**  */
    scrollHandler : function( ev ){
        var self = this;
        var pxToBottom = self._scrollDistanceToBottom();

        // if the scrollbar is past the trigger point, we're not already fetching,
        // AND we're not displaying some panel OVER this one: fetch more contents
        // note: is( :visible ) won't work here - it's still visible when this is covered with other panels
        if( pxToBottom < self.INFINITE_SCROLL_FETCH_THRESHOLD_PX && !self._fetching && _.isEmpty( self.panelStack ) ){
            self.listenToOnce( self.model.contents, 'sync', self.bulkAppendItemViews );
            // TODO: gotta be a better way than a _fetching flag
            self._fetching = true;
            self.model.contents.fetchMore({ silent : true, useSync: true })
                .always( function(){ delete self._fetching; });
        }
    },

    /** return the number of px the scrollbar has until it bottoms out */
    _scrollDistanceToBottom : function(){
        var $container = this.$scrollContainer();
        var pxToBottom = this.$el.outerHeight() - ( $container.scrollTop() + $container.innerHeight() );
        return pxToBottom;
    },

    /**  */
    showContentsLoadingIndicator : function( speed ){
        speed = _.isNumber( speed )? speed : this.fxSpeed;
        if( this.$emptyMessage().is( ':visible' ) ){
            this.$emptyMessage().hide();
        }
        // look for an existing indicator and stop all animations on it, otherwise make one
        var $indicator = this.$( '.contents-loading-indicator' );
        if( $indicator.size() ){
            return $indicator.clearQueue().stop();
        }

        // move it to the bottom and fade it in
        // $indicator = $( '<div class="contents-loading-indicator">' + _l( 'Loading...' ) + '</div>' ).hide();
        $indicator = $( '<div class="contents-loading-indicator"><span class="fa fa-2x fa-spin fa-spinner"></span></div>' ).hide();
        return $indicator
            .insertAfter( this.$( '> .list-items' ) )
            .slideDown( speed );
    },

    /**  */
    hideContentsLoadingIndicator : function( speed ){
        speed = _.isNumber( speed )? speed : this.fxSpeed;
        this.$( '> .contents-loading-indicator' ).hide({ duration: 0, complete: function _complete(){
            $( this ).remove();
        }});
    },

    // ------------------------------------------------------------------------ loading history/hda models
    /**  */
    loadHistory : function( historyId, options, contentsOptions ){
        this.info( 'loadHistory:', historyId, options, contentsOptions );
        var self = this;
        self.setModel( new HISTORY_MODEL.History({ id : historyId }) );
        //TODO:?? cache histories?

        self.trigger( 'loading' );
        return self.model
            .fetchWithContents( options, contentsOptions )
            .always( function(){
                self.trigger( 'loading-done' );
            });
    },

    /** convenience alias to the model. Updates the item list only (not the history) */
    refreshContents : function( options ){
        if( this.model ){
            return this.model.refresh( options );
        }
        // may have callbacks - so return an empty promise
        return $.when();
    },

    /** release/free/shutdown old models and set up panel for new models
     *  @fires new-model with the panel as parameter
     */
    setModel : function( model, attributes ){
        attributes = attributes || {};
        _super.prototype.setModel.call( this, model, attributes );
        if( this.model ){
            this._setUpWebStorage();
        }
    },

    /** Override to reset web storage when the id changes (since it needs the id) */
    _setUpModelListeners : function(){
        _super.prototype._setUpModelListeners.call( this );
        return this.listenTo( this.model, {
            'change:id' : this._setUpWebStorage,
        });
    },

    /** Override to reset web storage when the id changes (since it needs the id) */
    _setUpCollectionListeners : function(){
        _super.prototype._setUpCollectionListeners.call( this );
        return this.listenTo( this.collection, {
            // 'all' : function(){ console.log( this.collection + ':', arguments ); },
            'fetching-more'     : this.showContentsLoadingIndicator,
            'fetching-more-done': this.hideContentsLoadingIndicator,
        });
    },

    // ------------------------------------------------------------------------ browser stored prefs
    /** Set up client side storage. Currently PersistanStorage keyed under 'history:<id>'
     *  @see PersistentStorage
     */
    _setUpWebStorage : function(){
        if( !this.model || !this.model.id ){ return this; }
        //this.log( '_setUpWebStorage', initiallyExpanded, show_deleted, show_hidden );
        if( this.storage ){
            this.stopListening( this.storage );
        }

        this.storage = new HISTORY_PREFS.HistoryPrefs({
            id: HISTORY_PREFS.HistoryPrefs.historyStorageKey( this.model.get( 'id' ) )
        });
        this.trigger( 'new-storage', this.storage, this );
        this.log( this + ' (init\'d) storage:', this.storage.get() );

// TODO: reverse this - have storage reflect what's used in the view and not visversa
        this.listenTo( this.storage, {
            'change:show_deleted' : function( view, newVal ){
                this.showDeleted = newVal;
            },
            'change:show_hidden' : function( view, newVal ){
                this.showHidden = newVal;
            }
        }, this );
        this.showDeleted = this.storage.get( 'show_deleted' ) || false;
        this.showHidden  = this.storage.get( 'show_hidden' ) || false;

        return this;
    },

    // ------------------------------------------------------------------------ panel rendering
    /** In this override, add a btn to toggle the selectors */
    _buildNewRender : function(){
        var $newRender = _super.prototype._buildNewRender.call( this );
        this._renderSelectButton( $newRender );
        return $newRender;
    },

    /** override to avoid showing intial empty message using contents_shown */
    _renderEmptyMessage : function( $whereTo ){
        var self = this;
        var empty = !self.model.get( 'contents_shown' ).shown;
        var $emptyMsg = self.$emptyMessage( $whereTo );

        if( empty ){
            return $emptyMsg.empty().append( self.emptyMsg ).show();

        } else if( self.searchFor && self.model.contents.haveSearchDetails() && !self.views.length ){
            return $emptyMsg.empty().append( self.noneFoundMsg ).show();
        }
        return $();
    },

    /** button for starting select mode */
    _renderSelectButton : function( $where ){
        $where = $where || this.$el;
        // do not render selector option if no actions
        if( !this.multiselectActions().length ){
            return null;
        }
        // do not render (and remove even) if nothing to select
        if( !this.views.length ){
            this.hideSelectors();
            $where.find( '.controls .actions .show-selectors-btn' ).remove();
            return null;
        }
        // don't bother rendering if there's one already
        var $existing = $where.find( '.controls .actions .show-selectors-btn' );
        if( $existing.size() ){
            return $existing;
        }

        return faIconButton({
            title   : _l( 'Operations on multiple datasets' ),
            classes : 'show-selectors-btn',
            faIcon  : 'fa-check-square-o'
        }).prependTo( $where.find( '.controls .actions' ) );
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
            && ( !model.hidden() || panel.showHidden )
            && ( !model.isDeletedOrPurged() || panel.showDeleted ) );
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
        return panel.listenTo( view, {
            'expanded': function( v ){
                panel.storage.addExpanded( v.model );
            },
            'collapsed': function( v ){
                panel.storage.removeExpanded( v.model );
            }
        });
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
        'click .show-selectors-btn'         : 'toggleSelectors',
        // allow (error) messages to be clicked away
        'click .messages [class$=message]'  : 'clearMessages'
    }),

    /** Toggle and store the deleted visibility and re-render items
     * @returns {Boolean} new show_deleted setting
     */
    toggleShowDeleted : function( show, store ){
        show = ( show !== undefined )?( show ):( !this.showDeleted );
        store = ( store !== undefined )?( store ):( true );
        var self = this;

        self.showDeleted = show;
        //TODO: at this point deleted/hidden makes more sense (simpler) in the collection
        self.model.contents.includeDeleted = show;
        self.trigger( 'show-deleted', show );
        if( store ){ self.storage.set( 'show_deleted', show ); }

        // this seems brittle or at least not cohesive with the other non-hid approaches
        var lastHid = self.collection.last().get( 'hid' );
        console.log( 'lastHid:', lastHid );
        var fetch = jQuery.when();
        if( show ){
            fetch = self.model.contents.fetchDeleted({
                silent  : true,
                filters : { 'hid-ge' : lastHid }
            });
        }
        fetch.done( function(){ self.renderItems(); });

        return self.showDeleted;
    },

    /** Toggle and store whether to render explicity hidden contents
     * @returns {Boolean} new show_hidden setting
     */
    toggleShowHidden : function( show, store ){
        show = ( show !== undefined )?( show ):( !this.showHidden );
        store = ( store !== undefined )?( store ):( true );
        var self = this;

        self.showHidden = show;
        self.model.contents.includeHidden = show;
        self.trigger( 'show-hidden', show );
        if( store ){
            self.storage.set( 'show_hidden', show );
        }
        var fetch = jQuery.when();
        if( show ){
            fetch = self.model.contents.fetchHidden({
                silent  : true,
            });
        }
        fetch.done( function(){ self.renderItems(); });

        return self.showHidden;
    },

    /** On the first search, if there are no details - load them, then search */
    _firstSearch : function( searchFor ){
        var self = this,
            inputSelector = '> .controls .search-input';
        this.log( 'onFirstSearch', searchFor );

        console.log( '_firstSearch:', self.model.contents.haveDetails() );
        if( self.model.contents.haveDetails() ){
            self.searchItems( searchFor );
            return;
        }

        self.$el.find( inputSelector ).searchInput( 'toggle-loading' );
        // self.model.contents.fetchAllDetails({ silent: true })
        self.model.contents.progressivelyFetchDetails({ silent: true })
            .progress( function( response, limit, offset ){
                // console.log( 'progress:', offset, offset + response.length );
                self.listenToOnce( self.model.contents, 'sync', self.bulkAppendItemViews );
            })
            .always( function(){
                self.$el.find( inputSelector ).searchInput( 'toggle-loading' );
            })
            .done( function(){
                self.searchItems( self.searchFor );
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

        // interrupted ajax
        if( xhr && xhr.status === 0 && xhr.readyState === 0 ){
            //TODO: gmail style 'retrying in Ns'

        // bad gateway
        } else if( xhr && xhr.status === 502 ){
            //TODO: gmail style 'retrying in Ns'

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
        var user = Galaxy.user,
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
        return $msgContainer.append( $msg );
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
        var $target = !_.isUndefined( ev )?
            $( ev.currentTarget )
            :this.$messages().children( '[class$="message"]' );
        $target.fadeOut( this.fxSpeed, function(){
            $( this ).remove();
        });
        return this;
    },

    // ........................................................................ scrolling
    /** Scrolls the panel to show the content sub-view with the given hid.
     *  @param {Integer} hid    the hid of item to scroll into view
     *  @returns {HistoryView} the panel
     */
    scrollToHid : function( hid ){
        return this.scrollToItem( _.first( this.viewsWhereModel({ hid: hid }) ) );
    },

    // ........................................................................ misc
    /** Return a string rep of the history */
    toString : function(){
        return 'HistoryView(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


//------------------------------------------------------------------------------ TEMPLATES
HistoryView.prototype.templates = (function(){

    var controlsTemplate = BASE_MVC.wrapTemplate([
        '<div class="controls">',
            '<div class="title">',
                '<div class="name"><%- history.name %></div>',
            '</div>',
            '<div class="subtitle"></div>',
            '<div class="history-size"><%- history.nice_size %></div>',

            '<div class="actions"></div>',

            '<div class="messages">',
                '<% if( history.deleted && history.purged ){ %>',
                    '<div class="deleted-msg warningmessagesmall">',
                        _l( 'This history has been purged and deleted' ),
                    '</div>',
                '<% } else if( history.deleted ){ %>',
                    '<div class="deleted-msg warningmessagesmall">',
                        _l( 'This history has been deleted' ),
                    '</div>',
                '<% } else if( history.purged ){ %>',
                    '<div class="deleted-msg warningmessagesmall">',
                        _l( 'This history has been purged' ),
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
                '<div class="list-action-menu btn-group">',
                '</div>',
            '</div>',
        '</div>'
    ], 'history' );

    return _.extend( _.clone( _super.prototype.templates ), {
        controls : controlsTemplate
    });
}());


//==============================================================================
    return {
        HistoryView: HistoryView
    };
});
