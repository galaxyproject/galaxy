define([
    "mvc/collection/dataset-collection-base",
    "mvc/base-mvc",
    "utils/localization"
], function( DC_BASE, BASE_MVC, _l ){
/* =============================================================================
TODO:

============================================================================= */
// =============================================================================
/** @class non-editable, read-only View/Controller for a dataset collection.
 *  @name CollectionPanel
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var CollectionPanel = Backbone.View.extend( BASE_MVC.LoggableMixin ).extend(
/** @lends CollectionPanel.prototype */{
    //MODEL is either a DatasetCollection (or subclass) or a DatasetCollectionElement (list of pairs)

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    tagName             : 'div',
    className           : 'dataset-collection-panel',

    /** (in ms) that jquery effects will use */
    fxSpeed             : 'fast',

    DatasetDCEViewClass : DC_BASE.DatasetDCEBaseView,
    NestedDCEViewClass  : DC_BASE.NestedDCEBaseView,

    // ......................................................................... SET UP
    /** Set up the view, set up storage, bind listeners to HistoryContents events
     *  @param {Object} attributes optional settings for the panel
     */
    initialize : function( attributes ){
        attributes = attributes || {};
        // set the logger if requested
        if( attributes.logger ){
            this.logger = attributes.logger;
        }
        this.log( this + '.initialize:', attributes );

        this.hasUser = attributes.hasUser;
        this.panelStack = [];
        this.parentName = attributes.parentName;
    },

    /** create any event listeners for the panel
     *  @fires: rendered:initial    on the first render
     *  @fires: empty-history       when switching to a history with no HDAs or creating a new history
     */
    _setUpListeners : function(){
        // debugging
        //if( this.logger ){
            this.on( 'all', function( event ){
                this.log( this + '', arguments );
            }, this );
        //}
        return this;
    },

    // ------------------------------------------------------------------------ history/hda event listening
    /** listening for history and HDA events */
    _setUpModelEventHandlers : function(){
        return this;
    },

    // ------------------------------------------------------------------------ panel rendering
    /** Render urls, historyPanel body, and hdas (if any are shown)
     *  @fires: rendered    when the panel is attached and fully visible
     *  @see Backbone.View#render
     */
    render : function( speed, callback ){
        this.log( 'render:', speed, callback );
        // send a speed of 0 to have no fade in/out performed
        speed = ( speed === undefined )?( this.fxSpeed ):( speed );
        //this.debug( this + '.render, fxSpeed:', speed );
        var panel = this,
            $newRender;

        // handle the possibility of no model (can occur if fetching the model returns an error)
        if( !this.model ){
            return this;
        }
        $newRender = this.renderModel();

        // fade out existing, swap with the new, fade in, set up behaviours
        $( panel ).queue( 'fx', [
            function( next ){
                if( speed && panel.$el.is( ':visible' ) ){
                    panel.$el.fadeOut( speed, next );
                } else {
                    next();
                }
            },
            function( next ){
                // swap over from temp div newRender
                panel.$el.empty();
                if( $newRender ){
                    panel.$el.append( $newRender.children() );
                }
                next();
            },
            function( next ){
                if( speed && !panel.$el.is( ':visible' ) ){
                    panel.$el.fadeIn( speed, next );
                } else {
                    next();
                }
            },
            function( next ){
                //TODO: ideally, these would be set up before the fade in (can't because of async save text)
                if( callback ){ callback.call( this ); }
                panel.trigger( 'rendered', this );
                next();
            }
        ]);
        return this;
    },

    /** render with history data
     *  @returns {jQuery} dom fragment as temporary container to be swapped out later
     */
    renderModel : function( ){
        // tmp div for final swap in render
//TODO: ugh - reuse issue - refactor out
        var type = this.model.get( 'collection_type' ) || this.model.object.get( 'collection_type' ),
            json = _.extend( this.model.toJSON(), {
                parentName  : this.parentName,
                type        : type
            }),
            $newRender = $( '<div/>' ).append( this.templates.panel( json ) );
        this._setUpBehaviours( $newRender );
        this.renderContents( $newRender );
        return $newRender;
    },

    /** Set up HistoryPanel js/widget behaviours */
    _setUpBehaviours : function( $where ){
        //TODO: these should be either sub-MVs, or handled by events
        $where = $where || this.$el;
        $where.find( '[title]' ).tooltip({ placement: 'bottom' });
        return this;
    },

    // ------------------------------------------------------------------------ sub-$element shortcuts
    /** the scroll container for this panel - can be $el, $el.parent(), or grandparent depending on context */
    $container : function(){
        return ( this.findContainerFn )?( this.findContainerFn.call( this ) ):( this.$el.parent() );
    },
    /** where hdaViews are attached */
    $datasetsList : function( $where ){
        return ( $where || this.$el ).find( '.datasets-list' );
    },

    // ------------------------------------------------------------------------ sub-views
    /** Set up/render a view for each HDA to be shown, init with model and listeners.
     *      HDA views are cached to the map this.hdaViews (using the model.id as key).
     *  @param {jQuery} $whereTo what dom element to prepend the HDA views to
     *  @returns the number of visible hda views
     */
    renderContents : function( $whereTo ){
        //this.debug( 'renderContents, elements:', this.model.elements );
        $whereTo = $whereTo || this.$el;

        this.warn( this + '.renderContents:, model:', this.model );
        var panel = this,
            contentViews = {},
            //NOTE: no filtering here
            visibleContents = this.model.getVisibleContents();
        this.log( 'renderContents, visibleContents:', visibleContents, $whereTo );

        this.$datasetsList( $whereTo ).empty();
        if( visibleContents && visibleContents.length ){
            visibleContents.each( function( content ){
                var contentId = content.id,
                    contentView = panel._createContentView( content );
                contentViews[ contentId ] = contentView;
                panel._attachContentView( contentView.render(), $whereTo );
            });
        }
        this.contentViews = contentViews;
        return this.contentViews;
    },

    /**  */
    _createContentView : function( content ){
        //this.debug( 'content json:', JSON.stringify( content, null, '  ' ) );
        var contentView = null,
            ContentClass = this._getContentClass( content );
        this.debug( 'ContentClass:', ContentClass );
        this.debug( 'content:', content );
        contentView = new ContentClass({
            model           : content,
            linkTarget      : this.linkTarget,
            //draggable       : true,
            hasUser         : this.hasUser,
            logger          : this.logger
        });
        this.debug( 'contentView:', contentView );
        this._setUpContentListeners( contentView );
        return contentView;
    },

    /**  */
    _getContentClass : function( content ){
        this.debug( this + '._getContentClass:', content );
        this.debug( 'DCEViewClass:', this.DCEViewClass );
        switch( content.get( 'element_type' ) ){
            case 'hda':
                return this.DCEViewClass;
            case 'dataset_collection':
                return this.DCEViewClass;
        }
        throw new TypeError( 'Unknown element type:', content.get( 'element_type' ) );
    },

    /** Set up listeners for content view events. In this override, handle collection expansion. */
    _setUpContentListeners : function( contentView ){
        var panel = this;
        if( contentView.model.get( 'element_type' ) === 'dataset_collection' ){
            contentView.on( 'expanded', function( collectionView ){
                panel.info( 'expanded', collectionView );
                panel._addCollectionPanel( collectionView );
            });
        }
    },

    /**  */
    _addCollectionPanel : function( collectionView ){
        var currPanel = this,
            collectionModel = collectionView.model;

        this.debug( 'collection panel (stack), collectionView:', collectionView );
        this.debug( 'collection panel (stack), collectionModel:', collectionModel );
        var panel = new PairCollectionPanel({
                model       : collectionModel,
                parentName  : this.model.get( 'name' )
            });
        currPanel.panelStack.push( panel );

        currPanel.$( '.controls' ).add( '.datasets-list' ).hide();
        currPanel.$el.append( panel.$el );
        panel.on( 'close', function(){
            currPanel.render();
            collectionView.collapse();
            currPanel.panelStack.pop();
        });

        //TODO: to hdca-model, hasDetails
        if( !panel.model.hasDetails() ){
            var xhr = panel.model.fetch();
            xhr.done( function(){
                //TODO: (re-)render collection contents
                panel.render();
            });
        } else {
            panel.render();
        }
    },

    /** attach an contentView to the panel */
    _attachContentView : function( contentView, $whereTo ){
        $whereTo = $whereTo || this.$el;
        var $datasetsList = this.$datasetsList( $whereTo );
        $datasetsList.append( contentView.$el );
        return this;
    },

    // ------------------------------------------------------------------------ panel events
    /** event map */
    events : {
        'click .navigation .back'       : 'close'
    },

    /**  */
    close : function( event ){
        this.$el.remove();
        this.trigger( 'close' );
    },

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'CollectionPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});

//----------------------------------------------------------------------------- TEMPLATES
/** underscore templates */
CollectionPanel.templates = CollectionPanel.prototype.templates = (function(){
// use closure to run underscore template fn only once at module load
    var _panelTemplate = _.template([
        '<div class="controls">',
            '<div class="navigation">',
                '<a class="back" href="javascript:void(0)">',
                    '<span class="fa fa-icon fa-angle-left"></span>',
                    _l( 'Back to ' ), '<%- collection.parentName %>',
                '</a>',
            '</div>',

            '<div class="title">',
                '<div class="name"><%- collection.name || collection.element_identifier %></div>',
                '<div class="subtitle">',
//TODO: remove logic from template
                    '<% if( collection.type === "list" ){ %>',
                        _l( 'a list of datasets' ),
                    '<% } else if( collection.type === "paired" ){ %>',
                        _l( 'a pair of datasets' ),
                    '<% } else if( collection.type === "list:paired" ){ %>',
                        _l( 'a list of paired datasets' ),
                    '<% } %>',
                '</div>',
            '</div>',
        '</div>',
        // where the datasets/hdas are added
        '<div class="datasets-list"></div>'
    ].join( '' ));

    // we override here in order to pass the localizer (_L) into the template scope - since we use it as a fn within
    return {
        panel : function( json ){
            return _panelTemplate({ _l: _l, collection: json });
        }
    };
}());


// =============================================================================
/** @class non-editable, read-only View/Controller for a dataset collection. */
var ListCollectionPanel = CollectionPanel.extend({

    DCEViewClass        : DC_BASE.DatasetDCEBaseView,

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'ListCollectionPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


// =============================================================================
/** @class non-editable, read-only View/Controller for a dataset collection. */
var PairCollectionPanel = ListCollectionPanel.extend({

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'PairCollectionPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


// =============================================================================
/** @class non-editable, read-only View/Controller for a dataset collection. */
var ListOfPairsCollectionPanel = CollectionPanel.extend({

    DCEViewClass        : DC_BASE.NestedDCDCEBaseView,

    // ........................................................................ misc
    /** string rep */
    toString    : function(){
        return 'ListOfPairsCollectionPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


//==============================================================================
    return {
        CollectionPanel             : CollectionPanel,
        ListCollectionPanel         : ListCollectionPanel,
        PairCollectionPanel         : PairCollectionPanel,
        ListOfPairsCollectionPanel  : ListOfPairsCollectionPanel
    };
});
