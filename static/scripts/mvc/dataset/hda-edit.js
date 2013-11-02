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
                title       : _l( 'Edit Attributes' ),
                href        : this.urls.edit,
                target      : 'galaxy_main',
                icon_class  : 'edit'
            };
            
        // disable if purged or deleted and explain why in the tooltip
        if( deleted || purged ){
            editBtnData.enabled = false;
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

        
        //return new IconButtonView({ model : new IconButton( editBtnData ) }).render().$el;

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
            delete_url = self.urls[ 'delete' ],
            deleteBtnData = {
                title       : _l( 'Delete' ),
                href        : delete_url,
                icon_class  : 'delete',
                onclick    : function() {
                    // ...bler... tooltips being left behind in DOM (hover out never called on deletion)
                    self.$el.find( '.menu-button.delete' ).trigger( 'mouseout' );
                    self.model[ 'delete' ]();
                }
        };
        if( this.model.get( 'deleted' ) || this.model.get( 'purged' ) ){
            deleteBtnData = {
                title       : _l( 'Dataset is already deleted' ),
                icon_class  : 'delete',
                enabled     : false
            };
        }
        //return new IconButtonView({ model : new IconButton( deleteBtnData ) }).render().$el;

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
        
        //return new IconButtonView({ model : new IconButton({
        //    title       : _l( 'View or report this error' ),
        //    href        : this.urls.report_error,
        //    target      : 'galaxy_main',
        //    icon_class  : 'bug'
        //})}).render().$el;

        return faIconButton({
            title       : _l( 'View or report this error' ),
            href        : this.urls.report_error,
            target      : 'galaxy_main',
            faIcon      : 'fa-bug'
        });
    },
    
    /** Render icon-button to re-run the job that created this hda.
     *  @returns {jQuery} rendered DOM
     */
    _render_rerunButton : function(){
        //return new IconButtonView({ model : new IconButton({
        //    title       : _l( 'Run this job again' ),
        //    href        : this.urls.rerun,
        //    target      : 'galaxy_main',
        //    icon_class  : 'arrow-circle'
        //}) }).render().$el;

        return faIconButton({
            title       : _l( 'Run this job again' ),
            href        : this.urls.rerun,
            target      : 'galaxy_main',
            faIcon      : 'fa-refresh'
        });
    },
    
    /** Render an icon-button or popupmenu based on the number of applicable visualizations
     *      and map button/popup clicks to viz setup functions.
     *  @returns {jQuery} rendered DOM
     */
    _render_visualizationsButton : function(){
        var visualizations = this.model.get( 'visualizations' );
        if( ( !this.model.hasData() )
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

        // render the icon from template
        //var visualizationsButton = new IconButtonView({ model : new IconButton({
        //    title       : _l( 'Visualize' ),
        //    href        : this.urls.visualization,
        //    icon_class  : 'chart_curve'
        //})});
        //var $icon = visualizationsButton.render().addClass( 'visualize-icon' ); // needed?
        ////return visualizationsButton.render().$el;

        var $icon = faIconButton({
            title       : _l( 'Visualize' ),
            href        : this.urls.visualization,
            faIcon      : 'fa-bar-chart-o'
        });

        // map a function to each visualization in the icon's attributes
        //  create a popupmenu from that map
        /** @inner */
        function create_viz_action( visualization ) {
            switch( visualization ){
                case 'trackster':
                    return create_trackster_action_fn( visualization_url, params, dbkey );
                case 'scatterplot':
                    return create_scatterplot_action_fn( visualization_url, params );
                default:
                    return function(){// add widget
                        Galaxy.frame_manager.frame_new(
                        {
                            title    : "Visualization",
                            type     : "url",
                            content  : visualization_url + '/' + visualization + '?' + $.param( params )
                        });
                    };
            }
        }

        // No need for popup menu because there's a single visualization.
        if ( visualizations.length === 1 ) {
            $icon.attr( 'title', visualizations[0] );
            $icon.click( create_viz_action( visualizations[0] ) );

        // >1: Populate menu dict with visualization fns, make the popupmenu
        } else {
            _.each( visualizations, function( visualization ) {
                var titleCaseVisualization = visualization.charAt( 0 ).toUpperCase() + visualization.slice( 1 );
                popup_menu_dict[ _l( titleCaseVisualization ) ] = create_viz_action( visualization );
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

        // render the icon from template
        //var visualizationsButton = new IconButtonView({ model : new IconButton({
        //    title       : _l( 'Visualize' ),
        //    icon_class  : 'chart_curve'
        //})});
        //var $icon = visualizationsButton.render().$el;
        var $icon = faIconButton({
            title       : _l( 'Visualize' ),
            faIcon      : 'fa-bar-chart-o'
        });
        $icon.addClass( 'visualize-icon' ); // needed?

        // No need for popup menu because there's a single visualization.
        if( _.keys( visualizations ).length === 1 ) {
            $icon.attr( 'title', _.keys( visualizations )[0] );
            $icon.attr( 'href', _.values( visualizations )[0] );

        // >1: Populate menu dict with visualization fns, make the popupmenu
        } else {
            var popup_menu_options = [];
            _.each( visualizations, function( linkData ) {
                popup_menu_options.push( linkData );
            });
            var popup = new PopupMenu( $icon, popup_menu_options );
        }
        return $icon;
    },
    
    // ......................................................................... secondary actions
    /** Render icon-button to load and display tagging html.
     *  @returns {jQuery} rendered DOM
     */
    _render_tagButton : function(){
        if( !this.hasUser ){
            return null;
        }
        
        //return new IconButtonView({ model : new IconButton({
        //    title       : _l( 'Edit dataset tags' ),
        //    target      : 'galaxy_main',
        //    href        : this.urls.tags.get,
        //    icon_class  : 'tags'
        //})}).render().$el;

        return faIconButton({
            title       : _l( 'Edit dataset tags' ),
            classes     : 'dataset-tag-btn',
            faIcon      : 'fa-tags'
        });
    },

    /** Render icon-button to load and display annotation html.
     *  @returns {jQuery} rendered DOM
     */
    _render_annotateButton : function(){
        if( !this.hasUser ){
            return null;
        }

        //return new IconButtonView({ model : new IconButton({
        //    title       : _l( 'Edit dataset annotation' ),
        //    target      : 'galaxy_main',
        //    icon_class  : 'annotate'
        //})}).render().$el;
        return faIconButton({
            title       : _l( 'Edit dataset annotation' ),
            classes     : 'dataset-annotate-btn',
            faIcon      : 'fa-comment'
        });
    },
    
    // ......................................................................... state body renderers
    /** Render an HDA where the metadata wasn't produced correctly.
     *      Overridden to add a link to dataset/edit
     *  @see HDABaseView#_render_body_failed_metadata
     */
    _render_body_failed_metadata : function(){
        // add a message box about the failure at the top of the body then render the remaining body as STATES.OK
        var $link = $( '<a/>' ).attr({ href: this.urls.edit, target: 'galaxy_main' })
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
        $body.find( '.dataset-actions .left' ).append( this._render_visualizationsButton() );
        $body.find( '.dataset-actions .right' ).append([
            this._render_tagButton(),
            this._render_annotateButton()
        ]);
        this.tagsEditor = new TagsEditor({
            model   : this.model,
            el      : $body.find( '.tags-display' )
        }).render();
        return $body;
    },

    makeDbkeyEditLink : function( $body ){
        // make the dbkey a link to editing
        if( this.model.get( 'metadata_dbkey' ) === '?'
        &&  !this.model.isDeletedOrPurged() ){
            $body.find( '.dataset-dbkey .value' ).replaceWith(
                $( '<a target="galaxy_main">?</a>' ).attr( 'href', this.urls.edit ) );
        }
    },

    // ......................................................................... events
    /** event map */
    events : {
        'click .dataset-title-bar'      : 'toggleBodyVisibility',
        'click .dataset-undelete'       : function( ev ){ this.model.undelete(); return false; },
        'click .dataset-unhide'         : function( ev ){ this.model.unhide();   return false; },
        'click .dataset-purge'          : 'confirmPurge',

        'click .dataset-tag-btn'        : 'displayTags',
        'click .dataset-annotate-btn'   : 'loadAndDisplayAnnotation'
    },
    
    /** listener for item purge */
    confirmPurge : function _confirmPurge( ev ){
//TODO: confirm dialog
        this.model.purge();
        return false;
    },

    // ......................................................................... tags
    /** Find the tag area and, if initial: load the html (via ajax) for displaying them; otherwise, unhide/hide
     */
//TODO: into sub-MV
    displayTags : function( event ){
        this.$el.find( '.tags-display' ).slideToggle( this.fxSpeed );
        return false;
    },

    // ......................................................................... annotations
    /** Find the annotation area and, if initial: load the html (via ajax) for displaying them; otherwise, unhide/hide
     */
    loadAndDisplayAnnotation : function( event ){
//TODO: this is a drop in from history.mako - should use MV as well
        this.log( this + '.loadAndDisplayAnnotation', event );
        var view = this,
            $annotationArea = this.$el.find( '.annotation-display' ),
            $annotationElem = $annotationArea.find( '.annotation' );

        // Show or hide annotation area; if showing annotation area and it's empty, fill it.
        if ( $annotationArea.is( ":hidden" ) ){
            if( !jQuery.trim( $annotationElem.html() ) ){
                // Need to fill annotation element.
                var xhr = $.ajax( this.urls.annotation.get );
                xhr.fail( function( xhr, status, error ){
                    view.log( "Annotation failed", xhr, status, error );
                    view.trigger( 'error', view, xhr, {}, _l( "Annotation failed" ) );
                });
                xhr.done( function( html ){
                    html = html || "<em>" + _l( "Describe or add notes to dataset" ) + "</em>";
                    $annotationElem.html( html );
                    $annotationArea.find( "[title]" ).tooltip();

                    $annotationElem.make_text_editable({
                        use_textarea: true,
                        on_finish: function( newAnnotation ){
                            $annotationElem.text( newAnnotation );
                            view.model.save({ annotation: newAnnotation }, { silent: true })
                                .fail( function(){
                                    $annotationElem.text( view.model.previous( 'annotation' ) );
                                });
                        }
                    });
                    $annotationArea.slideDown( view.fxSpeed );
                });
            } else {
                $annotationArea.slideDown( view.fxSpeed );
            }
        } else {
            $annotationArea.slideUp( view.fxSpeed );
        }
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
function create_scatterplot_action_fn( url, params ){
    action = function() {
        // add widget
        Galaxy.frame_manager.frame_new(
        {
            title      : "Scatterplot",
            type       : "url",
            content    : url + '/scatterplot?' + $.param(params),
            location   : 'center'
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
                                                parent.Galaxy.frame_manager.frame_new({
                                                    title    : "Trackster",
                                                    type     : "url",
                                                    content  : vis_url + "/trackster?" + $.param(dataset_params)
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
                                parent.Galaxy.frame_manager.frame_new({
                                    title    : "Trackster",
                                    type     : "url",
                                    content  : url
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
