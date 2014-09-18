define([
    "mvc/list/list-item",
    "mvc/base-mvc",
    "utils/localization"
], function( LIST_ITEM, BASE_MVC, _l ){
/* ============================================================================
TODO:

============================================================================ */
/** @class View for a list/collection of models and the sub-views of those models.
 *      Sub-views must (at least have the interface if not) inherit from ListItemView.
 *      (For a list panel that also includes some 'container' model (History->HistoryContents)
 *      use ModelWithListPanel)
 *
 *  Allows for:
 *      searching collection/sub-views
 *      selecting/multi-selecting sub-views
 *
 *  Currently used:
 *      for dataset/dataset-choice
 *      as superclass of ModelListPanel
 */
var ListPanel = Backbone.View.extend( BASE_MVC.LoggableMixin ).extend(
/** @lends ReadOnlyHistoryPanel.prototype */{

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    /** class to use for constructing the sub-views */
    viewClass           : LIST_ITEM.ListItemView,
    /** class to used for constructing collection of sub-view models */
    collectionClass     : Backbone.Collection,

    tagName             : 'div',
    className           : 'list-panel',

    /** (in ms) that jquery effects will use */
    fxSpeed             : 'fast',

    /** string to display when the collection has no contents */
    emptyMsg            : _l( 'This list is empty' ),
    /** displayed when no items match the search terms */
    noneFoundMsg        : _l( 'No matching items found' ),
    /** string used for search placeholder */
    searchPlaceholder   : _l( 'search' ),

    /** actions available for multiselected items */
    multiselectActions  : [],

    // ......................................................................... SET UP
    /** Set up the view, set up storage, bind listeners to HistoryContents events
     *  @param {Object} attributes optional settings for the list
     */
    initialize : function( attributes, options ){
        attributes = attributes || {};
        // set the logger if requested
        if( attributes.logger ){
            this.logger = attributes.logger;
        }
        this.log( this + '.initialize:', attributes );

        // ---- instance vars
        /** how quickly should jquery fx run? */
        this.fxSpeed = _.has( attributes, 'fxSpeed' )?( attributes.fxSpeed ):( this.fxSpeed );

        /** filters for displaying subviews */
        this.filters = [];
        /** current search terms */
        this.searchFor = attributes.searchFor || '';

        /** loading indicator */
        this.indicator = new LoadingIndicator( this.$el );

        /** currently showing selectors on items? */
        this.selecting = ( attributes.selecting !== undefined )? attributes.selecting : true;
        //this.selecting = false;

        /** cached selected item.model.ids to persist btwn renders */
        this.selected = attributes.selected || [];
        /** the last selected item.model.id */
        this.lastSelected = null;

        /** list item view class (when passed models) */
        this.viewClass = attributes.viewClass || this.viewClass;

        /** list item views */
        this.views = [];
        /** list item models */
        this.collection = attributes.collection || ( new this.collectionClass([]) );

        /** filter fns run over collection items to see if they should show in the list */
        this.filters = attributes.filters || [];

        /** override $scrollContainer fn via attributes - fn should return jq for elem to call scrollTo on */
        this.$scrollContainer = attributes.$scrollContainer || this.$scrollContainer;

//TODO: remove
        this.title = attributes.title || '';
        this.subtitle = attributes.subtitle || '';

        // allow override of multiselectActions through attributes
        this.multiselectActions = attributes.multiselectActions || this.multiselectActions;
        /** the popup displayed when 'for all selected...' is clicked */
        this.actionsPopup = null;

        this._setUpListeners();
    },

    /** free any sub-views the list has */
    freeViews : function(){
//TODO: stopListening? remove?
        _.each( this.views, function( view ){
            view.off();
        });
        this.views = [];
        return this;
    },

    // ------------------------------------------------------------------------ listeners
    /** create any event listeners for the list
     */
    _setUpListeners : function(){
        this.off();

        this.on( 'error', function( model, xhr, options, msg, details ){
            //this.errorHandler( model, xhr, options, msg, details );
            console.error( model, xhr, options, msg, details );
        }, this );

        // show hide the loading indicator
        this.on( 'loading', function(){
            this._showLoadingIndicator( 'loading...', 40 );
        }, this );
        this.on( 'loading-done', function(){
            this._hideLoadingIndicator( 40 );
        }, this );

        // throw the first render up as a diff namespace using once (for outside consumption)
        this.once( 'rendered', function(){
            this.trigger( 'rendered:initial', this );
        }, this );

        // debugging
        if( this.logger ){
            this.on( 'all', function( event ){
                this.log( this + '', arguments );
            }, this );
        }

        this._setUpCollectionListeners();
        this._setUpViewListeners();
        return this;
    },

    /** listening for collection events */
    _setUpCollectionListeners : function(){
        this.log( this + '._setUpCollectionListeners', this.collection );
        this.collection.off();

        // bubble up error events
        this.collection.on( 'error', function( model, xhr, options, msg, details ){
            this.trigger( 'error', model, xhr, options, msg, details );
        }, this );

        this.collection.on( 'reset', function(){
            this.renderItems();
        }, this );
        this.collection.on( 'add', this.addItemView, this );
        this.collection.on( 'remove', this.removeItemView, this );

        // debugging
        if( this.logger ){
            this.collection.on( 'all', function( event ){
                this.info( this + '(collection)', arguments );
            }, this );
        }
        return this;
    },

    /** listening for sub-view events that bubble up with the 'view:' prefix */
    _setUpViewListeners : function(){
        this.log( this + '._setUpViewListeners' );

        // shift to select a range
        this.on( 'view:selected', function( view, ev ){
            if( ev && ev.shiftKey && this.lastSelected ){
                var lastSelectedView = this.viewFromModelId( this.lastSelected );
                if( lastSelectedView ){
                    this.selectRange( view, lastSelectedView );
                }
            }
            this.selected.push( view.model.id );
            this.lastSelected = view.model.id;
        }, this );

        this.on( 'view:de-selected', function( view, ev ){
            this.selected = _.without( this.selected, view.model.id );
            //this.lastSelected = view.model.id;
        }, this );
    },

    // ------------------------------------------------------------------------ rendering
    /** Render this content, set up ui.
     *  @param {Number or String} speed   the speed of the render
     */
    render : function( speed ){
        this.log( this + '.render', speed );
        var $newRender = this._buildNewRender();
        this._setUpBehaviors( $newRender );
        this._queueNewRender( $newRender, speed );
        return this;
    },

    /** Build a temp div containing the new children for the view's $el.
     */
    _buildNewRender : function(){
        this.debug( this + '(ListPanel)._buildNewRender' );
        var $newRender = $( this.templates.el( {}, this ) );
        this._renderControls( $newRender );
        this._renderTitle( $newRender );
        this._renderSubtitle( $newRender );
        this._renderSearch( $newRender );
        this.renderItems( $newRender );
        return $newRender;
    },

    /** Build a temp div containing the new children for the view's $el.
     */
    _renderControls : function( $newRender ){
        this.debug( this + '(ListPanel)._renderControls' );
        var $controls = $( this.templates.controls( {}, this ) );
        $newRender.find( '.controls' ).replaceWith( $controls );
        return $controls;
    },

    /**
     */
    _renderTitle : function( $where ){
        //$where = $where || this.$el;
        //$where.find( '.title' ).replaceWith( ... )
    },

    /**
     */
    _renderSubtitle : function( $where ){
        //$where = $where || this.$el;
        //$where.find( '.title' ).replaceWith( ... )
    },

    /** Fade out the old el, swap in the new contents, then fade in.
     *  @param {Number or String} speed   jq speed to use for rendering effects
     *  @fires rendered when rendered
     */
    _queueNewRender : function( $newRender, speed ) {
        speed = ( speed === undefined )?( this.fxSpeed ):( speed );
        var panel = this;
        panel.log( '_queueNewRender:', $newRender, speed );

        $( panel ).queue( 'fx', [
            function( next ){ this.$el.fadeOut( speed, next ); },
            function( next ){
                panel._swapNewRender( $newRender );
                next();
            },
            function( next ){ this.$el.fadeIn( speed, next ); },
            function( next ){
                panel.trigger( 'rendered', panel );
                next();
            }
        ]);
    },

    /** empty out the current el, move the $newRender's children in */
    _swapNewRender : function( $newRender ){
        this.$el.empty().attr( 'class', this.className ).append( $newRender.children() );
        if( this.selecting ){ this.showSelectors( 0 ); }
        return this;
    },

    /**  */
    _setUpBehaviors : function( $where ){
        $where = $where || this.$el;
        $where.find( '.controls [title]' ).tooltip({ placement: 'bottom' });
        return this;
    },

    // ------------------------------------------------------------------------ sub-$element shortcuts
    /** the scroll container for this panel - can be $el, $el.parent(), or grandparent depending on context */
    $scrollContainer : function(){
        // override or set via attributes.$scrollContainer
        return this.$el.parent().parent();
    },
    /**  */
    $list : function( $where ){
        return ( $where || this.$el ).find( '> .list-items' );
    },
    /** container where list messages are attached */
    $messages : function( $where ){
        return ( $where || this.$el ).find( '> .controls .messages' );
    },
    /** the message displayed when no views can be shown (no views, none matching search) */
    $emptyMessage : function( $where ){
        return ( $where || this.$el ).find( '> .empty-message' );
    },

    // ------------------------------------------------------------------------ hda sub-views
    /**
     *  @param {jQuery} $whereTo what dom element to prepend the sub-views to
     *  @returns the visible item views
     */
    renderItems : function( $whereTo ){
        $whereTo = $whereTo || this.$el;
        var panel = this;
        panel.log( this + '.renderItems', $whereTo );

        var $list = panel.$list( $whereTo );
//TODO: free prev. views?
        panel.views = panel._filterCollection().map( function( itemModel ){
//TODO: creates views each time - not neccessarily good
                return panel._createItemView( itemModel ).render( 0 );
            });
        //panel.debug( item$els );
        //panel.debug( newViews );

        $list.empty();
        if( panel.views.length ){
            panel._attachItems( $whereTo );
            panel.$emptyMessage( $whereTo ).hide();
            
        } else {
            panel._renderEmptyMessage( $whereTo ).show();
        }
        
        return panel.views;
    },

    /** Filter the collection to only those models that should be currently viewed */
    _filterCollection : function(){
        // override this
        var panel = this;
        return panel.collection.filter( _.bind( panel._filterItem, panel ) );
    },

    /** Should the model be viewable in the current state?
     *     Checks against this.filters and this.searchFor
     */
    _filterItem : function( model ){
        // override this
        var panel = this;
        return ( _.every( panel.filters.map( function( fn ){ return fn.call( model ); }) ) )
            && ( !panel.searchFor || model.matchesAll( panel.searchFor ) );
    },

    /** Create a view for a model and set up it's listeners */
    _createItemView : function( model ){
        var ViewClass = this._getItemViewClass( model ),
            options = _.extend( this._getItemViewOptions( model ), {
                    model : model
                }),
            view = new ViewClass( options );
        this._setUpItemViewListeners( view );
        return view;
    },

    /** Get the bbone view class based on the model */
    _getItemViewClass : function( model ){
        // override this
        return this.viewClass;
    },

    /** Get the options passed to the new view based on the model */
    _getItemViewOptions : function( model ){
        // override this
        return {
            //logger      : this.logger,
            fxSpeed     : this.fxSpeed,
            expanded    : false,
            selectable  : this.selecting,
            selected    : _.contains( this.selected, model.id ),
            draggable   : this.dragging
        };
    },

    /** Set up listeners for new models */
    _setUpItemViewListeners : function( view ){
        var panel = this;
        // send all events to the panel, re-namspaceing them with the view prefix
        view.on( 'all', function(){
            var args = Array.prototype.slice.call( arguments, 0 );
            args[0] = 'view:' + args[0];
            panel.trigger.apply( panel, args );
        });

        // debugging
        //if( this.logger ){
        //    view.on( 'all', function( event ){
        //        this.log( this + '(view)', arguments );
        //    }, this );
        //}
        return panel;
    },

    /** Attach views in this.views to the model based on $whereTo */
    _attachItems : function( $whereTo ){
        this.$list( $whereTo ).append( this.views.map( function( view ){
            return view.$el;
        }));
        return this;
    },

    /** render the empty/none-found message */
    _renderEmptyMessage : function( $whereTo ){
        this.debug( '_renderEmptyMessage', $whereTo, this.searchFor );
        var text = this.searchFor? this.noneFoundMsg : this.emptyMsg;
        return this.$emptyMessage( $whereTo ).text( text );
    },

    /** collapse all item views */
    expandAll : function(){
        _.each( this.views, function( view ){
            view.expand();
        });
    },

    /** collapse all item views */
    collapseAll : function(){
        _.each( this.views, function( view ){
            view.collapse();
        });
    },

    // ------------------------------------------------------------------------ collection/views syncing
    /** Add a view (if the model should be viewable) to the panel */
    addItemView : function( model, collection, options ){
        this.log( this + '.addItemView:', model );
        var panel = this;
        if( !panel._filterItem( model ) ){ return undefined; }

//TODO: sorted? position?
        var view = panel._createItemView( model );
        panel.views.push( view );

        // hide the empty message if only view
        $( view ).queue( 'fx', [
            function( next ){ panel.$emptyMessage().fadeOut( panel.fxSpeed, next ); },
            function( next ){
//TODO: auto render?
// slide down?
                panel.$list().append( view.render().$el );
                next();
            }
        ]);
        return view;
    },

    /** Remove a view from the panel (if found) */
    removeItemView : function( model, collection, options ){
        this.log( this + '.removeItemView:', model );
        var panel = this,
            view = panel.viewFromModel( model );
        if( !view ){ return undefined; }

        // potentially show the empty message if no views left
        // use anonymous queue here - since remove can happen multiple times
        $({}).queue( 'fx', [
            function( next ){ view.$el.fadeOut( panel.fxSpeed, next ); },
            function( next ){
                panel.views = _.without( panel.views, view );
                view.remove();
                if( !panel.views.length ){
                    panel._renderEmptyMessage().fadeIn( panel.fxSpeed, next );
                } else {
                    next();
                }
            }
        ]);
        return view;
    },

    /** get views based on model.id */
    viewFromModelId : function( id ){
        for( var i=0; i<this.views.length; i++ ){
            if( this.views[i].model.id === id ){
                return this.views[i];
            }
        }
        return undefined;
    },

    /** get views based on model */
    viewFromModel : function( model ){
        return this.viewFromModelId( model.id );
    },

    /** get views based on model properties */
    viewsWhereModel : function( properties ){
        return this.views.filter( function( view ){
            //return view.model.matches( properties );
//TODO: replace with _.matches (underscore 1.6.0)
            var json = view.model.toJSON();
            //console.debug( '\t', json, properties );
            for( var key in properties ){
                if( properties.hasOwnProperty( key ) ){
                    //console.debug( '\t\t', json[ key ], view.model.properties[ key ] );
                    if( json[ key ] !== view.model.get( key ) ){
                        return false;
                    }
                }
            }
            return true;
        });
    },

    /** A range of views between (and including) viewA and viewB */
    viewRange : function( viewA, viewB ){
        if( viewA === viewB ){ return ( viewA )?( [ viewA ] ):( [] ); }

        var indexA = this.views.indexOf( viewA ),
            indexB = this.views.indexOf( viewB );

        // handle not found
        if( indexA === -1 || indexB === -1 ){
            if( indexA === indexB ){ return []; }
            return ( indexA === -1 )?( [ viewB ] ):( [ viewA ] );
        }
        // reverse if indeces are
        //note: end inclusive
        return ( indexA < indexB )?
            this.views.slice( indexA, indexB + 1 ) :
            this.views.slice( indexB, indexA + 1 );
    },

    // ------------------------------------------------------------------------ searching
    /** render a search input for filtering datasets shown
     *      (see SearchableMixin in base-mvc for implementation of the actual searching)
     *      return will start the search
     *      esc will clear the search
     *      clicking the clear button will clear the search
     *      uses searchInput in ui.js
     */
    _renderSearch : function( $where ){
        $where.find( '.controls .search-input' ).searchInput({
            placeholder     : this.searchPlaceholder,
            initialVal      : this.searchFor,
            onfirstsearch   : _.bind( this._firstSearch, this ),
            onsearch        : _.bind( this.searchItems, this ),
            onclear         : _.bind( this.clearSearch, this )
        });
        return $where;
    },

    /** What to do on the first search entered */
    _firstSearch : function( searchFor ){
        // override to load model details if necc.
        this.log( 'onFirstSearch', searchFor );
        return this.searchItems( searchFor );
    },

    /** filter view list to those that contain the searchFor terms */
    searchItems : function( searchFor ){
        this.searchFor = searchFor;
        this.trigger( 'search:searching', searchFor, this );
        this.renderItems();
        return this;
    },

    /** clear the search filters and show all views that are normally shown */
    clearSearch : function( searchFor ){
        //this.log( 'onSearchClear', this );
        this.searchFor = '';
        this.trigger( 'search:clear', this );
        this.renderItems();
        return this;
    },

    // ------------------------------------------------------------------------ selection
    /** show selectors on all visible itemViews and associated controls */
    showSelectors : function( speed ){
        speed = ( speed !== undefined )?( speed ):( this.fxSpeed );
        this.selecting = true;
        this.$( '.list-actions' ).slideDown( speed );
        _.each( this.views, function( view ){
            view.showSelector( speed );
        });
        //this.selected = [];
        //this.lastSelected = null;
    },

    /** hide selectors on all visible itemViews and associated controls */
    hideSelectors : function( speed ){
        speed = ( speed !== undefined )?( speed ):( this.fxSpeed );
        this.selecting = false;
        this.$( '.list-actions' ).slideUp( speed );
        _.each( this.views, function( view ){
            view.hideSelector( speed );
        });
        this.selected = [];
        this.lastSelected = null;
    },

    /** show or hide selectors on all visible itemViews and associated controls */
    toggleSelectors : function(){
        if( !this.selecting ){
            this.showSelectors();
        } else {
            this.hideSelectors();
        }
    },

    /** select all visible items */
    selectAll : function( event ){
        _.each( this.views, function( view ){
            view.select( event );
        });
    },

    /** deselect all visible items */
    deselectAll : function( event ){
        this.lastSelected = null;
        _.each( this.views, function( view ){
            view.deselect( event );
        });
    },

    /** select a range of datasets between A and B */
    selectRange : function( viewA, viewB ){
        var range = this.viewRange( viewA, viewB );
        _.each( range, function( view ){
            view.select();
        });
        return range;
    },

    /** return an array of all currently selected itemViews */
    getSelectedViews : function(){
        return _.filter( this.views, function( v ){
            return v.selected;
        });
    },

    /** return a collection of the models of all currenly selected items */
    getSelectedModels : function(){
        return new this.collection.constructor( _.map( this.getSelectedViews(), function( view ){
            return view.model;
        }));
    },

    // ------------------------------------------------------------------------ loading indicator
//TODO: questionable
    /** hide the $el and display a loading indicator (in the $el's parent) when loading new data */
    _showLoadingIndicator : function( msg, speed, callback ){
        this.debug( '_showLoadingIndicator', this.indicator, msg, speed, callback );
        speed = ( speed !== undefined )?( speed ):( this.fxSpeed );
        if( !this.indicator ){
            this.indicator = new LoadingIndicator( this.$el, this.$el.parent() );
            this.debug( '\t created', this.indicator );
        }
        if( !this.$el.is( ':visible' ) ){
            this.indicator.show( 0, callback );
        } else {
            this.$el.fadeOut( speed );
            this.indicator.show( msg, speed, callback );
        }
    },

    /** hide the loading indicator */
    _hideLoadingIndicator : function( speed, callback ){
        this.debug( '_hideLoadingIndicator', this.indicator, speed, callback );
        speed = ( speed !== undefined )?( speed ):( this.fxSpeed );
        if( this.indicator ){
            this.indicator.hide( speed, callback );
        }
    },

    // ------------------------------------------------------------------------ scrolling
    /** get the current scroll position of the panel in its parent */
    scrollPosition : function(){
        return this.$scrollContainer().scrollTop();
    },

    /** set the current scroll position of the panel in its parent */
    scrollTo : function( pos, speed ){
        speed = speed || 0;
        this.$scrollContainer().animate({ scrollTop: pos }, speed );
        return this;
    },

    /** Scrolls the panel to the top. */
    scrollToTop : function( speed ){
        return this.scrollTo( 0, speed );
    },

    /**  */
    scrollToItem : function( view, speed ){
        if( !view ){ return this; }
        //var itemTop = view.$el.offset().top;
        var itemTop = view.$el.position().top;
        return this.scrollTo( itemTop, speed );
    },

    /** Scrolls the panel to show the content with the given id. */
    scrollToId : function( id, speed ){
        return this.scrollToItem( this.viewFromModelId( id ), speed );
    },

    // ------------------------------------------------------------------------ panel events
    /** event map */
    events : {
        'click .select-all'     : 'selectAll',
        'click .deselect-all'   : 'deselectAll'
    },

    // ------------------------------------------------------------------------ misc
    /** Return a string rep of the panel */
    toString : function(){
        return 'ListPanel(' + this.collection + ')';
    }
});

// ............................................................................ TEMPLATES
/** underscore templates */
ListPanel.prototype.templates = (function(){
//TODO: move to require text! plugin

    var elTemplate = BASE_MVC.wrapTemplate([
        // temp container
        '<div>',
            '<div class="controls"></div>',
            '<div class="list-items"></div>',
            '<div class="empty-message infomessagesmall"></div>',
        '</div>'
    ]);

    var controlsTemplate = BASE_MVC.wrapTemplate([
        '<div class="controls">',
            '<div class="title">',
                '<div class="name"><%= view.title %></div>',
            '</div>',
            '<div class="subtitle"><%= view.subtitle %></div>',
            // buttons, controls go here
            '<div class="actions"></div>',
            // deleted msg, etc.
            '<div class="messages"></div>',

            '<div class="search">',
                '<div class="search-input"></div>',
            '</div>',

            // show when selectors are shown
            '<div class="list-actions">',
                '<div class="btn-group">',
                    '<button class="select-all btn btn-default"',
                            'data-mode="select">', _l( 'All' ), '</button>',
                    '<button class="deselect-all btn btn-default"',
                            'data-mode="select">', _l( 'None' ), '</button>',
                '</div>',
                //'<button class="list-action-popup-btn btn btn-default">',
                //    _l( 'For all selected' ), '...',
                //'</button>',
            '</div>',
        '</div>'
    ]);

    return {
        el          : elTemplate,
        controls    : controlsTemplate
    };
}());


//=============================================================================
/** View for a model that has a sub-collection (e.g. History, DatasetCollection)
 *  Allows:
 *      the model to be reset
 *      auto assign panel.collection to panel.model[ panel.modelCollectionKey ]
 *
 */
var ModelListPanel = ListPanel.extend({

    /** key of attribute in model to assign to this.collection */
    modelCollectionKey : 'contents',

    initialize : function( attributes ){
        ListPanel.prototype.initialize.call( this, attributes );
        this.selecting = ( attributes.selecting !== undefined )? attributes.selecting : false;

        this.setModel( this.model, attributes );
    },

    /** release/free/shutdown old models and set up panel for new models
     *  @fires new-model with the panel as parameter
     */
    setModel : function( model, attributes ){
        attributes = attributes || {};
        this.debug( this + '.setModel:', model, attributes );

        this.freeModel();
        this.freeViews();

        if( model ){
            // set up the new model with user, logger, storage, events
            this.model = model;
            if( this.logger ){
                this.model.logger = this.logger;
            }
            this._setUpModelListeners();

//TODO: relation btwn model, collection becoming tangled here
            // free the collection, and assign the new collection to either
            //  the model[ modelCollectionKey ], attributes.collection, or an empty vanilla collection
            this.collection.off();
            this.collection = ( this.model[ this.modelCollectionKey ] )?
                this.model[ this.modelCollectionKey ]:
                ( attributes.collection || ( new this.collectionClass([]) ) );
            this._setUpCollectionListeners();

            this.trigger( 'new-model', this );
        }
        return this;
    },

    /** free the current model and all listeners for it, free any views for the model */
    freeModel : function(){
        // stop/release the previous model, and clear cache to sub-views
        if( this.model ){
            this.stopListening( this.model );
            //TODO: see base-mvc
            //this.model.free();
            //this.model = null;
        }
        return this;
    },

    // ------------------------------------------------------------------------ listening
    /** listening for model events */
    _setUpModelListeners : function(){
        // override
        this.log( this + '._setUpModelListeners', this.model );
        // bounce model errors up to the panel
        this.model.on( 'error', function(){
            //TODO: namespace?
            //var args = Array.prototype.slice.call( arguments, 0 );
            //args[0] = 'model:' + args[0];
            this.trigger.apply( panel, arguments );
        }, this );
        return this;
    },

    /** Build a temp div containing the new children for the view's $el.
     */
    _renderControls : function( $newRender ){
        this.debug( this + '(ListPanel)._renderControls' );
        var json = this.model? this.model.toJSON() : {},
            $controls = $( this.templates.controls( json, this ) );
        $newRender.find( '.controls' ).replaceWith( $controls );
        return $controls;
    },

    // ------------------------------------------------------------------------ misc
    /** Return a string rep of the panel */
    toString : function(){
        return 'ModelListPanel(' + this.model + ')';
    }
});

// ............................................................................ TEMPLATES
/** underscore templates */
ModelListPanel.prototype.templates = (function(){
//TODO: move to require text! plugin

    var controlsTemplate = BASE_MVC.wrapTemplate([
        '<div class="controls">',
            '<div class="title">',
//TODO: this is really the only difference - consider factoring titlebar out
                '<div class="name"><%= model.name %></div>',
            '</div>',
            '<div class="subtitle"><%= view.subtitle %></div>',
            '<div class="actions"></div>',
            '<div class="messages"></div>',

            '<div class="search">',
                '<div class="search-input"></div>',
            '</div>',

            '<div class="list-actions">',
                '<div class="btn-group">',
                    '<button class="select-all btn btn-default"',
                            'data-mode="select">', _l( 'All' ), '</button>',
                    '<button class="deselect-all btn btn-default"',
                            'data-mode="select">', _l( 'None' ), '</button>',
                '</div>',
                //'<button class="list-action-popup-btn btn btn-default">',
                //    _l( 'For all selected' ), '...',
                //'</button>',
            '</div>',
        '</div>'
    ]);

    return _.extend( _.clone( ListPanel.prototype.templates ), {
        controls : controlsTemplate
    });
}());


//=============================================================================
    return {
        ListPanel      : ListPanel,
        ModelListPanel : ModelListPanel
    };
});
