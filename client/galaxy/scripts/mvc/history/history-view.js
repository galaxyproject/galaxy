define([
    "mvc/list/list-view",
    "mvc/history/history-model",
    "mvc/history/history-contents",
    "mvc/history/history-preferences",
    "mvc/history/hda-li",
    "mvc/history/hdca-li",
    "mvc/user/user-model",
    "mvc/ui/error-modal",
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
    ERROR_MODAL,
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

    /** create and return a collection for when none is initially passed */
    _createDefaultCollection : function(){
        // override
        return new this.collectionClass([], { history: history });
    },

    /** In this override, clear the update timer on the model */
    freeModel : function(){
        _super.prototype.freeModel.call( this );
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

    // ------------------------------------------------------------------------ loading history/hda models
    /** load the history with the given id then it's contents, sending ajax options to both */
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

    /** override to avoid showing intial empty message using contents_active */
    _renderEmptyMessage : function( $whereTo ){
        var self = this;
        var empty = !self.model.get( 'contents_active' ).active;
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

    // ------------------------------------------------------------------------ client-side pagination
    /**   */
    renderItems : function( $whereTo ){
        $whereTo = $whereTo || this.$el;
        var self = this;
        var contents = self.model.contents;
        var hidsPerSection = contents.hidsPerSection;

        // if there's less than 500 *shown*
        var contents_active = self.model.get( 'contents_active' ) || 0;
        if( contents_active.active < hidsPerSection ){
            return _super.prototype.renderItems.call( self, $whereTo );
        }

        // render sections
        self.$list( $whereTo ).html( contents._mapSectionRanges( function( section ){
            return self.templates.listItemsSection( section );
        }).join( '\n' ));
        // render views from collection for the current section, replacing that section marker with them
        // note: shows only one section's worth of views at a time
        self.views = self._getCurrentSectionCollection().map( function( itemModel ){
            return self._createItemView( itemModel );
        });
        // console.log( self.$currentSection( $whereTo ) );
        self.$emptyMessage( $whereTo ).hide();
        self.$currentSection( $whereTo ).replaceWith( self.views.map( function( view ){
            return self._renderItemView$el( view );
        }));

        self.trigger( 'views:ready', self.views );
        return self.views;
    },

    _getCurrentSectionCollection : function(){
        return this.model.contents._filterCurrentSectionCollection( _.bind( this._filterItem, this ) );
    },

    /** list-items: where the subviews are contained in the view's dom */
    $currentSection : function( $where ){
        var selector = '.list-items-section[data-section="' + this.model.contents.currentSection + '"]';
        return this.$list( $where ).find( selector );
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

    /** override to remove expandedIds from webstorage */
    collapseAll : function(){
        this.storage.set( 'expandedIds', {} );
        _super.prototype.collapseAll.call( this );
    },

    // ------------------------------------------------------------------------ selection
    /** Override to correctly set the historyId of the new collection */
    getSelectedModels : function(){
        var collection = _super.prototype.getSelectedModels.call( this );
        collection.historyId = this.collection.historyId;
        return collection;
    },

    /** show the user that the contents are loading/contacting the server */
    showContentsLoadingIndicator : function( speed ){
        speed = _.isNumber( speed )? speed : this.fxSpeed;
        if( this.$emptyMessage().is( ':visible' ) ){
            this.$emptyMessage().hide();
        }
        // look for an existing indicator and stop all animations on it, otherwise make one
        var $indicator = this.$( '.contents-loading-indicator' );
        if( $indicator.size() ){
            return $indicator.stop().clearQueue();
        }

        // move it to the bottom and fade it in
        // $indicator = $( '<div class="contents-loading-indicator">' + _l( 'Loading...' ) + '</div>' ).hide();
        $indicator = $( this.templates.contentsLoadingIndicator( {}, this )).hide();
        return $indicator
            .insertAfter( this.$( '> .list-items' ) )
            .slideDown( speed );
    },

    /** show the user we're done loading */
    hideContentsLoadingIndicator : function( speed ){
        speed = _.isNumber( speed )? speed : this.fxSpeed;
        this.$( '> .contents-loading-indicator' ).slideUp({ duration: 100, complete: function _complete(){
            $( this ).remove();
        }});
    },

    // ------------------------------------------------------------------------ panel events
    /** event map */
    events : _.extend( _.clone( _super.prototype.events ), {
        // toggle list item selectors
        'click .show-selectors-btn'         : 'toggleSelectors',
        // allow (error) messages to be clicked away
        'click .messages [class$=message]'  : 'clearMessages',
        'click .list-items-section' : function( ev ){
            this.openSection( $( ev.currentTarget ).data( 'section' ) );
        }
    }),

    /** loads a section and re-renders items */
    openSection : function( section ){
        var self = this;
        return self.model.contents.fetchSection( section ).done( function(){
            self.model.contents.currentSection = section;
            self.renderItems();
        });
    },

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
        var last = self.collection.last();
        var lastHid = last? last.get( 'hid' ) : 0;
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
        var self = this;
        var inputSelector = '> .controls .search-input';
        var initialContentsLength = self.model.contents.length;
        this.log( 'onFirstSearch', searchFor );

        // if the contents already have enough details to search, search and return now
        if( self.model.contents.haveSearchDetails() ){
            self.searchItems( searchFor );
            return;
        }

        // otherwise, load the details progressively here
        self.$( inputSelector ).searchInput( 'toggle-loading' );
        // TODO?: self.$( inputSelector + ' input' ).prop( 'disabled', true ) ?? not disabling could cause trouble here
        self.model.contents.progressivelyFetchDetails({ silent: true })
            .progress( function( response, limit, offset ){
                // if we're still only merging new attrs to what the contents already have,
                // just render what's there again
                if( offset + response.length <= initialContentsLength ){
                    self.renderItems();
                // if we're adding new items, then listen for sync'ing and bulk add those views
                } else {
                    self.listenToOnce( self.model.contents, 'sync', self.bulkAppendItemViews );
                }
            })
            .always( function(){
                self.$el.find( inputSelector ).searchInput( 'toggle-loading' );
            })
            .done( function(){
                self.searchItems( self.searchFor );
            });
    },

    // ........................................................................ error handling
    /** Event handler for errors (from the panel, the history, or the history's contents)
     *  Alternately use two strings for model and xhr to use custom message and title (respectively)
     *  @param {Model or View} model    the (Backbone) source of the error
     *  @param {XMLHTTPRequest} xhr     any ajax obj. assoc. with the error
     *  @param {Object} options         the options map commonly used with bbone ajax
     */
    errorHandler : function( model, xhr, options ){
        //TODO: to mixin or base model
        // interrupted ajax or no connection
        if( xhr && xhr.status === 0 && xhr.readyState === 0 ){
            // return ERROR_MODAL.offlineErrorModal();
            // fail silently
            return;
        }
        // otherwise, leave something to report in the console
        this.error( model, xhr, options );
        // and feedback to a modal
        // if sent two strings (and possibly details as 'options'), use those as message and title
        if( _.isString( model ) && _.isString( xhr ) ){
            var message = model;
            var title = xhr;
            return ERROR_MODAL.errorModal( message, title, options );
        }
        // bad gateway
        // TODO: possibly to global handler
        if( xhr && xhr.status === 502 ){
            return ERROR_MODAL.badGatewayErrorModal();
        }
        return ERROR_MODAL.ajaxErrorModal( model, xhr, options );
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

    var mainTemplate = BASE_MVC.wrapTemplate([
        // temp container
        '<div>',
            '<div class="controls"></div>',
            '<div class="list-items"></div>',
            '<div class="empty-message infomessagesmall"></div>',
        '</div>'
    ]);

    var controlsTemplate = BASE_MVC.wrapTemplate([
        '<div class="controls">',
            '<div class="title">',
                '<div class="name"><%- history.name %></div>',
            '</div>',
            '<div class="subtitle"></div>',
            '<div class="history-size"><%- history.nice_size %></div>',

            '<div class="actions"></div>',

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

            '<div class="messages">',
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

    var contentsLoadingIndicatorTemplate = BASE_MVC.wrapTemplate([
        '<div class="contents-loading-indicator">',
            '<span class="fa fa-2x fa-spin fa-spinner">',
        '</span></div>'
    ], 'history' );

    var paginationTemplate = BASE_MVC.wrapTemplate([
        '<button class="prev">previous</button>',
        '<% function getHid( content ){ return content? content.get( "hid" ) : "?"; } %>',
        '<button class="pages">',
            '<%- getHid( view.model.contents.last() ) %> to <%- getHid( view.model.contents.first() ) %>',
        '</button>',
        '<button class="next">next</button>',
    ], 'history' );

    var listItemsSectionTemplate = BASE_MVC.wrapTemplate([
        '<li class="list-items-section" data-section="<%- section.number %>">',
            '<a href="javascript:void(0)" data-first-hid="<%- section.first %>" data-last-hid="<%- section.last %>">',
            '<%- section.first %>  ', _l( "to" ), ' <%- section.last %>',
        '</a></li>',
    ], 'section' );

    return _.extend( _.clone( _super.prototype.templates ), {
        el                      : mainTemplate,
        controls                : controlsTemplate,
        contentsLoadingIndicator: contentsLoadingIndicatorTemplate,
        pagination              : paginationTemplate,
        listItemsSection        : listItemsSectionTemplate
    });
}());


//==============================================================================
    return {
        HistoryView: HistoryView
    };
});
