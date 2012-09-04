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
_ = _;

//==============================================================================
var Loggable = {
    // replace null with console (if available) to see all logs
    logger      : null,
    
    log : function(){
        return ( this.logger )?( this.logger.debug.apply( this, arguments ) )
                              :( undefined );
    }
};
var LoggingModel = BaseModel.extend( Loggable );
var LoggingView  = BaseView.extend( Loggable );

//==============================================================================
//TODO: move to Galaxy obj./namespace, decorate for current page (as GalaxyPaths)
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
var HistoryItem = LoggingModel.extend({
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
        // roughly can_edit from history_common.mako
        return ( !( this.get( 'deleted' ) || this.get( 'purged' ) ) );
    },
    
    hasData : function(){
        //TODO:?? is this equivalent to all possible hda.has_data calls?
        return ( this.get( 'file_size' ) > 0 );
    },

    toString : function(){
        return 'HistoryItem(' + ( this.get( 'name' ) || this.get( 'id' ) || '' ) + ')';
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
var HistoryItemView = LoggingView.extend({
    // view for HistoryItem model above

    // uncomment this out see log messages
    logger              : console,

    tagName     : "div",
    className   : "historyItemContainer",
    
    
    // ................................................................................ SET UP
    initialize  : function(){
        this.log( this + '.initialize:', this, this.model );
        return this;
    },
   
    // ................................................................................ RENDER MAIN
    //??: this style builds an entire, new DOM tree - is that what we want??
    render : function(){
        this.log( this + '.model:', this.model );
        var id = this.model.get( 'id' ),
            state = this.model.get( 'state' );
        
        this.$el.attr( 'id', 'historyItemContainer-' + id );
        
        var itemWrapper = $( '<div/>' ).attr( 'id', 'historyItem-' + id )
            .addClass( 'historyItemWrapper' ).addClass( 'historyItem' )
            .addClass( 'historyItem-' + state );
            
        itemWrapper.append( this._render_purgedWarning() );
        itemWrapper.append( this._render_deletionWarning() );
        itemWrapper.append( this._render_visibleWarning() );
        
        itemWrapper.append( this._render_titleBar() );
        
        this.body = $( this._render_body() );
        itemWrapper.append( this.body );
        
        // set up canned behavior (bootstrap, popupmenus, editable_text, etc.)
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
    
    // ................................................................................ RENDER WARNINGS
    //TODO: refactor into generalized warning widget/view
    //TODO: refactor the three following - too much common ground
    _render_purgedWarning : function(){
        // Render warnings for purged
        //this.log( this + '_render_purgedWarning' );
        var warning = null;
        if( this.model.get( 'purged' ) ){
            warning = $( HistoryItemView.STRINGS.purgedMsg );
        } 
        //this.log( 'warning:', warning );
        return warning;
    },
    
    _render_deletionWarning : function(){
        //this.log( this + '_render_deletionWarning' );
        // Render warnings for deleted items (and links: undelete and purge)
        //pre: this.model.purge_url will be undefined if trans.app.config.allow_user_dataset_purge=False
        var warningElem = null;
        if( this.model.get( 'deleted' ) ){
            var warning = '';
            
            if( this.model.get( 'undelete_url' ) ){
                warning += HistoryItemView.TEMPLATES.undeleteLink( this.model.attributes );
            }
            if( this.model.get( 'purge_url' ) ){
                warning += HistoryItemView.TEMPLATES.purgeLink( this.model.attributes );
            }
            // wrap it in the standard warning msg
            warningElem = $( HistoryItemView.TEMPLATES.warningMsg({ warning: warning }) );
        }
        //this.log( 'warning:', warning );
        return warningElem;
    },
    
    _render_visibleWarning : function(){
        //this.log( this + '_render_visibleWarning' );
        // Render warnings for hidden items (and link: unhide)
        var warningElem = null;
        if( !this.model.get( 'visible' ) && this.model.get( 'unhide_url' ) ){
            var warning = HistoryItemView.TEMPLATES.hiddenMsg( this.model.attributes );
            
            // wrap it in the standard warning msg
            warningElem = $( HistoryItemView.TEMPLATES.warningMsg({ warning: warning }) );
        }
        //this.log( 'warning:', warning );
        return warningElem;
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
        var buttonDiv = $( '<div class="historyItemButtons"></div>' ),
            for_editing = this.model.get( 'for_editing' );
            
        // don't show display, edit while uploading
        if( this.model.get( 'state' ) !== HistoryItem.STATES.UPLOAD ){
            buttonDiv.append( this._render_displayButton() );
            
            if( for_editing ){ buttonDiv.append( this._render_editButton() ); }
        }
        if( for_editing ){ buttonDiv.append( this._render_deleteButton() ); }
        return buttonDiv;
    },
    
    //TODO: refactor the following three - use extend for new href (with model data or something else)
    //TODO: move other data (non-href) into {} in view definition, cycle over those keys in _titlebuttons
    //TODO: move disabled span data into view def, move logic into _titlebuttons
    _render_displayButton : function(){
        // render the display icon-button
        // show a disabled display if the data's been purged
        if( this.model.get( 'purged' ) ){
            return $( '<span class="icon-button display_disabled tooltip" ' +
                      'title="Cannot display datasets removed from disk"></span>' );
        }
        var id = this.model.get( 'id' ),
            displayBtnData = {
                //TODO: localized title
                title       : 'Display data in browser',
                //TODO: need generated url here
                href        : '/datasets/' + id + '/display/?preview=True',
                target      : ( this.model.get( 'for_editing' ) )?( 'galaxy_main' ):( '' ),
                classes     : [ 'icon-button', 'tooltip', 'display' ],
                dataset_id  : id
            };
        return $( linkHTMLTemplate( displayBtnData ) );
    },
    
    _render_editButton : function(){
        // render the edit attr icon-button
        var id = this.model.get( 'id' ),
            purged = this.model.get( 'purged' ),
            deleted = this.model.get( 'deleted' );
            
        if( deleted || purged ){
            if( !purged ){
                return $( '<span class="icon-button edit_disabled tooltip" ' +
                          'title="Undelete dataset to edit attributes"></span>' );
            } else {
                return $( '<span class="icon-button edit_disabled tooltip" ' +
                          'title="Cannot edit attributes of datasets removed from disk"></span>' );
            }
        }
        return $( linkHTMLTemplate({
            title       : 'Edit attributes',
            //TODO: need generated url here
            href        : '/datasets/' + id + '/edit',
            target      : 'galaxy_main',
            classes     : [ 'icon-button', 'tooltip', 'edit' ]
        }) );
    },
    
    _render_deleteButton : function(){
        // render the delete icon-button
        var id = this.model.get( 'id' ),
            purged = this.model.get( 'purged' ),
            deleted = this.model.get( 'deleted' );
            
        //??: WHAAAA? can_edit == deleted??
        //  yes! : (history_common.mako) can_edit=( not ( data.deleted or data.purged ) )
        if( purged || deleted ){
            return $( '<span title="Dataset is already deleted" ' +
                      'class="icon-button delete_disabled tooltip"></span>' );
        }
        return $( linkHTMLTemplate({
            title       : 'Delete',
            //TODO: need generated url here
            href        : '/datasets/' + id + '/delete?show_deleted_on_refresh=False',
            target      : 'galaxy_main',
            id          : 'historyItemDeleter-' + id,
            classes     : [ 'icon-button', 'tooltip', 'delete' ]
        }));
    },
    
    _render_titleLink : function(){
        // render the title (hda name)
        var h_name = this.model.get( 'name' ),
            hid = this.model.get( 'hid' );
            title = ( hid + ': ' + h_name );
        return $( linkHTMLTemplate({
            href        : 'javascript:void(0);',
            text        : '<span class="historyItemTitle">' + title + '</span>'
        }));
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
            actionBtnDiv.prepend( $( linkHTMLTemplate({
                title       : 'View or report this error',
                href        : this.model.get( 'report_errors_url' ),
                target      : 'galaxy_main',
                classes     : [ 'icon-button', 'tooltip', 'bug' ]
            })));
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
        parent.append( $( HistoryItemView.TEMPLATES.warningMsg({ warning: warningMsgText }) ) );
        
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
                    // tags, annotation buttons and display areas
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
                    
                    var tagArea = $( '<div class="tag-area" style="display: none">' );
                    tagArea.append( '<strong>Tags:</strong>' );
                    tagArea.append( '<div class="tag-elt"></div>' );
                    actionBtnDiv.append( tagArea );
                    
                    var annotationArea = $( ( '<div id="${dataset_id}-annotation-area"'
                                            + ' class="annotation-area" style="display: none">' ) );
                    annotationArea.append( '<strong>Annotation:</strong>' );
                    annotationArea.append( ( '<div id="${dataset_id}-annotation-elt" '
                        + 'style="margin: 1px 0px 1px 0px" class="annotation-elt tooltip editable-text" '
                        + 'title="Edit dataset annotation"></div>' ) );
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
        this.log( this + '_render_body' );
        var state = this.model.get( 'state' ),
            for_editing = this.model.get( 'for_editing' );
        this.log( 'state:', state, 'for_editing', for_editing );
        
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
        // default span rendering
        var dbkeyHTML = _.template( '<span class="<%= dbkey %>"><%= dbkey %></span>',
                                { dbkey: this.model.get( 'metadata_dbkey' ) } );
        // if there's no dbkey and it's editable : render a link to editing in the '?'
        if( this.model.get( 'metadata_dbkey' ) === '?' && this.model.isEditable() ){
            dbkeyHTML = linkHTMLTemplate({
                text        : this.model.get( 'metadata_dbkey' ),
                href        : this.model.get( 'edit_url' ),
                target      : 'galaxy_main'
            });
        }
        return ( HistoryItemView.TEMPLATES.hdaSummary(
            _.extend({ dbkeyHTML: dbkeyHTML }, this.model.attributes ) ) );
    },

    _render_showParamsAndRerun : function(){
        //TODO??: generalize to _render_actionButtons, pass in list of 'buttons' to render, default to these two
        var actionBtnDiv = $( '<div/>' );
        actionBtnDiv.append( $( linkHTMLTemplate({
            title       : 'View details',
            href        : this.model.get( 'show_params_url' ),
            target      : 'galaxy_main',
            classes     : [ 'icon-button', 'tooltip', 'information' ]
        })));
        if( this.model.get( 'for_editing' ) ){
            actionBtnDiv.append( $( linkHTMLTemplate({
                title       : 'Run this job again',
                href        : this.model.get( 'rerun_url' ),
                target      : 'galaxy_main',
                classes     : [ 'icon-button', 'tooltip', 'arrow-circle' ]
            })));
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
        'click .historyItemTitle' : 'toggleBodyVisibility'
    },
    
    // ................................................................................ STATE CHANGES / MANIPULATION
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

//------------------------------------------------------------------------------
HistoryItemView.TEMPLATES = {};

//TODO: move next one out - doesn't belong
HistoryItemView.TEMPLATES.warningMsg =
    _.template( '<div class=warningmessagesmall><strong><%= warning %></strong></div>' );
    

//??TODO: move into functions?        
HistoryItemView.TEMPLATES.undeleteLink = _.template(
    'This dataset has been deleted. ' + 
    'Click <a href="<%= undelete_url %>" class="historyItemUndelete" id="historyItemUndeleter-{{ id }}" ' +
    '         target="galaxy_history">here</a> to undelete it.' );
    
HistoryItemView.TEMPLATES.purgeLink = _.template(
    ' or <a href="<%= purge_url %>" class="historyItemPurge" id="historyItemPurger-{{ id }}"' + 
    '      target="galaxy_history">here</a> to immediately remove it from disk.' );
        
HistoryItemView.TEMPLATES.hiddenMsg = _.template(
    'This dataset has been hidden. ' + 
    'Click <a href="<%= unhide_url %>" class="historyItemUnhide" id="historyItemUnhider-{{ id }}" ' +
    '         target="galaxy_history">here</a> to unhide it.' );

//TODO: contains localized strings
HistoryItemView.TEMPLATES.hdaSummary = _.template([
    '<%= misc_blurb %><br />',
    'format: <span class="<%= data_type %>"><%= data_type %></span>, ',
    'database: <%= dbkeyHTML %>'
].join( '' ));

    
//------------------------------------------------------------------------------
HistoryItemView.STRINGS = {};

HistoryItemView.STRINGS.purgedMsg = HistoryItemView.TEMPLATES.warningMsg(
    { warning: 'This dataset has been deleted and removed from disk.' });


//==============================================================================
var HistoryCollection = Backbone.Collection.extend({
    model           : HistoryItem,
    
    toString        : function(){
         return ( 'HistoryCollection()' );
    }
});


//==============================================================================
var History = LoggingModel.extend({
    
    // uncomment this out see log messages
    logger              : console,

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
var HistoryView = LoggingView.extend({
    // view for the HistoryCollection (as per current right hand panel)
    
    // uncomment this out see log messages
    logger              : console,

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
//USE_MOCK_DATA = true;
if( window.USE_MOCK_DATA ){
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
                      { state : HistoryItem.STATES.ERROR }),
        discarded :
            _.extend( _.clone( mockHistory.data.template ),
                      { state : HistoryItem.STATES.DISCARDED }),
        setting_metadata :
            _.extend( _.clone( mockHistory.data.template ),
                      { state : HistoryItem.STATES.SETTING_METADATA }),
        failed_metadata :
            _.extend( _.clone( mockHistory.data.template ),
                      { state : HistoryItem.STATES.FAILED_METADATA })
        
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

