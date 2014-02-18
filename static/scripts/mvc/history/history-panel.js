define([
    "mvc/dataset/hda-model",
    "mvc/dataset/hda-edit",
    "mvc/history/readonly-history-panel"
], function( hdaModel, hdaEdit, readonlyPanel ){
/* =============================================================================
TODO:

============================================================================= */
/** @class View/Controller for the history model.
 *  @name HistoryPanel
 *
 *  Allows:
 *      (everything ReadOnlyHistoryPanel allows)
 *      changing the name
 *      displaying and editing tags and annotations
 *      multi-selection and operations on mulitple hdas
 *  Does not allow:
 *      changing the name
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HistoryPanel = readonlyPanel.ReadOnlyHistoryPanel.extend(
/** @lends HistoryPanel.prototype */{

    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,

    /** class to use for constructing the HDA views */
    HDAViewClass : hdaEdit.HDAEditView,

    // ......................................................................... SET UP
    /** Set up the view, set up storage, bind listeners to HDACollection events
     *  @param {Object} attributes
     */
    initialize : function( attributes ){
        attributes = attributes || {};

        // ---- set up instance vars
        /** selected hda ids */
        this.selectedHdaIds = [];

        // states/modes the panel can be in
        /** is the panel currently showing the dataset selection controls? */
        this.selecting = attributes.selecting || false;
        this.annotationEditorShown  = attributes.annotationEditorShown || false;
        this.tagsEditorShown  = attributes.tagsEditorShown || false;

        readonlyPanel.ReadOnlyHistoryPanel.prototype.initialize.call( this, attributes );
    },

    // ------------------------------------------------------------------------ panel rendering
    /** listening for history and HDA events */
    _setUpModelEventHandlers : function(){
        readonlyPanel.ReadOnlyHistoryPanel.prototype._setUpModelEventHandlers.call( this );

        this.model.on( 'change:nice_size', this.updateHistoryDiskSize, this );

        this.model.hdas.on( 'change:deleted', this.handleHdaDeletionChange, this );
        this.model.hdas.on( 'change:visible', this.handleHdaVisibleChange, this );
        this.model.hdas.on( 'change:purged', function( hda ){
            // hafta get the new nice-size w/o the purged hda
            this.model.fetch();
        }, this );
    },

    // ------------------------------------------------------------------------ panel rendering
    /** render with history data */
    renderModel : function( ){
        var $newRender = $( '<div/>' );

        $newRender.append( HistoryPanel.templates.historyPanel( this.model.toJSON() ) );
        if( Galaxy.currUser.id && Galaxy.currUser.id === this.model.get( 'user_id' ) ){
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

    _renderTags : function( $where ){
        var panel = this;
        this.tagsEditor = new TagsEditor({
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
    _renderAnnotation : function( $where ){
        var panel = this;
        this.annotationEditor = new AnnotationEditor({
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
                title   : _l( 'Edit history Annotation' ),
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

    /** Set up HistoryPanel js/widget behaviours */
    _setUpBehaviours : function( $where ){
        //TODO: these should be either sub-MVs, or handled by events
        $where = $where || this.$el;
        $where.find( '[title]' ).tooltip({ placement: 'bottom' });

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

    _setUpDatasetActionsPopup : function( $where ){
        var panel = this;
        ( new PopupMenu( $where.find( '.history-dataset-action-popup-btn' ), [
            {
                html: _l( 'Hide datasets' ), func: function(){
                    var action = hdaModel.HistoryDatasetAssociation.prototype.hide;
                    panel.getSelectedHdaCollection().ajaxQueue( action );
                }
            },
            {
                html: _l( 'Unhide datasets' ), func: function(){
                    var action = hdaModel.HistoryDatasetAssociation.prototype.unhide;
                    panel.getSelectedHdaCollection().ajaxQueue( action );
                }
            },
            {
                html: _l( 'Delete datasets' ), func: function(){
                    var action = hdaModel.HistoryDatasetAssociation.prototype['delete'];
                    panel.getSelectedHdaCollection().ajaxQueue( action );
                }
            },
            {
                html: _l( 'Undelete datasets' ), func: function(){
                    var action = hdaModel.HistoryDatasetAssociation.prototype.undelete;
                    panel.getSelectedHdaCollection().ajaxQueue( action );
                }
            },
            {
                html: _l( 'Permanently delete datasets' ), func: function(){
                    if( confirm( _l( 'This will permanently remove the data in your datasets. Are you sure?' ) ) ){
                        var action = hdaModel.HistoryDatasetAssociation.prototype.purge;
                        panel.getSelectedHdaCollection().ajaxQueue( action );
                    }
                }
            }
        ]));
    },

    // ------------------------------------------------------------------------ hda sub-views
    /** If this hda is deleted and we're not showing deleted hdas, remove the view
     *  @param {HistoryDataAssociation} the hda to check
     */
    handleHdaDeletionChange : function( hda ){
        if( hda.get( 'deleted' ) && !this.storage.get( 'show_deleted' ) ){
            this.removeHdaView( this.hdaViews[ hda.id ] );
        } // otherwise, the hdaView rendering should handle it
    },


    /** If this hda is hidden and we're not showing hidden hdas, remove the view
     *  @param {HistoryDataAssociation} the hda to check
     */
    handleHdaVisibleChange : function( hda ){
        if( hda.hidden() && !this.storage.get( 'show_hidden' ) ){
            this.removeHdaView( this.hdaViews[ hda.id ] );
        } // otherwise, the hdaView rendering should handle it
    },

    /** Create an HDA view for the given HDA (but leave attachment for addHdaView above)
     *  @param {HistoryDatasetAssociation} hda
     */
    createHdaView : function( hda ){
        var hdaId = hda.get( 'id' ),
            hdaView = new this.HDAViewClass({
                model           : hda,
                linkTarget      : this.linkTarget,
                expanded        : this.storage.get( 'expandedHdas' )[ hdaId ],
                //draggable       : true,
                selectable      : this.selecting,
                hasUser         : this.model.ownedByCurrUser(),
                logger          : this.logger,
                tagsEditorShown       : !this.tagsEditor.isHidden(),
                annotationEditorShown : !this.annotationEditor.isHidden()
            });
        this._setUpHdaListeners( hdaView );
        return hdaView;
    },

    /** Set up HistoryPanel listeners for HDAView events. Currently binds:
     *      HDAView#body-visible, HDAView#body-hidden to store expanded states
     *  @param {HDAView} hdaView HDAView (base or edit) to listen to
     */
    _setUpHdaListeners : function( hdaView ){
        var historyView = this;
        readonlyPanel.ReadOnlyHistoryPanel.prototype._setUpHdaListeners.call( this, hdaView );

        // maintain a list of hdas that are selected
        hdaView.on( 'selected', function( hdaView ){
            var id = hdaView.model.get( 'id' );
            historyView.selectedHdaIds = _.union( historyView.selectedHdaIds, [ id ] );
            //console.debug( 'selected', historyView.selectedHdaIds );
        });
        hdaView.on( 'de-selected', function( hdaView ){
            var id = hdaView.model.get( 'id' );
            historyView.selectedHdaIds = _.without( historyView.selectedHdaIds, id );
            //console.debug( 'de-selected', historyView.selectedHdaIds );
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
                panel.$el.find( panel.emptyMsgSelector ).fadeIn( panel.fxSpeed, function(){
                    panel.trigger( 'empty-history', panel );
                });
            }
        });
    },

    // ------------------------------------------------------------------------ panel events
    /** event map */
    events : _.extend( _.clone( readonlyPanel.ReadOnlyHistoryPanel.prototype.events ), {
        'click .history-select-btn'     : function( e ){ this.toggleSelectors( this.fxSpeed ); },
        'click .history-select-all-datasets-btn'    : 'selectAllDatasets',
        'click .history-deselect-all-datasets-btn'  : 'deselectAllDatasets'
    }),

    /** Update the history size display (curr. upper right of panel).
     */
    updateHistoryDiskSize : function(){
        this.$el.find( '.history-size' ).text( this.model.get( 'nice_size' ) );
    },

    // ........................................................................ multi-select of hdas
    /** show selectors on all visible hdas and associated controls */
    showSelectors : function( speed ){
        this.selecting = true;
        this.$el.find( '.history-dataset-actions' ).slideDown( speed );
        _.each( this.hdaViews, function( view ){
            view.showSelector( speed );
        });
        this.selectedHdaIds = [];
    },

    /** hide selectors on all visible hdas and associated controls */
    hideSelectors : function( speed ){
        this.selecting = false;
        this.$el.find( '.history-dataset-actions' ).slideUp( speed );
        _.each( this.hdaViews, function( view ){
            view.hideSelector( speed );
        });
        this.selectedHdaIds = [];
    },

    /** show or hide selectors on all visible hdas and associated controls */
    toggleSelectors : function( speed ){
        if( !this.selecting ){
            this.showSelectors( speed );
        } else {
            this.hideSelectors( speed );
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
        _.each( this.hdaViews, function( view ){
            view.deselect( event );
        });
    },

    /** return an array of all currently selected hdas */
    getSelectedHdaViews : function(){
        return _.filter( this.hdaViews, function( v ){
            return v.selected;
        });
    },

    /** return an HdaCollection of the models of all currenly selected hdas */
    getSelectedHdaCollection : function(){
        return new hdaModel.HDACollection( _.map( this.getSelectedHdaViews(), function( hdaView ){
            return hdaView.model;
        }), { historyId: this.model.id });
    },

    // ........................................................................ misc
    /** Return a string rep of the history */
    toString    : function(){
        return 'HistoryPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});

//------------------------------------------------------------------------------ TEMPLATES
HistoryPanel.templates = {
    historyPanel     : Handlebars.templates[ 'template-history-historyPanel' ],
    anonHistoryPanel : Handlebars.templates[ 'template-history-historyPanel-anon' ]
};

//==============================================================================
    return {
        HistoryPanel        : HistoryPanel
    };
});
