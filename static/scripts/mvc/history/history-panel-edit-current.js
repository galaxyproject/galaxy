define([
    "mvc/history/history-model",
    "mvc/history/history-panel-edit",
    "mvc/collection/collection-panel",
    "mvc/base-mvc",
    "utils/localization"
], function( HISTORY_MODEL, HPANEL_EDIT, DC_PANEL, BASE_MVC, _l ){
// ============================================================================
/** session storage for history panel preferences (and to maintain state)
 */
var HistoryPanelPrefs = BASE_MVC.SessionStorageModel.extend(
/** @lends HistoryPanelPrefs.prototype */{
    defaults : {
        /** should the tags editor be shown or hidden initially? */
        tagsEditorShown : false,
        /** should the annotation editor be shown or hidden initially? */
        annotationEditorShown : false
    },
    toString : function(){
        return 'HistoryPanelPrefs(' + JSON.stringify( this.toJSON() ) + ')';
    }
});

/** key string to store panel prefs (made accessible on class so you can access sessionStorage directly) */
HistoryPanelPrefs.storageKey = function storageKey(){
    return ( 'history-panel' );
};

/* =============================================================================
TODO:

============================================================================= */
var _super = HPANEL_EDIT.HistoryPanelEdit;
// used in root/index.mako
/** @class View/Controller for the user's current history model as used in the history
 *      panel (current right hand panel) of the analysis page.
 *
 *  The only history panel that will poll for updates.
 */
var CurrentHistoryPanel = _super.extend(
/** @lends CurrentHistoryPanel.prototype */{

    className           : _super.prototype.className + ' current-history-panel',

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    emptyMsg            : _l( "This history is empty. Click 'Get Data' on the left tool menu to start" ),
    noneFoundMsg        : _l( "No matching datasets found" ),

    // ......................................................................... SET UP
    /** Set up the view, set up storage, bind listeners to HistoryContents events */
    initialize : function( attributes ){
        attributes = attributes || {};

        // ---- persistent preferences
        /** maintain state / preferences over page loads */
        this.preferences = new HistoryPanelPrefs( _.extend({
            id : HistoryPanelPrefs.storageKey()
        }, _.pick( attributes, _.keys( HistoryPanelPrefs.prototype.defaults ) )));

        _super.prototype.initialize.call( this, attributes );

        /** sub-views that will overlay this panel (collections) */
        this.panelStack = [];
    },

    // ------------------------------------------------------------------------ loading history/item models
    /** (re-)loads the user's current history & contents w/ details */
    loadCurrentHistory : function( attributes ){
        this.debug( this + '.loadCurrentHistory' );
        // implemented as a 'fresh start' or for when there is no model (intial panel render)
        var panel = this;
        return this.loadHistoryWithDetails( 'current', attributes )
            .then(function( historyData, contentsData ){
                panel.trigger( 'current-history', panel );
            });
    },

    /** loads a history & contents w/ details and makes them the current history */
    switchToHistory : function( historyId, attributes ){
        //this.info( 'switchToHistory:', historyId, attributes );
        var panel = this,
            historyFn = function(){
                // make this current and get history data with one call
                return jQuery.getJSON( galaxy_config.root + 'history/set_as_current?id=' + historyId  );
                //    method  : 'PUT'
                //});
            };
        return this.loadHistoryWithDetails( historyId, attributes, historyFn )
            .then(function( historyData, contentsData ){
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
                // create a new history and save: the server will return the proper JSON
                return jQuery.getJSON( galaxy_config.root + 'history/create_new_current'  );
            };

        // id undefined bc there is no historyId yet - the server will provide
        //  (no need for details - nothing expanded in new history)
        return this.loadHistory( undefined, attributes, historyFn )
            .then(function( historyData, contentsData ){
                panel.trigger( 'new-history', panel );
            });
    },

    /** release/free/shutdown old models and set up panel for new models */
    setModel : function( model, attributes, render ){
        _super.prototype.setModel.call( this, model, attributes, render );
        if( this.model ){
            this.log( 'checking for updates' );
            this.model.checkForUpdates();
        }
        return this;
    },

    // ------------------------------------------------------------------------ history/content event listening
    /** listening for collection events */
    _setUpCollectionListeners : function(){
        _super.prototype._setUpCollectionListeners.call( this );

        // if a hidden item is created (gen. by a workflow), moves thru the updater to the ready state,
        //  then: remove it from the collection if the panel is set to NOT show hidden datasets
        this.collection.on( 'state:ready', function( model, newState, oldState ){
            if( ( !model.get( 'visible' ) )
            &&  ( !this.storage.get( 'show_hidden' ) ) ){
                this.removeItemView( this.viewFromModel( model ) );
            }
        }, this );
    },

    /** listening for history events */
    _setUpModelListeners : function(){
        _super.prototype._setUpModelListeners.call( this );
        // ---- history
        // update the quota meter when current history changes size
//TODO: global - have Galaxy listen to this instead
        if( Galaxy && Galaxy.quotaMeter ){
            this.listenTo( this.model, 'change:nice_size', function(){
                //this.info( '!! model size changed:', this.model.get( 'nice_size' ) )
                Galaxy.quotaMeter.update();
            });
        }

    },

    // ------------------------------------------------------------------------ panel rendering
    /** In this override, handle null models and move the search input to the top */
    _buildNewRender : function(){
        if( !this.model ){ return $(); }
        var $newRender = _super.prototype._buildNewRender.call( this );
        //TODO: hacky
        $newRender.find( '.search' ).prependTo( $newRender.find( '.controls' ) );
        this._renderQuotaMessage( $newRender );
        return $newRender;
    },

    /** render the message displayed when a user is over quota and can't run jobs */
    _renderQuotaMessage : function( $whereTo ){
        $whereTo = $whereTo || this.$el;
        return $( this.templates.quotaMsg( {}, this ) ).prependTo( $whereTo.find( '.messages' ) );
    },

    /** In this override, add links to open data uploader or get data in the tools section */
    _renderEmptyMessage : function( $whereTo ){
        var panel = this,
            $emptyMsg = panel.$emptyMessage( $whereTo ),
            $toolMenu = $( '.toolMenuContainer' );

        if( ( _.isEmpty( panel.views ) && !panel.searchFor )
        &&  ( Galaxy && Galaxy.upload && $toolMenu.size() ) ){
            $emptyMsg.empty();

            $emptyMsg.html([
                _l( 'This history is empty' ), '. ', _l( 'You can ' ),
                '<a class="uploader-link" href="javascript:void(0)">',
                    _l( 'load your own data' ),
                '</a>',
                _l( ' or ' ), '<a class="get-data-link" href="javascript:void(0)">',
                    _l( 'get data from an external source' ),
                '</a>'
            ].join('') );
            $emptyMsg.find( '.uploader-link' ).click( function( ev ){
                Galaxy.upload._eventShow( ev );
            });
            $emptyMsg.find( '.get-data-link' ).click( function( ev ){
                $toolMenu.parent().scrollTop( 0 );
                $toolMenu.find( 'span:contains("Get Data")' )
                    .click();
                    //.fadeTo( 200, 0.1, function(){
                    //    this.debug( this )
                    //    $( this ).fadeTo( 200, 1.0 );
                    //});
            });
            return $emptyMsg.show();
        }
        return _super.prototype._renderEmptyMessage.call( this, $whereTo );
    },

    /** In this override, get and set current panel preferences when editor is used */
    _renderTags : function( $where ){
        var panel = this;
        // render tags and show/hide based on preferences
        _super.prototype._renderTags.call( this, $where );
        if( this.preferences.get( 'tagsEditorShown' ) ){
            this.tagsEditor.toggle( true );
        }
        // store preference when shown or hidden
        this.tagsEditor.on( 'hiddenUntilActivated:shown hiddenUntilActivated:hidden',
            function( tagsEditor ){
                panel.preferences.set( 'tagsEditorShown', tagsEditor.hidden );
            });
    },
    /** In this override, get and set current panel preferences when editor is used */
    _renderAnnotation : function( $where ){
        var panel = this;
        // render annotation and show/hide based on preferences
        _super.prototype._renderAnnotation.call( this, $where );
        if( this.preferences.get( 'annotationEditorShown' ) ){
            this.annotationEditor.toggle( true );
        }
        // store preference when shown or hidden
        this.annotationEditor.on( 'hiddenUntilActivated:shown hiddenUntilActivated:hidden',
            function( annotationEditor ){
                panel.preferences.set( 'annotationEditorShown', annotationEditor.hidden );
            });
    },

    // ------------------------------------------------------------------------ sub-views
    /** Override to reverse order of views - newest contents on top */
    _attachItems : function( $whereTo ){
        this.$list( $whereTo ).append( this.views.reverse().map( function( view ){
            return view.$el;
        }));
        return this;
    },

    /** In this override, handle collection expansion. */
    _setUpItemViewListeners : function( view ){
        var panel = this;
        _super.prototype._setUpItemViewListeners.call( panel, view );

        if( view instanceof panel.HDCAViewClass ){
            view.off( 'expanded' );
            view.on( 'expanded', function( collectionView ){
                panel.info( 'expanded', collectionView );
                panel._addCollectionPanel( collectionView );
            });
            view.off( 'collapsed' );
        }
    },

    /** In this override, handle collection expansion. */
    _addCollectionPanel : function( collectionView ){
        var panel = this,
            collectionModel = collectionView.model;

        this.debug( 'history panel (stack), collectionModel:', collectionModel );
        var overlaid = new ( this._getCollectionPanelClass( collectionModel ) )({
                model           : collectionModel,
                HDAViewClass    : this.HDAViewClass,
                parentName      : this.model.get( 'name' ),
                linkTarget      : this.linkTarget
            });
        panel.panelStack.push( overlaid );

        panel.$( '.controls' ).add( panel.$list() ).hide();
        panel.$el.append( overlaid.$el );
        overlaid.on( 'close', function(){
            panel.render();
            collectionView.collapse();
            panel.panelStack.pop();
        });

        //TODO: to hdca-model, hasDetails
        if( !overlaid.model.hasDetails() ){
            var xhr = overlaid.model.fetch();
            xhr.done( function(){
                //this.debug( 'collection data fetched' );
                //this.debug( JSON.stringify( overlaid.model.toJSON(), null, '  ' ) );
                //TODO: (re-)render collection contents
                overlaid.render();
            });
        } else {
            overlaid.render();
        }
    },

    _getCollectionPanelClass : function( model ){
        switch( model.get( 'collection_type' ) ){
            case 'list':
                return DC_PANEL.ListCollectionPanel;
            case 'paired':
                return DC_PANEL.PairCollectionPanel;
            case 'list:paired':
                return DC_PANEL.ListOfPairsCollectionPanel;
        }
        throw new TypeError( 'Uknown collection_type: ' + model.get( 'collection_type' ) );
    },

    /** In this override, check for any overlaid panels first */
    addItemView : function( model, collection, options ){
        this.log( this + '.addItemView:', model );
        if( !this._filterItem( model ) ){ return undefined; }

        var panel = this;
        // don't show/add if there are panels overlaid on this one
        if( this.panelStack.length ){
            return panel;
        }

        // current history item order is reversed - use unshift and prepend
        var view = panel._createItemView( model );
        this.views.unshift( view );
        panel.scrollToTop();

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
                //view.render().$el.hide();
                panel.scrollToTop();
                panel.$list().prepend( view.render( 0 ).$el.hide() );
                view.$el.slideDown( panel.fxSpeed );
            }
        ]);
        return view;
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
        return 'CurrentHistoryPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


//------------------------------------------------------------------------------ TEMPLATES
CurrentHistoryPanel.prototype.templates = (function(){

    var quotaMsgTemplate = BASE_MVC.wrapTemplate([
        '<div class="quota-message errormessage">',
            _l( 'You are over your disk quota' ), '. ',
            _l( 'Tool execution is on hold until your disk usage drops below your allocated quota' ), '.',
        '</div>'
    ], 'history' );
    return _.extend( _.clone( _super.prototype.templates ), {
        quotaMsg : quotaMsgTemplate
    });

}());


//==============================================================================
    return {
        CurrentHistoryPanel        : CurrentHistoryPanel
    };
});
