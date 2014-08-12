define([
    "mvc/history/history-panel",
    "mvc/history/history-contents",
    "mvc/dataset/states",
    "mvc/history/hda-model",
    "mvc/history/hda-li-edit",
    "mvc/history/hdca-li-edit",
    "mvc/tags",
    "mvc/annotations",
    "utils/localization"
], function(
    HPANEL,
    HISTORY_CONTENTS,
    STATES,
    HDA_MODEL,
    HDA_LI_EDIT,
    HDCA_LI_EDIT,
    TAGS,
    ANNOTATIONS,
    _l
){
/* =============================================================================
TODO:

============================================================================= */
var _super = HPANEL.ReadOnlyHistoryPanel;
// base class for current-history-panel and used as-is in history/view.mako
/** @class Editable View/Controller for the history model.
 *  @name HistoryPanel
 *
 *  Allows:
 *      (everything ReadOnlyHistoryPanel allows)
 *      changing the name
 *      displaying and editing tags and annotations
 *      multi-selection and operations on mulitple hdas
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HistoryPanel = _super.extend(
/** @lends HistoryPanel.prototype */{

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    /** class to use for constructing the HistoryDatasetAssociation views */
    HDAViewClass    : HDA_LI_EDIT.HDAListItemEdit,
    /** class to use for constructing the HistoryDatasetCollectionAssociation views */
    HDCAViewClass   : HDCA_LI_EDIT.HDCAListItemEdit,

    // ......................................................................... SET UP
    /** Set up the view, set up storage, bind listeners to HistoryContents events
     *  @param {Object} attributes
     */
    initialize : function( attributes ){
        attributes = attributes || {};

        // ---- set up instance vars
        /** selected hda ids */
        this.selectedHdaIds = [];
        /** last selected hda */
        this.lastSelectedViewId = null;

        /** editor for tags - sub-view */
        this.tagsEditor = null;
        /** editor for annotations - sub-view */
        this.annotationEditor = null;

        /** allow user purge of dataset files? */
        this.purgeAllowed = attributes.purgeAllowed || false;

        // states/modes the panel can be in
        /** is the panel currently showing the dataset selection controls? */
        this.selecting = attributes.selecting || false;
        this.annotationEditorShown  = attributes.annotationEditorShown || false;
        this.tagsEditorShown  = attributes.tagsEditorShown || false;

        _super.prototype.initialize.call( this, attributes );
    },

    // ------------------------------------------------------------------------ panel rendering
    /** listening for history and HDA events */
    _setUpModelEventHandlers : function(){
        _super.prototype._setUpModelEventHandlers.call( this );

        this.model.on( 'change:nice_size', this.updateHistoryDiskSize, this );

        this.model.contents.on( 'change:deleted', this._handleHdaDeletionChange, this );
        this.model.contents.on( 'change:visible', this._handleHdaVisibleChange, this );
        this.model.contents.on( 'change:purged', function( hda ){
            // hafta get the new nice-size w/o the purged hda
            this.model.fetch();
        }, this );
    },

    // ------------------------------------------------------------------------ panel rendering
    /** render with history data
     *  In this override, add tags, annotations, and multi select
     *  @returns {jQuery} dom fragment as temporary container to be swapped out later
     */
    renderModel : function( ){
//TODO: can't call ReadOnlyHistoryPanel?
        var $newRender = $( '<div/>' );

        $newRender.append( HistoryPanel.templates.historyPanel( this.model.toJSON() ) );
        this.$emptyMessage( $newRender ).text( this.emptyMsg );
        if( Galaxy && Galaxy.currUser && Galaxy.currUser.id && Galaxy.currUser.id === this.model.get( 'user_id' ) ){
            this._renderTags( $newRender );
            this._renderAnnotation( $newRender );
        }
        // search and select available to both anon/logged-in users
        $newRender.find( '.history-secondary-actions' ).prepend( this._renderSelectButton() );
        $newRender.find( '.history-dataset-actions' ).toggle( this.selecting );
        $newRender.find( '.history-secondary-actions' ).prepend( this._renderSearchButton() );

        this._setUpBehaviours( $newRender );

        // render hda views (if any and any shown (show_deleted/hidden)
        this.renderHdas( $newRender );
        return $newRender;
    },

    /** render the tags sub-view controller */
    _renderTags : function( $where ){
        var panel = this;
        this.tagsEditor = new TAGS.TagsEditor({
            model           : this.model,
            el              : $where.find( '.history-controls .tags-display' ),
            onshowFirstTime : function(){ this.render(); },
            // show hide hda view tag editors when this is shown/hidden
            onshow          : function(){
                panel.toggleHDATagEditors( true,  panel.fxSpeed );
            },
            onhide          : function(){
                panel.toggleHDATagEditors( false, panel.fxSpeed );
            },
            $activator      : faIconButton({
                title   : _l( 'Edit history tags' ),
                classes : 'history-tag-btn',
                faIcon  : 'fa-tags'
            }).appendTo( $where.find( '.history-secondary-actions' ) )
        });
    },
    /** render the annotation sub-view controller */
    _renderAnnotation : function( $where ){
        var panel = this;
        this.annotationEditor = new ANNOTATIONS.AnnotationEditor({
            model           : this.model,
            el              : $where.find( '.history-controls .annotation-display' ),
            onshowFirstTime : function(){ this.render(); },
            // show hide hda view annotation editors when this is shown/hidden
            onshow          : function(){
                panel.toggleHDAAnnotationEditors( true,  panel.fxSpeed );
            },
            onhide          : function(){
                panel.toggleHDAAnnotationEditors( false, panel.fxSpeed );
            },
            $activator      : faIconButton({
                title   : _l( 'Edit history annotation' ),
                classes : 'history-annotate-btn',
                faIcon  : 'fa-comment'
            }).appendTo( $where.find( '.history-secondary-actions' ) )
        });
    },

    /** button for starting select mode */
    _renderSelectButton : function( $where ){
        return faIconButton({
            title   : _l( 'Operations on multiple datasets' ),
            classes : 'history-select-btn',
            faIcon  : 'fa-check-square-o'
        });
    },

    /** Set up HistoryPanel js/widget behaviours
     *  In this override, add the multi select popup menu and make the name editable
     */
    _setUpBehaviours : function( $where ){
        $where = $where || this.$el;
        _super.prototype._setUpBehaviours.call( this, $where );

        // anon users shouldn't have access to any of the following
        if( !this.model ){
            return;
        }

        // set up the pupup for actions available when multi selecting
        this._setUpDatasetActionsPopup( $where );

        // anon users shouldn't have access to any of the following
        if( ( !Galaxy.currUser || Galaxy.currUser.isAnonymous() )
        ||  ( Galaxy.currUser.id !== this.model.get( 'user_id' ) ) ){
            return;
        }

        var panel = this;
        $where.find( '.history-name' )
            .attr( 'title', _l( 'Click to rename history' ) ).tooltip({ placement: 'bottom' })
            .make_text_editable({
                on_finish: function( newName ){
                    var previousName = panel.model.get( 'name' );
                    if( newName && newName !== previousName ){
                        panel.$el.find( '.history-name' ).text( newName );
                        panel.model.save({ name: newName })
                            .fail( function(){
                                panel.$el.find( '.history-name' ).text( panel.model.previous( 'name' ) );
                            });
                    } else {
                        panel.$el.find( '.history-name' ).text( previousName );
                    }
                }
            });
    },

    /** return a new popup menu for choosing a multi selection action
     *  ajax calls made for multiple datasets are queued
     */
    _setUpDatasetActionsPopup : function( $where ){
        var panel = this,
            actions = [
                {   html: _l( 'Hide datasets' ), func: function(){
                        var action = HDA_MODEL.HistoryDatasetAssociation.prototype.hide;
                        panel.getSelectedHdaCollection().ajaxQueue( action );
                    }
                },
                {   html: _l( 'Unhide datasets' ), func: function(){
                        var action = HDA_MODEL.HistoryDatasetAssociation.prototype.unhide;
                        panel.getSelectedHdaCollection().ajaxQueue( action );
                    }
                },
                {   html: _l( 'Delete datasets' ), func: function(){
                        var action = HDA_MODEL.HistoryDatasetAssociation.prototype['delete'];
                        panel.getSelectedHdaCollection().ajaxQueue( action );
                    }
                },
                {   html: _l( 'Undelete datasets' ), func: function(){
                        var action = HDA_MODEL.HistoryDatasetAssociation.prototype.undelete;
                        panel.getSelectedHdaCollection().ajaxQueue( action );
                    }
                }            ];
        if( panel.purgeAllowed ){
            actions.push({
                html: _l( 'Permanently delete datasets' ), func: function(){
                    if( confirm( _l( 'This will permanently remove the data in your datasets. Are you sure?' ) ) ){
                        var action = HDA_MODEL.HistoryDatasetAssociation.prototype.purge;
                        panel.getSelectedHdaCollection().ajaxQueue( action );
                    }
                }
            });
        }
        actions.push( {
            html: _l( 'Build Dataset List (Experimental)' ), func: function() {
                panel.getSelectedHdaCollection().promoteToHistoryDatasetCollection( panel.model, "list" );
            }
        });
        actions.push( {
            // TODO: Only show quick pair if two things selected.
            html: _l( 'Build Dataset Pair (Experimental)' ), func: function() {
                panel.getSelectedHdaCollection().promoteToHistoryDatasetCollection( panel.model, "paired" );
            }
        });
        actions.push( {
            // TODO: Only show quick pair if two things selected.
            html: _l( 'Build List of Dataset Pairs (Experimental)' ),
            func: _.bind( panel._showPairedCollectionModal, panel )
        });
        return new PopupMenu( $where.find( '.history-dataset-action-popup-btn' ), actions );
    },

    _showPairedCollectionModal : function(){
        var panel = this,
            datasets = panel.getSelectedHdaCollection().toJSON().filter( function( content ){
                return content.history_content_type === 'dataset'
                    && content.state === STATES.OK;
            });
        if( datasets.length ){
            require([ 'mvc/collection/paired-collection-creator' ], function( creator ){
                window.creator = creator.pairedCollectionCreatorModal( datasets, {
                    historyId : panel.model.id
                });
            });
        } else {
            //Galaxy.modal.show({
            //    body : _l( 'No valid datasets were selected' ),
            //    buttons : {
            //        'Ok': function(){ Galaxy.modal.hide(); }
            //    }
            //});
        }
    },

    // ------------------------------------------------------------------------ hda sub-views
    /** If this hda is deleted and we're not showing deleted hdas, remove the view
     *  @param {HistoryDataAssociation} the hda to check
     */
    _handleHdaDeletionChange : function( hda ){
        if( hda.get( 'deleted' ) && !this.storage.get( 'show_deleted' ) ){
            this.removeHdaView( this.hdaViews[ hda.id ] );
        } // otherwise, the hdaView rendering should handle it
    },


    /** If this hda is hidden and we're not showing hidden hdas, remove the view
     *  @param {HistoryDataAssociation} the hda to check
     */
    _handleHdaVisibleChange : function( hda ){
        if( hda.hidden() && !this.storage.get( 'show_hidden' ) ){
            this.removeHdaView( this.hdaViews[ hda.id ] );
        } // otherwise, the hdaView rendering should handle it
    },

    _getContentOptions : function( content ){
        var options = _super.prototype._getContentOptions.call( this, content );
        _.extend( options, {
            selectable              : this.selecting,
            purgeAllowed            : this.purgeAllowed,
            tagsEditorShown         : ( this.tagsEditor && !this.tagsEditor.hidden ),
            annotationEditorShown   : ( this.annotationEditor && !this.annotationEditor.hidden )
        });
        return options;
    },

    /** Set up HistoryPanel listeners for HDAView events. Currently binds:
     *      HDAView#body-visible, HDAView#body-hidden to store expanded states
     *  @param {HDAView} hdaView HDAView (base or edit) to listen to
     */
    _setUpHdaListeners : function( hdaView ){
        var historyView = this;
        _super.prototype._setUpHdaListeners.call( this, hdaView );

        // maintain a list of hdas that are selected
        hdaView.on( 'selected', function( hdaView, event ){
            if( !event ){ return; }
            //this.debug( 'selected', event );
            var selectedIds = [];
            //this.debug( historyView.lastSelectedViewId, historyView.hdaViews[ historyView.lastSelectedViewId ] );

            // shift will select a range, but not set lastSelectedViewId
            if( ( event.shiftKey )
            &&  ( historyView.lastSelectedViewId && _.has( historyView.hdaViews, historyView.lastSelectedViewId ) ) ){
                var lastSelectedView = historyView.hdaViews[ historyView.lastSelectedViewId ];
                selectedIds = historyView.selectDatasetRange( hdaView, lastSelectedView )
                    .map( function( view ){ return view.model.id; });

            // only
            } else {
                var id = hdaView.model.id;
                historyView.lastSelectedViewId = id;
                //this.debug( 'lastSelectedViewId:', historyView.lastSelectedViewId );
                selectedIds = [ id ];
            }
            //this.debug( 'selectedIds:', selectedIds );
            historyView.selectedHdaIds = _.union( historyView.selectedHdaIds, selectedIds );
            //TODO: might want to use getSelectedHdaViews instead managing these lists with ops
            //this.debug( 'selected', historyView.selectedHdaIds );
        });
        hdaView.on( 'de-selected', function( hdaView, event ){
            //this.debug( 'de-selected', event );
            var id = hdaView.model.id;
            historyView.selectedHdaIds = _.without( historyView.selectedHdaIds, id );
            //this.debug( 'de-selected', historyView.selectedHdaIds );
        });
    },

    /** toggle the visibility of each hdaView's tagsEditor applying all the args sent to this function */
    toggleHDATagEditors : function( showOrHide ){
        var args = arguments;
        _.each( this.hdaViews, function( hdaView ){
            if( hdaView.tagsEditor ){
                hdaView.tagsEditor.toggle.apply( hdaView.tagsEditor, args );
            }
        });
    },

    /** toggle the visibility of each hdaView's annotationEditor applying all the args sent to this function */
    toggleHDAAnnotationEditors : function( showOrHide ){
        var args = arguments;
        _.each( this.hdaViews, function( hdaView ){
            if( hdaView.annotationEditor ){
                hdaView.annotationEditor.toggle.apply( hdaView.annotationEditor, args );
            }
        });
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
                panel.trigger( 'empty-history', panel );
                panel._renderEmptyMsg();
            }
        });
    },

    // ------------------------------------------------------------------------ panel events
    /** event map */
    events : _.extend( _.clone( _super.prototype.events ), {
        'click .history-select-btn'                 : 'toggleSelectors',
        'click .history-select-all-datasets-btn'    : 'selectAllDatasets',
        'click .history-deselect-all-datasets-btn'  : 'deselectAllDatasets'
    }),

    /** Update the history size display (curr. upper right of panel).
     */
    updateHistoryDiskSize : function(){
        this.$el.find( '.history-size' ).text( this.model.get( 'nice_size' ) );
    },

    // ........................................................................ multi-select of hdas
//TODO: to toggle showOrHide pattern
    /** show selectors on all visible hdas and associated controls */
    showSelectors : function( speed ){
        speed = ( speed !== undefined )?( speed ):( this.fxSpeed );
        this.selecting = true;
        this.$( '.history-dataset-actions' ).slideDown( speed );
        _.each( this.hdaViews, function( view ){
            view.showSelector();
        });
        this.selectedHdaIds = [];
        this.lastSelectedViewId = null;
    },

    /** hide selectors on all visible hdas and associated controls */
    hideSelectors : function( speed ){
        speed = ( speed !== undefined )?( speed ):( this.fxSpeed );
        this.selecting = false;
        this.$( '.history-dataset-actions' ).slideUp( speed );
        _.each( this.hdaViews, function( view ){
            view.hideSelector();
        });
        this.selectedHdaIds = [];
        this.lastSelectedViewId = null;
    },

    /** show or hide selectors on all visible hdas and associated controls */
    toggleSelectors : function(){
        if( !this.selecting ){
            this.showSelectors();
        } else {
            this.hideSelectors();
        }
    },

    /** select all visible hdas */
    selectAllDatasets : function( event ){
        _.each( this.hdaViews, function( view ){
            view.select( event );
        });
    },

    /** deselect all visible hdas */
    deselectAllDatasets : function( event ){
        this.lastSelectedViewId = null;
        _.each( this.hdaViews, function( view ){
            view.deselect( event );
        });
    },

    /** select a range of datasets between A and B */
    selectDatasetRange : function( viewA, viewB ){
        var range = this.hdaViewRange( viewA, viewB );
        _.each( range, function( view ){
            view.select();
        });
        return range;
    },

    /** return an array of all currently selected hdas */
    getSelectedHdaViews : function(){
        return _.filter( this.hdaViews, function( v ){
            return v.selected;
        });
    },

    /** return an HdaCollection of the models of all currenly selected hdas */
    getSelectedHdaCollection : function(){
        return new HISTORY_CONTENTS.HistoryContents( _.map( this.getSelectedHdaViews(), function( hdaView ){
            return hdaView.model;
        }), { historyId: this.model.id });
    },

    // ........................................................................ misc
    /** Return a string rep of the history */
    toString    : function(){
        return 'HistoryPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});

//==============================================================================
    return {
        HistoryPanel        : HistoryPanel
    };
});
