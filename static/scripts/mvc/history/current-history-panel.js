define([
    "mvc/dataset/hda-edit",
    "mvc/history/history-panel",
    "mvc/base-mvc",
    "utils/localization"
], function( hdaEdit, hpanel, baseMVC, _l ){
// ============================================================================
/** session storage for history panel preferences (and to maintain state)
 */
var HistoryPanelPrefs = baseMVC.SessionStorageModel.extend({
    defaults : {
        /** is the panel currently showing the search/filter controls? */
        searching       : false,
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
/** @class View/Controller for the user's current history model as used in the history
 *      panel (current right hand panel).
 *  @name HistoryPanel
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var CurrentHistoryPanel = hpanel.HistoryPanel.extend(
/** @lends HistoryPanel.prototype */{

    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,

    /** class to use for constructing the HDA views */
    HDAViewClass        : hdaEdit.HDAEditView,

    emptyMsg            : _l( "This history is empty. Click 'Get Data' on the left tool menu to start" ),
    noneFoundMsg        : _l( "No matching datasets found" ),

    // ......................................................................... SET UP
    /** Set up the view, set up storage, bind listeners to HDACollection events
     *  @param {Object} attributes
     */
    initialize : function( attributes ){
        attributes = attributes || {};

        // ---- persistent preferences
        /** maintain state / preferences over page loads */
        this.preferences = new HistoryPanelPrefs( _.extend({
            id : HistoryPanelPrefs.storageKey()
        }, _.pick( attributes, _.keys( HistoryPanelPrefs.prototype.defaults ) )));

        hpanel.HistoryPanel.prototype.initialize.call( this, attributes );
    },

    // ------------------------------------------------------------------------ loading history/hda models
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
                return jQuery.ajax({
                    url     : galaxy_config.root + 'api/histories/' + historyId + '/set_as_current',
                    method  : 'PUT'
                });
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

    /** release/free/shutdown old models and set up panel for new models */
    setModel : function( model, attributes, render ){
        hpanel.HistoryPanel.prototype.setModel.call( this, model, attributes, render );
        if( this.model ){
            this.log( 'checking for updates' );
            this.model.checkForUpdates();
        }
        return this;
    },

    // ------------------------------------------------------------------------ history/hda event listening
    /** listening for history and HDA events */
    _setUpModelEventHandlers : function(){
        hpanel.HistoryPanel.prototype._setUpModelEventHandlers.call( this );
        // ---- history
        // update the quota meter when current history changes size
        if( Galaxy && Galaxy.quotaMeter ){
            this.listenTo( this.model, 'change:nice_size', function(){
                //console.info( '!! model size changed:', this.model.get( 'nice_size' ) )
//TODO: global
                Galaxy.quotaMeter.update();
            });
        }

        // if an a hidden hda is created (gen. by a workflow), moves thru the updater to the ready state,
        //  then: remove it from the collection if the panel is set to NOT show hidden datasets
        this.model.hdas.on( 'state:ready', function( hda, newState, oldState ){
            if( ( !hda.get( 'visible' ) )
            &&  ( !this.storage.get( 'show_hidden' ) ) ){
                this.removeHdaView( this.hdaViews[ hda.id ] );
            }
        }, this );
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
                    panel.renderBasedOnPrefs();
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

    /** perform additional rendering based on preferences */
    renderBasedOnPrefs : function(){
        if( this.preferences.get( 'searching' ) ){
            this.toggleSearchControls( 0, true );
        }
    },

    /** In this override, add links to open data uploader or get data in the tools section */
    _renderEmptyMsg : function( $whereTo ){
        var panel = this,
            $emptyMsg = panel.$emptyMessage( $whereTo ),
            $toolMenu = $( '.toolMenuContainer' );

        if( ( _.isEmpty( panel.hdaViews ) && !panel.searchFor )
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
                    //    console.debug( this )
                    //    $( this ).fadeTo( 200, 1.0 );
                    //});
            });

            $emptyMsg.show();


        } else {
            hpanel.HistoryPanel.prototype._renderEmptyMsg.call( this, $whereTo );
        }
        return this;
    },

    /** In this override, save the search control visibility state to preferences */
    toggleSearchControls : function( eventOrSpeed, show ){
        var visible = hpanel.HistoryPanel.prototype.toggleSearchControls.call( this, eventOrSpeed, show );
        this.preferences.set( 'searching', visible );
    },

    /** render the tag sub-view controller
     *  In this override, get and set current panel preferences when editor is used
     */
    _renderTags : function( $where ){
        var panel = this;
        // render tags and show/hide based on preferences
        hpanel.HistoryPanel.prototype._renderTags.call( this, $where );
        if( this.preferences.get( 'tagsEditorShown' ) ){
            this.tagsEditor.toggle( true );
        }
        // store preference when shown or hidden
        this.tagsEditor.on( 'hiddenUntilActivated:shown hiddenUntilActivated:hidden',
            function( tagsEditor ){
                panel.preferences.set( 'tagsEditorShown', tagsEditor.hidden );
            });
    },
    /** render the annotation sub-view controller
     *  In this override, get and set current panel preferences when editor is used
     */
    _renderAnnotation : function( $where ){
        var panel = this;
        // render annotation and show/hide based on preferences
        hpanel.HistoryPanel.prototype._renderAnnotation.call( this, $where );
        if( this.preferences.get( 'annotationEditorShown' ) ){
            this.annotationEditor.toggle( true );
        }
        // store preference when shown or hidden
        this.annotationEditor.on( 'hiddenUntilActivated:shown hiddenUntilActivated:hidden',
            function( annotationEditor ){
                panel.preferences.set( 'annotationEditorShown', annotationEditor.hidden );
            });
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


//==============================================================================
    return {
        CurrentHistoryPanel        : CurrentHistoryPanel
    };
});
