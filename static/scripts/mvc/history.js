/*
Backbone.js implementation of history panel

TODO:
    replicate then refactor (could be the wrong order)
    History meta controls (rename, annotate, etc. - see history.js.120823.bak)
    choose a templating system and use it consistently
    HIview state transitions (eg. upload -> ok), curr: build new, delete old, place new (in render)
    events (local/ui and otherwise)
    widget building (popupmenu, etc.)
    localization
    incorporate relations
    convert function comments to /** style
    complete comments
    
    don't draw body until it's first unhide event
    
    as always: where does the model end and the view begin?
    HistoryPanel
    HistoryCollection: (collection of History: 'Saved Histories')
    
    CASES:
        logged-in/NOT
        show-deleted/DONT
        
    ?? anyway to _clone_ base HistoryItemView instead of creating a new one each time?

    move inline styles into base.less
    add classes, ids on empty divs
    localized text from template
    watch the magic strings
    
    poly HistoryItemView on: can/cant_edit
*/

//==============================================================================

//==============================================================================
//TODO: move to Galaxy obj./namespace, decorate for current page (as GalaxyPaths)
/*
var Localizable = {
    localizedStrings : {},
    setLocalizedString : function( str, localizedString ){
        this.localizedStrings[ str ] = localizedString;
    },
    localize : function( str ){
        if( str in this.localizedStrings ){ return this.localizedStrings[ str ]; }
        return str;
    }
};
var LocalizableView = LoggingView.extend( Localizable );
*/
//TODO: wire up to views

//==============================================================================
// jq plugin?
//?? into template? I dunno: need to handle variadic keys, remove empty attrs (href="")
//TODO: not happy with this (a 4th rendering/templating system!?) or it being global
function linkHTMLTemplate( config, tag ){
    // Create an anchor (or any tag) using any config params passed in
    //NOTE!: send class attr as 'classes' to avoid res. keyword collision (jsLint)
    if( !config ){ return '<a></a>'; }
    tag = tag || 'a';
    
    var template = [ '<' + tag ];
    for( key in config ){
        var val = config[ key ];
        if( val === '' ){ continue; }
        switch( key ){
            case 'text': continue;
            case 'classes':
                // handle keyword class which is also an HTML attr name
                key = 'class';
                val = ( config.classes.join )?( config.classes.join( ' ' ) ):( config.classes );
                //note: lack of break (fall through)
            default:
                template.push( [ ' ', key, '="', val, '"' ].join( '' ) );
        }
    }
    template.push( '>' );
    if( 'text' in config ){ template.push( config.text ); }
    template.push( '</' + tag + '>' );
    
    return template.join( '' );
}

//==============================================================================
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
    NEW         : 'new',
    UPLOAD      : 'upload',
    QUEUED      : 'queued',
    RUNNING     : 'running',
    OK          : 'ok',
    EMPTY       : 'empty',
    ERROR       : 'error',
    DISCARDED   : 'discarded',
    SETTING_METADATA    : 'setting_metadata',
    FAILED_METADATA     : 'failed_metadata'
};


//==============================================================================
var HistoryItemView = BaseView.extend( LoggableMixin ).extend({
    //??TODO: add alias in initialize this.hda = this.model?
    // view for HistoryItem model above

    // uncomment this out see log messages
    logger              : console,

    tagName     : "div",
    className   : "historyItemContainer",
    
    // ................................................................................ SET UP
    initialize  : function(){
        this.log( this + '.initialize:', this, this.model );
        
    },
   
    // ................................................................................ RENDER MAIN
    //??: this style builds an entire, new DOM tree - is that what we want??
    render : function(){
        this.log( this + '.model:', this.model );
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
        
        //TODO: broken
        var popupmenus = itemWrapper.find( '[popupmenu]' );
        popupmenus.each( function( i, menu ){
            menu = $( menu );
            make_popupmenu( menu );
        });
        
        //TODO: better transition/method than this...
        this.$el.children().remove();
        return this.$el.append( itemWrapper );
    },
    
    clearReferences : function(){
        //??TODO: best way?
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

    // ................................................................................ DISPLAY, EDIT ATTR, DELETE
    _render_titleButtons : function(){
        // render the display, edit attr and delete icon-buttons
        var buttonDiv = $( '<div class="historyItemButtons"></div>' );
        buttonDiv.append( this._render_displayButton() );
        buttonDiv.append( this._render_editButton() );
        buttonDiv.append( this._render_deleteButton() );
        return buttonDiv;
    },
    
    //TODO: refactor the following three - use extend for new href (with model data or something else)
    //TODO: move other data (non-href) into {} in view definition, cycle over those keys in _titlebuttons
    //TODO: move disabled span data into view def, move logic into _titlebuttons
    _render_displayButton : function(){
        
        // don't show display while uploading
        if( this.model.get( 'state' ) === HistoryItem.STATES.UPLOAD ){ return null; }
        
        // show a disabled display if the data's been purged
        displayBtnData = ( this.model.get( 'purged' ) )?({
            title       : 'Cannot display datasets removed from disk',
            enabled     : false,
            icon_class  : 'display',
            
        // if not, render the display icon-button with href 
        }):({
            title       : 'Display data in browser',
            href        : this.model.get( 'display_url' ),
            target      : ( this.model.get( 'for_editing' ) )?( 'galaxy_main' ):( null ),
            icon_class  : 'display',
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
        
        var deleteBtnData = ( this.model.get( 'delete_url' ) )?({
            title       : 'Delete',
            href        : this.model.get( 'delete_url' ),
            target      : 'galaxy_main',
            id          : 'historyItemDeleter-' + this.model.get( 'id' ),
            icon_class  : 'delete'
        }):({
            title       : 'Dataset is already deleted',
            icon_class  : 'delete',
            enabled     : false
        });
        this.deleteButton = new IconButtonView({ model : new IconButton( deleteBtnData ) });
        return this.deleteButton.render().$el;
    },
    
    _render_titleLink : function(){
        this.log( 'model:', this.model.toJSON() );
        return $( jQuery.trim( HistoryItemView.templates.titleLink( this.model.toJSON() ) ) );
    },

    // ................................................................................ RENDER BODY
    // _render_body fns for the various states
    _render_body_not_viewable : function( parent ){
        parent.append( $( '<div>You do not have permission to view dataset.</div>' ) );
    },
    
    _render_body_uploading : function( parent ){
        parent.append( $( '<div>Dataset is uploading</div>' ) );
    },
        
    _render_body_queued : function( parent ){
        parent.append( $( '<div>Job is waiting to run.</div>' ) );
        parent.append( this._render_showParamsAndRerun() );
    },
        
    _render_body_running : function( parent ){
        parent.append( '<div>Job is currently running.</div>' );
        parent.append( this._render_showParamsAndRerun() );
    },
        
    _render_body_error : function( parent ){
        if( !this.model.get( 'purged' ) ){
            parent.append( $( '<div>' + this.model.get( 'misc_blurb' ) + '</div>' ) );
        }
        parent.append( ( 'An error occurred running this job: '
                       + '<i>' + $.trim( this.model.get( 'misc_info' ) ) + '</i>' ) );
        
        var actionBtnDiv = $( this._render_showParamsAndRerun() );
        // bug report button
        //NOTE: these are shown _before_ info, rerun so use _prepend_
        if( this.model.get( 'for_editing' ) ){
            //TODO??: save to view 'this.errButton'
            this.errButton = new IconButtonView({ model : new IconButton({
                title       : 'View or report this error',
                href        : this.model.get( 'report_error_url' ),
                target      : 'galaxy_main',
                icon_class  : 'bug'
            })});
            actionBtnDiv.prepend( this.errButton.render().$el );
        }
        if( this.model.hasData() ){
            //TODO: render_download_links( data, dataset_id )
            // download dropdown
            actionBtnDiv.prepend( this._render_downloadLinks() );
        }
        parent.append( actionBtnDiv );
    },
        
    _render_body_discarded : function( parent ){
        parent.append( '<div>The job creating this dataset was cancelled before completion.</div>' );
        parent.append( this._render_showParamsAndRerun() );
    },
        
    _render_body_setting_metadata : function( parent ){
        parent.append( $( '<div>Metadata is being auto-detected.</div>' ) );
    },
    
    _render_body_empty : function( parent ){
        //TODO: replace i with dataset-misc-info class 
        //?? why are we showing the file size when we know it's zero??
        parent.append( $( '<div>No data: <i>' + this.model.get( 'misc_blurb' ) + '</i></div>' ) );
        parent.append( this._render_showParamsAndRerun() );
    },
        
    _render_body_failed_metadata : function( parent ){
        // add a message box about the failure at the top of the body, then...
        var warningMsgText = 'An error occurred setting the metadata for this dataset.';
        if( this.model.isEditable() ){
            var editLink = linkHTMLTemplate({
                text        : 'set it manually or retry auto-detection',
                href        : this.model.get( 'edit_url' ),
                target      : 'galaxy_main'
            });
            warningMsgText += 'You may be able to ' + editLink + '.';
        }
        parent.append( $( HistoryItemView.templates.warningMsg({ warning: warningMsgText }) ) );
        
        //...render the remaining body as STATES.OK (only diff between these states is the box above)
        this._render_body_ok( parent );
    },
        
    _render_body_ok : function( parent ){
        // most common state renderer and the most complicated
        
        // build the summary info (using template and dbkey data)
        parent.append( this._render_hdaSummary() );
        
        if( this.model.get( 'misc_info' ) ){
            parent.append( $( '<div class="info">Info: ' + this.model.get( 'misc_info' ) + '</div>' ) );
        }
        
        // hasData
        if( this.model.hasData() ){
            var actionBtnDiv = $( '<div/>' );
            
            // render download links, show_params
            actionBtnDiv.append( this._render_downloadLinks() );
            actionBtnDiv.append( $( linkHTMLTemplate({
                title       : 'View details',
                href        : this.model.get( 'show_params_url' ),
                target      : 'galaxy_main',
                classes     : [ 'icon-button', 'tooltip', 'information' ]
            })));
            
            // if for_editing
            if( this.model.get( 'for_editing' ) ){
                
                // rerun
                actionBtnDiv.append( $( linkHTMLTemplate({
                    title       : 'Run this job again',
                    href        : this.model.get( 'rerun_url' ),
                    target      : 'galaxy_main',
                    classes     : [ 'icon-button', 'tooltip', 'arrow-circle' ]
                })));
                
                if( this.model.get( 'trackster_urls' ) ){
                    // link to trackster
                    var trackster_urls = this.model.get( 'trackster_urls' );
                    actionBtnDiv.append( $( linkHTMLTemplate({
                        title       : 'View in Trackster',
                        href        : "javascript:void(0)",
                        classes     : [ 'icon-button', 'tooltip', 'chart_curve', 'trackster-add' ],
                        // prob just _.extend
                        'data-url'  : trackster_urls[ 'data-url' ],
                        'action-url': trackster_urls[ 'action-url' ],
                        'new-url'   : trackster_urls[ 'new-url' ]
                    })));
                }
                
                // if trans.user
                if( this.model.get( 'retag_url' ) && this.model.get( 'annotate_url' ) ){
                    // tag, annotate buttons
                    //TODO: move to tag, Annot MV
                    var tagsAnnotationsBtns = $( '<div style="float: right;"></div>' );
                    tagsAnnotationsBtns.append( $( linkHTMLTemplate({
                        title       : 'Edit dataset tags',
                        target      : 'galaxy_main',
                        href        : this.model.get( 'retag_url' ),
                        classes     : [ 'icon-button', 'tooltip', 'tags' ]
                    })));
                    tagsAnnotationsBtns.append( $( linkHTMLTemplate({
                        title       : 'Edit dataset annotation',
                        target      : 'galaxy_main',
                        href        : this.model.get( 'annotation_url' ),
                        classes     : [ 'icon-button', 'tooltip', 'annotate' ]
                    })));
                    actionBtnDiv.append( tagsAnnotationsBtns );
                    actionBtnDiv.append( '<div style="clear: both"></div>' );
                    
                    // tag/annot display areas
                    this.tagArea = $( '<div class="tag-area" style="display: none">' );
                    this.tagArea.append( '<strong>Tags:</strong>' );
                    this.tagElt = $( '<div class="tag-elt"></div>' );
                    actionBtnDiv.append( this.tagArea.append( this.tagElt ) );
                    
                    var annotationArea = $( ( '<div id="${dataset_id}-annotation-area"'
                                            + ' class="annotation-area" style="display: none">' ) );
                    this.annotationArea = annotationArea;
                    annotationArea.append( '<strong>Annotation:</strong>' );
                    this.annotationElem = $( '<div id="' + this.model.get( 'id' ) + '-annotation-elt" '
                        + 'style="margin: 1px 0px 1px 0px" class="annotation-elt tooltip editable-text" '
                        + 'title="Edit dataset annotation"></div>' );
                    annotationArea.append( this.annotationElem );
                    actionBtnDiv.append( annotationArea );
                }
            }
            // clear div
            actionBtnDiv.append( '<div style="clear: both;"></div>' );
            parent.append( actionBtnDiv );
            
            var display_appsDiv = $( '<div/>' );
            if( this.model.get( 'display_apps' ) ){
                var display_apps = this.model.get( 'display_apps' ),
                    display_app_span = $( '<span/>' );
                    
                //TODO: grrr...somethings not in the right scope here
                for( app_name in display_apps ){
                    //TODO: to template
                    var display_app = display_apps[ app_name ],
                        display_app_HTML = app_name + ' ';
                    for( location_name in display_app ){
                        display_app_HTML += linkHTMLTemplate({
                            text    : location_name,
                            href    : display_app[ location_name ].url,
                            target  : display_app[ location_name ].target
                        }) + ' ';
                    }
                    display_app_span.append( display_app_HTML );
                }
                display_appsDiv.append( display_app_span );
            }
            //display_appsDiv.append( '<br />' );
            parent.append( display_appsDiv );
        
        } else if( this.model.get( 'for_editing' ) ){
            parent.append( this._render_showParamsAndRerun() );
        }
        
        parent.append( this._render_peek() );
    },
    
    _render_body : function(){
        //this.log( this + '_render_body' );
        var state = this.model.get( 'state' ),
            for_editing = this.model.get( 'for_editing' );
        //this.log( 'state:', state, 'for_editing', for_editing );
        
        //TODO: incorrect id (encoded - use hid?)
        var body = $( '<div/>' )
            .attr( 'id', 'info-' + this.model.get( 'id' ) )
            .addClass( 'historyItemBody' )
            .attr(  'style', 'display: block' );
        
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
        return body;
    },

    _render_hdaSummary : function(){
        var modelData = this.model.toJSON();
        
        // if there's no dbkey and it's editable : pass a flag to the template to render a link to editing in the '?'
        if( this.model.get( 'metadata_dbkey' ) === '?'
        &&  this.model.isEditable() ){
            _.extend( modelData, { dbkey_unknown_and_editable : true });
        }
        return HistoryItemView.templates.hdaSummary( modelData );
    },

    _render_showParamsAndRerun : function(){
        //TODO??: generalize to _render_actionButtons, pass in list of 'buttons' to render, default to these two
        var actionBtnDiv = $( '<div/>' );
        
        this.showParamsButton = new IconButtonView({ model : new IconButton({
            title       : 'View details',
            href        : this.model.get( 'show_params_url' ),
            target      : 'galaxy_main',
            icon_class  : 'information'
        }) });
        actionBtnDiv.append( this.showParamsButton.render().$el );
        
        if( this.model.get( 'for_editing' ) ){
            this.rerunButton = new IconButtonView({ model : new IconButton({
                title       : 'Run this job again',
                href        : this.model.get( 'rerun_url' ),
                target      : 'galaxy_main',
                icon_class  : 'arrow-circle'
            }) });
        }
        return actionBtnDiv;
    },
    
    _render_downloadLinks : function(){
        // return either: a single download icon-button (if there are no meta files)
        //  or a popupmenu with links to download assoc. meta files (if there are meta files)
        
        // don't show anything if the data's been purged
        if( this.model.get( 'purged' ) ){ return null; }
        
        var downloadLink = linkHTMLTemplate({
            title       : 'Download',
            href        : this.model.get( 'download_url' ),
            classes     : [ 'icon-button', 'tooltip', 'disk' ]
        });
        
        // if no metafiles, return only the main download link
        var download_meta_urls = this.model.get( 'download_meta_urls' );
        if( !download_meta_urls ){
            return downloadLink;
        }
        
        // build the popupmenu for downloading main, meta files
        var popupmenu = $( '<div popupmenu="dataset-' + this.model.get( 'id' ) + '-popup"></div>' );
        popupmenu.append( linkHTMLTemplate({
            text        : 'Download Dataset',
            title       : 'Download',
            href        : this.model.get( 'download_url' ),
            classes     : [ 'icon-button', 'tooltip', 'disk' ]
        }));
        popupmenu.append( '<a>Additional Files</a>' );
        for( file_type in download_meta_urls ){
            popupmenu.append( linkHTMLTemplate({
                text        : 'Download ' + file_type,
                href        : download_meta_urls[ file_type ],
                classes     : [ 'action-button' ]
            }));
        }
        var menuButton = $( ( '<div style="float:left;" class="menubutton split popup"'
                          + ' id="dataset-${dataset_id}-popup"></div>' ) );
        menuButton.append( downloadLink );
        popupmenu.append( menuButton );
        return popupmenu;
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

    // ................................................................................ EVENTS
    events : {
        'click .historyItemTitle'           : 'toggleBodyVisibility',
        'click a.icon-button.tags'          : 'loadAndDisplayTags',
        'click a.icon-button.annotate'      : 'loadAndDisplayAnnotation'
    },
    
    // ................................................................................ STATE CHANGES / MANIPULATION
    loadAndDisplayTags : function( event ){
        //TODO: this is a drop in from history.mako - should use MV as well
        this.log( this, '.loadAndDisplayTags', event );
        var tagArea = this.tagArea;
        var tagElt = this.tagElt;

        // Show or hide tag area; if showing tag area and it's empty, fill it.
        if( tagArea.is( ":hidden" ) ){
            if( !tagElt.html() ){
                // Need to fill tag element.
                $.ajax({
                    url: this.model.get( 'ajax_get_tag_url' ),
                    error: function() { alert( "Tagging failed" ) },
                    success: function(tag_elt_html) {
                        this.log( 'tag_elt_html:', tag_elt_html );
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
        //TODO: this is a drop in from history.mako - should use MV as well
        this.log( this, '.loadAndDisplayAnnotation', event );
        var annotationArea = this.annotationArea,
            annotationElem = this.annotationElem,
            setAnnotationUrl = this.model.get( 'ajax_set_annotation_url' );

        // Show or hide annotation area; if showing annotation area and it's empty, fill it.
        this.log( 'annotationArea hidden:', annotationArea.is( ":hidden" ) );
        this.log( 'annotationElem html:', annotationElem.html() );
        if ( annotationArea.is( ":hidden" ) ){
            if( !annotationElem.html() ){
                // Need to fill annotation element.
                $.ajax({
                    url: this.model.get( 'ajax_get_annotation_url' ),
                    error: function(){ alert( "Annotations failed" ) },
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

    toggleBodyVisibility : function(){
        this.log( this + '.toggleBodyVisibility' );
        this.$el.find( '.historyItemBody' ).toggle();
    },

    // ................................................................................ UTILTIY
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '' );
        return 'HistoryItemView(' + modelString + ')';    
    }
});


//==============================================================================
//HistoryItemView.templates = InDomTemplateLoader.getTemplates({
HistoryItemView.templates = CompiledTemplateLoader.getTemplates({
    'history-templates.html' : {
        messages        : 'template-history-warning-messages',
        titleLink       : 'template-history-titleLink',
        hdaSummary      : 'template-history-hdaSummary'
    }
});

//==============================================================================
var HistoryCollection = Backbone.Collection.extend({
    model           : HistoryItem,
    
    toString        : function(){
         return ( 'HistoryCollection()' );
    }
});


//==============================================================================
var History = BaseModel.extend( LoggableMixin ).extend({
    
    // uncomment this out see log messages
    //logger              : console,

    // values from api (may need more)
    defaults : {
        id              : '', 
        name            : '', 
        state           : '', 
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
        }
    },
    
    initialize : function( data, history_datasets ){
        this.log( this + '.initialize', data, history_datasets );
        this.items = new HistoryCollection();
    },

    loadDatasetsAsHistoryItems : function( datasets ){
        // adds the given dataset/Item data to historyItems
        //  and updates this.state based on their states
        //pre: datasets is a list of objs
        //this.log( this + '.loadDatasets', datasets );
        var self = this,
            selfID = this.get( 'id' ),
            stateDetails = this.get( 'state_details' );
            
        _.each( datasets, function( dataset, index ){
            self.log( 'loading dataset: ', dataset, index );
            
            // create an item sending along the history_id as well
            var historyItem = new HistoryItem(
                _.extend( dataset, { history_id: selfID } ) );
            self.log( 'as History:', historyItem );
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
var HistoryView = BaseView.extend( LoggableMixin ).extend({
    // view for the HistoryCollection (as per current right hand panel)
    
    // uncomment this out see log messages
    //logger              : console,

    // direct attachment to existing element
    el                  : 'body.historyPage',
    
    initialize  : function(){
        this.log( this + '.initialize' );
        this.itemViews = [];
        var parent = this;
        this.model.items.each( function( item ){
            var itemView = new HistoryItemView({ model: item });
            parent.itemViews.push( itemView );
        });
        //itemViews.reverse();
    },
    
    render      : function(){
        this.log( this + '.render' );
        
        // render to temp, move all at once, remove temp holder
        //NOTE!: render in reverse (newest on top) via prepend (instead of append)
        var tempDiv = $( '<div/>' );
        _.each( this.itemViews, function( view ){
            tempDiv.prepend( view.render() );
        });
        this.$el.append( tempDiv.children() );
        tempDiv.remove();
    },
    
    toString    : function(){
        var nameString = this.model.get( 'name' ) || '';
        return 'HistoryView(' + nameString + ')';
    }
});


//==============================================================================
function createMockHistoryData(){
    mockHistory = {};
    mockHistory.data = {
        
        template : {
            id                  : 'a799d38679e985db', 
            name                : 'template', 
            data_type           : 'fastq', 
            file_size           : 226297533, 
            genome_build        : '?', 
            metadata_data_lines : 0, 
            metadata_dbkey      : '?', 
            metadata_sequences  : 0, 
            misc_blurb          : '215.8 MB', 
            misc_info           : 'uploaded fastq file', 
            model_class         : 'HistoryDatasetAssociation', 
            download_url        : '', 
            state               : 'ok', 
            visible             : true,
            deleted             : false, 
            purged              : false,
            
            hid                 : 0,
            //TODO: move to history
            for_editing         : true,
            //for_editing         : false,
            
            //?? not needed
            //can_edit            : true,
            //can_edit            : false,
            
            //TODO: move into model functions (build there (and cache?))
            //!! be careful with adding these accrd. to permissions
            //!!    IOW, don't send them via template/API if the user doesn't have perms to use
            //!!    (even if they don't show up)
            undelete_url        : 'example.com/undelete',
            purge_url           : 'example.com/purge',
            unhide_url          : 'example.com/unhide',
            
            display_url         : 'example.com/display',
            edit_url            : 'example.com/edit',
            delete_url          : 'example.com/delete',
            
            show_params_url     : 'example.com/show_params',
            rerun_url           : 'example.com/rerun',
            
            retag_url           : 'example.com/retag',
            annotate_url        : 'example.com/annotate',
            
            peek                : [
                '<table cellspacing="0" cellpadding="3"><tr><th>1.QNAME</th><th>2.FLAG</th><th>3.RNAME</th><th>4.POS</th><th>5.MAPQ</th><th>6.CIGAR</th><th>7.MRNM</th><th>8.MPOS</th><th>9.ISIZE</th><th>10.SEQ</th><th>11.QUAL</th><th>12.OPT</th></tr>',
                '<tr><td colspan="100%">@SQ	SN:gi|87159884|ref|NC_007793.1|	LN:2872769</td></tr>',
                '<tr><td colspan="100%">@PG	ID:bwa	PN:bwa	VN:0.5.9-r16</td></tr>',
                '<tr><td colspan="100%">HWUSI-EAS664L:15:64HOJAAXX:1:1:13280:968	73	gi|87159884|ref|NC_007793.1|	2720169	37	101M	=	2720169	0	NAATATGACATTATTTTCAAAACAGCTGAAAATTTAGACGTACCGATTTATCTACATCCCGCGCCAGTTAACAGTGACATTTATCAATCATACTATAAAGG	!!!!!!!!!!$!!!$!!!!!$!!!!!!$!$!$$$!!$!!$!!!!!!!!!!!$!</td></tr>',
                '<tr><td colspan="100%">!!!$!$!$$!!$$!!$!!!!!!!!!!!!!!!!!!!!!!!!!!$!!$!!	XT:A:U	NM:i:1	SM:i:37	AM:i:0	X0:i:1	X1:i:0	XM:i:1	XO:i:0	XG:i:0	MD:Z:0A100</td></tr>',
                '<tr><td colspan="100%">HWUSI-EAS664L:15:64HOJAAXX:1:1:13280:968	133	gi|87159884|ref|NC_007793.1|	2720169	0	*	=	2720169	0	NAAACTGTGGCTTCGTTNNNNNNNNNNNNNNNGTGANNNNNNNNNNNNNNNNNNNGNNNNNNNNNNNNNNNNNNNNCNAANNNNNNNNNNNNNNNNNNNNN	!!!!!!!!!!!!$!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!</td></tr>',
                '<tr><td colspan="100%">!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!</td></tr>',
                '</table>'
            ].join( '' )
        }
        
    };
    _.extend( mockHistory.data, {
        
        //deleted, purged, visible
        deleted     :
            _.extend( _.clone( mockHistory.data.template ),
                      { deleted : true }),
        //purged      :
        //    _.extend( _.clone( mockHistory.data.template ),
        //              { purged : true, deleted : true }),
        purgedNotDeleted :
            _.extend( _.clone( mockHistory.data.template ),
                      { purged : true }),
        notvisible  :
            _.extend( _.clone( mockHistory.data.template ),
                      { visible : false }),

        hasDisplayApps :
            _.extend( _.clone( mockHistory.data.template ),
                { display_apps : {
                        'display in IGB' : {
                            Web: "/display_application/63cd3858d057a6d1/igb_bam/Web",
                            Local: "/display_application/63cd3858d057a6d1/igb_bam/Local"
                        }
                    }
                }
            ),
        canTrackster :
            _.extend( _.clone( mockHistory.data.template ),
                { trackster_urls      : {
                        'data-url'      : "example.com/trackster-data",
                        'action-url'    : "example.com/trackster-action",
                        'new-url'       : "example.com/trackster-new"
                    }
                }
            ),
        zeroSize  :
            _.extend( _.clone( mockHistory.data.template ),
                      { file_size : 0 }),
            
        hasMetafiles  :
            _.extend( _.clone( mockHistory.data.template ), {
                download_meta_urls : {
                    'bam_index'      : "example.com/bam-index"
                }
            }),
            
        //states
        upload :
            _.extend( _.clone( mockHistory.data.template ),
                      { state : HistoryItem.STATES.UPLOAD }),
        queued :
            _.extend( _.clone( mockHistory.data.template ),
                      { state : HistoryItem.STATES.QUEUED }),
        running :
            _.extend( _.clone( mockHistory.data.template ),
                      { state : HistoryItem.STATES.RUNNING }),
        empty :
            _.extend( _.clone( mockHistory.data.template ),
                      { state : HistoryItem.STATES.EMPTY }),
        error :
            _.extend( _.clone( mockHistory.data.template ),
                      { state : HistoryItem.STATES.ERROR,
                        report_error_url: 'example.com/report_err' }),
        discarded :
            _.extend( _.clone( mockHistory.data.template ),
                      { state : HistoryItem.STATES.DISCARDED }),
        setting_metadata :
            _.extend( _.clone( mockHistory.data.template ),
                      { state : HistoryItem.STATES.SETTING_METADATA }),
        failed_metadata :
            _.extend( _.clone( mockHistory.data.template ),
                      { state : HistoryItem.STATES.FAILED_METADATA })
/*
*/        
    });
    
    $( document ).ready( function(){
        //mockHistory.views.deleted.logger = console;
        mockHistory.items = {};
        mockHistory.views = {};
        for( key in mockHistory.data ){
            mockHistory.items[ key ] = new HistoryItem( mockHistory.data[ key ] );
            mockHistory.items[ key ].set( 'name', key );
            mockHistory.views[ key ] = new HistoryItemView({ model : mockHistory.items[ key ] });
            //console.debug( 'view: ', mockHistory.views[ key ] );
            $( 'body' ).append( mockHistory.views[ key ].render() );
        }
    });
}

