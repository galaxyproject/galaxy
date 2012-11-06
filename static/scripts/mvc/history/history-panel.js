//define([
//    "../mvc/base-mvc"
//], function(){
/* =============================================================================
Backbone.js implementation of history panel

TODO:
    anon user, mako template init:
        bug: rename url seems to be wrong url

    logged in, mako template:
        BUG: meter is not updating RELIABLY on change:nice_size
        BUG: am able to start upload even if over quota - 'runs' forever
        bug: quotaMeter bar rendering square in chrome
        BUG: quotaMsg not showing when 100% (on load)
        BUG: imported, shared history with unaccessible dataset errs in historycontents when getting history
            (entire history is inaccessible)
            ??: still happening?

    from loadFromApi:
        BUG: not showing previous annotations

    fixed:
        BUG: upload, history size, doesn't change
            FIXED: using change:nice_size to trigger re-render of history size
        BUG: delete uploading hda - now in state 'discarded'! ...new state to handle
            FIXED: handled state
        BUG: historyItem, error'd ds show display, download?
            FIXED: removed
        bug: loading hdas (alt_hist)
            FIXED: added anon user api request ( trans.user == None and trans.history.id == requested id )
        bug: quota meter not updating on upload/tool run
            FIXED: quotaMeter now listens for 'state:ready' from glx_history in alternate_history.mako
        bug: use of new HDACollection with event listener in init doesn't die...keeps reporting
            FIXED: change getVisible to return an array
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

    replication:
        show_deleted/hidden:
            use storage
            on/off ui
        move histview fadein/out in render to app?
        don't draw body until it's first expand event
        localize all
        ?: render url templates on init or render?
        ?: history, annotation won't accept unicode

    RESTful:
        move over webui functions available in api
            delete, undelete
            update?
        currently, adding a dataset (via tool execute, etc.) creates a new dataset and refreshes the page
            provide a means to update the panel via js

    hierarchy:
        to relational model?
            HDACollection, meta_files, display_apps, etc.
        dataset -> hda
        history -> historyForEditing, historyForViewing
        display_structured?

    meta:
        css/html class/id 'item' -> hda
        add classes, ids on empty divs
        events (local/ui and otherwise)
            list in docs as well
        require.js
        convert function comments to jsDoc style, complete comments
        move inline styles into base.less
        watch the magic strings
        watch your globals
    
    feature creep:
        lineage
        hide button
        show permissions in info
        show shared/sharing status on ds, history
        maintain scroll position on refresh (storage?)
        selection, multi-select (and actions common to selected (ugh))
        searching
        sorting, re-shuffling
    
============================================================================= */
/** view for the HDACollection (as per current right hand panel)
 *
 */
var HistoryPanel = BaseView.extend( LoggableMixin ).extend({
    
    // uncomment this out see log messages
    //logger              : console,

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

        // bind events from the model's hda collection
        //this.model.bind( 'change', this.render, this );
        this.model.bind( 'change:nice_size', this.updateHistoryDiskSize, this );

        this.model.hdas.bind( 'add',   this.add,    this );
        this.model.hdas.bind( 'reset', this.addAll, this );
        this.model.hdas.bind( 'all',   this.all,    this );

        //this.bind( 'all', function(){
        //    this.log( arguments );
        //}, this );

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
            modelJson = this.model.toJSON(),
            initialRender = ( this.$el.children().size() === 0 );

        //console.debug( this + '.render, initialRender:', initialRender );

        // render the urls and add them to the model json
        modelJson.urls = this.renderUrls( modelJson );

        // render the main template, tooltips
        //NOTE: this is done before the items, since item views should handle theirs themselves
        newRender.append( HistoryPanel.templates.historyPanel( modelJson ) );
        newRender.find( '.tooltip' ).tooltip();

        // render hda views (if any and any shown (show_deleted/hidden)
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
            
            if( initialRender ){
                historyView.trigger( 'rendered:initial' );

            } else {
                historyView.trigger( 'rendered' );
            }
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
        _.each( visibleHdas, function( hda ){
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
        var historyView = this;

        // use storage to maintain a list of hdas whose bodies are expanded
        hdaView.bind( 'toggleBodyVisibility', function( id, visible ){
            if( visible ){
                historyView.storage.get( 'expandedHdas' ).set( id, true );
            } else {
                historyView.storage.get( 'expandedHdas' ).deleteKey( id );
            }
        });

        // rendering listeners
        hdaView.bind( 'rendered:ready', function(){ historyView.trigger( 'hda:rendered:ready' ); });
    },

    // set up js/widget behaviours: tooltips,
    //TODO: these should be either sub-MVs, or handled by events
    setUpBehaviours : function(){
        // anon users shouldn't have access to any of these
        if( !( this.model.get( 'user' ) && this.model.get( 'user' ).email ) ){ return; }

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

    // update the history size display (curr. upper right of panel)
    updateHistoryDiskSize : function(){
        this.$el.find( '#history-size' ).text( this.model.get( 'nice_size' ) );
    },
    
    //TODO: this seems more like a per user message than a history message; IOW, this doesn't belong here
    showQuotaMessage : function( userData ){
        var msg = this.$el.find( '#quota-message-container' );
        //this.log( this + ' showing quota message:', msg, userData );
        if( msg.is( ':hidden' ) ){ msg.slideDown( 'fast' ); }
    },

    //TODO: this seems more like a per user message than a history message
    hideQuotaMessage : function( userData ){
        var msg = this.$el.find( '#quota-message-container' );
        //this.log( this + ' hiding quota message:', msg, userData );
        if( !msg.is( ':hidden' ) ){ msg.slideUp( 'fast' ); }
    },

    events : {
        'click #history-collapse-all'   : 'hideAllHdaBodies',
        'click #history-tag'            : 'loadAndDisplayTags'
    },

    // collapse all hda bodies
    hideAllHdaBodies : function(){
        _.each( this.hdaViews, function( item ){
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

//------------------------------------------------------------------------------
HistoryPanel.templates = {
    historyPanel : Handlebars.templates[ 'template-history-historyPanel' ]
};

//==============================================================================
//return {
//    HistoryPanel     : HistoryPanel
//};});
