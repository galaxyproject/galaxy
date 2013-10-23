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

    /** Set up js behaviors, event handlers for elements within the given container.
     *      Overridden from hda-base.
     *  @param {jQuery} $container jq object that contains the elements to process (defaults to this.$el)
     */
    _setUpBehaviors : function( $container ){
        hdaBase.HDABaseView.prototype._setUpBehaviors.call( this, $container );
        //var hdaView = this;
    },

    // ......................................................................... render warnings
    /** Render any hda warnings including: is deleted, is purged, is hidden.
     *      Overrides _render_warnings to include links to further actions (undelete, etc.)).
     *  @returns {Object} the templated urls
     *  @see HDABaseView#_render_warnings
     */
    _render_warnings : function(){
        // jQ errs on building dom with whitespace - if there are no messages, trim -> ''
        return $( jQuery.trim( hdaBase.HDABaseView.templates.messages(
            _.extend( this.model.toJSON(), { urls: this.urls } )
        )));
    },
    
    // ......................................................................... edit attr, delete
    /** Render icon-button group for the common, most easily accessed actions.
     *      Overrides _render_titleButtons to include edit and delete buttons.
     *  @see HDABaseView#_render_titleButtons
     *  @returns {jQuery} rendered DOM
     */
    _render_titleButtons : function(){
        // render the display, edit attr and delete icon-buttons
        var buttonDiv = $( '<div class="historyItemButtons"></div>' );
        buttonDiv.append( this._render_displayButton() );
        buttonDiv.append( this._render_editButton() );
        buttonDiv.append( this._render_deleteButton() );
        return buttonDiv;
    },
    
//TODO: move titleButtons into state renderers, remove state checks in the buttons

    /** Render icon-button to edit the attributes (format, permissions, etc.) this hda.
     *  @returns {jQuery} rendered DOM
     */
    _render_editButton : function(){
        // don't show edit while uploading, in-accessible
        // DO show if in error (ala previous history panel)
        if( ( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.NEW )
        ||  ( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.UPLOAD )
        ||  ( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.NOT_VIEWABLE )
        ||  ( !this.model.get( 'accessible' ) ) ){
            this.editButton = null;
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
        }
        
        this.editButton = new IconButtonView({ model : new IconButton( editBtnData ) });
        return this.editButton.render().$el;
    },
    
    /** Render icon-button to delete this hda.
     *  @returns {jQuery} rendered DOM
     */
    _render_deleteButton : function(){
        // don't show delete if...
        if( ( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.NEW )
        ||  ( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.NOT_VIEWABLE )
        ||  ( !this.model.get( 'accessible' ) ) ){
            this.deleteButton = null;
            return null;
        }
        
        var self = this,
            id = 'historyItemDeleter-' + self.model.get( 'id' ),
            delete_url = self.urls[ 'delete' ],
            deleteBtnData = {
                title       : _l( 'Delete' ),
                href        : delete_url,
                id          : id,
                icon_class  : 'delete',
                on_click    : function() {
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
        this.deleteButton = new IconButtonView({ model : new IconButton( deleteBtnData ) });
        return this.deleteButton.render().$el;
    },

    // ......................................................................... render body
    /** Render the data/metadata summary (format, size, misc info, etc.).
     *      Overrides _render_hdaSummary to include edit link in dbkey.
     *  @see HDABaseView#_render_hdaSummary
     *  @returns {jQuery} rendered DOM
     */
    _render_hdaSummary : function(){
        var modelData = _.extend( this.model.toJSON(), { urls: this.urls } );
        // if there's no dbkey and it's editable : pass a flag to the template to render a link to editing in the '?'
        if( this.model.get( 'metadata_dbkey' ) === '?'
        &&  !this.model.isDeletedOrPurged() ){
            _.extend( modelData, { dbkey_unknown_and_editable : true });
        }
        return hdaBase.HDABaseView.templates.hdaSummary( modelData );
    },

    // ......................................................................... primary actions
    /** Render icon-button to report an error on this hda to the galaxy admin.
     *  @returns {jQuery} rendered DOM
     */
    _render_errButton : function(){
        if( this.model.get( 'state' ) !== hdaModel.HistoryDatasetAssociation.STATES.ERROR ){
            this.errButton = null;
            return null;
        }
        
        this.errButton = new IconButtonView({ model : new IconButton({
            title       : _l( 'View or report this error' ),
            href        : this.urls.report_error,
            target      : 'galaxy_main',
            icon_class  : 'bug'
        })});
        return this.errButton.render().$el;
    },
    
    /** Render icon-button to re-run the job that created this hda.
     *  @returns {jQuery} rendered DOM
     */
    _render_rerunButton : function(){
        this.rerunButton = new IconButtonView({ model : new IconButton({
            title       : _l( 'Run this job again' ),
            href        : this.urls.rerun,
            target      : 'galaxy_main',
            icon_class  : 'arrow-circle'
        }) });
        return this.rerunButton.render().$el;
    },
    
    /** Render an icon-button or popupmenu based on the number of applicable visualizations
     *      and map button/popup clicks to viz setup functions.
     *  @returns {jQuery} rendered DOM
     */
    _render_visualizationsButton : function(){
        var visualizations = this.model.get( 'visualizations' );
        if( ( !this.model.hasData() )
        ||  ( _.isEmpty( visualizations ) ) ){
            this.visualizationsButton = null;
            return null;
        }

        //TODO: this is a bridge to allow the framework to be switched off
        // remove this fn and use the other when fully integrated
        if( _.isObject( visualizations[0] ) ){
            return this._render_visualizationsFrameworkButton( visualizations );
        }

        if( !this.urls.visualization ){
            this.visualizationsButton = null;
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
        this.visualizationsButton = new IconButtonView({ model : new IconButton({
            title       : _l( 'Visualize' ),
            href        : this.urls.visualization,
            icon_class  : 'chart_curve'
        })});
        var $icon = this.visualizationsButton.render().$el;
        $icon.addClass( 'visualize-icon' ); // needed?

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
            this.visualizationsButton = null;
            return null;
        }

        // render the icon from template
        this.visualizationsButton = new IconButtonView({ model : new IconButton({
            title       : _l( 'Visualize' ),
            icon_class  : 'chart_curve'
        })});
        var $icon = this.visualizationsButton.render().$el;
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
    /** Render secondary actions: currently tagging and annotation (if user is allowed).
     *  @param {Array} buttonRenderingFuncs array of rendering functions appending the results in order
     *  @returns {jQuery} rendered DOM
     */
    _render_secondaryActionButtons : function( buttonRenderingFuncs ){
        // move to the right (same level as primary)
        var secondaryActionButtons = $( '<div/>' ),
            view = this;
        secondaryActionButtons
            .attr( 'style', 'float: right;' )
            .attr( 'id', 'secondary-actions-' + this.model.get( 'id' ) );
            
        _.each( buttonRenderingFuncs, function( fn ){
            secondaryActionButtons.append( fn.call( view ) );
        });
        return secondaryActionButtons;
    },

    /** Render icon-button to load and display tagging html.
     *  @returns {jQuery} rendered DOM
     */
    _render_tagButton : function(){
        if( !this.hasUser || !this.urls.tags.get ){
            this.tagButton = null;
            return null;
        }
        
        this.tagButton = new IconButtonView({ model : new IconButton({
            title       : _l( 'Edit dataset tags' ),
            target      : 'galaxy_main',
            href        : this.urls.tags.get,
            icon_class  : 'tags'
        })});
        return this.tagButton.render().$el;
    },

    /** Render icon-button to load and display annotation html.
     *  @returns {jQuery} rendered DOM
     */
    _render_annotateButton : function(){
        if( !this.hasUser || !this.urls.annotation.get ){
            this.annotateButton = null;
            return null;
        }

        this.annotateButton = new IconButtonView({ model : new IconButton({
            title       : _l( 'Edit dataset annotation' ),
            target      : 'galaxy_main',
            icon_class  : 'annotate'
        })});
        return this.annotateButton.render().$el;
    },
    
    // ......................................................................... state body renderers
    /** Render an HDA whose job has failed.
     *      Overrides _render_body_error to prepend error report button to primary actions strip.
     *  @param {jQuery} parent DOM to which to append this body
     *  @see HDABaseView#_render_body_error
     */
    _render_body_error : function( parent ){
        hdaBase.HDABaseView.prototype._render_body_error.call( this, parent );
        var primaryActions = parent.find( '#primary-actions-' + this.model.get( 'id' ) );
        primaryActions.prepend( this._render_errButton() );
    },
        
    /** Render an HDA that's done running and where everything worked.
     *      Overrides _render_body_ok to add tag/annotation functionality and additional primary actions
     *  @param {jQuery} parent DOM to which to append this body
     *  @see HDABaseView#_render_body_ok
     */
    _render_body_ok : function( parent ){
        // most common state renderer and the most complicated
        parent.append( this._render_hdaSummary() );

        // return shortened form if del'd
        //TODO: is this correct? maybe only on purged
        if( this.model.isDeletedOrPurged() ){
            parent.append( this._render_primaryActionButtons([
                this._render_downloadButton,
                this._render_showParamsButton,
                this._render_rerunButton
            ]));
            return;
        }
        
        //NOTE: change the order here
        parent.append( this._render_primaryActionButtons([
            this._render_downloadButton,
            this._render_showParamsButton,
            this._render_rerunButton,
            this._render_visualizationsButton
        ]));
        parent.append( this._render_secondaryActionButtons([
            this._render_tagButton,
            this._render_annotateButton
        ]));
        parent.append( '<div class="clear"/>' );
        
        parent.append( this._render_tagArea() );
        parent.append( this._render_annotationArea() );
        
        parent.append( this._render_displayAppArea() );
        this._render_displayApps( parent );
        parent.append( this._render_peek() );
    },

    // ......................................................................... events
    /** event map */
    events : {
        'click .historyItemTitle'           : 'toggleBodyVisibility',
        'click .historyItemUndelete'        : function( ev ){ this.model.undelete(); return false; },
        'click .historyItemUnhide'          : function( ev ){ this.model.unhide();   return false; },
        'click .historyItemPurge'           : 'confirmPurge',

        'click a.icon-button.tags'          : 'loadAndDisplayTags',
        'click a.icon-button.annotate'      : 'loadAndDisplayAnnotation'
    },
    
    /** listener for item purge */
    confirmPurge : function _confirmPurge( ev ){
//TODO: confirm dialog
        this.model.purge({ url: this.urls.purge });
        return false;
    },

    // ......................................................................... tags
    /** Render area to display tags.
     *  @returns {jQuery} rendered DOM
     */
//TODO: into sub-MV
    _render_tagArea : function(){
        if( !this.hasUser || !this.urls.tags.set ){ return null; }
        return $( HDAEditView.templates.tagArea(
            _.extend( this.model.toJSON(), { urls: this.urls } )
        ).trim() );
    },

    /** Find the tag area and, if initial: load the html (via ajax) for displaying them; otherwise, unhide/hide
     */
//TODO: into sub-MV
    loadAndDisplayTags : function( event ){
        //BUG: broken with latest
        //TODO: this is a drop in from history.mako - should use MV as well
        this.log( this + '.loadAndDisplayTags', event );
        var view = this,
            tagArea = this.$el.find( '.tag-area' ),
            tagElt = tagArea.find( '.tag-elt' );

        // Show or hide tag area; if showing tag area and it's empty, fill it.
        if( tagArea.is( ":hidden" ) ){
            if( !jQuery.trim( tagElt.html() ) ){
                // Need to fill tag element.
                $.ajax({
                    //TODO: the html from this breaks a couple of times
                    url: this.urls.tags.get,
                    error: function( xhr, status, error ){
                        view.log( "Tagging failed", xhr, status, error );
                        view.trigger( 'error', view, xhr, {}, _l( "Tagging failed" ) );
                    },
                    success: function(tag_elt_html) {
                        tagElt.html(tag_elt_html);
                        tagElt.find("[title]").tooltip();
                        tagArea.slideDown( view.fxSpeed );
                    }
                });
            } else {
                // Tag element is filled; show.
                tagArea.slideDown( view.fxSpeed );
            }
        } else {
            // Hide.
            tagArea.slideUp( view.fxSpeed );
        }
        return false;
    },

    // ......................................................................... annotations
    /** Render area to display annotation.
     *  @returns {jQuery} rendered DOM
     */
//TODO: into sub-MV
    _render_annotationArea : function(){
        if( !this.hasUser || !this.urls.annotation.get ){ return null; }
        return $( HDAEditView.templates.annotationArea(
            _.extend( this.model.toJSON(), { urls: this.urls } )
        ).trim() );
    },
    
    /** Find the annotation area and, if initial: load the html (via ajax) for displaying them; otherwise, unhide/hide
     */
    loadAndDisplayAnnotation : function( event ){
//TODO: this is a drop in from history.mako - should use MV as well
        this.log( this + '.loadAndDisplayAnnotation', event );
        var view = this,
            annotationArea = this.$el.find( '.annotation-area' ),
            annotationElem = annotationArea.find( '.annotation-elt' ),
            setAnnotationUrl = this.urls.annotation.set;

        // Show or hide annotation area; if showing annotation area and it's empty, fill it.
        if ( annotationArea.is( ":hidden" ) ){
            if( !jQuery.trim( annotationElem.html() ) ){
                // Need to fill annotation element.
                $.ajax({
                    url: this.urls.annotation.get,
                    error: function(){
                        view.log( "Annotation failed", xhr, status, error );
                        view.trigger( 'error', view, xhr, {}, _l( "Annotation failed" ) );
                    },
                    success: function( htmlFromAjax ){
                        if( htmlFromAjax === "" ){
                            htmlFromAjax = "<em>" + _l( "Describe or add notes to dataset" ) + "</em>";
                        }
                        annotationElem.html( htmlFromAjax );
                        annotationArea.find("[title]").tooltip();
                        
                        async_save_text(
                            annotationElem.attr("id"), annotationElem.attr("id"),
                            setAnnotationUrl,
                            "new_annotation", 18, true, 4
                        );
                        annotationArea.slideDown( view.fxSpeed );
                    }
                });
            } else {
                annotationArea.slideDown( view.fxSpeed );
            }
            
        } else {
            // Hide.
            annotationArea.slideUp( view.fxSpeed );
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

//------------------------------------------------------------------------------
HDAEditView.templates = {
    tagArea             : Handlebars.templates[ 'template-hda-tagArea' ],
    annotationArea      : Handlebars.templates[ 'template-hda-annotationArea' ]
};

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
