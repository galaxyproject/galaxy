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
var _super = HPANEL.HistoryPanel;
// base class for current-history-panel and used as-is in history/view.mako
/** @class Editable View/Controller for the history model.
 *
 *  Allows:
 *      (everything HistoryPanel allows)
 *      changing the name
 *      displaying and editing tags and annotations
 *      multi-selection and operations on mulitple content items
 */
var HistoryPanelEdit = _super.extend(
/** @lends HistoryPanelEdit.prototype */{

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
        _super.prototype.initialize.call( this, attributes );

        // ---- set up instance vars
        /** editor for tags - sub-view */
        this.tagsEditor = null;
        /** editor for annotations - sub-view */
        this.annotationEditor = null;

        /** allow user purge of dataset files? */
        this.purgeAllowed = attributes.purgeAllowed || false;

        // states/modes the panel can be in
        /** is the panel currently showing the dataset selection controls? */
        this.annotationEditorShown  = attributes.annotationEditorShown || false;
        this.tagsEditorShown  = attributes.tagsEditorShown || false;

        this.multiselectActions = attributes.multiselectActions || this._getActions();
    },

    // ------------------------------------------------------------------------ panel rendering
    /** listening for collection events */
    _setUpCollectionListeners : function(){
        _super.prototype._setUpCollectionListeners.call( this );

        this.collection.on( 'change:deleted', this._handleHdaDeletionChange, this );
        this.collection.on( 'change:visible', this._handleHdaVisibleChange, this );
        this.collection.on( 'change:purged', function( model ){
            // hafta get the new nice-size w/o the purged model
            this.model.fetch();
        }, this );
        return this;
    },

    /** listening for history and HDA events */
    _setUpModelListeners : function(){
        _super.prototype._setUpModelListeners.call( this );
        this.model.on( 'change:nice_size', this.updateHistoryDiskSize, this );
        return this;
    },

    // ------------------------------------------------------------------------ panel rendering
    /** In this override, add tag and annotation editors and a btn to toggle the selectors */
    _buildNewRender : function(){
        // create a new render using a skeleton template, render title buttons, render body, and set up events, etc.
        var $newRender = _super.prototype._buildNewRender.call( this );
        if( !this.model ){ return $newRender; }

        if( Galaxy && Galaxy.currUser && Galaxy.currUser.id && Galaxy.currUser.id === this.model.get( 'user_id' ) ){
            this._renderTags( $newRender );
            this._renderAnnotation( $newRender );
        }
        return $newRender;
    },

    /** render the tags sub-view controller */
    _renderTags : function( $where ){
        var panel = this;
        this.tagsEditor = new TAGS.TagsEditor({
            model           : this.model,
            el              : $where.find( '.controls .tags-display' ),
            onshowFirstTime : function(){ this.render(); },
            // show hide sub-view tag editors when this is shown/hidden
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
            }).appendTo( $where.find( '.controls .actions' ) )
        });
    },
    /** render the annotation sub-view controller */
    _renderAnnotation : function( $where ){
        var panel = this;
        this.annotationEditor = new ANNOTATIONS.AnnotationEditor({
            model           : this.model,
            el              : $where.find( '.controls .annotation-display' ),
            onshowFirstTime : function(){ this.render(); },
            // show hide sub-view view annotation editors when this is shown/hidden
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
            }).appendTo( $where.find( '.controls .actions' ) )
        });
    },

    /** Set up HistoryPanelEdit js/widget behaviours
     *  In this override, add the multi select popup menu and make the name editable
     */
    _setUpBehaviors : function( $where ){
        $where = $where || this.$el;
        _super.prototype._setUpBehaviors.call( this, $where );
        if( !this.model ){ return; }

        // set up the pupup for actions available when multi selecting
        if( this.multiselectActions.length ){
            this.actionsPopup = new PopupMenu( $where.find( '.list-action-popup-btn' ), this.multiselectActions );
        }

        // anon users shouldn't have access to any of the following
        if( ( !Galaxy.currUser || Galaxy.currUser.isAnonymous() )
        ||  ( Galaxy.currUser.id !== this.model.get( 'user_id' ) ) ){
            return;
        }

        var panel = this,
            nameSelector = '.controls .name';
        $where.find( nameSelector )
            .attr( 'title', _l( 'Click to rename history' ) )
            .tooltip({ placement: 'bottom' })
            .make_text_editable({
                on_finish: function( newName ){
                    var previousName = panel.model.get( 'name' );
                    if( newName && newName !== previousName ){
                        panel.$el.find( nameSelector ).text( newName );
                        panel.model.save({ name: newName })
                            .fail( function(){
                                panel.$el.find( nameSelector ).text( panel.model.previous( 'name' ) );
                            });
                    } else {
                        panel.$el.find( nameSelector ).text( previousName );
                    }
                }
            });
    },

    /** return a new popup menu for choosing a multi selection action
     *  ajax calls made for multiple datasets are queued
     */
    _getActions : function(){
        var panel = this,
            actions = [
                {   html: _l( 'Hide datasets' ), func: function(){
                        var action = HDA_MODEL.HistoryDatasetAssociation.prototype.hide;
                        panel.getSelectedModels().ajaxQueue( action );
                    }
                },
                {   html: _l( 'Unhide datasets' ), func: function(){
                        var action = HDA_MODEL.HistoryDatasetAssociation.prototype.unhide;
                        panel.getSelectedModels().ajaxQueue( action );
                    }
                },
                {   html: _l( 'Delete datasets' ), func: function(){
                        var action = HDA_MODEL.HistoryDatasetAssociation.prototype['delete'];
                        panel.getSelectedModels().ajaxQueue( action );
                    }
                },
                {   html: _l( 'Undelete datasets' ), func: function(){
                        var action = HDA_MODEL.HistoryDatasetAssociation.prototype.undelete;
                        panel.getSelectedModels().ajaxQueue( action );
                    }
                }
            ];
        if( panel.purgeAllowed ){
            actions.push({
                html: _l( 'Permanently delete datasets' ), func: function(){
                    if( confirm( _l( 'This will permanently remove the data in your datasets. Are you sure?' ) ) ){
                        var action = HDA_MODEL.HistoryDatasetAssociation.prototype.purge;
                        panel.getSelectedModels().ajaxQueue( action );
                    }
                }
            });
        }
        actions.push( {
            html: _l( 'Build Dataset List' ), func: function() {
                panel.getSelectedModels().promoteToHistoryDatasetCollection( panel.model, "list" );
            }
        });
        actions.push( {
            // TODO: Only show quick pair if two things selected.
            html: _l( 'Build Dataset Pair' ), func: function() {
                panel.getSelectedModels().promoteToHistoryDatasetCollection( panel.model, "paired" );
            }
        });
        actions.push( {
            // TODO: Only show quick pair if two things selected.
            html: _l( 'Build List of Dataset Pairs' ),
            func: _.bind( panel._showPairedCollectionModal, panel )
        });
        return actions;
    },

    _showPairedCollectionModal : function(){
        var panel = this,
            datasets = panel.getSelectedModels().toJSON().filter( function( content ){
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

    // ------------------------------------------------------------------------ sub-views
    /** In this override, add purgeAllowed and whether tags/annotation editors should be shown */
    _getItemViewOptions : function( model ){
        var options = _super.prototype._getItemViewOptions.call( this, model );
        _.extend( options, {
            purgeAllowed            : this.purgeAllowed,
//TODO: not working
            tagsEditorShown         : ( this.tagsEditor && !this.tagsEditor.hidden ),
            annotationEditorShown   : ( this.annotationEditor && !this.annotationEditor.hidden )
        });
        return options;
    },

    /** If this item is deleted and we're not showing deleted items, remove the view
     *  @param {Model} the item model to check
     */
    _handleHdaDeletionChange : function( itemModel ){
        if( itemModel.get( 'deleted' ) && !this.storage.get( 'show_deleted' ) ){
            this.removeItemView( itemModel );
        }
    },

    /** If this item is hidden and we're not showing hidden items, remove the view
     *  @param {Model} the item model to check
     */
    _handleHdaVisibleChange : function( itemModel ){
        if( itemModel.hidden() && !this.storage.get( 'show_hidden' ) ){
            this.removeItemView( itemModel );
        }
    },

    /** toggle the visibility of each content's tagsEditor applying all the args sent to this function */
    toggleHDATagEditors : function( showOrHide ){
        var args = Array.prototype.slice.call( arguments, 1 );
        _.each( this.views, function( view ){
            if( view.tagsEditor ){
                view.tagsEditor.toggle.apply( view.tagsEditor, args );
            }
        });
    },

    /** toggle the visibility of each content's annotationEditor applying all the args sent to this function */
    toggleHDAAnnotationEditors : function( showOrHide ){
        var args = Array.prototype.slice.call( arguments, 1 );
        _.each( this.views, function( view ){
            if( view.annotationEditor ){
                view.annotationEditor.toggle.apply( view.annotationEditor, args );
            }
        });
    },

    // ------------------------------------------------------------------------ panel events
    /** event map */
    events : _.extend( _.clone( _super.prototype.events ), {
        'click .show-selectors-btn'                 : 'toggleSelectors'
    }),

    /** Update the history size display (curr. upper right of panel).
     */
    updateHistoryDiskSize : function(){
        this.$el.find( '.history-size' ).text( this.model.get( 'nice_size' ) );
    },

    // ........................................................................ misc
    /** Return a string rep of the history */
    toString    : function(){
        return 'HistoryPanelEdit(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});

//==============================================================================
    return {
        HistoryPanelEdit : HistoryPanelEdit
    };
});
