//define([
//    "../mvc/base-mvc"
//], function(){
//==============================================================================
/** @class Read only view for HistoryDatasetAssociation.
 *  @name HDABaseView
 * 
 *  @augments BaseView
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HDABaseView = BaseView.extend( LoggableMixin ).extend(
/** @lends HDABaseView.prototype */{

    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,

    tagName     : "div",
    className   : "historyItemContainer",

    // ......................................................................... SET UP
    /** Set up the view, cache url templates, bind listeners
     *  @param {Object} attributes
     *  @config {Object} urlTemplates nested object containing url templates for this view
     *  @throws 'needs urlTemplates' if urlTemplates isn't present
     *  @see Backbone.View#initialize
     */
    initialize  : function( attributes ){
        if( attributes.logger ){ this.logger = this.model.logger = attributes.logger; }
        this.log( this + '.initialize:', attributes );

        /** list of rendering functions for the default, primary icon-buttons. */
        this.defaultPrimaryActionButtonRenderers = [
            this._render_showParamsButton
        ];
        
        // cache urlTemplates (gen. provided by GalaxyPaths) to urls
        if( !attributes.urlTemplates ){ throw( 'HDAView needs urlTemplates on initialize' ); }
        this.urlTemplates = attributes.urlTemplates;

        /** is the body of this hda view expanded/not. */
        this.expanded = attributes.expanded || false;

        // re-render the entire view on any model change
        this.model.bind( 'change', this.render , this );

        //this.bind( 'all', function( event ){
        //    this.log( event );
        //}, this );
    },
   
    // ......................................................................... RENDER MAIN
    /** Render this HDA, set up ui.
     *  @fires rendered:ready when rendered and NO running HDAs
     *  @fires rendered when rendered and running HDAs
     *  @fires rendered:initial on first render with running HDAs
     *  @fires rendered:initial:ready when first rendered and NO running HDAs
     *  @returns {Object} this HDABaseView
     */
    render : function(){
        var view = this,
            id = this.model.get( 'id' ),
            state = this.model.get( 'state' ),
            itemWrapper = $( '<div/>' ).attr( 'id', 'historyItem-' + id ),
            initialRender = ( this.$el.children().size() === 0 );

        this.$el.attr( 'id', 'historyItemContainer-' + id );

        /** web controller urls for functions relating to this hda.
         *      These are rendered from urlTemplates using the model data. */
        this.urls = this._renderUrls( this.urlTemplates, this.model.toJSON() );

        itemWrapper
            .addClass( 'historyItemWrapper' ).addClass( 'historyItem' )
            .addClass( 'historyItem-' + state );

        itemWrapper.append( this._render_warnings() );
        itemWrapper.append( this._render_titleBar() );

        //NOTE: only sets behaviors on title and warnings - body will set up it's own
        this._setUpBehaviors( itemWrapper );

        this.body = $( this._render_body() );
        itemWrapper.append( this.body );

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

    /** render the urls for this hda using the model data and the url templates from initialize.
     *  @param {Object} urlTemplates a map (or nested map) of underscore templates (currently, anyhoo)
     *  @param {Object} modelJson data from the model
     *  @returns {Object} the templated urls
     */
    _renderUrls : function( urlTemplates, modelJson ){
        var hdaView = this,
            urls = {};
        _.each( urlTemplates, function( urlTemplateOrObj, urlKey ){
            // object == nested templates: recurse
            if( _.isObject( urlTemplateOrObj ) ){
                urls[ urlKey ] = hdaView._renderUrls( urlTemplateOrObj, modelJson );

            // string == template:
            } else {
                // meta_down load is a special case (see renderMetaDownloadUrls)
                //TODO: should be a better (gen.) way to handle this case
                if( urlKey === 'meta_download' ){
                    urls[ urlKey ] = hdaView._renderMetaDownloadUrls( urlTemplateOrObj, modelJson );

                } else {
                    try {
                        urls[ urlKey ] = _.template( urlTemplateOrObj, modelJson );
                    } catch( Error ){
                        throw( hdaView + '._renderUrls error: ' + Error +
                               '\n rendering:' + urlTemplateOrObj +
                               '\n with ' + JSON.stringify( modelJson ) );
                    }
                }
            }
        });
        return urls;
    },

    /** there can be more than one meta_file (e.g. bam index) to download,
     *      so return a list of url and file_type for each
     *  @param {Object} urlTemplate underscore templates for meta download urls
     *  @param {Object} modelJson data from the model
     *  @returns {Object} url and filetype for each meta file
     */
    _renderMetaDownloadUrls : function( urlTemplate, modelJson ){
        return _.map( modelJson.meta_files, function( meta_file ){
            return {
                url         : _.template( urlTemplate, { id: modelJson.id, file_type: meta_file.file_type }),
                file_type   : meta_file.file_type
            };
        });
    },

    /** set up js behaviors, event handlers for elements within the given container
     *  @param {jQuery} $container jq object that contains the elements to process (defaults to this.$el)
     */
    _setUpBehaviors : function( $container ){
        $container = $container || this.$el;
        // set up canned behavior on children (bootstrap, popupmenus, editable_text, etc.)
        //TODO: we can potentially skip this step and call popupmenu directly on the download button
        make_popup_menus( $container );
        $container.find( '.tooltip' ).tooltip({ placement : 'bottom' });
    },

    // ................................................................................ RENDER titlebar
    /** Render any hda warnings including: is deleted, is purged, is hidden.
     *      (including links to further actions (undelete, etc.))
     *  @returns {jQuery} rendered DOM
     */
    _render_warnings : function(){
        // jQ errs on building dom with whitespace - if there are no messages, trim -> ''
        return $( jQuery.trim( HDABaseView.templates.messages( this.model.toJSON() )));
    },
    
    /** Render the part of an hda always shown (whether the body is expanded or not): title link, title buttons.
     *  @returns {jQuery} rendered DOM
     */
    _render_titleBar : function(){
        var titleBar = $( '<div class="historyItemTitleBar" style="overflow: hidden"></div>' );
        titleBar.append( this._render_titleButtons() );
        titleBar.append( '<span class="state-icon"></span>' );
        titleBar.append( this._render_titleLink() );
        return titleBar;
    },

    /** Render icon-button group for the common, most easily accessed actions.
     *  @returns {jQuery} rendered DOM
     */
    _render_titleButtons : function(){
        // render the display, edit attr and delete icon-buttons
        var buttonDiv = $( '<div class="historyItemButtons"></div>' );
        buttonDiv.append( this._render_displayButton() );
        return buttonDiv;
    },
    
    /** Render icon-button to display this hda in the galaxy main iframe.
     *  @returns {jQuery} rendered DOM
     */
    _render_displayButton : function(){
        // don't show display if not viewable or not accessible
        // (do show if in error, running)
        if( ( this.model.get( 'state' ) === HistoryDatasetAssociation.STATES.NOT_VIEWABLE )
        ||  ( !this.model.get( 'accessible' ) ) ){
            this.displayButton = null;
            return null;
        }
        //NOTE: line 88 in history_common.mako should be handled by the url template generation
        
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
    
    /** Render the hid and hda.name as a link (that will expand the body).
     *  @returns {jQuery} rendered DOM
     */
    _render_titleLink : function(){
        return $( jQuery.trim( HDABaseView.templates.titleLink(
            //TODO?? does this need urls?
            _.extend( this.model.toJSON(), { urls: this.urls } )
        )));
    },

    // ......................................................................... RENDER BODY
    /** Render the data/metadata summary (format, size, misc info, etc.).
     *  @returns {jQuery} rendered DOM
     */
    _render_hdaSummary : function(){
        var modelData = _.extend( this.model.toJSON(), { urls: this.urls } );
        return HDABaseView.templates.hdaSummary( modelData );
    },

    // ......................................................................... primary actions
    /** Render the icon-buttons gen. placed underneath the hda summary (e.g. download, show params, etc.)
     *  @param {Array} buttonRenderingFuncs array of rendering functions appending the results in order
     *  @returns {jQuery} rendered DOM
     */
    _render_primaryActionButtons : function( buttonRenderingFuncs ){
        var view = this,
            primaryActionButtons = $( '<div/>' ).attr( 'id', 'primary-actions-' + this.model.get( 'id' ) );
        _.each( buttonRenderingFuncs, function( fn ){
            primaryActionButtons.append( fn.call( view ) );
        });
        return primaryActionButtons;
    },
    
    /** Render icon-button/popupmenu to download the data (and/or the associated meta files (bai, etc.)) for this hda.
     *  @returns {jQuery} rendered DOM
     */
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
    
    /** Render icon-button to show the input and output (stdout/err) for the job that created this hda.
     *  @returns {jQuery} rendered DOM
     */
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
    
    // ......................................................................... other elements
    /** Render links to external genome display applications (igb, gbrowse, etc.).
     *  @returns {jQuery} rendered DOM
     */
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
            
    /** Render the data peek.
     *  @returns {jQuery} rendered DOM
     */
    //TODO: curr. pre-formatted into table on the server side - may not be ideal/flexible
    _render_peek : function(){
        var peek = this.model.get( 'peek' );
        if( !peek ){ return null; }
        return $( '<div/>' ).append(
            $( '<pre/>' )
                .attr( 'id', 'peek' + this.model.get( 'id' ) )
                .addClass( 'peek' )
                .append( peek )
        );
    },
    
    // ......................................................................... state body renderers
    /** Render the enclosing div of the hda body and, if expanded, the html in the body
     *  @returns {jQuery} rendered DOM
     */
    //TODO: only render these on expansion (or already expanded)
    _render_body : function(){
        var body = $( '<div/>' )
            .attr( 'id', 'info-' + this.model.get( 'id' ) )
            .addClass( 'historyItemBody' )
            .attr( 'style', 'display: none' );

        if( this.expanded ){
            // only render the body html if it's being shown
            this._render_body_html( body );
            body.show();
        }
        return body;
    },

    /** Render the (expanded) body of an HDA, dispatching to other functions based on the HDA state
     *  @param {jQuery} body the body element to append the html to
     */
    //TODO: only render these on expansion (or already expanded)
    _render_body_html : function( body ){
        //this.log( this + '_render_body' );
        body.html( '' );
        //TODO: not a fan of this dispatch
        switch( this.model.get( 'state' ) ){
            case HistoryDatasetAssociation.STATES.NEW :
                break;
            case HistoryDatasetAssociation.STATES.NOT_VIEWABLE :
                this._render_body_not_viewable( body );
                break;
            case HistoryDatasetAssociation.STATES.UPLOAD :
                this._render_body_uploading( body );
                break;
            case HistoryDatasetAssociation.STATES.PAUSED:
                this._render_body_paused( body );
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
                body.append( $( '<div>Error: unknown dataset state "' + this.model.get( 'state' ) + '".</div>' ) );
        }
        body.append( '<div style="clear: both"></div>' );
        this._setUpBehaviors( body );
    },

    /** Render inaccessible, not-owned by curr user.
     *  @param {jQuery} parent DOM to which to append this body
     */
    _render_body_not_viewable : function( parent ){
        //TODO: revisit - still showing display, edit, delete (as common) - that CAN'T be right
        parent.append( $( '<div>' + _l( 'You do not have permission to view dataset' ) + '.</div>' ) );
    },
    
    /** Render an HDA still being uploaded.
     *  @param {jQuery} parent DOM to which to append this body
     */
    _render_body_uploading : function( parent ){
        parent.append( $( '<div>' + _l( 'Dataset is uploading' ) + '</div>' ) );
    },
        
    /** Render an HDA whose job is queued.
     *  @param {jQuery} parent DOM to which to append this body
     */
    _render_body_queued : function( parent ){
        parent.append( $( '<div>' + _l( 'Job is waiting to run' ) + '.</div>' ) );
        parent.append( this._render_primaryActionButtons( this.defaultPrimaryActionButtonRenderers ));
    },

    /** Render an HDA whose job is paused.
     *  @param {jQuery} parent DOM to which to append this body
     */
    _render_body_paused: function( parent ){
        parent.append( $( '<div>' + _l( 'Job is paused.  Use the history menu to resume' ) + '.</div>' ) );
        parent.append( this._render_primaryActionButtons( this.defaultPrimaryActionButtonRenderers ));
    },
        
    /** Render an HDA whose job is running.
     *  @param {jQuery} parent DOM to which to append this body
     */
    _render_body_running : function( parent ){
        parent.append( '<div>' + _l( 'Job is currently running' ) + '.</div>' );
        parent.append( this._render_primaryActionButtons( this.defaultPrimaryActionButtonRenderers ));
    },
        
    /** Render an HDA whose job has failed.
     *  @param {jQuery} parent DOM to which to append this body
     */
    _render_body_error : function( parent ){
        if( !this.model.get( 'purged' ) ){
            parent.append( $( '<div>' + this.model.get( 'misc_blurb' ) + '</div>' ) );
        }
        parent.append( ( _l( 'An error occurred with this dataset' ) + ': '
                       + '<i>' + $.trim( this.model.get( 'misc_info' ) ) + '</i>' ) );
        parent.append( this._render_primaryActionButtons(
            this.defaultPrimaryActionButtonRenderers.concat([ this._render_downloadButton ])
        ));
    },
        
    /** Render an HDA which was deleted during upload.
     *  @param {jQuery} parent DOM to which to append this body
     */
    _render_body_discarded : function( parent ){
        parent.append( '<div>' + _l( 'The job creating this dataset was cancelled before completion' ) + '.</div>' );
        parent.append( this._render_primaryActionButtons( this.defaultPrimaryActionButtonRenderers ));
    },
        
    /** Render an HDA where the metadata is still being determined.
     *  @param {jQuery} parent DOM to which to append this body
     */
    _render_body_setting_metadata : function( parent ){
        parent.append( $( '<div>' + _l( 'Metadata is being auto-detected' ) + '.</div>' ) );
    },
    
    /** Render an empty/no data HDA.
     *  @param {jQuery} parent DOM to which to append this body
     */
    _render_body_empty : function( parent ){
        //TODO: replace i with dataset-misc-info class 
        //?? why are we showing the file size when we know it's zero??
        parent.append( $( '<div>' + _l( 'No data' ) + ': <i>' + this.model.get( 'misc_blurb' ) + '</i></div>' ) );
        parent.append( this._render_primaryActionButtons( this.defaultPrimaryActionButtonRenderers ));
    },
        
    /** Render an HDA where the metadata wasn't produced correctly.
     *  @param {jQuery} parent DOM to which to append this body
     */
    _render_body_failed_metadata : function( parent ){
        //TODO: the css for this box is broken (unlike the others)
        // add a message box about the failure at the top of the body...
        parent.append( $( HDABaseView.templates.failedMetadata(
            _.extend( this.model.toJSON(), { urls: this.urls } )
        )));
        //...then render the remaining body as STATES.OK (only diff between these states is the box above)
        this._render_body_ok( parent );
    },
        
    /** Render an HDA that's done running and where everything worked.
     *  @param {jQuery} parent DOM to which to append this body
     */
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
    
    // ......................................................................... EVENTS
    /** event map */
    events : {
        'click .historyItemTitle'           : 'toggleBodyVisibility'
    },

    /** Render an HDA that's done running and where everything worked.
     *  @param {Event} event the event that triggered this (@link HDABaseView#events)
     *  @param {Boolean} expanded if true, expand; if false, collapse
     *  @fires body-expanded when a body has been expanded
     *  @fires body-collapsed when a body has been collapsed
     */
    toggleBodyVisibility : function( event, expanded ){
        var hdaView = this;
        this.expanded = ( expanded === undefined )?( !this.body.is( ':visible' ) ):( expanded );
        //this.log( 'toggleBodyVisibility, expanded:', expanded, '$body:', $body );

        if( this.expanded ){
            hdaView._render_body_html( hdaView.body );
            this.body.slideDown( 'fast', function(){
                hdaView.trigger( 'body-expanded', hdaView.model.get( 'id' ) );
            });
        } else {
            this.body.slideUp( 'fast', function(){
                hdaView.trigger( 'body-collapsed', hdaView.model.get( 'id' ) );
            });
        }
    },

    remove : function( callback ){
        var hdaView = this;
        this.$el.fadeOut( 'fast', function(){
            hdaView.$el.remove();
            if( callback ){ callback(); }
        });
    },

    // ......................................................................... MISC
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'HDABaseView(' + modelString + ')';
    }
});

//------------------------------------------------------------------------------ TEMPLATES
HDABaseView.templates = {
    warningMsg          : Handlebars.templates[ 'template-warningmessagesmall' ],

    messages            : Handlebars.templates[ 'template-hda-warning-messages' ],
    titleLink           : Handlebars.templates[ 'template-hda-titleLink' ],
    hdaSummary          : Handlebars.templates[ 'template-hda-hdaSummary' ],
    downloadLinks       : Handlebars.templates[ 'template-hda-downloadLinks' ],
    failedMetadata      : Handlebars.templates[ 'template-hda-failedMetadata' ],
    displayApps         : Handlebars.templates[ 'template-hda-displayApps' ]
};

//==============================================================================
//return {
//    HDABaseView  : HDABaseView,
//};});
