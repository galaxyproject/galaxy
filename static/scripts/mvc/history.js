//define([
//    "../mvc/base-mvc"
//    
//], function(){
/* =============================================================================
Backbone.js implementation of history panel

TODO:
    currently, adding a dataset (via tool execute, etc.) creates a new dataset and refreshes the page

    meta:
        require.js
        convert function comments to jsDoc style, complete comments
        move inline styles into base.less
        watch the magic strings
        watch your globals
    
    all:
        add classes, ids on empty divs
        incorporate relations?
        events (local/ui and otherwise)
        have info bodies prev. opened, redisplay on refresh
        transfer history.mako js:
            updater, etc.
            create viz icon
                trackster
                scatterplot
                phylo-viz
            on ready:
                delete function
                check_transfer_status (running->ok)
            quota meter update
        
    historyItemView:
        poly HistoryItemView (and HistoryView?) on: for_editing, display_structured, trans.user
        don't draw body until it's first unhide event
        HIview state transitions (eg. upload -> ok), curr: build new, delete old, place new (in render)
        move visualizations menu
            include phyloviz
    
    History:
        renaming broken
        tags rendering broken (url?)
        annotation (url?)
        meta controls : collapse all, rename, annotate, etc.
        
    collection:
        show_deleted, show_hidden (thru js - no refresh)

    
============================================================================= */
//TODO: use initialize (or validate) to check purged AND deleted -> purged XOR deleted
var HistoryItem = BaseModel.extend( LoggableMixin ).extend({
    // a single HDA model
    
    // uncomment this out see log messages
    //logger              : console,
    
    defaults : {
        
        id                  : null, 
        name                : '', 
        data_type           : null, 
        file_size           : 0, 
        genome_build        : null, 
        metadata_data_lines : 0, 
        metadata_dbkey      : null, 
        metadata_sequences  : 0, 
        misc_blurb          : '', 
        misc_info           : '', 
        model_class         : '', 
        state               : '',
        deleted             : false, 
        purged              : false,
        
        // clash with BaseModel here?
        visible             : true,
        
        for_editing         : true,
        // additional urls will be passed and added, if permissions allow their use
        
        bodyIsShown         : false
    },
    
    initialize : function(){
        this.log( this + '.initialize', this.attributes );
        this.log( '\tparent history_id: ' + this.get( 'history_id' ) );
        
        //TODO: accessible is set in alt_hist
        // this state is not in trans.app.model.Dataset.states - set it here
        if( !this.get( 'accessible' ) ){
            this.set( 'state', HistoryItem.STATES.NOT_VIEWABLE );
        }
    },

    isEditable : function(){
        // roughly can_edit from history_common.mako - not deleted or purged = editable
        return (
            //this.get( 'for_editing' )
            //&& !( this.get( 'deleted' ) || this.get( 'purged' ) )
            !( this.get( 'deleted' ) || this.get( 'purged' ) )
        );
    },
    
    hasData : function(){
        //TODO:?? is this equivalent to all possible hda.has_data calls?
        return ( this.get( 'file_size' ) > 0 );
    },

    toString : function(){
        var nameAndId = this.get( 'id' ) || '';
        if( this.get( 'name' ) ){
            nameAndId += ':"' + this.get( 'name' ) + '"';
        }
        return 'HistoryItem(' + nameAndId + ')';
    }
});

//------------------------------------------------------------------------------
HistoryItem.STATES = {
    NOT_VIEWABLE        : 'not_viewable',   // not in trans.app.model.Dataset.states
    NEW                 : 'new',
    UPLOAD              : 'upload',
    QUEUED              : 'queued',
    RUNNING             : 'running',
    OK                  : 'ok',
    EMPTY               : 'empty',
    ERROR               : 'error',
    DISCARDED           : 'discarded',
    SETTING_METADATA    : 'setting_metadata',
    FAILED_METADATA     : 'failed_metadata'
};


//==============================================================================
var HistoryItemView = BaseView.extend( LoggableMixin ).extend({
    //??TODO: add alias in initialize this.hda = this.model?
    // view for HistoryItem model above

    // uncomment this out see log messages
    //logger              : console,

    tagName     : "div",
    className   : "historyItemContainer",
    
    // ................................................................................ SET UP
    initialize  : function( attributes ){
        this.log( this + '.initialize:', this, this.model );
        this.visible = attributes.visible;
    },
   
    // ................................................................................ RENDER MAIN
    //??: this style builds an entire, new DOM tree - is that what we want??
    render : function(){
        var id = this.model.get( 'id' ),
            state = this.model.get( 'state' );
        this.clearReferences();
        
        this.$el.attr( 'id', 'historyItemContainer-' + id );
        
        var itemWrapper = $( '<div/>' ).attr( 'id', 'historyItem-' + id )
            .addClass( 'historyItemWrapper' ).addClass( 'historyItem' )
            .addClass( 'historyItem-' + state );
            
        itemWrapper.append( this._render_warnings() );
        itemWrapper.append( this._render_titleBar() );
        this.body = $( this._render_body() );
        itemWrapper.append( this.body );
        
        // set up canned behavior on children (bootstrap, popupmenus, editable_text, etc.)
        itemWrapper.find( '.tooltip' ).tooltip({ placement : 'bottom' });
        
        // we can potentially skip this step and call popupmenu directly on the download button
        make_popup_menus( itemWrapper );
        
        //TODO: better transition/method than this...
        this.$el.children().remove();
        return this.$el.append( itemWrapper );
    },
    
    clearReferences : function(){
        //??TODO: best way?
        //?? do we really need these - not so far
        this.displayButton = null;
        this.editButton = null;
        this.deleteButton = null;
        this.errButton = null;
    },
    
    // ................................................................................ RENDER WARNINGS
    _render_warnings : function(){
        // jQ errs on building dom with whitespace - if there are no messages, trim -> ''
        return $( jQuery.trim( HistoryItemView.templates.messages( this.model.toJSON() ) ) );
    },
    
    // ................................................................................ RENDER TITLEBAR
    _render_titleBar : function(){
        var titleBar = $( '<div class="historyItemTitleBar" style="overflow: hidden"></div>' );
        titleBar.append( this._render_titleButtons() );
        titleBar.append( '<span class="state-icon"></span>' );
        titleBar.append( this._render_titleLink() );
        return titleBar;
    },

    // ................................................................................ display, edit attr, delete
    _render_titleButtons : function(){
        // render the display, edit attr and delete icon-buttons
        var buttonDiv = $( '<div class="historyItemButtons"></div>' );
        buttonDiv.append( this._render_displayButton() );
        buttonDiv.append( this._render_editButton() );
        buttonDiv.append( this._render_deleteButton() );
        return buttonDiv;
    },
    
    //TODO: ?? the three title buttons render for err'd datasets: is this normal?
    _render_displayButton : function(){
        // don't show display while uploading
        if( this.model.get( 'state' ) === HistoryItem.STATES.UPLOAD ){ return null; }
        
        // show a disabled display if the data's been purged
        displayBtnData = ( this.model.get( 'purged' ) )?({
            title       : 'Cannot display datasets removed from disk',
            enabled     : false,
            icon_class  : 'display'
            
        // if not, render the display icon-button with href 
        }):({
            title       : 'Display data in browser',
            href        : this.model.get( 'display_url' ),
            target      : ( this.model.get( 'for_editing' ) )?( 'galaxy_main' ):( null ),
            icon_class  : 'display'
        });
        this.displayButton = new IconButtonView({ model : new IconButton( displayBtnData ) });
        return this.displayButton.render().$el;
    },
    
    _render_editButton : function(){
        // don't show edit while uploading, or if editable
        if( ( this.model.get( 'state' ) === HistoryItem.STATES.UPLOAD )
        ||  ( !this.model.get( 'for_editing' ) ) ){
            return null;
        }
        
        var purged = this.model.get( 'purged' ),
            deleted = this.model.get( 'deleted' ),
            editBtnData = {
                title       : 'Edit attributes',
                href        : this.model.get( 'edit_url' ),
                target      : 'galaxy_main',
                icon_class  : 'edit'
            };
            
        // disable if purged or deleted and explain why in the tooltip
        //TODO: if for_editing
        if( deleted || purged ){
            editBtnData.enabled = false;
        }
        if( deleted ){
            editBtnData.title = 'Undelete dataset to edit attributes';
        } else if( purged ){
            editBtnData.title = 'Cannot edit attributes of datasets removed from disk';
        }
        
        this.editButton = new IconButtonView({ model : new IconButton( editBtnData ) });
        return this.editButton.render().$el;
    },
    
    _render_deleteButton : function(){
        // don't show delete if not editable
        if( !this.model.get( 'for_editing' ) ){ return null; }
        
        var deleteBtnData = {
            title       : 'Delete',
            href        : this.model.get( 'delete_url' ),
            id          : 'historyItemDeleter-' + this.model.get( 'id' ),
            icon_class  : 'delete'
        };
        if( ( this.model.get( 'deleted' ) || this.model.get( 'purged' ) )
        && ( !this.model.get( 'delete_url' ) ) ){
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
    _render_titleLink : function(){
        return $( jQuery.trim( HistoryItemView.templates.titleLink( this.model.toJSON() ) ) );
    },

    // ................................................................................ RENDER BODY
    _render_hdaSummary : function(){
        var modelData = this.model.toJSON();
        // if there's no dbkey and it's editable : pass a flag to the template to render a link to editing in the '?'
        if( this.model.get( 'metadata_dbkey' ) === '?'
        &&  this.model.isEditable() ){
            _.extend( modelData, { dbkey_unknown_and_editable : true });
        }
        return HistoryItemView.templates.hdaSummary( modelData );
    },

    // ................................................................................ primary actions
    _render_primaryActionButtons : function( buttonRenderingFuncs ){
        var primaryActionButtons = $( '<div/>' ).attr( 'id', 'primary-actions-' + this.model.get( 'id' ) ),
            view = this;
        _.each( buttonRenderingFuncs, function( fn ){
            primaryActionButtons.append( fn.call( view ) );
        });
        return primaryActionButtons;
    },
    
    _render_downloadButton : function(){
        // don't show anything if the data's been purged
        if( this.model.get( 'purged' ) ){ return null; }
        
        // return either: a single download icon-button (if there are no meta files)
        //  or a popupmenu with links to download assoc. meta files (if there are meta files)
        var downloadLinkHTML = HistoryItemView.templates.downloadLinks( this.model.toJSON() );
        //this.log( this + '_render_downloadButton, downloadLinkHTML:', downloadLinkHTML );
        return $( downloadLinkHTML );
    },
    
    //NOTE: button renderers have the side effect of caching their IconButtonViews to this view
    _render_errButton : function(){    
        if( ( this.model.get( 'state' ) !== HistoryItem.STATES.ERROR )
        ||  ( !this.model.get( 'for_editing' ) ) ){ return null; }
        
        this.errButton = new IconButtonView({ model : new IconButton({
            title       : 'View or report this error',
            href        : this.model.get( 'report_error_url' ),
            target      : 'galaxy_main',
            icon_class  : 'bug'
        })});
        return this.errButton.render().$el;
    },
    
    _render_showParamsButton : function(){
        // gen. safe to show in all cases
        this.showParamsButton = new IconButtonView({ model : new IconButton({
            title       : 'View details',
            href        : this.model.get( 'show_params_url' ),
            target      : 'galaxy_main',
            icon_class  : 'information'
        }) });
        return this.showParamsButton.render().$el;
    },
    
    _render_rerunButton : function(){
        if( !this.model.get( 'for_editing' ) ){ return null; }
        this.rerunButton = new IconButtonView({ model : new IconButton({
            title       : 'Run this job again',
            href        : this.model.get( 'rerun_url' ),
            target      : 'galaxy_main',
            icon_class  : 'arrow-circle'
        }) });
        return this.rerunButton.render().$el;
    },
    
    _render_tracksterButton : function(){
        var trackster_urls = this.model.get( 'trackster_urls' );
        if( !( this.model.hasData() )
        ||  !( this.model.get( 'for_editing' ) )
        ||  !( trackster_urls ) ){ return null; }
        
        this.tracksterButton = new IconButtonView({ model : new IconButton({
            title       : 'View in Trackster',
            icon_class  : 'chart_curve'
        })});
        this.errButton.render(); //?? needed?
        this.errButton.$el.addClass( 'trackster-add' ).attr({
            'data-url'  : trackster_urls[ 'data-url' ],
            'action-url': trackster_urls[ 'action-url' ],
            'new-url'   : trackster_urls[ 'new-url' ]
        });
        return this.errButton.$el;
    },
    
    // ................................................................................ secondary actions
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

    _render_tagButton : function(){
        if( !( this.model.hasData() )
        ||  !( this.model.get( 'for_editing' ) )
        ||   ( !this.model.get( 'retag_url' ) ) ){ return null; }
        
        this.tagButton = new IconButtonView({ model : new IconButton({
            title       : 'Edit dataset tags',
            target      : 'galaxy_main',
            href        : this.model.get( 'retag_url' ),
            icon_class  : 'tags'
        })});
        return this.tagButton.render().$el;
    },

    _render_annotateButton : function(){
        if( !( this.model.hasData() )
        ||  !( this.model.get( 'for_editing' ) )
        ||   ( !this.model.get( 'annotate_url' ) ) ){ return null; }

        this.annotateButton = new IconButtonView({ model : new IconButton({
            title       : 'Edit dataset annotation',
            target      : 'galaxy_main',
            href        : this.model.get( 'annotate_url' ),
            icon_class  : 'annotate'
        })});
        return this.annotateButton.render().$el;
    },
    
    // ................................................................................ other elements
    _render_tagArea : function(){
        if( !this.model.get( 'retag_url' ) ){ return null; }
        //TODO: move to mvc/tags.js
        return $( HistoryItemView.templates.tagArea( this.model.toJSON() ) );
    },
    
    _render_annotationArea : function(){
        if( !this.model.get( 'annotate_url' ) ){ return null; }
        //TODO: move to mvc/annotations.js
        return $( HistoryItemView.templates.annotationArea( this.model.toJSON() ) );
    },
    
    _render_displayApps : function(){
        // render links to external genome display applications (igb, gbrowse, etc.)
        if( !this.model.hasData() ){ return null; }
        
        var displayAppsDiv = $( '<div/>' ).addClass( 'display-apps' );
        if( !_.isEmpty( this.model.get( 'display_types' ) ) ){
            //this.log( this + 'display_types:', this.model.get( 'display_types' ) );
            //TODO:?? does this ever get used?
            displayAppsDiv.append(
                HistoryItemView.templates.displayApps({ displayApps : this.model.toJSON().display_types })
            );
        }
        if( !_.isEmpty( this.model.get( 'display_apps' ) ) ){
            //this.log( this + 'display_apps:',  this.model.get( 'display_apps' ) );
            displayAppsDiv.append(
                HistoryItemView.templates.displayApps({ displayApps : this.model.toJSON().display_apps })
            );
        }
        return displayAppsDiv;
    },
            
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
        parent.append( $( HistoryItemView.templates.failedMetadata( this.model.toJSON() ) ) );
        //...then render the remaining body as STATES.OK (only diff between these states is the box above)
        this._render_body_ok( parent );
    },
        
    _render_body_ok : function( parent ){
        // most common state renderer and the most complicated
        parent.append( this._render_hdaSummary() );
        
        parent.append( this._render_primaryActionButtons([
            this._render_downloadButton,
            this._render_errButton,
            this._render_showParamsButton,
            this._render_rerunButton
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
    },
    
    _render_body : function(){
        //this.log( this + '_render_body' );
        var state = this.model.get( 'state' );
        //this.log( 'state:', state, 'for_editing', for_editing );
        
        //TODO: incorrect id (encoded - use hid?)
        var body = $( '<div/>' )
            .attr( 'id', 'info-' + this.model.get( 'id' ) )
            .addClass( 'historyItemBody' )
            .attr(  'style', 'display: block' );
        
        //TODO: not a fan of this
        switch( state ){
            case HistoryItem.STATES.NOT_VIEWABLE :
                this._render_body_not_viewable( body ); 
				break;
            case HistoryItem.STATES.UPLOAD :
				this._render_body_uploading( body ); 
				break;
            case HistoryItem.STATES.QUEUED :
				this._render_body_queued( body ); 
				break;
            case HistoryItem.STATES.RUNNING :
				this._render_body_running( body ); 
				break;
            case HistoryItem.STATES.ERROR :
				this._render_body_error( body ); 
				break;
            case HistoryItem.STATES.DISCARDED :
				this._render_body_discarded( body ); 
				break;
            case HistoryItem.STATES.SETTING_METADATA :
				this._render_body_setting_metadata( body ); 
				break;
            case HistoryItem.STATES.EMPTY :
				this._render_body_empty( body ); 
				break;
            case HistoryItem.STATES.FAILED_METADATA :
				this._render_body_failed_metadata( body ); 
				break;
            case HistoryItem.STATES.OK :
				this._render_body_ok( body ); 
				break;
            default:
                //??: no body?
                body.append( $( '<div>Error: unknown dataset state "' + state + '".</div>' ) );
        }
            
        body.append( '<div style="clear: both"></div>' );
        if( this.model.get( 'bodyIsShown' ) === false ){
            body.hide();
        }
        if( this.visible ){
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
                    url: this.model.get( 'ajax_get_tag_url' ),
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
    
    loadAndDisplayAnnotation : function( event ){
        //BUG: broken with latest
        //TODO: this is a drop in from history.mako - should use MV as well
        this.log( this + '.loadAndDisplayAnnotation', event );
        var annotationArea = this.$el.find( '.annotation-area' ),
            annotationElem = annotationArea.find( '.annotation-elt' ),
            setAnnotationUrl = this.model.get( 'ajax_set_annotation_url' );

        // Show or hide annotation area; if showing annotation area and it's empty, fill it.
        if ( annotationArea.is( ":hidden" ) ){
            if( !jQuery.trim( annotationElem.html() ) ){
                // Need to fill annotation element.
                $.ajax({
                    url: this.model.get( 'ajax_get_annotation_url' ),
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

    toggleBodyVisibility : function( visible ){
        var $body = this.$el.find( '.historyItemBody' );
        $body.toggle();
        this.trigger( 'toggleBodyVisibility', this.model.get( 'id' ), $body.is( ':visible' ) );
    },

    // ................................................................................ UTILTIY
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'HistoryItemView(' + modelString + ')';    
    }
});


//------------------------------------------------------------------------------
//HistoryItemView.templates = InDomTemplateLoader.getTemplates({
HistoryItemView.templates = {
    warningMsg      : Handlebars.templates[ 'template-warningmessagesmall' ],

    messages        : Handlebars.templates[ 'template-history-warning-messages' ],
    titleLink       : Handlebars.templates[ 'template-history-titleLink' ],
    hdaSummary      : Handlebars.templates[ 'template-history-hdaSummary' ],
    downloadLinks   : Handlebars.templates[ 'template-history-downloadLinks' ],
    failedMetadata  : Handlebars.templates[ 'template-history-failedMetaData' ],
    tagArea         : Handlebars.templates[ 'template-history-tagArea' ],
    annotationArea  : Handlebars.templates[ 'template-history-annotationArea' ],
    displayApps     : Handlebars.templates[ 'template-history-displayApps' ]
};

//==============================================================================
var HistoryCollection = Backbone.Collection.extend({
    model           : HistoryItem,
    
    toString        : function(){
         return ( 'HistoryCollection()' );
    }
});


//==============================================================================
var History = BaseModel.extend( LoggableMixin ).extend({
    //TODO: bind change events from items and collection to this (itemLengths, states)
    
    // uncomment this out see log messages
    //logger              : console,

    // values from api (may need more)
    defaults : {
        id              : '', 
        name            : '', 
        state           : '',
        //TODO:?? change these to a list of encoded ids?
        state_details   : {
            discarded       : 0, 
            empty           : 0, 
            error           : 0, 
            failed_metadata : 0, 
            ok              : 0, 
            queued          : 0, 
            running         : 0, 
            setting_metadata: 0, 
            upload          : 0
        },
        
        // maybe security issues...
        userIsAdmin     : false,
        userRoles       : [],
        //TODO: hardcoded
        
        //TODO: wire this to items
        itemsLength     : 0,
        showDeleted     : false,
        showHidden      : false,
        
        diskSize : 0,
        deleted : false,
        
        //  tagging_common.mako: render_individual_tagging_element(user=trans.get_user(),
        //      tagged_item=history, elt_context="history.mako", use_toggle_link=False, input_size="20")
        tags        : [],
        annotation  : null,
        message     : null,
        quotaMsg    : false,
        
        baseURL         : null,
        hideDeletedURL  : null,
        hideHiddenURL   : null,
        tagURL          : null,
        annotateURL     : null
    },
    
    initialize : function( data, history_datasets ){
        //this.log( this + '.initialize', data, history_datasets );
        this.items = new HistoryCollection();
    },

    toJSON : function(){
        // unfortunately, bb doesn't call 'get' to form the JSON meaning computed vals from get aren't used, so...
        // a simple example of override and super call
        var json = Backbone.Model.prototype.toJSON.call( this );
        json.itemsLength = this.items.length;
        //this.log( this + '.json:', json );
        return json;
    },
    
    loadDatasetsAsHistoryItems : function( datasets ){
        //TODO: add via ajax - multiple datasets at once
        // adds the given dataset/Item data to historyItems
        //  and updates this.state based on their states
        //pre: datasets is a list of objs
        //this.log( this + '.loadDatasets', datasets );
        var self = this,
            selfID = this.get( 'id' ),
            stateDetails = this.get( 'state_details' );
            
        _.each( datasets, function( dataset, index ){
            //self.log( 'loading dataset: ', dataset, index );
            
            // create an item sending along the history_id as well
            var historyItem = new HistoryItem(
                _.extend( dataset, { history_id: selfID } ) );
            //self.log( 'as History:', historyItem );
            self.items.add( historyItem );
   
            // add item's state to running totals in stateDetails
            var itemState = dataset.state;
            stateDetails[ itemState ] += 1;
        });
        
        // get overall History state from totals
        this.set( 'state_details', stateDetails );
        this._stateFromStateDetails();
        return this;
    },
    
    _stateFromStateDetails : function(){
        // sets this.state based on current historyItems' states
        //  ported from api/histories.traverse
        //pre: state_details is current counts of dataset/item states
        this.set( 'state', '' );
        var stateDetails = this.get( 'state_details' );
        
        //TODO: make this more concise
        if( ( stateDetails.error > 0  )
        ||  ( stateDetails.failed_metadata > 0  ) ){
            this.set( 'state', HistoryItem.STATES.ERROR );
            
        } else if( ( stateDetails.running > 0  )
        ||         ( stateDetails.setting_metadata > 0  ) ){
            this.set( 'state', HistoryItem.STATES.RUNNING );
            
        } else if( stateDetails.queued > 0  ){
            this.set( 'state', HistoryItem.STATES.QUEUED );

        } else if( stateDetails.ok === this.items.length ){
            this.set( 'state', HistoryItem.STATES.OK );

        } else {
            throw( '_stateFromStateDetails: unable to determine '
                 + 'history state from state details: ' + this.state_details );
        }
        return this;
    },
    
    toString : function(){
        var nameString = ( this.get( 'name' ) )?
            ( ',' + this.get( 'name' ) ) : ( '' ); 
        return 'History(' + this.get( 'id' ) + nameString + ')';
    }
});

//------------------------------------------------------------------------------
// view for the HistoryCollection (as per current right hand panel)
//var HistoryView = BaseView.extend( LoggableMixin ).extend( UsesStorageMixin ) .extend({
var HistoryView = BaseView.extend( LoggableMixin ).extend({
    
    // uncomment this out see log messages
    //logger              : console,

    // direct attachment to existing element
    el                  : 'body.historyPage',
    //TODO: add id?

    initialize : function(){
        this.log( this + '.initialize:', this );
        // data that needs to be persistant over page refreshes
        this.storage = new PersistantStorage(
            'HistoryView.' + this.model.get( 'id' ),
            { visibleItems : {} }
        );
        // set up the individual history items/datasets
        this.initializeItems();
    },

    initializeItems : function(){
        this.itemViews = {};
        var historyPanel = this;
        this.model.items.each( function( item ){
            var itemId = item.get( 'id' ),
                itemView = new HistoryItemView({
                    model: item, visible:
                    historyPanel.storage.get( 'visibleItems' ).get( itemId )
                });
            historyPanel.setUpItemListeners( itemView );
            historyPanel.itemViews[ itemId ] = itemView;
        });
    },

    setUpItemListeners : function( itemView ){
        var HistoryPanel = this;
        // use storage to maintain a list of items whose bodies are visible
        itemView.bind( 'toggleBodyVisibility', function( id, visible ){
            if( visible ){
                HistoryPanel.storage.get( 'visibleItems' ).set( id, true );
            } else {
                HistoryPanel.storage.get( 'visibleItems' ).deleteKey( id );
            }
        });
    },
    
    render : function(){
        this.$el.append( HistoryView.templates.historyPanel( this.model.toJSON() ) );
        this.log( this + ' rendered from template:', this.$el );
        
        // set up aliases
        this.itemsDiv = this.$el.find( '#' + this.model.get( 'id' ) + '-datasets' );
        
        //TODO: set up widgets, tooltips, etc.
        
        if( this.model.items.length ){
            // render to temp, move all at once, remove temp holder
            var tempDiv = this._render_items();
            this.itemsDiv.append( tempDiv.children() );
            tempDiv.remove();
        }
    },

    _render_items : function(){
        var div = $( '<div/>' ),
            view = this;
        //NOTE!: render in reverse (newest on top) via prepend (instead of append)
        _.each( this.itemViews, function( itemView, viewId ){
            view.log( view + '.render_items:', viewId, itemView );
            div.prepend( itemView.render() );
        });
        return div;
    },
    
    toString    : function(){
        var nameString = this.model.get( 'name' ) || '';
        return 'HistoryView(' + nameString + ')';
    }
});
HistoryView.templates = {
    historyPanel : Handlebars.templates[ 'template-history-historyPanel' ]
};



//==============================================================================
//return {
//    HistoryItem     : HistoryItem,
//    HitoryItemView  : HistoryItemView,
//    HistoryCollection : HistoryCollection,
//    History         : History,
//    HistoryView     : HistoryView
//};});
