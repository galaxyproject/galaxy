define([
    "mvc/base-mvc",
    "utils/localization"
], function( BASE_MVC, _l ){
/* =============================================================================
TODO:

============================================================================= */
/** @class  List that contains ListItemViews.
 */
var ListPanel = Backbone.View.extend( BASE_MVC.LoggableMixin ).extend(
/** @lends ReadOnlyHistoryPanel.prototype */{

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    /** class to use for constructing the sub-views */
    viewClass           : BASE_MVC.ListItemView,

    tagName             : 'div',
    className           : 'list-panel',

    /** (in ms) that jquery effects will use */
    fxSpeed             : 'fast',

    /** string to display when the model has no hdas */
    emptyMsg            : _l( 'This list is empty' ),
    /** string to no hdas match the search terms */
    noneFoundMsg        : _l( 'No matching items found' ),

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
        this.collection = attributes.collection || ( new Backbone.Collection([]) );

        /** filter fns run over collection items to see if they should show in the list */
        this.filters = attributes.filters || [];

//TODO: remove
        this.title = attributes.title || '';
        this.subtitle = attributes.subtitle || '';

        this._setUpListeners();
    },

    /** create any event listeners for the list
     */
    _setUpListeners : function(){
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

    /** free any sub-views the list has */
    freeViews : function(){
//TODO: stopListening? remove?
        this.views = [];
        return this;
    },

    // ------------------------------------------------------------------------ item listeners
    /** listening for history and HDA events */
    _setUpCollectionListeners : function(){

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

    /** listening for history and HDA events */
    _setUpViewListeners : function(){

        // shift to select a range
        this.on( 'view:selected', function( view, ev ){
            if( ev && ev.shiftKey && this.lastSelected ){
                var lastSelectedView = _.find( this.views, function( view ){
                    return view.model.id === this.lastSelected;
                });
                if( lastSelectedView ){
                    this.selectRange( view, lastSelectedView );
                }
            }
            this.selected.push( view.model.id );
            this.lastSelected = view.model.id;
        }, this );
    },

    // ------------------------------------------------------------------------ rendering
    /** Render this content, set up ui.
     *  @param {Number or String} speed   the speed of the render
     */
    render : function( speed ){
        var $newRender = this._buildNewRender();
        this._setUpBehaviors( $newRender );
        this._queueNewRender( $newRender, speed );
        return this;
    },

    /** Build a temp div containing the new children for the view's $el.
     */
    _buildNewRender : function(){
        // create a new render using a skeleton template, render title buttons, render body, and set up events, etc.
        var json = this.model? this.model.toJSON() : {},
            $newRender = $( this.templates.el( json, this ) );
        this._renderTitle( $newRender );
        this._renderSubtitle( $newRender );
        this._renderSearch( $newRender );
        this.renderItems( $newRender );
        return $newRender;
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
        var view = this;

        $( view ).queue( 'fx', [
            function( next ){ this.$el.fadeOut( speed, next ); },
            function( next ){
                view._swapNewRender( $newRender );
                next();
            },
            function( next ){ this.$el.fadeIn( speed, next ); },
            function( next ){
                view.trigger( 'rendered', view );
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
        // override
        return this.$el.parent().parent();
    },
    /**  */
    $list : function( $where ){
        return ( $where || this.$el ).find( '.list-items' );
    },
    /** container where list messages are attached */
    $messages     : function( $where ){
        return ( $where || this.$el ).find( '.message-container' );
    },
    /** the message displayed when no views can be shown (no views, none matching search) */
    $emptyMessage : function( $where ){
        return ( $where || this.$el ).find( '.empty-message' );
    },

    // ------------------------------------------------------------------------ hda sub-views
    /**
     *  @param {jQuery} $whereTo what dom element to prepend the HDA views to
     *  @returns the visible item views
     */
    renderItems : function( $whereTo ){
        $whereTo = $whereTo || this.$el;
        var list = this,
            newViews = [];

        var $list = this.$list( $whereTo ),
            item$els = this._filterCollection().map( function( itemModel ){
//TODO: creates views each time - not neccessarily good
                var view = list._createItemView( itemModel );
                newViews.push( view );
                return view.render( 0 ).$el;
            });
        this.debug( item$els );
        this.debug( newViews );

        $list.empty();
        if( item$els.length ){
            $list.append( item$els );
            this.$emptyMessage( $whereTo ).hide();
            
        } else {
            this._renderEmptyMessage( $whereTo ).show();
        }
        
        this.views = newViews;
        return newViews;
    },

    /**
     */
    _filterCollection : function(){
        // override this
        var list = this;
        return list.collection.filter( _.bind( list._filterItem, list ) );
    },

    /**
     */
    _filterItem : function( model ){
        // override this
        var list = this;
        return ( _.every( list.filters.map( function( fn ){ return fn.call( model ); }) ) )
            && ( !list.searchFor || model.matchesAll( list.searchFor ) );
    },

    /**
     */
    _createItemView : function( model ){
        var ViewClass = this._getItemViewClass( model ),
            options = _.extend( this._getItemViewOptions( model ), {
                    model : model
                }),
            view = new ViewClass( options );
        this._setUpItemViewListeners( view );
        return view;
    },

    _getItemViewClass : function( model ){
        // override this
        return this.viewClass;
    },

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

    /**
     */
    _setUpItemViewListeners : function( view ){
        var list = this;
        view.on( 'all', function(){
            var args = Array.prototype.slice.call( arguments, 0 );
            args[0] = 'view:' + args[0];
            list.trigger.apply( list, args );
        });

        // debugging
        //if( this.logger ){
        //    view.on( 'all', function( event ){
        //        this.log( this + '(view)', arguments );
        //    }, this );
        //}
        return this;
    },

    /** render the empty/none-found message */
    _renderEmptyMessage : function( $whereTo ){
        //this.debug( '_renderEmptyMessage', $whereTo, this.searchFor );
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
    /**
     */
    addItemView : function( model, collection, options ){
        this.log( this + '.addItemView:', model );
        var list = this;
        if( !this._filterItem( model ) ){ return undefined; }

//TODO: sorted? position?
        var view = list._createItemView( model );
        this.views.push( view );

        $( view ).queue( 'fx', [
            function( next ){ list.$emptyMessage().fadeOut( list.fxSpeed, next ); },
            function( next ){
//TODO: auto render?
                list.$list().append( view.render().$el );
                next();
            }
        ]);
        return view;
    },

    /**
     */
    removeItemView : function( model, collection, options ){
        this.log( this + '.removeItemView:', model );
        var list = this,
            view = list.viewFromModel( model );
        if( !view ){ return undefined; }

        this.views = _.without( this.views, view );
        view.remove();
        if( !this.views.length ){
            list._renderEmptyMessage().fadeIn( list.fxSpeed );
        }
        return view;
    },

    /** get views based on model
     */
    viewFromModel : function( model ){
        for( var i=0; i<this.views.length; i++ ){
            var view = this.views[i];
            if( view.model === model ){
                return view;
            }
        }
        return undefined;
    },

    /** get views based on model properties
     */
    viewsWhereModel : function( properties ){
        return this.views.filter( function( view ){
            //return view.model.matches( properties );
//TODO: replace with _.matches (underscore 1.6.0)
            var json = view.model.toJSON();
            //console.debug( '\t', json, properties );
            for( var key in properties ){
                if( properties.hasOwnPropery( key ) ){
                    //console.debug( '\t\t', json[ key ], view.model.properties[ key ] );
                    if( json[ key ] !== view.model.properties[ key ] ){
                        return false;
                    }
                }
            }
            return true;
        });
    },

    /**
     */
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
     *      (see the search section in the HDA model for implementation of the actual searching)
     *      return will start the search
     *      esc will clear the search
     *      clicking the clear button will clear the search
     *      uses searchInput in ui.js
     */
    _renderSearch : function( $where ){
        $where.find( '.controls .search-input' ).searchInput({
            placeholder     : 'search',
            initialVal      : this.searchFor,
            onfirstsearch   : _.bind( this._firstSearch, this ),
            onsearch        : _.bind( this.searchItems, this ),
            onclear         : _.bind( this.clearSearch, this )
        });
        return $where;
    },

    _firstSearch : function( searchFor ){
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
    /** show selectors on all visible hdas and associated controls */
    showSelectors : function( speed ){
        speed = ( speed !== undefined )?( speed ):( this.fxSpeed );
        this.selecting = true;
        this.$( '.list-actions' ).slideDown( speed );
        _.each( this.views, function( view ){
            view.showSelector( speed );
        });
        this.selected = [];
        this.lastSelected = null;
    },

    /** hide selectors on all visible hdas and associated controls */
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

    /** show or hide selectors on all visible hdas and associated controls */
    toggleSelectors : function(){
        if( !this.selecting ){
            this.showSelectors();
        } else {
            this.hideSelectors();
        }
    },

    /** select all visible hdas */
    selectAll : function( event ){
        _.each( this.views, function( view ){
            view.select( event );
        });
    },

    /** deselect all visible hdas */
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

    /** return an array of all currently selected hdas */
    getSelectedViews : function(){
        return _.filter( this.views, function( v ){
            return v.selected;
        });
    },

    /** return an collection of the models of all currenly selected hdas */
    getSelectedModels : function(){
        return new this.collection.constructor( _.map( this.getSelectedViews(), function( view ){
            return view.model;
        }));
    },

    // ------------------------------------------------------------------------ loading indicator
//TODO: questionable
    /** hide the $el and display a loading indicator (in the $el's parent) when loading new data */
    _showLoadingIndicator : function( msg, speed, callback ){
        speed = ( speed !== undefined )?( speed ):( this.fxSpeed );
        if( !this.indicator ){
            this.indicator = new LoadingIndicator( this.$el, this.$el.parent() );
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
    scrollTo : function( pos ){
        this.$scrollContainer().scrollTop( pos );
        return this;
    },

    /** Scrolls the panel to the top. */
    scrollToTop : function(){
        this.$scrollContainer().scrollTop( 0 );
        return this;
    },

    /**  */
    scrollToItem : function( view ){
        if( !view ){ return; }
        var itemTop = view.$el.offset().top;
        this.$scrollContainer().scrollTop( itemTop );
    },

    // ------------------------------------------------------------------------ panel events
    /** event map */
    events : {
        'click .select-all'     : 'selectAll',
        'click .deselect-all'   : 'deselectAll'
    },

    // ------------------------------------------------------------------------ misc
    /** Return a string rep of the history */
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
            '<div class="controls">',
                '<div class="title">',
                    '<div class="name"><%= model.name || view.title %></div>',
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
                    //'<button class="action-popup-btn btn btn-default">',
                    //    _l( 'For all selected' ), '...',
                    //'</button>',
                '</div>',
            '</div>',
            '<div class="list-items"></div>',
            '<div class="empty-message infomessagesmall"></div>',
        '</div>'
    ]);

    return {
        el          : elTemplate
    };
}());



//==============================================================================
    return {
        ListPanel: ListPanel
    };
});
