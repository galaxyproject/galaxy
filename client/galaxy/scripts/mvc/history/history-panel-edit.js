define([
    "mvc/history/history-panel",
    "mvc/history/history-contents",
    "mvc/dataset/states",
    "mvc/history/hda-model",
    "mvc/history/hda-li-edit",
    "mvc/history/hdca-li-edit",
    "mvc/tags",
    "mvc/annotations",
    "mvc/collection/list-collection-creator",
    "mvc/collection/pair-collection-creator",
    "mvc/collection/list-of-pairs-collection-creator",
    "ui/fa-icon-button",
    "mvc/ui/popup-menu",
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
    LIST_COLLECTION_CREATOR,
    PAIR_COLLECTION_CREATOR,
    LIST_OF_PAIRS_COLLECTION_CREATOR,
    faIconButton,
    PopupMenu,
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
    },

    /** Override to handle history as drag-drop target */
    _setUpListeners : function(){
        var panel = this;
        _super.prototype._setUpListeners.call( panel );

        panel.on( 'drop', function( ev, data ){
            panel.dataDropped( data );
            // remove the drop target
            panel.dropTargetOff();
        });
        panel.on( 'view:attached view:removed', function(){
            panel._renderCounts();
        }, panel );
    },

    // ------------------------------------------------------------------------ listeners
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
        this.model.on( 'change:size', this.updateHistoryDiskSize, this );
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

    /** override to render counts when the items are rendered */
    renderItems : function( $whereTo ){
        var views = _super.prototype.renderItems.call( this, $whereTo );
        this._renderCounts( $whereTo );
        return views;
    },

    /** override to show counts, what's deleted/hidden, and links to toggle those */
    _renderCounts : function( $whereTo ){
//TODO: too complicated
        function toggleLink( _class, text ){
            return [ '<a class="', _class, '" href="javascript:void(0);">', text, '</a>' ].join( '' );
        }
        $whereTo = $whereTo || this.$el;
        var deleted  = this.collection.where({ deleted: true }),
            hidden   = this.collection.where({ visible: false }),
            msgs = [];

        if( this.views.length ){
            msgs.push( [ this.views.length, _l( 'shown' ) ].join( ' ' ) );
        }
        if( deleted.length ){
            msgs.push( ( !this.showDeleted )?
                 ([ deleted.length, toggleLink( 'toggle-deleted-link', _l( 'deleted' ) ) ].join( ' ' ))
                :( toggleLink( 'toggle-deleted-link', _l( 'hide deleted' ) ) )
            );
        }
        if( hidden.length ){
            msgs.push( ( !this.showHidden )?
                 ([ hidden.length, toggleLink( 'toggle-hidden-link', _l( 'hidden' ) ) ].join( ' ' ))
                :( toggleLink( 'toggle-hidden-link', _l( 'hide hidden' ) ) )
            );
        }
        return $whereTo.find( '> .controls .subtitle' ).html( msgs.join( ', ' ) );
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
     *  In this override, make the name editable
     */
    _setUpBehaviors : function( $where ){
        $where = $where || this.$el;
        _super.prototype._setUpBehaviors.call( this, $where );
        if( !this.model ){ return; }

        // anon users shouldn't have access to any of the following
        if( ( !Galaxy.currUser || Galaxy.currUser.isAnonymous() )
        ||  ( Galaxy.currUser.id !== this.model.get( 'user_id' ) ) ){
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
                        .done( function(){ panel.model.refresh() });
                }
            },
            // TODO: Only show quick pair if two things selected.
            {   html: _l( 'Build Dataset Pair' ), func: function() {
                    PAIR_COLLECTION_CREATOR.createPairCollection( panel.getSelectedModels() )
                        .done( function(){ panel.model.refresh() });
                }
            },
            {   html: _l( 'Build List of Dataset Pairs' ), func: function() {
                    LIST_OF_PAIRS_COLLECTION_CREATOR.createListOfPairsCollection( panel.getSelectedModels() )
                        .done( function(){ panel.model.refresh() });
                }
            },
        ];
    },

    // ------------------------------------------------------------------------ sub-views
    // reverse HID order
    /** Override to reverse order of views - newest contents on top */
    _attachItems : function( $whereTo ){
        this.$list( $whereTo ).append( this.views.reverse().map( function( view ){
            return view.$el;
        }));
        return this;
    },

    /** Override to add new contents at the top */
    _attachView : function( view ){
        var panel = this;
        // override to control where the view is added, how/whether it's rendered
        panel.views.unshift( view );
        panel.$list().prepend( view.render( 0 ).$el.hide() );
        panel.trigger( 'view:attached', view );
        view.$el.slideDown( panel.fxSpeed, function(){
            panel.trigger( 'view:attached:rendered' );
        });
    },

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

    ///** Override to alter data in drag based on multiselection */
    //_setUpItemViewListeners : function( view ){
    //    var panel = this;
    //    _super.prototype._setUpItemViewListeners.call( panel, view );
    //
    //},

    /** If this item is deleted and we're not showing deleted items, remove the view
     *  @param {Model} the item model to check
     */
    _handleHdaDeletionChange : function( itemModel ){
        if( itemModel.get( 'deleted' ) && !this.showDeleted ){
            this.removeItemView( itemModel );
        }
        this._renderCounts();
    },

    /** If this item is hidden and we're not showing hidden items, remove the view
     *  @param {Model} the item model to check
     */
    _handleHdaVisibleChange : function( itemModel ){
        if( itemModel.hidden() && !this.showHidden ){
            this.removeItemView( itemModel );
        }
        this._renderCounts();
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
        'click .show-selectors-btn'                 : 'toggleSelectors',
        'click .toggle-deleted-link'                : function( ev ){ this.toggleShowDeleted(); },
        'click .toggle-hidden-link'                 : function( ev ){ this.toggleShowHidden(); }
    }),

    /** Update the history size display (curr. upper right of panel).
     */
    updateHistoryDiskSize : function(){
        this.$el.find( '.history-size' ).text( this.model.get( 'nice_size' ) );
    },

    // ------------------------------------------------------------------------ as drop target
    /**  */
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
//TODO: scroll to top
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

    /**  */
    _renderDropTarget : function(){
        this.$( '.history-drop-target' ).remove();
        return $( '<div/>' ).addClass( 'history-drop-target' )
            .css({
                'height': '64px',
                'margin': '0px 10px 10px 10px',
                'border': '1px dashed black',
                'border-radius' : '3px'
            });
    },

    /**  */
    _renderDropTargetHelp : function(){
        this.$( '.history-drop-target-help' ).remove();
        return $( '<div/>' ).addClass( 'history-drop-target-help' )
            .css({
                'margin'        : '10px 10px 4px 10px',
                'color'         : 'grey',
                'font-size'     : '80%',
                'font-style'    : 'italic'
            })
            .text( _l( 'Drag datasets here to copy them to the current history' ) );
    },

    /**  */
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
    /**  */
    dropTargetToggle : function(){
        if( this.dropTarget ){
            this.dropTargetOff();
        } else {
            this.dropTargetOn();
        }
        return this;
    },

    /**  */
    dragenter : function( ev ){
        //console.debug( 'dragenter:', this, ev );
        ev.preventDefault();
        ev.stopPropagation();
        this.$( '.history-drop-target' ).css( 'border', '2px solid black' );
    },
    /**  */
    dragover : function( ev ){
        ev.preventDefault();
        ev.stopPropagation();
    },
    /**  */
    dragleave : function( ev ){
        //console.debug( 'dragleave:', this, ev );
        ev.preventDefault();
        ev.stopPropagation();
        this.$( '.history-drop-target' ).css( 'border', '1px dashed black' );
    },
    /**  */
    drop : function( ev ){
        //console.warn( 'dataTransfer:', ev.dataTransfer.getData( 'text' ) );
        //console.warn( 'dataTransfer:', ev.originalEvent.dataTransfer.getData( 'text' ) );
        ev.preventDefault();
        //ev.stopPropagation();
        ev.dataTransfer.dropEffect = 'move';

        //console.debug( 'ev.dataTransfer:', ev.dataTransfer );

        var panel = this,
            data = ev.dataTransfer.getData( "text" );
        try {
            data = JSON.parse( data );

        } catch( err ){
            this.warn( 'error parsing JSON from drop:', data );
        }
        this.trigger( 'droptarget:drop', ev, data, panel );
        return false;
    },

    /**  */
    dataDropped : function( data ){
        var panel = this;
        // HDA: dropping will copy it to the history
        if( _.isObject( data ) && data.model_class === 'HistoryDatasetAssociation' && data.id ){
            return panel.model.contents.copy( data.id );
        }
        return jQuery.when();
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
