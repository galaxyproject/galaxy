//define([
//    "../mvc/base-mvc"
//], function(){
/* =============================================================================
Backbone.js implementation of history panel

TODO:
    replication:
        show_deleted/hidden:
            use storage
            on/off ui
                need urls
                change template
        move histview fadein/out in render to app?
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
/** @class View/Controller for the history model as used in the history
 *      panel (current right hand panel).
 *  @name HistoryPanel
 *
 *  @augments BaseView
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HistoryPanel = BaseView.extend( LoggableMixin ).extend(
/** @lends HistoryPanel.prototype */{
    
    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,

    // direct attachment to existing element
    el                  : 'body.historyPage',
    /** which class to use for constructing the HDA views */
    //HDAView             : HDABaseView,
    HDAView             : HDAEditView,

    /** event map
     */
    events : {
        'click #history-tag'            : 'loadAndDisplayTags',
        'click #message-container'      : 'removeMessage'
    },

    // ......................................................................... SET UP
    /** Set up the view, set up storage, bind listeners to HDACollection events
     *  @param {Object} attributes
     *  @config {Object} urlTemplates.history nested object containing url templates for this view
     *  @config {Object} urlTemplates.hda nested object containing url templates for HDAViews
     *  @throws 'needs urlTemplates' if urlTemplates.history or urlTemplates.hda aren't present
     *  @see PersistantStorage
     *  @see Backbone.View#initialize
     */
    initialize : function( attributes ){
        // set the logger if requested
        if( attributes.logger ){ this.logger = this.model.logger = attributes.logger; }
        this.log( this + '.initialize:', attributes );

        // set up url templates
        //TODO: prob. better to put this in class scope (as the handlebars templates), but...
        //  they're added to GalaxyPaths on page load (after this file is loaded)
        if( !attributes.urlTemplates ){         throw( this + ' needs urlTemplates on initialize' ); }
        if( !attributes.urlTemplates.history ){ throw( this + ' needs urlTemplates.history on initialize' ); }
        if( !attributes.urlTemplates.hda ){     throw( this + ' needs urlTemplates.hda on initialize' ); }
        this.urlTemplates = attributes.urlTemplates.history;
        /** map web controller urls for history related actions */
        this.hdaUrlTemplates = attributes.urlTemplates.hda;

        this._setUpWebStorage( attributes.initiallyExpanded, attributes.show_deleted, attributes.show_hidden );

        this._setUpEventHandlers();

        // set up instance vars
        /** map of hda model ids to hda views */
        this.hdaViews = {};
        /** map web controller urls for history related actions */
        this.urls = {};
    },

    _setUpEventHandlers : function(){
        // ---- model
        // don't need to re-render entire model on all changes, just render disk size when it changes
        //this.model.bind( 'change', this.render, this );
        this.model.bind( 'change:nice_size', this.updateHistoryDiskSize, this );

        // don't need to re-render entire model on all changes, just render disk size when it changes
        this.model.bind( 'error', function( msg, xhr, error, status ){
            this.displayMessage( 'error', msg );
            this.model.attributes.error = undefined;
        }, this );

        // ---- hdas
        // bind events from the model's hda collection
        this.model.hdas.bind( 'add',   this.add,    this );
        this.model.hdas.bind( 'reset', this.addAll, this );

        // when a hda model is (un)deleted or (un)hidden, re-render entirely
        //TODO??: purged
        //TODO??: could be more selective here
        this.model.hdas.bind( 'change:deleted', this.handleHdaDeletionChange, this );

        // if an a hidden hda is created (gen. by a workflow), moves thru the updater to the ready state,
        //  then: remove it from the collection if the panel is set to NOT show hidden datasets
        this.model.hdas.bind( 'state:ready', function( hda, newState, oldState ){
            if( ( !hda.get( 'visible' ) )
            &&  ( !this.storage.get( 'show_hidden' ) ) ){
                this.removeHdaView( hda.get( 'id' ) );
            }
        }, this );

        // ---- self
        this.bind( 'error', function( msg, xhr, error, status ){
            this.displayMessage( 'error', msg );
        });

        if( this.logger ){
            this.bind( 'all', function( event ){
                this.log( this + '', arguments );
            }, this );
        }
    },

    /** Set up client side storage. Currently PersistanStorage keyed under 'HistoryPanel.<id>'
     *  @param {Object} initiallyExpanded
     *  @param {Boolean} show_deleted whether to show deleted HDAs (overrides stored)
     *  @param {Boolean} show_hidden
     *  @see PersistantStorage
     */
    _setUpWebStorage : function( initiallyExpanded, show_deleted, show_hidden ){
        //this.log( '_setUpWebStorage, initiallyExpanded:', initiallyExpanded,
        //    'show_deleted:', show_deleted, 'show_hidden', show_hidden );

        // data that needs to be persistant over page refreshes
        //  (note the key function which uses the history id as well)
        this.storage = new PersistantStorage( 'HistoryView.' + this.model.get( 'id' ), {
            //TODOL initiallyExpanded only works on first load right now
            expandedHdas : {},
            show_deleted : false,
            show_hidden  : false
        });
        this.log( this + ' (prev) storage:', JSON.stringify( this.storage.get(), null, 2 ) );

        // expanded Hdas is a map of hda.ids -> a boolean rep'ing whether this hda's body is expanded
        // store any pre-expanded ids passed in
        if( initiallyExpanded ){
            this.storage.set( 'exandedHdas', initiallyExpanded );
        }

        // get the show_deleted/hidden settings giving priority to values passed in,
        //  using web storage otherwise
        // if the page has specifically requested show_deleted/hidden, these will be either true or false
        //  (as opposed to undefined, null) - and we give priority to that setting
        if( ( show_deleted === true ) || ( show_deleted === false ) ){
            // save them to web storage
            this.storage.set( 'show_deleted', show_deleted );
        }
        if( ( show_hidden === true ) || ( show_hidden === false ) ){
            this.storage.set( 'show_hidden', show_hidden );
        }
        // if the page hasn't specified whether to show_deleted/hidden, pull show_deleted/hidden from the web storage
        this.show_deleted = this.storage.get( 'show_deleted' );
        this.show_hidden  = this.storage.get( 'show_hidden' );
        //this.log( 'this.show_deleted:', this.show_deleted, 'show_hidden', this.show_hidden );
        this.log( this + ' (init\'d) storage:', this.storage.get() );
    },

    /** Add an hda to this history's collection
     *  @param {HistoryDatasetAssociation} hda hda to add to the collection
     */
    add : function( hda ){
        //this.log( 'add.' + this, hda );
        //KISS: just re-render the entire thing when adding
        this.render();
    },

    /** Event hander to respond when hdas are reset
     */
    addAll : function(){
        //this.log( 'addAll.' + this );
        // re render when all hdas are reset
        this.render();
    },

    /** If this hda is deleted and we're not showing deleted hdas, remove the view
     *  @param {HistoryDataAssociation} the hda to check
     */
    handleHdaDeletionChange : function( hda ){
        if( hda.get( 'deleted' ) && !this.storage.get( 'show_deleted' ) ){
            this.removeHdaView( hda.get( 'id' ) );
        } // otherwise, the hdaView rendering should handle it
    },

    /** Remove a view from the panel and if the panel is now empty, re-render
     *  @param {Int} the id of the hdaView to remove
     */
    removeHdaView : function( id, callback ){
        var hdaView = this.hdaViews[ id ];
        if( !hdaView ){ return; }

        hdaView.remove( callback );
        delete this.hdaViews[ id ];
        if( _.isEmpty( this.hdaViews ) ){
            this.render();
        }
    },

    // ......................................................................... RENDERING
    /** Render urls, historyPanel body, and hdas (if any are shown)
     *  @see Backbone.View#render
     */
    /** event rendered triggered when the panel rendering is complete */
    /** event rendered:initial triggered when the FIRST panel rendering is complete */
    render : function(){
        var historyView = this,
            setUpQueueName = historyView.toString() + '.set-up',
            newRender = $( '<div/>' ),
            modelJson = this.model.toJSON(),
            initialRender = ( this.$el.children().size() === 0 );

        // render the urls and add them to the model json
        modelJson.urls = this._renderUrls( modelJson );

        // render the main template, tooltips
        //NOTE: this is done before the items, since item views should handle theirs themselves
        newRender.append( HistoryPanel.templates.historyPanel( modelJson ) );
        newRender.find( '.tooltip' ).tooltip({ placement: 'bottom' });

        // render hda views (if any and any shown (show_deleted/hidden)
        //TODO: this seems too elaborate
        if( !this.model.hdas.length
        ||  !this.renderItems( newRender.find( '#' + this.model.get( 'id' ) + '-datasets' ) ) ){
            // if history is empty or no hdas would be rendered, show the empty message
            newRender.find( '#emptyHistoryMessage' ).show();
        }

        // fade out existing, swap with the new, fade in, set up behaviours
        $( historyView ).queue( setUpQueueName, function( next ){
            historyView.$el.fadeOut( 'fast', function(){ next(); });
            //historyView.$el.show( function(){ next(); });
        });
        $( historyView ).queue( setUpQueueName, function( next ){
            // swap over from temp div newRender
            historyView.$el.html( '' );
            historyView.$el.append( newRender.children() );

            historyView.$el.fadeIn( 'fast', function(){ next(); });
            //historyView.$el.show( function(){ next(); });
        });
        $( historyView ).queue( setUpQueueName, function( next ){
            this.log( historyView + ' rendered:', historyView.$el );

            //TODO: ideally, these would be set up before the fade in (can't because of async save text)
            historyView._setUpBehaviours();
            
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

    /** Render the urls for this view using urlTemplates and the model data
     *  @param {Object} modelJson data from the model used to fill templates
     */
    _renderUrls : function( modelJson ){
        var historyView = this;

        historyView.urls = {};
        _.each( this.urlTemplates, function( urlTemplate, urlKey ){
            historyView.urls[ urlKey ] = _.template( urlTemplate, modelJson );
        });
        return historyView.urls;
    },

    /** Set up/render a view for each HDA to be shown, init with model and listeners.
     *      HDA views are cached to the map this.hdaViews (using the model.id as key).
     *  @param {jQuery} $whereTo what dom element to prepend the HDA views to
     *  @returns the number of visible hda views
     */
    renderItems : function( $whereTo ){
        this.hdaViews = {};
        var historyView = this,
            // only render the shown hdas
            //TODO: switch to more general filtered pattern
            visibleHdas  = this.model.hdas.getVisible(
                this.storage.get( 'show_deleted' ),
                this.storage.get( 'show_hidden' )
            );

        _.each( visibleHdas, function( hda ){
            var hdaId = hda.get( 'id' ),
                expanded = historyView.storage.get( 'expandedHdas' ).get( hdaId );

            historyView.hdaViews[ hdaId ] = new historyView.HDAView({
                    model           : hda,
                    expanded        : expanded,
                    urlTemplates    : historyView.hdaUrlTemplates,
                    logger          : historyView.logger
                });
            historyView._setUpHdaListeners( historyView.hdaViews[ hdaId ] );

            // render it (NOTE: reverse order, newest on top (prepend))
            //TODO: by default send a reverse order list (although this may be more efficient - it's more confusing)
            $whereTo.prepend( historyView.hdaViews[ hdaId ].render().$el );
        });
        return visibleHdas.length;
    },

    /** Set up HistoryPanel listeners for HDAView events. Currently binds:
     *      HDAView#body-visible, HDAView#body-hidden to store expanded states
     *  @param {HDAView} hdaView HDAView (base or edit) to listen to
     */
    _setUpHdaListeners : function( hdaView ){
        var historyView = this;
        // maintain a list of hdas whose bodies are expanded
        hdaView.bind( 'body-expanded', function( id ){
            historyView.storage.get( 'expandedHdas' ).set( id, true );
        });
        hdaView.bind( 'body-collapsed', function( id ){
            historyView.storage.get( 'expandedHdas' ).deleteKey( id );
        });
        hdaView.bind( 'error', function( msg, xhr, status, error ){
            historyView.displayMessage( 'error', msg );
        });
    },

    /** Set up HistoryPanel js/widget behaviours
     */
    //TODO: these should be either sub-MVs, or handled by events
    _setUpBehaviours : function(){
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

    // ......................................................................... EVENTS
    /** Update the history size display (curr. upper right of panel).
     */
    updateHistoryDiskSize : function(){
        this.$el.find( '#history-size' ).text( this.model.get( 'nice_size' ) );
    },
    
    /** Show the over quota message (which happens to be in the history panel).
     */
    //TODO: this seems more like a per user message than a history message; IOW, this doesn't belong here
    showQuotaMessage : function(){
        var msg = this.$el.find( '#quota-message-container' );
        //this.log( this + ' showing quota message:', msg, userData );
        if( msg.is( ':hidden' ) ){ msg.slideDown( 'fast' ); }
    },

    /** Hide the over quota message (which happens to be in the history panel).
     */
    //TODO: this seems more like a per user message than a history message
    hideQuotaMessage : function(){
        var msg = this.$el.find( '#quota-message-container' );
        //this.log( this + ' hiding quota message:', msg, userData );
        if( !msg.is( ':hidden' ) ){ msg.slideUp( 'fast' ); }
    },

    /** Handle the user toggling the deleted visibility by:
     *      (1) storing the new value in the persistant storage
     *      (2) re-rendering the history
     * @returns {Boolean} new show_deleted setting
     */
    toggleShowDeleted : function(){
        this.storage.set( 'show_deleted', !this.storage.get( 'show_deleted' ) );
        this.render();
        return this.storage.get( 'show_deleted' );
    },

    /** Handle the user toggling the deleted visibility by:
     *      (1) storing the new value in the persistant storage
     *      (2) re-rendering the history
     * @returns {Boolean} new show_hidden setting
     */
    toggleShowHidden : function(){
        this.storage.set( 'show_hidden', !this.storage.get( 'show_hidden' ) );
        this.render();
        return this.storage.get( 'show_hidden' );
    },

    /** Collapse all hda bodies and clear expandedHdas in the storage
     */
    collapseAllHdaBodies : function(){
        _.each( this.hdaViews, function( item ){
            item.toggleBodyVisibility( null, false );
        });
        this.storage.set( 'expandedHdas', {} );
    },

    /** Find the tag area and, if initial: load the html (via ajax) for displaying them; otherwise, unhide/hide
     */
    //TODO: into sub-MV
    loadAndDisplayTags : function( event ){
        this.log( this + '.loadAndDisplayTags', event );
        var panel = this,
            tagArea = this.$el.find( '#history-tag-area' ),
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
                    error: function( xhr, error, status ) {
                        panel.log( 'Error loading tag area html', xhr, error, status );
                        panel.trigger( 'error', _l( "Tagging failed" ), xhr, error, status );
                    },
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

    /** display a message in the top of the panel
     *  @param {String} type    type of message ('done', 'error', 'warning')
     *  @param {String} msg     the message to display
     */
    displayMessage : function( type, msg ){
        var $msgContainer = this.$el.find( '#message-container' ),
            $msg = $( '<div/>' ).addClass( type + 'message' ).text( msg );
        $msgContainer.html( $msg );
    },

    /** Remove a message from the panel
     */
    removeMessage : function(){
        var $msgContainer = this.$el.find( '#message-container' );
        $msgContainer.html( null );
    },

    // ......................................................................... MISC
    /** Return a string rep of the history
     */
    toString    : function(){
        var nameString = this.model.get( 'name' ) || '';
        return 'HistoryPanel(' + nameString + ')';
    }
});

//------------------------------------------------------------------------------ TEMPLATES
HistoryPanel.templates = {
    historyPanel : Handlebars.templates[ 'template-history-historyPanel' ]
};

//==============================================================================
//return {
//    HistoryPanel     : HistoryPanel
//};});
