//define([
//    "../mvc/base-mvc"
//    
//], function(){
/* =============================================================================
Backbone.js implementation of history panel

TODO:
    currently, adding a dataset (via tool execute, etc.) creates a new dataset and refreshes the page
    from mako template:
        BUG: imported, shared history with unaccessible dataset errs in historycontents when getting history
            (entire history is inaccessible)
        BUG: anon user, broken updater (upload)
            added check_state to UsesHistoryDatasetAssocMixin
        BUG: anon user
        BUG: historyItem, error'd ds show display, download?

    from loadFromAPI:
        BUG: not showing previous annotations

    fixed:
        BUG: history, broken intial hist state (running, updater, etc.)
            ??: doesn't seem to happen anymore
        BUG: collapse all should remove all expanded from storage
            FIXED: hideAllItemBodies now resets storage.expandedItems
        BUG: historyItem, shouldn't allow tag, annotate, peek on purged datasets
            FIXED: ok state now shows only: info, rerun
        BUG: history?, some ids aren't returning encoded...
            FIXED:???
        BUG: history, showing deleted ds
            FIXED
        UGH: historyItems have to be decorated with history_ids (api/histories/:history_id/contents/:id)
            FIXED by adding history_id to history_contents.show
        BUG: history, if hist has err'd ds, hist has perm state 'error', updater on following ds's doesn't run
            FIXED by reordering history state from ds' states here and histories
        BUG: history, broken annotation on reload (can't get thru api (sets fine, tho))
            FIXED: get thru api for now

    to relational model?
        HDACollection, meta_files, display_apps, etc.

    
    break this file up
    localize all
    ?: render url templates on init or render?
    ?: history, annotation won't accept unicode
    quota mgr
    show_deleted/hidden:
        use storage
        on/off ui
    move histview fadein/out in render to app?
    don't draw body until it's first expand event

    hierarchy:
        dataset -> hda
        history -> historyForEditing, historyForViewing
        display_structured?

    btw: get an error'd ds by running fastqc on fastq (when you don't have it installed)

    meta:
        css/html class/id 'item' -> hda
        add classes, ids on empty divs
        events (local/ui and otherwise)
        require.js
        convert function comments to jsDoc style, complete comments
        move inline styles into base.less
        watch the magic strings
        watch your globals
    
    features:
        lineage
        hide button
        show permissions in info
        show shared/sharing status on ds, history
        maintain scroll position on refresh (storage?)
        selection, multi-select (and actions common to selected (ugh))
        searching
        sorting, re-shuffling
    
============================================================================= */
var HistoryDatasetAssociation = BaseModel.extend( LoggableMixin ).extend({
    // a single HDA model
    
    // uncomment this out see log messages
    //logger              : console,
    
    defaults : {
        // ---these are part of an HDA proper:

        // parent (containing) history
        history_id          : null,
        // often used with tagging
        model_class         : 'HistoryDatasetAssociation',
        // index within history (??)
        hid                 : 0,
        
        // ---whereas these are Dataset related/inherited

        id                  : null, 
        name                : '',
        // one of HistoryDatasetAssociation.STATES
        state               : '',
        // sniffed datatype (sam, tabular, bed, etc.)
        data_type           : null,
        // size in bytes
        file_size           : 0,

        // array of associated file types (eg. [ 'bam_index', ... ])
        meta_files          : [],
        misc_blurb          : '', 
        misc_info           : '',

        deleted             : false, 
        purged              : false,
        // aka. !hidden
        visible             : false,
        // based on trans.user (is_admin or security_agent.can_access_dataset( <user_roles>, hda.dataset ))
        accessible          : false,
        
        // this needs to be removed (it is a function of the view type (e.g. HDAForEditingView))
        for_editing         : true
    },

    // fetch location of this history in the api
    url : function(){
        //TODO: get this via url router
        return 'api/histories/' + this.get( 'history_id' ) + '/contents/' + this.get( 'id' );
    },
    
    // (curr) only handles changing state of non-accessible hdas to STATES.NOT_VIEWABLE
    //TODO: use initialize (or validate) to check purged AND deleted -> purged XOR deleted
    initialize : function(){
        this.log( this + '.initialize', this.attributes );
        this.log( '\tparent history_id: ' + this.get( 'history_id' ) );
        
        //!! this state is not in trans.app.model.Dataset.states - set it here
        if( !this.get( 'accessible' ) ){
            this.set( 'state', HistoryDatasetAssociation.STATES.NOT_VIEWABLE );
        }

        this.on( 'change', function( event, x, y, z ){
            this.log( this + ' has changed:', event, x, y, z );
        });
    },

    isDeletedOrPurged : function(){
        return ( this.get( 'deleted' ) || this.get( 'purged' ) );
    },

    // roughly can_edit from history_common.mako - not deleted or purged = editable
    isEditable : function(){
        return (
            //this.get( 'for_editing' )
            //&& !( this.get( 'deleted' ) || this.get( 'purged' ) )??
            !this.isDeletedOrPurged()
        );
    },

    // based on show_deleted, show_hidden (gen. from the container control), would this ds show in the list of ds's?
    //TODO: too many visibles
    isVisible : function( show_deleted, show_hidden ){
        var isVisible = true;
        if( ( !show_deleted )
        &&  ( this.get( 'deleted' ) || this.get( 'purged' ) ) ){
            isVisible = false;
        }
        if( ( !show_hidden )
        &&  ( !this.get( 'visible' ) ) ){
            isVisible = false;
        }
        return isVisible;
    },
    
    // 'final' states are states where no processing (for the ds) is left to do on the server
    inFinalState : function(){
        return (
            ( this.get( 'state' ) === HistoryDatasetAssociation.STATES.OK )
        ||  ( this.get( 'state' ) === HistoryDatasetAssociation.STATES.FAILED_METADATA )
        ||  ( this.get( 'state' ) === HistoryDatasetAssociation.STATES.EMPTY )
        ||  ( this.get( 'state' ) === HistoryDatasetAssociation.STATES.ERROR )
        );
    },

    // convenience fn to match hda.has_data
    hasData : function(){
        //TODO:?? is this equivalent to all possible hda.has_data calls?
        return ( this.get( 'file_size' ) > 0 );
    },

    toString : function(){
        var nameAndId = this.get( 'id' ) || '';
        if( this.get( 'name' ) ){
            nameAndId += ':"' + this.get( 'name' ) + '"';
        }
        return 'HistoryDatasetAssociation(' + nameAndId + ')';
    }
});

//------------------------------------------------------------------------------
HistoryDatasetAssociation.STATES = {
    NOT_VIEWABLE        : 'noPermission',   // not in trans.app.model.Dataset.states
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
var HDACollection = Backbone.Collection.extend( LoggableMixin ).extend({
    model           : HistoryDatasetAssociation,

    logger          : console,

    // return the ids of every hda in this collection
    ids : function(){
        return this.map( function( item ){ return item.id; });
    },

    // return an HDA collection containing every 'shown' hda based on show_deleted/hidden
    getVisible : function( show_deleted, show_hidden ){
        return new HDACollection(
            this.filter( function( item ){ return item.isVisible( show_deleted, show_hidden ); })
        );
    },

    // get a map where <possible hda state> : [ <list of hda ids in that state> ]
    getStateLists : function(){
        var stateLists = {};
        _.each( _.values( HistoryDatasetAssociation.STATES ), function( state ){
            stateLists[ state ] = [];
        });
        //NOTE: will err on unknown state
        this.each( function( item ){
            stateLists[ item.get( 'state' ) ].push( item.get( 'id' ) );
        });
        return stateLists;
    },

    // update (fetch -> render) the hdas with the ids given
    update : function( ids ){
        this.log( this + 'update:', ids );

        if( !( ids && ids.length ) ){ return; }

        var collection = this;
        _.each( ids, function( id, index ){
            var historyItem = collection.get( id );
            historyItem.fetch();
        });
    },

    toString : function(){
         return ( 'HDACollection(' + this.ids().join(',') + ')' );
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

        //TODO: wire these to items (or this)
        show_deleted     : false,
        show_hidden      : false,

        diskSize : 0,
        deleted : false,

        tags        : [],
        annotation  : null,

        //TODO: quota msg and message? how to get those over the api?
        message     : null,
        quotaMsg    : false
    },

    url : function(){
        // api location of history resource
        //TODO: hardcoded
        return 'api/histories/' + this.get( 'id' );
    },

    initialize : function( initialSettings, initialHdas ){
        this.log( this + ".initialize:", initialSettings, initialHdas );

        this.hdas = new HDACollection();

        // if we've got hdas passed in the constructor, load them and set up updates if needed
        if( initialHdas && initialHdas.length ){
            this.hdas.reset( initialHdas );
            this.checkForUpdates();
        }

        this.on( 'change', function( event, x, y, z ){
            this.log( this + ' has changed:', event, x, y, z );
        });
    },

    // get data via the api (alternative to sending options,hdas to initialize)
    loadFromAPI : function( historyId, callback ){
        var history = this;

        // fetch the history AND the user (mainly to see if they're logged in at this point)
        history.attributes.id = historyId;
        //TODO:?? really? fetch user here?
        jQuery.when( jQuery.ajax( 'api/users/current' ), history.fetch()

            ).then( function( userResponse, historyResponse ){
                //console.warn( 'fetched user, history: ', userResponse, historyResponse );
                history.attributes.user = userResponse[0]; //? meh.
                history.log( history );

            }).then( function(){
                // ...then the hdas (using contents?ids=...)
                jQuery.ajax( history.url() + '/contents?' + jQuery.param({
                    ids : history.itemIdsFromStateIds().join( ',' )

                // reset the collection to the hdas returned
                })).success( function( hdas ){
                    //console.warn( 'fetched hdas' );
                    history.hdas.reset( hdas );
                    history.checkForUpdates();
                    callback();
                });
            });
    },

    // reduce the state_ids map of hda id lists -> a single list of ids
    //...ugh - seems roundabout; necessary because the history doesn't have a straightforward list of ids
    //  (and history_contents/index curr returns a summary only)
    hdaIdsFromStateIds : function(){
        return _.reduce( _.values( this.get( 'state_ids' ) ), function( reduction, currIdList ){
            return reduction.concat( currIdList );
        });
    },

    // get the history's state from it's cummulative ds states, delay + update if needed
    checkForUpdates : function( datasets ){
        // get overall History state from collection, run updater if History has running/queued hdas
        this.stateFromStateIds();
        if( ( this.get( 'state' ) === HistoryDatasetAssociation.STATES.RUNNING )
        ||  ( this.get( 'state' ) === HistoryDatasetAssociation.STATES.QUEUED ) ){
            this.stateUpdater();
        }
        return this;
    },

    // sets history state based on current hdas' states
    //  ported from api/histories.traverse (with placement of error state changed)
    stateFromStateIds : function(){
        var stateIdLists = this.hdas.getStateLists();
        this.attributes.state_ids = stateIdLists;

        //TODO: make this more concise
        if( ( stateIdLists.running.length > 0  )
        ||  ( stateIdLists.upload.length > 0  )
        ||  ( stateIdLists.setting_metadata.length > 0  ) ){
            this.set( 'state', HistoryDatasetAssociation.STATES.RUNNING );

        } else if( stateIdLists.queued.length > 0  ){
            this.set( 'state', HistoryDatasetAssociation.STATES.QUEUED );

        } else if( ( stateIdLists.error.length > 0  )
        ||         ( stateIdLists.failed_metadata.length > 0  ) ){
            this.set( 'state', HistoryDatasetAssociation.STATES.ERROR );

        } else if( stateIdLists.ok.length === this.hdas.length ){
            this.set( 'state', HistoryDatasetAssociation.STATES.OK );

        } else {
            throw( this + '.stateFromStateDetails: unable to determine '
                 + 'history state from hda states: ' + this.get( 'state_ids' ) );
        }
        return this;
    },

    // update this history, find any hda's running/queued, update ONLY those that have changed states,
    //  set up to run this again in some interval of time
    stateUpdater : function(){
        var history = this,
            oldState = this.get( 'state' ),
            // state ids is a map of every possible hda state, each containing a list of ids for hdas in that state
            oldStateIds = this.get( 'state_ids' );

        // pull from the history api
        //TODO: fetch?
        jQuery.ajax( 'api/histories/' + this.get( 'id' )

        ).success( function( response ){
            //this.log( 'historyApiRequest, response:', response );
            history.set( response );
            history.log( 'current history state:', history.get( 'state' ), '(was)', oldState );

            // for each state, check for the difference between old dataset states and new
            //  the goal here is to check ONLY those datasets that have changed states (not all datasets)
            var changedIds = [];
            _.each( _.keys( response.state_ids ), function( state ){
                var diffIds = _.difference( response.state_ids[ state ], oldStateIds[ state ] );
                // aggregate those changed ids
                changedIds = changedIds.concat( diffIds );
            });

            // send the changed ids (if any) to dataset collection to have them fetch their own model changes
            if( changedIds.length ){
                history.hdas.update( changedIds );
            }

            // set up to keep pulling if this history in run/queue state
            //TODO: magic number here
            if( ( history.get( 'state' ) === HistoryDatasetAssociation.STATES.RUNNING )
            ||  ( history.get( 'state' ) === HistoryDatasetAssociation.STATES.QUEUED ) ){
                setTimeout( function(){
                    history.stateUpdater();
                }, 4000 );
            }

        }).error( function( xhr, status, error ){
            if( console && console.warn ){
                console.warn( 'Error getting history updates from the server:', xhr, status, error );
            }
            alert( 'Error getting history updates from the server.\n' + error );
        });
    },

    toString : function(){
        var nameString = ( this.get( 'name' ) )?
            ( ',' + this.get( 'name' ) ) : ( '' );
        return 'History(' + this.get( 'id' ) + nameString + ')';
    }
});

//==============================================================================
var HDAView = BaseView.extend( LoggableMixin ).extend({
    //??TODO: add alias in initialize this.hda = this.model?
    // view for HistoryDatasetAssociation model above

    // uncomment this out see log messages
    logger              : console,

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
            itemWrapper = $( '<div/>' ).attr( 'id', 'historyItem-' + id );

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
                view.trigger( 'rendered' );
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
        // don't show display if not in final state, error'd, or not accessible
        if( ( !this.model.inFinalState() )
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
        &&  this.model.isEditable() ){
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
// view for the HDACollection (as per current right hand panel)
var HistoryView = BaseView.extend( LoggableMixin ).extend({
    
    // uncomment this out see log messages
    logger              : console,

    // direct attachment to existing element
    el                  : 'body.historyPage',

    // init with the model, urlTemplates, set up storage, bind HDACollection events
    //NOTE: this will create or load PersistantStorage keyed under 'HistoryView.<id>'
    //pre: you'll need to pass in the urlTemplates (urlTemplates : { history : {...}, hda : {...} })
    initialize : function( attributes ){
        this.log( this + '.initialize:', attributes );

        // set up url templates
        //TODO: prob. better to put this in class scope (as the handlebars templates), but...
        //  they're added to GalaxyPaths on page load (after this file is loaded)
        if( !attributes.urlTemplates ){         throw( 'HDAView needs urlTemplates on initialize' ); }
        if( !attributes.urlTemplates.history ){ throw( 'HDAView needs urlTemplates.history on initialize' ); }
        if( !attributes.urlTemplates.hda ){     throw( 'HDAView needs urlTemplates.hda on initialize' ); }
        this.urlTemplates = attributes.urlTemplates.history;
        this.hdaUrlTemplates = attributes.urlTemplates.hda;

        // data that needs to be persistant over page refreshes
        //  (note the key function which uses the history id as well)
        this.storage = new PersistantStorage(
            'HistoryView.' + this.model.get( 'id' ),
            { expandedHdas : {} }
        );

        //this.model.bind( 'change', this.render, this );

        // bind events from the model's hda collection
        this.model.hdas.bind( 'add',   this.add,    this );
        this.model.hdas.bind( 'reset', this.addAll, this );
        this.model.hdas.bind( 'all',   this.all,    this );

        // set up instance vars
        this.hdaViews = {};
        this.urls = {};
    },

    add : function( hda ){
        //console.debug( 'add.' + this, hda );
        //TODO
    },

    addAll : function(){
        //console.debug( 'addAll.' + this );
        // re render when all hdas are reset
        this.render();
    },

    all : function( event ){
        //console.debug( 'allItemEvents.' + this, event );
        //...for which to do the debuggings
    },

    // render the urls for this view using urlTemplates and the model data
    renderUrls : function( modelJson ){
        var historyView = this;

        historyView.urls = {};
        _.each( this.urlTemplates, function( urlTemplate, urlKey ){
            historyView.urls[ urlKey ] = _.template( urlTemplate, modelJson );
        });
        return historyView.urls;
    },

    // render urls, historyView body, and hdas (if any are shown), fade out, swap, fade in, set up behaviours
    render : function(){
        var historyView = this,
            setUpQueueName = historyView.toString() + '.set-up',
            newRender = $( '<div/>' ),
            modelJson = this.model.toJSON();

        // render the urls and add them to the model json
        modelJson.urls = this.renderUrls( modelJson );

        // render the main template, tooltips
        //NOTE: this is done before the items, since item views should handle theirs themselves
        newRender.append( HistoryView.templates.historyPanel( modelJson ) );
        historyView.$el.find( '.tooltip' ).tooltip();

        // render hda views (if any)
        if( !this.model.hdas.length
        ||  !this.renderItems( newRender.find( '#' + this.model.get( 'id' ) + '-datasets' ) ) ){
            // if history is empty or no hdas would be rendered, show the empty message
            newRender.find( '#emptyHistoryMessage' ).show();
        }

        // fade out existing, swap with the new, fade in, set up behaviours
        $( historyView ).queue( setUpQueueName, function( next ){
            historyView.$el.fadeOut( 'fast', function(){ next(); });
        });
        $( historyView ).queue( setUpQueueName, function( next ){
            // swap over from temp div newRender
            historyView.$el.html( '' );
            historyView.$el.append( newRender.children() );

            historyView.$el.fadeIn( 'fast', function(){ next(); });
        });
        $( historyView ).queue( setUpQueueName, function( next ){
            this.log( historyView + ' rendered:', historyView.$el );

            //TODO: ideally, these would be set up before the fade in (can't because of async save text)
            historyView.setUpBehaviours();
            historyView.trigger( 'rendered' );
            next();
        });
        $( historyView ).dequeue( setUpQueueName );
        return this;
    },

    // set up a view for each item to be shown, init with model and listeners, cache to map ( model.id : view )
    renderItems : function( $whereTo ){
        this.hdaViews = {};
        var historyView = this,
            show_deleted = this.model.get( 'show_deleted' ),
            show_hidden  = this.model.get( 'show_hidden' ),
            visibleHdas  = this.model.hdas.getVisible( show_deleted, show_hidden );

        // only render the shown hdas
        visibleHdas.each( function( hda ){
            var hdaId = hda.get( 'id' ),
                expanded = historyView.storage.get( 'expandedHdas' ).get( hdaId );
            historyView.hdaViews[ hdaId ] = new HDAView({
                    model           : hda,
                    expanded        : expanded,
                    urlTemplates    : historyView.hdaUrlTemplates
                });
            historyView.setUpHdaListeners( historyView.hdaViews[ hdaId ] );
            // render it (NOTE: reverse order, newest on top (prepend))
            //TODO: by default send a reverse order list (although this may be more efficient - it's more confusing)
            $whereTo.prepend(  historyView.hdaViews[ hdaId ].render().$el );
        });
        return visibleHdas.length;
    },

    // set up HistoryView->HDAView listeners
    setUpHdaListeners : function( hdaView ){
        var history = this;

        // use storage to maintain a list of hdas whose bodies are expanded
        hdaView.bind( 'toggleBodyVisibility', function( id, visible ){
            if( visible ){
                history.storage.get( 'expandedHdas' ).set( id, true );
            } else {
                history.storage.get( 'expandedHdas' ).deleteKey( id );
            }
        });
    },

    // set up js/widget behaviours: tooltips,
    //TODO: these should be either sub-MVs, or handled by events
    setUpBehaviours : function(){
        // annotation slide down
        var historyAnnotationArea = this.$( '#history-annotation-area' );
        this.$( '#history-annotate' ).click( function() {
            if ( historyAnnotationArea.is( ":hidden" ) ) {
                historyAnnotationArea.slideDown( "fast" );
            } else {
                historyAnnotationArea.slideUp( "fast" );
            }
            return false;
        });

        // title and annotation editable text
        //NOTE: these use page scoped selectors - so these need to be in the page DOM before they're applicable
        async_save_text( "history-name-container", "history-name",
            this.urls.rename, "new_name", 18 );

        async_save_text( "history-annotation-container", "history-annotation",
            this.urls.annotate, "new_annotation", 18, true, 4 );
    },
    
    events : {
        'click #history-collapse-all'   : 'hideAllHdaBodies',
        'click #history-tag'            : 'loadAndDisplayTags'
    },

    // collapse all hda bodies
    hideAllHdaBodies : function(){
        _.each( this.itemViews, function( item ){
            item.toggleBodyVisibility( null, false );
        });
        this.storage.set( 'expandedHdas', {} );
    },

    // find the tag area and, if initial: (via ajax) load the html for displaying them; otherwise, unhide/hide
    //TODO: into sub-MV
    loadAndDisplayTags : function( event ){
        this.log( this + '.loadAndDisplayTags', event );
        var tagArea = this.$el.find( '#history-tag-area' ),
            tagElt = tagArea.find( '.tag-elt' );
        this.log( '\t tagArea', tagArea, ' tagElt', tagElt );

        // Show or hide tag area; if showing tag area and it's empty, fill it
        if( tagArea.is( ":hidden" ) ){
            if( !jQuery.trim( tagElt.html() ) ){
                var view = this;
                // Need to fill tag element.
                $.ajax({
                    //TODO: the html from this breaks a couple of times
                    url: view.urls.tag,
                    error: function() { alert( "Tagging failed" ); },
                    success: function(tag_elt_html) {
                        //view.log( view + ' tag elt html (ajax)', tag_elt_html );
                        tagElt.html(tag_elt_html);
                        tagElt.find(".tooltip").tooltip();
                        tagArea.slideDown("fast");
                    }
                });
            } else {
                // Tag element already filled: show
                tagArea.slideDown("fast");
            }

        } else {
            // Currently shown: Hide
            tagArea.slideUp("fast");
        }
        return false;
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
//    HDAView  : HDAView,
//    HistoryCollection : HistoryCollection,
//    History         : History,
//    HistoryView     : HistoryView
//};});
