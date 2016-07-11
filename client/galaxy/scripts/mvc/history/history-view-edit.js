define([
    "mvc/history/history-view",
    "mvc/history/history-contents",
    "mvc/dataset/states",
    "mvc/history/hda-model",
    "mvc/history/hda-li-edit",
    "mvc/history/hdca-li-edit",
    "mvc/tag",
    "mvc/annotation",
    "mvc/collection/list-collection-creator",
    "mvc/collection/pair-collection-creator",
    "mvc/collection/list-of-pairs-collection-creator",
    "ui/fa-icon-button",
    "mvc/ui/popup-menu",
    "mvc/base-mvc",
    "utils/localization",
    "ui/editable-text",
], function(
    HISTORY_VIEW,
    HISTORY_CONTENTS,
    STATES,
    HDA_MODEL,
    HDA_LI_EDIT,
    HDCA_LI_EDIT,
    TAGS,
    ANNOTATIONS,
    LIST_COLLECTION_CREATOR,
    PAIR_COLLECTION_CREATOR,
    LIST_OF_PAIRS_COLLECTION_CREATOR,
    faIconButton,
    PopupMenu,
    BASE_MVC,
    _l
){

'use strict';

/* =============================================================================
TODO:

============================================================================= */
var _super = HISTORY_VIEW.HistoryView;
// base class for history-view-edit-current and used as-is in history/view.mako
/** @class Editable View/Controller for the history model.
 *
 *  Allows:
 *      (everything HistoryView allows)
 *      changing the name
 *      displaying and editing tags and annotations
 *      multi-selection and operations on mulitple content items
 */
var HistoryViewEdit = _super.extend(
/** @lends HistoryViewEdit.prototype */{

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
    },

    /** Override to handle history as drag-drop target */
    _setUpListeners : function(){
        _super.prototype._setUpListeners.call( this );
        return this.on({
            'droptarget:drop': function( ev, data ){
                // process whatever was dropped and re-hide the drop target
                this.dataDropped( data );
                this.dropTargetOff();
            },
            'view:attached view:removed': function(){
                this._renderCounts();
            },
            'search:loading-progress': this._renderSearchProgress,
            'search:searching': this._renderSearchFindings,
        });
    },

    // ------------------------------------------------------------------------ listeners
    /** listening for history and HDA events */
    _setUpModelListeners : function(){
        _super.prototype._setUpModelListeners.call( this );
        this.listenTo( this.model, 'change:size', this.updateHistoryDiskSize );
        return this;
    },

    /** listening for collection events */
    _setUpCollectionListeners : function(){
        _super.prototype._setUpCollectionListeners.call( this );
        this.listenTo( this.collection, {
            'change:deleted': this._handleItemDeletedChange,
            'change:visible': this._handleItemVisibleChange,
            'change:purged' : function( model ){
                // hafta get the new nice-size w/o the purged model
                this.model.fetch();
            },
            // loading indicators for deleted/hidden
            'fetching-deleted'      : function( collection ){
                this.$( '> .controls .deleted-count' )
                    .html( '<i>' + _l( 'loading...' ) + '</i>' );
            },
            'fetching-hidden'       : function( collection ){
                this.$( '> .controls .hidden-count' )
                    .html( '<i>' + _l( 'loading...' ) + '</i>' );
            },
            'fetching-deleted-done fetching-hidden-done'  : this._renderCounts,
        });
        return this;
    },

    // ------------------------------------------------------------------------ panel rendering
    /** In this override, add tag and annotation editors and a btn to toggle the selectors */
    _buildNewRender : function(){
        // create a new render using a skeleton template, render title buttons, render body, and set up events, etc.
        var $newRender = _super.prototype._buildNewRender.call( this );
        if( !this.model ){ return $newRender; }

        if( Galaxy && Galaxy.user && Galaxy.user.id && Galaxy.user.id === this.model.get( 'user_id' ) ){
            this._renderTags( $newRender );
            this._renderAnnotation( $newRender );
        }
        return $newRender;
    },

    /** Update the history size display (curr. upper right of panel). */
    updateHistoryDiskSize : function(){
        this.$( '.history-size' ).text( this.model.get( 'nice_size' ) );
    },

    /** override to render counts when the items are rendered */
    renderItems : function( $whereTo ){
        var views = _super.prototype.renderItems.call( this, $whereTo );
        if( !this.searchFor ){ this._renderCounts( $whereTo ); }
        return views;
    },

    /** override to show counts, what's deleted/hidden, and links to toggle those */
    _renderCounts : function( $whereTo ){
        $whereTo = $whereTo instanceof jQuery? $whereTo : this.$el;
        var html = this.templates.counts( this.model.toJSON(), this );
        return $whereTo.find( '> .controls .subtitle' ).html( html );
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

    /** Set up HistoryViewEdit js/widget behaviours
     *  In this override, make the name editable
     */
    _setUpBehaviors : function( $where ){
        $where = $where || this.$el;
        _super.prototype._setUpBehaviors.call( this, $where );
        if( !this.model ){ return; }

        // anon users shouldn't have access to any of the following
        if( ( !Galaxy.user || Galaxy.user.isAnonymous() )
        ||  ( Galaxy.user.id !== this.model.get( 'user_id' ) ) ){
            return;
        }

        var panel = this,
            nameSelector = '> .controls .name';
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
    multiselectActions : function(){
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
        actions = actions.concat( panel._collectionActions() );
        return actions;
    },

    /**   */
    _collectionActions : function(){
        var panel = this;
        return [
            {   html: _l( 'Build Dataset List' ), func: function() {
                    LIST_COLLECTION_CREATOR.createListCollection( panel.getSelectedModels() )
                        .done( function(){ panel.model.refresh(); });
                }
            },
            // TODO: Only show quick pair if two things selected.
            {   html: _l( 'Build Dataset Pair' ), func: function() {
                    PAIR_COLLECTION_CREATOR.createPairCollection( panel.getSelectedModels() )
                        .done( function(){ panel.model.refresh(); });
                }
            },
            {   html: _l( 'Build List of Dataset Pairs' ), func: function() {
                    LIST_OF_PAIRS_COLLECTION_CREATOR.createListOfPairsCollection( panel.getSelectedModels() )
                        .done( function(){ panel.model.refresh(); });
                }
            },
        ];
    },

    // ------------------------------------------------------------------------ sub-views
    /** In this override, add purgeAllowed and whether tags/annotation editors should be shown */
    _getItemViewOptions : function( model ){
        var options = _super.prototype._getItemViewOptions.call( this, model );
        _.extend( options, {
            purgeAllowed            : this.purgeAllowed,
            tagsEditorShown         : ( this.tagsEditor && !this.tagsEditor.hidden ),
            annotationEditorShown   : ( this.annotationEditor && !this.annotationEditor.hidden )
        });
        return options;
    },

    /** If this item is deleted and we're not showing deleted items, remove the view
     *  @param {Model} the item model to check
     */
    _handleItemDeletedChange : function( itemModel ){
        if( itemModel.get( 'deleted' ) ){
            this._handleItemDeletion( itemModel );
        } else {
            this._handleItemUndeletion( itemModel );
        }
        this._renderCounts();
    },

    _handleItemDeletion : function( itemModel ){
        var contentsShown = this.model.get( 'contents_active' );
        contentsShown.deleted += 1;
        contentsShown.active -= 1;
        if( !this.model.contents.includeDeleted ){
            this.removeItemView( itemModel );
        }
        this.model.set( 'contents_active', contentsShown );
    },

    _handleItemUndeletion : function( itemModel ){
        var contentsShown = this.model.get( 'contents_active' );
        contentsShown.deleted -= 1;
        if( !this.model.contents.includeDeleted ){
            contentsShown.active -= 1;
        }
        this.model.set( 'contents_active', contentsShown );
    },

    /** If this item is hidden and we're not showing hidden items, remove the view
     *  @param {Model} the item model to check
     */
    _handleItemVisibleChange : function( itemModel ){
        if( itemModel.hidden() ){
            this._handleItemHidden( itemModel );
        } else {
            this._handleItemUnhidden( itemModel );
        }
        this._renderCounts();
    },

    _handleItemHidden : function( itemModel ){
        var contentsShown = this.model.get( 'contents_active' );
        contentsShown.hidden += 1;
        contentsShown.active -= 1;
        if( !this.model.contents.includeHidden ){
            this.removeItemView( itemModel );
        }
        this.model.set( 'contents_active', contentsShown );
    },

    _handleItemUnhidden : function( itemModel ){
        var contentsShown = this.model.get( 'contents_active' );
        contentsShown.hidden -= 1;
        if( !this.model.contents.includeHidden ){
            contentsShown.active -= 1;
        }
        this.model.set( 'contents_active', contentsShown );
    },

    /** toggle the visibility of each content's tagsEditor applying all the args sent to this function */
    toggleHDATagEditors : function( showOrHide, speed ){
        _.each( this.views, function( view ){
            if( view.tagsEditor ){
                view.tagsEditor.toggle( showOrHide, speed );
            }
        });
    },

    /** toggle the visibility of each content's annotationEditor applying all the args sent to this function */
    toggleHDAAnnotationEditors : function( showOrHide, speed ){
        _.each( this.views, function( view ){
            if( view.annotationEditor ){
                view.annotationEditor.toggle( showOrHide, speed );
            }
        });
    },

    // ------------------------------------------------------------------------ panel events
    /** event map */
    events : _.extend( _.clone( _super.prototype.events ), {
        'click .show-selectors-btn'                 : 'toggleSelectors',
        'click .toggle-deleted-link'                : function( ev ){ this.toggleShowDeleted(); },
        'click .toggle-hidden-link'                 : function( ev ){ this.toggleShowHidden(); }
    }),

    // ------------------------------------------------------------------------ search
    _renderSearchProgress : function( limit, offset ){
        var stop = limit + offset;
        return this.$( '> .controls .subtitle' ).html([
            '<i>',
                _l( 'Searching ' ), stop, '/', this.model.contentsShown(),
            '</i>'
        ].join(''));
    },

    /** override to display number found in subtitle */
    _renderSearchFindings : function(){
        this.$( '> .controls .subtitle' ).html([
            _l( 'Found' ), this.views.length
        ].join(' '));
        return this;
    },

    // ------------------------------------------------------------------------ as drop target
    /** turn all the drag and drop handlers on and add some help text above the drop area */
    dropTargetOn : function(){
        if( this.dropTarget ){ return this; }
        this.dropTarget = true;

        //TODO: to init
        var dropHandlers = {
            'dragenter' : _.bind( this.dragenter, this ),
            'dragover'  : _.bind( this.dragover,  this ),
            'dragleave' : _.bind( this.dragleave, this ),
            'drop'      : _.bind( this.drop, this )
        };

        var $dropTarget = this._renderDropTarget();
        this.$list().before([ this._renderDropTargetHelp(), $dropTarget ]);
        for( var evName in dropHandlers ){
            if( dropHandlers.hasOwnProperty( evName ) ){
                //console.debug( evName, dropHandlers[ evName ] );
                $dropTarget.on( evName, dropHandlers[ evName ] );
            }
        }
        return this;
    },

    /** render a box to serve as a 'drop here' area on the history */
    _renderDropTarget : function(){
        this.$( '.history-drop-target' ).remove();
        return $( '<div/>' ).addClass( 'history-drop-target' );
    },

    /** tell the user how it works  */
    _renderDropTargetHelp : function(){
        this.$( '.history-drop-target-help' ).remove();
        return $( '<div/>' ).addClass( 'history-drop-target-help' )
            .text( _l( 'Drag datasets here to copy them to the current history' ) );
    },

    /** shut down drag and drop event handlers and remove drop target */
    dropTargetOff : function(){
        if( !this.dropTarget ){ return this; }
        //this.log( 'dropTargetOff' );
        this.dropTarget = false;
        var dropTarget = this.$( '.history-drop-target' ).get(0);
        for( var evName in this._dropHandlers ){
            if( this._dropHandlers.hasOwnProperty( evName ) ){
                dropTarget.off( evName, this._dropHandlers[ evName ] );
            }
        }
        this.$( '.history-drop-target' ).remove();
        this.$( '.history-drop-target-help' ).remove();
        return this;
    },
    /** toggle the target on/off */
    dropTargetToggle : function(){
        if( this.dropTarget ){
            this.dropTargetOff();
        } else {
            this.dropTargetOn();
        }
        return this;
    },

    dragenter : function( ev ){
        //console.debug( 'dragenter:', this, ev );
        ev.preventDefault();
        ev.stopPropagation();
        this.$( '.history-drop-target' ).css( 'border', '2px solid black' );
    },
    dragover : function( ev ){
        ev.preventDefault();
        ev.stopPropagation();
    },
    dragleave : function( ev ){
        //console.debug( 'dragleave:', this, ev );
        ev.preventDefault();
        ev.stopPropagation();
        this.$( '.history-drop-target' ).css( 'border', '1px dashed black' );
    },
    /** when (text) is dropped try to parse as json and trigger an event */
    drop : function( ev ){
        ev.preventDefault();
        //ev.stopPropagation();

        var self = this;
        var dataTransfer = ev.originalEvent.dataTransfer;
        var data = dataTransfer.getData( "text" );

        dataTransfer.dropEffect = 'move';
        try {
            data = JSON.parse( data );
        } catch( err ){
            self.warn( 'error parsing JSON from drop:', data );
        }

        self.trigger( 'droptarget:drop', ev, data, self );
        return false;
    },

    /** handler that copies data into the contents */
    dataDropped : function( data ){
        var self = this;
        // HDA: dropping will copy it to the history
        if( _.isObject( data ) && data.model_class === 'HistoryDatasetAssociation' && data.id ){
            if( self.contents.currentPage !== 0 ){
                return self.contents.fetchPage( 0 )
                    .then( function(){
                        return self.model.contents.copy( data.id );
                    });
            }
            return self.model.contents.copy( data.id );
        }
        return jQuery.when();
    },

    // ........................................................................ misc
    /** Return a string rep of the history */
    toString    : function(){
        return 'HistoryViewEdit(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});

//------------------------------------------------------------------------------ TEMPLATES
HistoryViewEdit.prototype.templates = (function(){

    var countsTemplate = BASE_MVC.wrapTemplate([
        '<% var shown = Math.max( view.views.length, history.contents_active.active ) %>',
        '<% if( shown ){ %>',
            '<span class="shown-count">',
                '<%- shown %> ', _l( 'shown' ),
            '</span>',
        '<% } %>',

        '<% if( history.contents_active.deleted ){ %>',
            '<span class="deleted-count">',
            '<% if( view.model.contents.includeDeleted ){ %>',
                '<a class="toggle-deleted-link" href="javascript:void(0);">',
                    _l( 'hide deleted' ),
                '</a>',
            '<% } else { %>',
                '<%- history.contents_active.deleted %> ',
                '<a class="toggle-deleted-link" href="javascript:void(0);">',
                    _l( 'deleted' ),
                '</a>',
            '<% } %>',
            '</span>',
        '<% } %>',

        '<% if( history.contents_active.hidden ){ %>',
            '<span class="hidden-count">',
            '<% if( view.model.contents.includeHidden ){ %>',
                '<a class="toggle-hidden-link" href="javascript:void(0);">',
                    _l( 'hide hidden' ),
                '</a>',
            '<% } else { %>',
                '<%- history.contents_active.hidden %> ',
                '<a class="toggle-hidden-link" href="javascript:void(0);">',
                    _l( 'hidden' ),
                '</a>',
            '<% } %>',
            '</span>',
        '<% } %>',
    ], 'history' );

    return _.extend( _.clone( _super.prototype.templates ), {
        counts : countsTemplate
    });
}());


//==============================================================================
    return {
        HistoryViewEdit : HistoryViewEdit
    };
});
