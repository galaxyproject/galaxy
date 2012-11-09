//define([
//    "../mvc/base-mvc"
//], function(){
//==============================================================================
/** read only view for HistoryDatasetAssociations
 *
 */
var HDABaseView = BaseView.extend( LoggableMixin ).extend({
    //??TODO: add alias in initialize this.hda = this.model?
    // view for HistoryDatasetAssociation model above

    // uncomment this out see log messages
    //logger              : console,

    tagName     : "div",
    className   : "historyItemContainer",

    // ................................................................................ SET UP
    initialize  : function( attributes ){
        this.log( this + '.initialize:', attributes );

        // which buttons go in most states (ok/failed meta are more complicated)
        this.defaultPrimaryActionButtonRenderers = [
            this._render_showParamsButton
        ];
        
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
    // events: rendered, rendered:ready, rendered:initial, rendered:ready:initial
    render : function(){
        var view = this,
            id = this.model.get( 'id' ),
            state = this.model.get( 'state' ),
            itemWrapper = $( '<div/>' ).attr( 'id', 'historyItem-' + id ),
            initialRender = ( this.$el.children().size() === 0 );

        //console.debug( this + '.render, initial?:', initialRender );
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
    
    // ................................................................................ RENDER WARNINGS
    // hda warnings including: is deleted, is purged, is hidden (including links to further actions (undelete, etc.))
    _render_warnings : function(){
        // jQ errs on building dom with whitespace - if there are no messages, trim -> ''
        return $( jQuery.trim( HDABaseView.templates.messages( this.model.toJSON() )));
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
        return buttonDiv;
    },
    
    // icon-button to display this hda in the galaxy main iframe
    _render_displayButton : function(){
        // don't show display if not in ready state, error'd, or not accessible
        if( ( !this.model.inReadyState() )
        ||  ( this.model.get( 'state' ) === HistoryDatasetAssociation.STATES.ERROR )
        ||  ( this.model.get( 'state' ) === HistoryDatasetAssociation.STATES.NOT_VIEWABLE )
        ||  ( !this.model.get( 'accessible' ) ) ){
            this.displayButton = null;
            return null;
        }
        
        var displayBtnData = {
            icon_class  : 'display',
            target      : 'galaxy_main'
        };

        // show a disabled display if the data's been purged
        if( this.model.get( 'purged' ) ){
            displayBtnData.enabled = false;
            displayBtnData.title = _l( 'Cannot display datasets removed from disk' );
            
        } else {
            displayBtnData.title = _l( 'Display data in browser' );
            displayBtnData.href  = this.urls.display;
        }

        this.displayButton = new IconButtonView({ model : new IconButton( displayBtnData ) });
        return this.displayButton.render().$el;
    },
    
    // ................................................................................ titleLink
    // render the hid and hda.name as a link (that will expand the body)
    _render_titleLink : function(){
        return $( jQuery.trim( HDABaseView.templates.titleLink(
            _.extend( this.model.toJSON(), { urls: this.urls } )
        )));
    },

    // ................................................................................ RENDER BODY
    // render the data/metadata summary (format, size, misc info, etc.)
    _render_hdaSummary : function(){
        var modelData = _.extend( this.model.toJSON(), { urls: this.urls } );
        return HDABaseView.templates.hdaSummary( modelData );
    },

    // ................................................................................ primary actions
    // render the icon-buttons gen. placed underneath the hda summary
    _render_primaryActionButtons : function( buttonRenderingFuncs ){
        var view = this,
            primaryActionButtons = $( '<div/>' ).attr( 'id', 'primary-actions-' + this.model.get( 'id' ) );
        _.each( buttonRenderingFuncs, function( fn ){
            primaryActionButtons.append( fn.call( view ) );
        });
        return primaryActionButtons;
    },
    
    // icon-button/popupmenu to down the data (and/or the associated meta files (bai, etc.)) for this hda
    _render_downloadButton : function(){
        // don't show anything if the data's been purged
        if( this.model.get( 'purged' ) || !this.model.hasData() ){ return null; }
        
        // return either: a single download icon-button (if there are no meta files)
        //  or a popupmenu with links to download assoc. meta files (if there are meta files)
        var downloadLinkHTML = HDABaseView.templates.downloadLinks(
            _.extend( this.model.toJSON(), { urls: this.urls } )
        );
        //this.log( this + '_render_downloadButton, downloadLinkHTML:', downloadLinkHTML );
        return $( downloadLinkHTML );
    },
    
    // icon-button to show the input and output (stdout/err) for the job that created this hda
    _render_showParamsButton : function(){
        // gen. safe to show in all cases
        this.showParamsButton = new IconButtonView({ model : new IconButton({
            title       : _l( 'View details' ),
            href        : this.urls.show_params,
            target      : 'galaxy_main',
            icon_class  : 'information'
        }) });
        return this.showParamsButton.render().$el;
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
                HDABaseView.templates.displayApps({ displayApps : this.model.get( 'display_types' ) })
            );
        }
        if( !_.isEmpty( this.model.get( 'display_apps' ) ) ){
            //this.log( this + 'display_apps:',  this.model.get( 'urls' ).display_apps );
            displayAppsDiv.append(
                HDABaseView.templates.displayApps({ displayApps : this.model.get( 'display_apps' ) })
            );
        }
        return displayAppsDiv;
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
        parent.append( $( '<div>' + _l( 'You do not have permission to view dataset' ) + '.</div>' ) );
    },
    
    _render_body_uploading : function( parent ){
        parent.append( $( '<div>' + _l( 'Dataset is uploading' ) + '</div>' ) );
    },
        
    _render_body_queued : function( parent ){
        parent.append( $( '<div>' + _l( 'Job is waiting to run' ) + '.</div>' ) );
        parent.append( this._render_primaryActionButtons( this.defaultPrimaryActionButtonRenderers ));
    },
        
    _render_body_running : function( parent ){
        parent.append( '<div>' + _l( 'Job is currently running' ) + '.</div>' );
        parent.append( this._render_primaryActionButtons( this.defaultPrimaryActionButtonRenderers ));
    },
        
    _render_body_error : function( parent ){
        if( !this.model.get( 'purged' ) ){
            parent.append( $( '<div>' + this.model.get( 'misc_blurb' ) + '</div>' ) );
        }
        parent.append( ( _l( 'An error occurred running this job' ) + ': '
                       + '<i>' + $.trim( this.model.get( 'misc_info' ) ) + '</i>' ) );
        parent.append( this._render_primaryActionButtons(
            this.defaultPrimaryActionButtonRenderers.concat([ this._render_downloadButton ])
        ));
    },
        
    _render_body_discarded : function( parent ){
        parent.append( '<div>' + _l( 'The job creating this dataset was cancelled before completion' ) + '.</div>' );
        parent.append( this._render_primaryActionButtons( this.defaultPrimaryActionButtonRenderers ));
    },
        
    _render_body_setting_metadata : function( parent ){
        parent.append( $( '<div>' + _l( 'Metadata is being auto-detected' ) + '.</div>' ) );
    },
    
    _render_body_empty : function( parent ){
        //TODO: replace i with dataset-misc-info class 
        //?? why are we showing the file size when we know it's zero??
        parent.append( $( '<div>' + _l( 'No data' ) + ': <i>' + this.model.get( 'misc_blurb' ) + '</i></div>' ) );
        parent.append( this._render_primaryActionButtons( this.defaultPrimaryActionButtonRenderers ));
    },
        
    _render_body_failed_metadata : function( parent ){
        //TODO: the css for this box is broken (unlike the others)
        // add a message box about the failure at the top of the body...
        parent.append( $( HDABaseView.templates.failedMetadata( this.model.toJSON() ) ) );
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
                this._render_showParamsButton
            ]));
            return;
        }
        
        //NOTE: change the order here
        parent.append( this._render_primaryActionButtons([
            this._render_downloadButton,
            this._render_showParamsButton
        ]));
        parent.append( '<div class="clear"/>' );
        
        parent.append( this._render_displayApps() );
        parent.append( this._render_peek() );
    },
    
    _render_body : function(){
        //this.log( this + '_render_body' );
        
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
        'click .historyItemTitle'           : 'toggleBodyVisibility'
    },

    // expand/collapse body
    // event: body-visible, body-hidden
    toggleBodyVisibility : function( event, expanded ){
        var hdaView = this,
            $body = this.$el.find( '.historyItemBody' );
        expanded = ( expanded === undefined )?( !$body.is( ':visible' ) ):( expanded );
        //this.log( 'toggleBodyVisibility, expanded:', expanded, '$body:', $body );

        if( expanded ){
            $body.slideDown( 'fast', function(){
                hdaView.trigger( 'body-visible', hdaView.model.get( 'id' ) );
            });
        } else {
            $body.slideUp( 'fast', function(){
                hdaView.trigger( 'body-hidden', hdaView.model.get( 'id' ) );
            });
        }
    },

    // ................................................................................ UTILTIY
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'HDABaseView(' + modelString + ')';
    }
});

//------------------------------------------------------------------------------
HDABaseView.templates = {
    warningMsg          : Handlebars.templates[ 'template-warningmessagesmall' ],

    messages            : Handlebars.templates[ 'template-hda-warning-messages' ],
    titleLink           : Handlebars.templates[ 'template-hda-titleLink' ],
    hdaSummary          : Handlebars.templates[ 'template-hda-hdaSummary' ],
    downloadLinks       : Handlebars.templates[ 'template-hda-downloadLinks' ],
    failedMetadata      : Handlebars.templates[ 'template-hda-failedMetaData' ],
    displayApps         : Handlebars.templates[ 'template-hda-displayApps' ]
};

//==============================================================================
//return {
//    HDABaseView  : HDABaseView,
//};});
