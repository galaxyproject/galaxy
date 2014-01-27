define([
    "mvc/dataset/hda-model",
    "mvc/dataset/hda-base"
], function( hdaModel, hdaBase ){
//==============================================================================
/** @class Editing view for HistoryDatasetAssociation.
 *  @name HDAEditView
 *
 *  @augments HDABaseView
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HDAEditView = hdaBase.HDABaseView.extend( LoggableMixin ).extend(
/** @lends HDAEditView.prototype */{

    // ......................................................................... set up
    /** Set up the view, cache url templates, bind listeners.
     *      Overrides HDABaseView.initialize to change default actions (adding re-run).
     *  @param {Object} attributes
     *  @config {Object} urlTemplates nested object containing url templates for this view
     *  @throws 'needs urlTemplates' if urlTemplates isn't present
     *  @see HDABaseView#initialize
     */
    initialize  : function( attributes ){
        hdaBase.HDABaseView.prototype.initialize.call( this, attributes );
        this.hasUser = attributes.hasUser;

        /** list of rendering functions for the default, primary icon-buttons. */
        this.defaultPrimaryActionButtonRenderers = [
            this._render_showParamsButton,
            // HDAEdit gets the rerun button on almost all states
            this._render_rerunButton
        ];

        //TODO: move to HiddenUntilActivatedViewMixin
        /** should the tags editor be shown or hidden initially? */
        this.tagsEditorShown        = attributes.tagsEditorShown || false;
        /** should the tags editor be shown or hidden initially? */
        this.annotationEditorShown  = attributes.annotationEditorShown || false;
    },

    // ......................................................................... edit attr, delete
    /** Render icon-button group for the common, most easily accessed actions.
     *      Overrides _render_titleButtons to include edit and delete buttons.
     *  @see HDABaseView#_render_titleButtons
     *  @returns {jQuery} rendered DOM
     */
    _render_titleButtons : function(){
        // render the display, edit attr and delete icon-buttons
        return hdaBase.HDABaseView.prototype._render_titleButtons.call( this ).concat([
            this._render_editButton(),
            this._render_deleteButton()
        ]);
    },
    
//TODO: move titleButtons into state renderers, remove state checks in the buttons

    /** Render icon-button to edit the attributes (format, permissions, etc.) this hda.
     *  @returns {jQuery} rendered DOM
     */
    _render_editButton : function(){
        // don't show edit while uploading, in-accessible
        // DO show if in error (ala previous history panel)
        if( ( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.NEW )
        ||  ( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.DISCARDED )
        ||  ( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.NOT_VIEWABLE )
        ||  ( !this.model.get( 'accessible' ) ) ){
            return null;
        }
        
        var purged = this.model.get( 'purged' ),
            deleted = this.model.get( 'deleted' ),
            editBtnData = {
                title       : _l( 'Edit attributes' ),
                href        : this.urls.edit,
                target      : this.linkTarget,
                classes     : 'dataset-edit'
            };
            
        // disable if purged or deleted and explain why in the tooltip
        if( deleted || purged ){
            editBtnData.disabled = true;
            if( purged ){
                editBtnData.title = _l( 'Cannot edit attributes of datasets removed from disk' );
            } else if( deleted ){
                editBtnData.title = _l( 'Undelete dataset to edit attributes' );
            }

        // disable if still uploading
        } else if( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.UPLOAD ){
            editBtnData.disabled = true;
            editBtnData.title = _l( 'This dataset must finish uploading before it can be edited' );
        }
        editBtnData.faIcon = 'fa-pencil';
        return faIconButton( editBtnData );
    },
    
    /** Render icon-button to delete this hda.
     *  @returns {jQuery} rendered DOM
     */
    _render_deleteButton : function(){
        // don't show delete if...
        if( ( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.NEW )
        ||  ( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.NOT_VIEWABLE )
        ||  ( !this.model.get( 'accessible' ) ) ){
            return null;
        }
        
        var self = this,
            deleteBtnData = {
                title       : _l( 'Delete' ),
                classes     : 'dataset-delete',
                onclick     : function() {
                    // ...bler... tooltips being left behind in DOM (hover out never called on deletion)
                    self.$el.find( '.icon-btn.dataset-delete' ).trigger( 'mouseout' );
                    self.model[ 'delete' ]();
                }
        };
        if( this.model.get( 'deleted' ) || this.model.get( 'purged' ) ){
            deleteBtnData = {
                title       : _l( 'Dataset is already deleted' ),
                disabled    : true
            };
        }
        deleteBtnData.faIcon = 'fa-times';
        return faIconButton( deleteBtnData );
    },

    // ......................................................................... primary actions
    /** Render icon-button to report an error on this hda to the galaxy admin.
     *  @returns {jQuery} rendered DOM
     */
    _render_errButton : function(){
        if( this.model.get( 'state' ) !== hdaModel.HistoryDatasetAssociation.STATES.ERROR ){
            return null;
        }
        return faIconButton({
            title       : _l( 'View or report this error' ),
            href        : this.urls.report_error,
            classes     : 'dataset-report-error-btn',
            target      : this.linkTarget,
            faIcon      : 'fa-bug'
        });
    },
    
    /** Render icon-button to re-run the job that created this hda.
     *  @returns {jQuery} rendered DOM
     */
    _render_rerunButton : function(){
        return faIconButton({
            title       : _l( 'Run this job again' ),
            href        : this.urls.rerun,
            classes     : 'dataset-rerun-btn',
            target      : this.linkTarget,
            faIcon      : 'fa-refresh'
        });
    },
    
    /** Render an icon-button or popupmenu based on the number of applicable visualizations
     *      and map button/popup clicks to viz setup functions.
     *  @returns {jQuery} rendered DOM
     */
    _render_visualizationsButton : function(){
        var visualizations = this.model.get( 'visualizations' );
        if( ( !this.hasUser )
        ||  ( !this.model.hasData() )
        ||  ( _.isEmpty( visualizations ) ) ){
            return null;
        }

        //TODO: this is a bridge to allow the framework to be switched off
        // remove this fn and use the other when fully integrated
        if( _.isObject( visualizations[0] ) ){
            return this._render_visualizationsFrameworkButton( visualizations );
        }

        if( !this.urls.visualization ){
            return null;
        }

        var dbkey = this.model.get( 'dbkey' ),
            visualization_url = this.urls.visualization,
            popup_menu_dict = {},
            params = {
                dataset_id: this.model.get( 'id' ),
                hda_ldda: 'hda'
            };
        // Add dbkey to params if it exists.
        if( dbkey ){ params.dbkey = dbkey; }

        var $icon = faIconButton({
            title       : _l( 'Visualize' ),
            classes     : 'dataset-visualize-btn',
            faIcon      : 'fa-bar-chart-o'
        });

        // map a function to each visualization in the icon's attributes
        //  create a popupmenu from that map
        var hdaView = this;
        /** @inner */
        function create_viz_action( visualization ) {
            switch( visualization ){
                case 'trackster':
                    return create_trackster_action_fn( visualization_url, params, dbkey );
                case 'scatterplot':
                    return create_scatterplot_action_fn( visualization_url, params, hdaView.linkTarget );
                default:
                    return function(){
                        Galaxy.frame.add({
                            title       : "Visualization",
                            type        : "url",
                            content     : visualization_url + '/' + visualization + '?' + $.param( params )
                        });
                    };
            }
        }

        function titleCase( string ){
            return string.charAt( 0 ).toUpperCase() + string.slice( 1 );
        }

        // No need for popup menu because there's a single visualization.
        if( visualizations.length === 1 ){
            $icon.attr( 'data-original-title', _l( 'Visualize in ' ) + _l( titleCase( visualizations[0] ) ) );
            $icon.click( create_viz_action( visualizations[0] ) );

        // >1: Populate menu dict with visualization fns, make the popupmenu
        } else {
            _.each( visualizations, function( visualization ) {
                popup_menu_dict[ _l( titleCase( visualization ) ) ] = create_viz_action( visualization );
            });
            make_popupmenu( $icon, popup_menu_dict );
        }
        return $icon;
    },

    /** Render an icon-button or popupmenu of links based on the applicable visualizations
     *  @returns {jQuery} rendered DOM
     */
    _render_visualizationsFrameworkButton : function( visualizations ){
        if( !( this.model.hasData() )
        ||  !( visualizations && !_.isEmpty( visualizations ) ) ){
            return null;
        }
        var $icon = faIconButton({
            title       : _l( 'Visualize' ),
            classes     : 'dataset-visualize-btn',
            faIcon      : 'fa-bar-chart-o'
        });

        // No need for popup menu because there's a single visualization.
        if( visualizations.length === 1 ) {
            var onlyVisualization = visualizations[0];
            $icon.attr( 'data-original-title', _l( 'Visualize in ' ) + onlyVisualization.html );
            $icon.attr( 'href', onlyVisualization.href );

        // >1: Populate menu dict with visualization fns, make the popupmenu
        } else {
            var popup_menu_options = [];
            _.each( visualizations, function( linkData ) {
                linkData.func = function(){
                    if( Galaxy.frame.active ){
                        Galaxy.frame.add({
                            title       : "Visualization",
                            type        : "url",
                            content     : linkData.href
                        });
                        return false;
                    }
                    return true;
                };
                popup_menu_options.push( linkData );
                return false;
            });
            PopupMenu.create( $icon, popup_menu_options );
        }
        return $icon;
    },

    // ......................................................................... render main
    _buildNewRender : function(){
        var $newRender = hdaBase.HDABaseView.prototype._buildNewRender.call( this );

        //TODO: this won't localize easily
        $newRender.find( '.dataset-deleted-msg' ).append(
            _l( 'Click <a href="javascript:void(0);" class="dataset-undelete">here</a> to undelete it' +
            ' or <a href="javascript:void(0);" class="dataset-purge">here</a> to immediately remove it from disk' ));

        $newRender.find( '.dataset-hidden-msg' ).append(
            _l( 'Click <a href="javascript:void(0);" class="dataset-unhide">here</a> to unhide it' ));

        return $newRender;
    },
    
    // ......................................................................... state body renderers
    /** Render an HDA where the metadata wasn't produced correctly.
     *      Overridden to add a link to dataset/edit
     *  @see HDABaseView#_render_body_failed_metadata
     */
    _render_body_failed_metadata : function(){
        // add a message box about the failure at the top of the body then render the remaining body as STATES.OK
        var $link = $( '<a/>' ).attr({ href: this.urls.edit, target: this.linkTarget })
                .text( _l( 'set it manually or retry auto-detection' ) ),
            $span = $( '<span/>' ).text( '. ' + _l( 'You may be able to' ) + ' ' ).append( $link ),
            $body = hdaBase.HDABaseView.prototype._render_body_failed_metadata.call( this );
        $body.find( '.warningmessagesmall strong' ).append( $span );
        return $body;
    },

    /** Render an HDA whose job has failed.
     *      Overrides _render_body_error to prepend error report button to primary actions strip.
     *  @see HDABaseView#_render_body_error
     */
    _render_body_error : function(){
        var $body = hdaBase.HDABaseView.prototype._render_body_error.call( this );
        $body.find( '.dataset-actions .left' ).prepend( this._render_errButton() );
        return $body;
    },

    /** Render an HDA that's done running and where everything worked.
     *      Overrides _render_body_ok to add tag/annotation functionality and additional primary actions
     *  @param {jQuery} parent DOM to which to append this body
     *  @see HDABaseView#_render_body_ok
     */
    _render_body_ok : function(){
        var $body = hdaBase.HDABaseView.prototype._render_body_ok.call( this );
        // return shortened form if del'd
        if( this.model.isDeletedOrPurged() ){
            return $body;
        }
        this.makeDbkeyEditLink( $body );

        // more actions/buttons
        if( this.hasUser ){
            $body.find( '.dataset-actions .left' ).append( this._render_visualizationsButton() );
            //TODO: might be better to move these into the render() and call setElement here
            this._renderTags( $body );
            this._renderAnnotation( $body );
        }
        return $body;
    },

    _renderTags : function( $where ){
        var view = this;
        this.tagsEditor = new TagsEditor({
            model           : this.model,
            el              : $where.find( '.tags-display' ),
            onshowFirstTime : function(){ this.render(); },
            // persist state on the hda view (and not the editor) since these are currently re-created each time
            onshow          : function(){ view.tagsEditorShown = true; },
            onhide          : function(){ view.tagsEditorShown = false; },
            $activator      : faIconButton({
                title   : _l( 'Edit dataset tags' ),
                classes : 'dataset-tag-btn',
                faIcon  : 'fa-tags'
            }).appendTo( $where.find( '.dataset-actions .right' ) )
        });
        if( this.tagsEditorShown ){ this.tagsEditor.toggle( true ); }
    },
    _renderAnnotation : function( $where ){
        var view = this;
        this.annotationEditor = new AnnotationEditor({
            model           : this.model,
            el              : $where.find( '.annotation-display' ),
            onshowFirstTime : function(){ this.render(); },
            // persist state on the hda view (and not the editor) since these are currently re-created each time
            onshow          : function(){ view.annotationEditorShown = true; },
            onhide          : function(){ view.annotationEditorShown = false; },
            $activator      : faIconButton({
                title   : _l( 'Edit dataset annotation' ),
                classes : 'dataset-annotate-btn',
                faIcon  : 'fa-comment'
            }).appendTo( $where.find( '.dataset-actions .right' ) )
        });
        if( this.annotationEditorShown ){ this.annotationEditor.toggle( true ); }
    },

    makeDbkeyEditLink : function( $body ){
        // make the dbkey a link to editing
        if( this.model.get( 'metadata_dbkey' ) === '?'
        &&  !this.model.isDeletedOrPurged() ){
            var editableDbkey = $( '<a class="value">?</a>' )
                .attr( 'href', this.urls.edit )
                .attr( 'target', this.linkTarget );
            $body.find( '.dataset-dbkey .value' ).replaceWith( editableDbkey );
        }
    },

    // ......................................................................... events
    /** event map */
    events : _.extend( _.clone( hdaBase.HDABaseView.prototype.events ), {
        'click .dataset-undelete'       : function( ev ){ this.model.undelete(); return false; },
        'click .dataset-unhide'         : function( ev ){ this.model.unhide();   return false; },
        'click .dataset-purge'          : 'confirmPurge'
    }),
    
    /** listener for item purge */
    confirmPurge : function _confirmPurge( ev ){
        //TODO: confirm dialog
        this.model.purge();
        return false;
    },

    // ......................................................................... misc
    /** string rep */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'HDAView(' + modelString + ')';
    }
});

//==============================================================================
//TODO: these belong somewhere else

/** Create scatterplot loading/set up function for use with the visualizations popupmenu.
 *  @param {String} url url (gen. 'visualizations') to which to append 'scatterplot' and params
 *  @param {Object} params parameters to convert to query string for splot page
 *  @returns function that loads the scatterplot
 */
//TODO: should be imported from scatterplot.js OR abstracted to 'load this in the galaxy_main frame'
function create_scatterplot_action_fn( url, params, target ){
    action = function() {
        Galaxy.frame.add({
            title       : "Scatterplot",
            type        : "url",
            content     : url + '/scatterplot?' + $.param(params),
            target      : target
        });

        //TODO: this needs to go away
        $( 'div.popmenu-wrapper' ).remove();
        return false;
    };
    return action;
}

// -----------------------------------------------------------------------------
/** Create trackster loading/set up function for use with the visualizations popupmenu.
 *      Shows modal dialog for load old/create new.
 *  @param {String} vis_url visualizations url (gen. 'visualizations')
 *  @param {Object} dataset_params parameters to pass to trackster in the query string.
 *  @returns function that displays modal, loads trackster
 */
//TODO: should be imported from trackster.js
//TODO: This function is redundant and also exists in data.js
    // create action
    function create_trackster_action_fn (vis_url, dataset_params, dbkey) {
        return function() {
            var listTracksParams = {};
            if (dbkey){
                // list_tracks seems to use 'f-dbkey' (??)
                listTracksParams[ 'f-dbkey' ] = dbkey;
            }
            $.ajax({
                url: vis_url + '/list_tracks?' + $.param( listTracksParams ),
                dataType: "html",
                error: function() { alert( ( "Could not add this dataset to browser" ) + '.' ); },
                success: function(table_html) {
                    var parent = window.parent;
                    parent.Galaxy.modal.show({
                        title   : "View Data in a New or Saved Visualization",
                        buttons :{
                            "Cancel": function(){
                                parent.Galaxy.modal.hide();
                            },
                            "View in saved visualization": function(){
                                // Show new modal with saved visualizations.
                                parent.Galaxy.modal.show(
                                {
                                    title: "Add Data to Saved Visualization",
                                    body: table_html,
                                    buttons :{
                                        "Cancel": function(){
                                            parent.Galaxy.modal.hide();
                                        },
                                        "Add to visualization": function(){
                                            $(parent.document).find('input[name=id]:checked').each(function(){
                                                // hide
                                                parent.Galaxy.modal.hide();
                                                
                                                var vis_id = $(this).val();
                                                dataset_params.id = vis_id;
                                        
                                                // add widget
                                                parent.Galaxy.frame.add({
                                                    title       : "Trackster",
                                                    type        : "url",
                                                    content     : vis_url + "/trackster?" + $.param(dataset_params)
                                                });
                                            });
                                        }
                                    }
                                });
                            },
                            "View in new visualization": function(){
                                // hide
                                parent.Galaxy.modal.hide();
                                
                                var url = vis_url + "/trackster?" + $.param(dataset_params);

                                // add widget
                                parent.Galaxy.frame.add({
                                    title       : "Trackster",
                                    type        : "url",
                                    content     : url
                                });
                            }
                        }
                    });
                }
            });
            return false;
        };
    }


//==============================================================================
return {
    HDAEditView  : HDAEditView
};});
