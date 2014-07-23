define([
    "mvc/collection/dataset-collection-base",
    "mvc/dataset/hda-base",
    "mvc/base-mvc",
    "utils/localization"
], function( DC_BASE, HDA_BASE, BASE_MVC, _l ){
/* =============================================================================
TODO:

============================================================================= */
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

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,

    tagName             : 'div',
    className           : 'history-panel',

    /** (in ms) that jquery effects will use */
    fxSpeed             : 'fast',

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
        this.HDAViewClass = attributes.HDAViewClass || HDA_BASE.HDABaseView;
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
        //console.debug( this + '.render, fxSpeed:', speed );
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
        var $newRender = $( '<div/>' ).append( CollectionPanel.templates.panel( this.model.toJSON() ) );
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
        //console.debug( 'renderContents, elements:', this.model.elements );
        $whereTo = $whereTo || this.$el;

        var panel = this,
            contentViews = {},
            visibleContents = this.model.elements || [];
        //this.log( 'renderContents, visibleContents:', visibleContents, $whereTo );

        this.$datasetsList( $whereTo ).empty();
        if( visibleContents && visibleContents.length ){
            visibleContents.each( function( content ){
                var contentId = content.id,
                    contentView = panel._createContentView( content );
                contentViews[ contentId ] = contentView;
                panel.attachContentView( contentView.render(), $whereTo );
            });
        }
        this.contentViews = contentViews;
        return this.contentViews;
    },

    /**
     *  @param {HistoryDatasetAssociation} content
     */
    _createContentView : function( content ){
        //console.debug( 'content json:', JSON.stringify( content, null, '  ' ) );
        var contentView = null,
            ContentClass = this._getContentClass( content );
        //console.debug( 'content.object json:', JSON.stringify( content.object, null, '  ' ) );
        //console.debug( 'ContentClass:', ContentClass );
        //console.debug( 'content:', content );
        //console.debug( 'content.object:', content.object );
        contentView = new ContentClass({
            model           : content.object,
            linkTarget      : this.linkTarget,
            //draggable       : true,
            hasUser         : this.hasUser,
            logger          : this.logger
        });
        //this._setUpHdaListeners( contentView );
        return contentView;
    },

    _getContentClass : function( content ){
        switch( content.get( 'element_type' ) ){
            case 'hda':
                return this.HDAViewClass;
            case 'dataset_collection':
                return DC_BASE.NestedDCEBaseView;
        }
        throw new TypeError( 'Unknown element type:', content.get( 'element_type' ) );
    },

//    /** Set up HistoryPanel listeners for HDAView events. Currently binds:
//     *      HDAView#body-visible, HDAView#body-hidden to store expanded states
//     *  @param {HDAView} hdaView HDAView (base or edit) to listen to
//     */
//    _setUpHdaListeners : function( hdaView ){
//        var panel = this;
//        hdaView.on( 'error', function( model, xhr, options, msg ){
//            panel.errorHandler( model, xhr, options, msg );
//        });
//        // maintain a list of hdas whose bodies are expanded
//        hdaView.on( 'body-expanded', function( model ){
//            panel.storage.addExpandedHda( model );
//        });
//        hdaView.on( 'body-collapsed', function( id ){
//            panel.storage.removeExpandedHda( id );
//        });
//        return this;
//    },

    /** attach an contentView to the panel */
    attachContentView : function( contentView, $whereTo ){
        $whereTo = $whereTo || this.$el;
        var $datasetsList = this.$datasetsList( $whereTo );
        $datasetsList.append( contentView.$el );
        return this;
    },

    // ------------------------------------------------------------------------ panel events
    /** event map */
    events : {
        'click .panel-navigation-back'       : 'close'
    },

    /**  */
    close : function( event ){
        this.$el.remove();
        this.trigger( 'collection-close' );
    },

    // ........................................................................ misc
    /** Return a string rep of the history */
    toString    : function(){
        return 'CollectionPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


//------------------------------------------------------------------------------ TEMPLATES
var _panelTemplate = [
    '<div class="history-controls">',
        '<div class="panel-navigation">',
            '<a class="panel-navigation-back" href="javascript:void(0)">', _l( 'Back' ), '</a>',
        '</div>',

        '<div class="history-title">',
            '<% if( collection.name ){ %>',
                '<div class="history-name"><%= collection.hid %> : <%= collection.name %></div>',
            '<% } %>',
        '</div>',

        //'<div class="history-subtitle clear">',
        //    '<% if( history.nice_size ){ %>',
        //        '<div class="history-size"><%= history.nice_size %></div>',
        //    '<% } %>',
        //    '<div class="history-secondary-actions"></div>',
        //'</div>',
        //
        //'<% if( history.deleted ){ %>',
        //    '<div class="warningmessagesmall"><strong>',
        //        _l( 'You are currently viewing a deleted history!' ),
        //    '</strong></div>',
        //'<% } %>',
        //
        //'<div class="message-container">',
        //    '<% if( history.message ){ %>',
        //        // should already be localized
        //        '<div class="<%= history.status %>message"><%= history.message %></div>',
        //    '<% } %>',
        //'</div>',
        //
        //'<div class="quota-message errormessage">',
        //    _l( 'You are over your disk quota' ), '. ',
        //    _l( 'Tool execution is on hold until your disk usage drops below your allocated quota' ), '.',
        //'</div>',
        //
        //'<div class="tags-display"></div>',
        //'<div class="annotation-display"></div>',
        //'<div class="history-dataset-actions">',
        //    '<div class="btn-group">',
        //        '<button class="history-select-all-datasets-btn btn btn-default"',
        //                'data-mode="select">', _l( 'All' ), '</button>',
        //        '<button class="history-deselect-all-datasets-btn btn btn-default"',
        //                'data-mode="select">', _l( 'None' ), '</button>',
        //    '</div>',
        //    '<button class="history-dataset-action-popup-btn btn btn-default">',
        //        _l( 'For all selected' ), '...</button>',
        //'</div>',
    '</div>',
    // end history controls

    // where the datasets/hdas are added
    '<div class="datasets-list"></div>'

].join( '' );

CollectionPanel.templates = {
    panel : function( JSON ){
        return _.template( _panelTemplate, JSON, { variable: 'collection' });
    }
};


//==============================================================================
    return {
        CollectionPanel: CollectionPanel
    };
});
