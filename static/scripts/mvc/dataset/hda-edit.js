//define([
//    "../mvc/base-mvc"
//], function(){
//==============================================================================
/** View for editing (working with - as opposed to viewing/read-only) an hda
 *
 */
var HDAView = BaseView.extend( LoggableMixin ).extend({
    //??TODO: add alias in initialize this.hda = this.model?
    // view for HistoryDatasetAssociation model above

    // uncomment this out see log messages
    //logger              : console,

    tagName     : "div",
    className   : "historyItemContainer",
    
    // ................................................................................ SET UP
    initialize  : function( attributes ){
        this.log( this + '.initialize:', attributes );

        // render urlTemplates (gen. provided by GalaxyPaths) to urls
        if( !attributes.urlTemplates ){ throw( 'HDAView needs urlTemplates on initialize' ); }
        this.urls = this.renderUrls( attributes.urlTemplates, this.model.toJSON() );

        // whether the body of this hda is expanded (shown)
        this.expanded = attributes.expanded || false;

        // re-render the entire view on any model change
        this.model.bind( 'change', this.render, this );
        //this.bind( 'all', function( event ){
        //    this.log( event );
        //}, this );
    },
   
    // urlTemplates is a map (or nested map) of underscore templates (currently, anyhoo)
    //  use the templates to create the apropo urls for each action this ds could use
    renderUrls : function( urlTemplates, modelJson ){
        var hdaView = this,
            urls = {};
        _.each( urlTemplates, function( urlTemplateOrObj, urlKey ){
            // object == nested templates: recurse
            if( _.isObject( urlTemplateOrObj ) ){
                urls[ urlKey ] = hdaView.renderUrls( urlTemplateOrObj, modelJson );

            // string == template:
            } else {
                // meta_down load is a special case (see renderMetaDownloadUrls)
                //TODO: should be a better (gen.) way to handle this case
                if( urlKey === 'meta_download' ){
                    urls[ urlKey ] = hdaView.renderMetaDownloadUrls( urlTemplateOrObj, modelJson );
                } else {
                    urls[ urlKey ] = _.template( urlTemplateOrObj, modelJson );
                }
            }
        });
        return urls;
    },

    // there can be more than one meta_file to download, so return a list of url and file_type for each
    renderMetaDownloadUrls : function( urlTemplate, modelJson ){
        return _.map( modelJson.meta_files, function( meta_file ){
            return {
                url         : _.template( urlTemplate, { id: modelJson.id, file_type: meta_file.file_type }),
                file_type   : meta_file.file_type
            };
        });
    },

    // ................................................................................ RENDER MAIN
    render : function(){
        var view = this,
            id = this.model.get( 'id' ),
            state = this.model.get( 'state' ),
            itemWrapper = $( '<div/>' ).attr( 'id', 'historyItem-' + id ),
            initialRender = ( this.$el.children().size() === 0 );

        //console.debug( this + '.render, initial?:', initialRender );

        this._clearReferences();
        this.$el.attr( 'id', 'historyItemContainer-' + id );
        
        itemWrapper
            .addClass( 'historyItemWrapper' ).addClass( 'historyItem' )
            .addClass( 'historyItem-' + state );
            
        itemWrapper.append( this._render_warnings() );
        itemWrapper.append( this._render_titleBar() );
        this.body = $( this._render_body() );
        itemWrapper.append( this.body );
        
        //TODO: move to own function: setUpBehaviours
        // we can potentially skip this step and call popupmenu directly on the download button
        make_popup_menus( itemWrapper );

        // set up canned behavior on children (bootstrap, popupmenus, editable_text, etc.)
        itemWrapper.find( '.tooltip' ).tooltip({ placement : 'bottom' });
        
        // transition...
        this.$el.fadeOut( 'fast', function(){
            view.$el.children().remove();
            view.$el.append( itemWrapper ).fadeIn( 'fast', function(){
                view.log( view + ' rendered:', view.$el );
                var renderedEventName = 'rendered';
                
                if( initialRender ){
                    renderedEventName += ':initial';
                } else if( view.model.inReadyState() ){
                    renderedEventName += ':ready';
                }
                view.trigger( renderedEventName );
            });
        });
        return this;
    },
    
    //NOTE: button renderers have the side effect of caching their IconButtonViews to this view
    // clear out cached sub-views, dom refs, etc. from prev. render
    _clearReferences : function(){
        //??TODO: we should reset these in the button logic checks (i.e. if not needed this.button = null; return null)
        //?? do we really need these - not so far
        //TODO: at least move these to a map
        this.displayButton = null;
        this.editButton = null;
        this.deleteButton = null;
        this.errButton = null;
        this.showParamsButton = null;
        this.rerunButton = null;
        this.visualizationsButton = null;
        this.tagButton = null;
        this.annotateButton = null;
    },
    
    // ................................................................................ RENDER WARNINGS
    // hda warnings including: is deleted, is purged, is hidden (including links to further actions (undelete, etc.))
    _render_warnings : function(){
        // jQ errs on building dom with whitespace - if there are no messages, trim -> ''
        return $( jQuery.trim( HDAView.templates.messages(
            _.extend( this.model.toJSON(), { urls: this.urls } )
        )));
    },
    
    // ................................................................................ RENDER TITLEBAR
    // the part of an hda always shown (whether the body is expanded or not): title link, title buttons
    _render_titleBar : function(){
        var titleBar = $( '<div class="historyItemTitleBar" style="overflow: hidden"></div>' );
        titleBar.append( this._render_titleButtons() );
        titleBar.append( '<span class="state-icon"></span>' );
        titleBar.append( this._render_titleLink() );
        return titleBar;
    },

    // ................................................................................ display, edit attr, delete
    // icon-button group for the common, most easily accessed actions
    //NOTE: these are generally displayed for almost every hda state (tho poss. disabled)
    _render_titleButtons : function(){
        // render the display, edit attr and delete icon-buttons
        var buttonDiv = $( '<div class="historyItemButtons"></div>' );
        buttonDiv.append( this._render_displayButton() );
        buttonDiv.append( this._render_editButton() );
        buttonDiv.append( this._render_deleteButton() );
        return buttonDiv;
    },
    
    // icon-button to display this hda in the galaxy main iframe
    _render_displayButton : function(){
        // don't show display if not in ready state, error'd, or not accessible
        if( ( !this.model.inReadyState() )
        ||  ( this.model.get( 'state' ) === HistoryDatasetAssociation.STATES.ERROR )
        ||  ( this.model.get( 'state' ) === HistoryDatasetAssociation.STATES.NOT_VIEWABLE )
        ||  ( !this.model.get( 'accessible' ) ) ){
            return null;
        }
        
        var displayBtnData = {
            icon_class  : 'display'
        };

        // show a disabled display if the data's been purged
        if( this.model.get( 'purged' ) ){
            displayBtnData.enabled = false;
            displayBtnData.title = 'Cannot display datasets removed from disk';
            
        } else {
            displayBtnData.title = 'Display data in browser';
            displayBtnData.href  = this.urls.display;
        }
        
        if( this.model.get( 'for_editing' ) ){
            displayBtnData.target = 'galaxy_main';
        }

        this.displayButton = new IconButtonView({ model : new IconButton( displayBtnData ) });
        return this.displayButton.render().$el;
    },
    
    // icon-button to edit the attributes (format, permissions, etc.) this hda
    _render_editButton : function(){
        // don't show edit while uploading, or if editable
        if( ( this.model.get( 'state' ) === HistoryDatasetAssociation.STATES.UPLOAD )
        ||  ( this.model.get( 'state' ) === HistoryDatasetAssociation.STATES.ERROR )
        ||  ( this.model.get( 'state' ) === HistoryDatasetAssociation.STATES.NOT_VIEWABLE )
        ||  ( !this.model.get( 'accessible' ) )
        ||  ( !this.model.get( 'for_editing' ) ) ){
            return null;
        }
        
        var purged = this.model.get( 'purged' ),
            deleted = this.model.get( 'deleted' ),
            editBtnData = {
                title       : 'Edit attributes',
                href        : this.urls.edit,
                target      : 'galaxy_main',
                icon_class  : 'edit'
            };
            
        // disable if purged or deleted and explain why in the tooltip
        //TODO: if for_editing
        if( deleted || purged ){
            editBtnData.enabled = false;
            if( purged ){
                editBtnData.title = 'Cannot edit attributes of datasets removed from disk';
            } else if( deleted ){
                editBtnData.title = 'Undelete dataset to edit attributes';
            }
        }
        
        this.editButton = new IconButtonView({ model : new IconButton( editBtnData ) });
        return this.editButton.render().$el;
    },
    
    // icon-button to delete this hda
    _render_deleteButton : function(){
        // don't show delete if...
        if( ( !this.model.get( 'for_editing' ) )
        ||  ( this.model.get( 'state' ) === HistoryDatasetAssociation.STATES.NOT_VIEWABLE )
        ||  ( !this.model.get( 'accessible' ) ) ){
            return null;
        }
        
        var deleteBtnData = {
            title       : 'Delete',
            href        : this.urls[ 'delete' ],
            id          : 'historyItemDeleter-' + this.model.get( 'id' ),
            icon_class  : 'delete'
        };
        if( this.model.get( 'deleted' ) || this.model.get( 'purged' ) ){
            deleteBtnData = {
                title       : 'Dataset is already deleted',
                icon_class  : 'delete',
                enabled     : false
            };
        }
        this.deleteButton = new IconButtonView({ model : new IconButton( deleteBtnData ) });
        return this.deleteButton.render().$el;
    },
    
    // ................................................................................ titleLink
    // render the hid and hda.name as a link (that will expand the body)
    _render_titleLink : function(){
        return $( jQuery.trim( HDAView.templates.titleLink(
            _.extend( this.model.toJSON(), { urls: this.urls } )
        )));
    },

    // ................................................................................ RENDER BODY
    // render the data/metadata summary (format, size, misc info, etc.)
    _render_hdaSummary : function(){
        var modelData = _.extend( this.model.toJSON(), { urls: this.urls } );
        // if there's no dbkey and it's editable : pass a flag to the template to render a link to editing in the '?'
        if( this.model.get( 'metadata_dbkey' ) === '?'
        &&  !this.model.isDeletedOrPurged() ){
            _.extend( modelData, { dbkey_unknown_and_editable : true });
        }
        return HDAView.templates.hdaSummary( modelData );
    },

    // ................................................................................ primary actions
    // render the icon-buttons gen. placed underneath the hda summary
    _render_primaryActionButtons : function( buttonRenderingFuncs ){
        var primaryActionButtons = $( '<div/>' ).attr( 'id', 'primary-actions-' + this.model.get( 'id' ) ),
            view = this;
        _.each( buttonRenderingFuncs, function( fn ){
            primaryActionButtons.append( fn.call( view ) );
        });
        return primaryActionButtons;
    },
    
    // icon-button/popupmenu to down the data (and/or the associated meta files (bai, etc.)) for this hda
    _render_downloadButton : function(){
        // don't show anything if the data's been purged
        if( this.model.get( 'purged' ) ){ return null; }
        
        // return either: a single download icon-button (if there are no meta files)
        //  or a popupmenu with links to download assoc. meta files (if there are meta files)
        var downloadLinkHTML = HDAView.templates.downloadLinks(
            _.extend( this.model.toJSON(), { urls: this.urls } )
        );
        //this.log( this + '_render_downloadButton, downloadLinkHTML:', downloadLinkHTML );
        return $( downloadLinkHTML );
    },
    
    // icon-button to show the input and output (stdout/err) for the job that created this hda
    _render_errButton : function(){    
        if( ( this.model.get( 'state' ) !== HistoryDatasetAssociation.STATES.ERROR )
        ||  ( !this.model.get( 'for_editing' ) ) ){ return null; }
        
        this.errButton = new IconButtonView({ model : new IconButton({
            title       : 'View or report this error',
            href        : this.urls.report_error,
            target      : 'galaxy_main',
            icon_class  : 'bug'
        })});
        return this.errButton.render().$el;
    },
    
    // icon-button to show the input and output (stdout/err) for the job that created this hda
    _render_showParamsButton : function(){
        // gen. safe to show in all cases
        this.showParamsButton = new IconButtonView({ model : new IconButton({
            title       : 'View details',
            href        : this.urls.show_params,
            target      : 'galaxy_main',
            icon_class  : 'information'
        }) });
        return this.showParamsButton.render().$el;
    },
    
    // icon-button to re run the job that created this hda
    _render_rerunButton : function(){
        if( !this.model.get( 'for_editing' ) ){ return null; }
        this.rerunButton = new IconButtonView({ model : new IconButton({
            title       : 'Run this job again',
            href        : this.urls.rerun,
            target      : 'galaxy_main',
            icon_class  : 'arrow-circle'
        }) });
        return this.rerunButton.render().$el;
    },
    
    // build an icon-button or popupmenu based on the number of applicable visualizations
    //  also map button/popup clicks to viz setup functions
    _render_visualizationsButton : function(){
        var dbkey = this.model.get( 'dbkey' ),
            visualizations = this.model.get( 'visualizations' ),
            visualization_url = this.urls.visualization,
            popup_menu_dict = {},
            params = {
                dataset_id: this.model.get( 'id' ),
                hda_ldda: 'hda'
            };

        if( !( this.model.hasData() )
        ||  !( this.model.get( 'for_editing' ) )
        ||  !( visualizations && visualizations.length )
        ||  !( visualization_url ) ){
            //console.warn( 'NOT rendering visualization icon' )
            return null;
        }
        
        // render the icon from template
        this.visualizationsButton = new IconButtonView({ model : new IconButton({
            title       : 'Visualize',
            href        : visualization_url,
            icon_class  : 'chart_curve'
        })});
        var $icon = this.visualizationsButton.render().$el;
        $icon.addClass( 'visualize-icon' ); // needed?

        //TODO: make this more concise
        // map a function to each visualization in the icon's attributes
        //  create a popupmenu from that map
        // Add dbkey to params if it exists.
        if( dbkey ){ params.dbkey = dbkey; }

        function create_viz_action( visualization ) {
            switch( visualization ){
                case 'trackster':
                    return create_trackster_action_fn( visualization_url, params, dbkey );
                case 'scatterplot':
                    return create_scatterplot_action_fn( visualization_url, params );
                default:
                    return function(){
                        window.parent.location = visualization_url + '/' + visualization + '?' + $.param( params ); };
            }
        }

        // No need for popup menu because there's a single visualization.
        if ( visualizations.length === 1 ) {
            $icon.attr( 'title', visualizations[0] );
            $icon.click( create_viz_action( visualizations[0] ) );

        // >1: Populate menu dict with visualization fns, make the popupmenu
        } else {
            _.each( visualizations, function( visualization ) {
                //TODO: move to utils
                var titleCaseVisualization = visualization.charAt( 0 ).toUpperCase() + visualization.slice( 1 );
                popup_menu_dict[ titleCaseVisualization ] = create_viz_action( visualization );
            });
            make_popupmenu( $icon, popup_menu_dict );
        }
        return $icon;
    },
    
    // ................................................................................ secondary actions
    // secondary actions: currently tagging and annotation (if user is allowed)
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

    // icon-button to load and display tagging html
    //TODO: these should be a sub-MV
    _render_tagButton : function(){
        if( !( this.model.hasData() )
        ||  !( this.model.get( 'for_editing' ) )
        ||   ( !this.urls.tags.get ) ){ return null; }
        
        this.tagButton = new IconButtonView({ model : new IconButton({
            title       : 'Edit dataset tags',
            target      : 'galaxy_main',
            href        : this.urls.tags.get,
            icon_class  : 'tags'
        })});
        return this.tagButton.render().$el;
    },

    // icon-button to load and display annotation html
    //TODO: these should be a sub-MV
    _render_annotateButton : function(){
        if( !( this.model.hasData() )
        ||  !( this.model.get( 'for_editing' ) )
        ||   ( !this.urls.annotation.get ) ){ return null; }

        this.annotateButton = new IconButtonView({ model : new IconButton({
            title       : 'Edit dataset annotation',
            target      : 'galaxy_main',
            icon_class  : 'annotate'
        })});
        return this.annotateButton.render().$el;
    },
    
    // ................................................................................ other elements
    // render links to external genome display applications (igb, gbrowse, etc.)
    //TODO: not a fan of the style on these
    _render_displayApps : function(){
        if( !this.model.hasData() ){ return null; }
        
        var displayAppsDiv = $( '<div/>' ).addClass( 'display-apps' );
        if( !_.isEmpty( this.model.get( 'display_types' ) ) ){
            //this.log( this + 'display_types:', this.model.get( 'urls' ).display_types );
            //TODO:?? does this ever get used?
            displayAppsDiv.append(
                HDAView.templates.displayApps({ displayApps : this.model.get( 'display_types' ) })
            );
        }
        if( !_.isEmpty( this.model.get( 'display_apps' ) ) ){
            //this.log( this + 'display_apps:',  this.model.get( 'urls' ).display_apps );
            displayAppsDiv.append(
                HDAView.templates.displayApps({ displayApps : this.model.get( 'display_apps' ) })
            );
        }
        return displayAppsDiv;
    },
            
    //TODO: into sub-MV
    // render the area used to load tag display
    _render_tagArea : function(){
        if( !this.urls.tags.set ){ return null; }
        //TODO: move to mvc/tags.js
        return $( HDAView.templates.tagArea(
            _.extend( this.model.toJSON(), { urls: this.urls } )
        ));
    },

    //TODO: into sub-MV
    // render the area used to load annotation display
    _render_annotationArea : function(){
        if( !this.urls.annotation.get ){ return null; }
        //TODO: move to mvc/annotations.js
        return $( HDAView.templates.annotationArea(
            _.extend( this.model.toJSON(), { urls: this.urls } )
        ));
    },

    // render the data peek
    //TODO: curr. pre-formatted into table on the server side - may not be ideal/flexible
    _render_peek : function(){
        if( !this.model.get( 'peek' ) ){ return null; }
        return $( '<div/>' ).append(
            $( '<pre/>' )
                .attr( 'id', 'peek' + this.model.get( 'id' ) )
                .addClass( 'peek' )
                .append( this.model.get( 'peek' ) )
        );
    },
    
    // ................................................................................ state body renderers
    // _render_body fns for the various states
    //TODO: only render these on expansion (or already expanded)
    _render_body_not_viewable : function( parent ){
        //TODO: revisit - still showing display, edit, delete (as common) - that CAN'T be right
        parent.append( $( '<div>You do not have permission to view dataset.</div>' ) );
    },
    
    _render_body_uploading : function( parent ){
        parent.append( $( '<div>Dataset is uploading</div>' ) );
    },
        
    _render_body_queued : function( parent ){
        parent.append( $( '<div>Job is waiting to run.</div>' ) );
        parent.append( this._render_primaryActionButtons([
            this._render_showParamsButton,
            this._render_rerunButton
        ]));
    },
        
    _render_body_running : function( parent ){
        parent.append( '<div>Job is currently running.</div>' );
        parent.append( this._render_primaryActionButtons([
            this._render_showParamsButton,
            this._render_rerunButton
        ]));
    },
        
    _render_body_error : function( parent ){
        if( !this.model.get( 'purged' ) ){
            parent.append( $( '<div>' + this.model.get( 'misc_blurb' ) + '</div>' ) );
        }
        parent.append( ( 'An error occurred running this job: '
                       + '<i>' + $.trim( this.model.get( 'misc_info' ) ) + '</i>' ) );
        parent.append( this._render_primaryActionButtons([
            this._render_downloadButton,
            this._render_errButton,
            this._render_showParamsButton,
            this._render_rerunButton
        ]));
    },
        
    _render_body_discarded : function( parent ){
        parent.append( '<div>The job creating this dataset was cancelled before completion.</div>' );
        parent.append( this._render_primaryActionButtons([
            this._render_showParamsButton,
            this._render_rerunButton
        ]));
    },
        
    _render_body_setting_metadata : function( parent ){
        parent.append( $( '<div>Metadata is being auto-detected.</div>' ) );
    },
    
    _render_body_empty : function( parent ){
        //TODO: replace i with dataset-misc-info class 
        //?? why are we showing the file size when we know it's zero??
        parent.append( $( '<div>No data: <i>' + this.model.get( 'misc_blurb' ) + '</i></div>' ) );
        parent.append( this._render_primaryActionButtons([
            this._render_showParamsButton,
            this._render_rerunButton
        ]));
    },
        
    _render_body_failed_metadata : function( parent ){
        //TODO: the css for this box is broken (unlike the others)
        // add a message box about the failure at the top of the body...
        parent.append( $( HDAView.templates.failedMetadata( this.model.toJSON() ) ) );
        //...then render the remaining body as STATES.OK (only diff between these states is the box above)
        this._render_body_ok( parent );
    },
        
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
            this._render_errButton,
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
        
        parent.append( this._render_displayApps() );
        parent.append( this._render_peek() );

        //TODO??: still needed?
        //// If Mozilla, hide scrollbars in hidden items since they cause animation bugs
        //if ( $.browser.mozilla ) {
        //    $( "div.historyItemBody" ).each( function() {
        //        if ( !$(this).is(":visible") ) { $(this).find( "pre.peek" ).css( "overflow", "hidden" ); }
        //    });
        //}
    },
    
    _render_body : function(){
        //this.log( this + '_render_body' );
        //this.log( 'state:', state, 'for_editing', for_editing );
        
        //TODO: incorrect id (encoded - use hid?)
        var body = $( '<div/>' )
            .attr( 'id', 'info-' + this.model.get( 'id' ) )
            .addClass( 'historyItemBody' )
            .attr(  'style', 'display: block' );
        
        //TODO: not a fan of this dispatch
        switch( this.model.get( 'state' ) ){
            case HistoryDatasetAssociation.STATES.NOT_VIEWABLE :
                this._render_body_not_viewable( body );
				break;
            case HistoryDatasetAssociation.STATES.UPLOAD :
				this._render_body_uploading( body );
				break;
            case HistoryDatasetAssociation.STATES.QUEUED :
				this._render_body_queued( body );
				break;
            case HistoryDatasetAssociation.STATES.RUNNING :
				this._render_body_running( body ); 
				break;
            case HistoryDatasetAssociation.STATES.ERROR :
				this._render_body_error( body );
				break;
            case HistoryDatasetAssociation.STATES.DISCARDED :
				this._render_body_discarded( body );
				break;
            case HistoryDatasetAssociation.STATES.SETTING_METADATA :
				this._render_body_setting_metadata( body );
				break;
            case HistoryDatasetAssociation.STATES.EMPTY :
				this._render_body_empty( body );
				break;
            case HistoryDatasetAssociation.STATES.FAILED_METADATA :
				this._render_body_failed_metadata( body );
				break;
            case HistoryDatasetAssociation.STATES.OK :
				this._render_body_ok( body );
				break;
            default:
                //??: no body?
                body.append( $( '<div>Error: unknown dataset state "' + state + '".</div>' ) );
        }
        body.append( '<div style="clear: both"></div>' );
            
        if( this.expanded ){
            body.show();
        } else {
            body.hide();
        }
        return body;
    },

    // ................................................................................ EVENTS
    events : {
        'click .historyItemTitle'           : 'toggleBodyVisibility',
        'click a.icon-button.tags'          : 'loadAndDisplayTags',
        'click a.icon-button.annotate'      : 'loadAndDisplayAnnotation'
    },
    
    // ................................................................................ STATE CHANGES / MANIPULATION
    // find the tag area and, if initial: (via ajax) load the html for displaying them; otherwise, unhide/hide
    //TODO: into sub-MV
    loadAndDisplayTags : function( event ){
        //BUG: broken with latest
        //TODO: this is a drop in from history.mako - should use MV as well
        this.log( this + '.loadAndDisplayTags', event );
        var tagArea = this.$el.find( '.tag-area' ),
            tagElt = tagArea.find( '.tag-elt' );

        // Show or hide tag area; if showing tag area and it's empty, fill it.
        if( tagArea.is( ":hidden" ) ){
            if( !jQuery.trim( tagElt.html() ) ){
                // Need to fill tag element.
                $.ajax({
                    //TODO: the html from this breaks a couple of times
                    url: this.urls.tags.get,
                    error: function() { alert( "Tagging failed" ); },
                    success: function(tag_elt_html) {
                        tagElt.html(tag_elt_html);
                        tagElt.find(".tooltip").tooltip();
                        tagArea.slideDown("fast");
                    }
                });
            } else {
                // Tag element is filled; show.
                tagArea.slideDown("fast");
            }
        } else {
            // Hide.
            tagArea.slideUp("fast");
        }
        return false;        
    },
    
    // find the annotation area and, if initial: (via ajax) load the html for displaying it; otherwise, unhide/hide
    //TODO: into sub-MV
    loadAndDisplayAnnotation : function( event ){
        //TODO: this is a drop in from history.mako - should use MV as well
        this.log( this + '.loadAndDisplayAnnotation', event );
        var annotationArea = this.$el.find( '.annotation-area' ),
            annotationElem = annotationArea.find( '.annotation-elt' ),
            setAnnotationUrl = this.urls.annotation.set;

        // Show or hide annotation area; if showing annotation area and it's empty, fill it.
        if ( annotationArea.is( ":hidden" ) ){
            if( !jQuery.trim( annotationElem.html() ) ){
                // Need to fill annotation element.
                $.ajax({
                    url: this.urls.annotation.get,
                    error: function(){ alert( "Annotations failed" ); },
                    success: function( htmlFromAjax ){
                        if( htmlFromAjax === "" ){
                            htmlFromAjax = "<em>Describe or add notes to dataset</em>";
                        }
                        annotationElem.html( htmlFromAjax );
                        annotationArea.find(".tooltip").tooltip();
                        
                        async_save_text(
                            annotationElem.attr("id"), annotationElem.attr("id"),
                            setAnnotationUrl,
                            "new_annotation", 18, true, 4
                        );
                        annotationArea.slideDown("fast");
                    }
                });
            } else {
                annotationArea.slideDown("fast");
            }
            
        } else {
            // Hide.
            annotationArea.slideUp("fast");
        }
        return false;        
    },

    // expand/collapse body
    //side effect: trigger event
    toggleBodyVisibility : function( event, expanded ){
        var $body = this.$el.find( '.historyItemBody' );
        expanded = ( expanded === undefined )?( !$body.is( ':visible' ) ):( expanded );
        //this.log( 'toggleBodyVisibility, expanded:', expanded, '$body:', $body );

        if( expanded ){
            $body.slideDown( 'fast' );
        } else {
            $body.slideUp( 'fast' );
        }
        this.trigger( 'toggleBodyVisibility', this.model.get( 'id' ), expanded );
    },

    // ................................................................................ UTILTIY
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'HDAView(' + modelString + ')';
    }
});

//------------------------------------------------------------------------------
HDAView.templates = {
    warningMsg          : Handlebars.templates[ 'template-warningmessagesmall' ],

    messages            : Handlebars.templates[ 'template-history-warning-messages' ],
    titleLink           : Handlebars.templates[ 'template-history-titleLink' ],
    hdaSummary          : Handlebars.templates[ 'template-history-hdaSummary' ],
    downloadLinks       : Handlebars.templates[ 'template-history-downloadLinks' ],
    failedMetadata      : Handlebars.templates[ 'template-history-failedMetaData' ],
    tagArea             : Handlebars.templates[ 'template-history-tagArea' ],
    annotationArea      : Handlebars.templates[ 'template-history-annotationArea' ],
    displayApps         : Handlebars.templates[ 'template-history-displayApps' ]
};

//==============================================================================
//TODO: these belong somewhere else

//TODO: should be imported from scatterplot.js
//TODO: OR abstracted to 'load this in the galaxy_main frame'
function create_scatterplot_action_fn( url, params ){
    action = function() {
        var galaxy_main = $( window.parent.document ).find( 'iframe#galaxy_main' ),
            final_url = url + '/scatterplot?' + $.param(params);
        galaxy_main.attr( 'src', final_url );
        //TODO: this needs to go away
        $( 'div.popmenu-wrapper' ).remove();
        return false;
    };
    return action;
}

// -----------------------------------------------------------------------------
// Create trackster action function.
//TODO: should be imported from trackster.js
function create_trackster_action_fn(vis_url, dataset_params, dbkey) {
    return function() {
        var params = {};
        if (dbkey) { params.dbkey = dbkey; }
        $.ajax({
            url: vis_url + '/list_tracks?f-' + $.param(params),
            dataType: "html",
            error: function() { alert( "Could not add this dataset to browser." ); },
            success: function(table_html) {
                var parent = window.parent;

                parent.show_modal("View Data in a New or Saved Visualization", "", {
                    "Cancel": function() {
                        parent.hide_modal();
                    },
                    "View in saved visualization": function() {
                        // Show new modal with saved visualizations.
                        parent.show_modal("Add Data to Saved Visualization", table_html, {
                            "Cancel": function() {
                                parent.hide_modal();
                            },
                            "Add to visualization": function() {
                                $(parent.document).find('input[name=id]:checked').each(function() {
                                    var vis_id = $(this).val();
                                    dataset_params.id = vis_id;
                                    parent.location = vis_url + "/trackster?" + $.param(dataset_params);
                                });
                            }
                        });
                    },
                    "View in new visualization": function() {
                        parent.location = vis_url + "/trackster?" + $.param(dataset_params);
                    }
                });
            }
        });
        return false;
    };
}

//==============================================================================
//return {
//    HDAView  : HDAView,
//};});
