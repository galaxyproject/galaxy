define([
    "mvc/history/history-view",
    "mvc/history/hda-li",
    "mvc/history/hdca-li",
    "mvc/base-mvc",
    "utils/localization"
], function( HISTORY_VIEW, HDA_LI, HDCA_LI, BASE_MVC, _l ){

'use strict';

/* =============================================================================
TODO:

============================================================================= */
var _super = HISTORY_VIEW.HistoryView;
// used in history/display.mako and history/embed.mako
/** @class View/Controller for a tabular view of the history model.
 *
 *  As ReadOnlyHistoryView, but with:
 *      history annotation always shown
 *      datasets displayed in a table:
 *          datasets in left cells, dataset annotations in the right
 */
var AnnotatedHistoryView = _super.extend(
/** @lends AnnotatedHistoryView.prototype */{

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    className    : _super.prototype.className + ' annotated-history-panel',

    // ------------------------------------------------------------------------ panel rendering
    /** In this override, add the history annotation
     */
    _buildNewRender : function(){
        //TODO: shouldn't this display regardless (on all non-current panels)?
        var $newRender = _super.prototype._buildNewRender.call( this );
        this.renderHistoryAnnotation( $newRender );
        return $newRender;
    },

    /** render the history's annotation as its own field */
    renderHistoryAnnotation : function( $newRender ){
        var annotation = this.model.get( 'annotation' );
        if( !annotation ){ return; }
        $newRender.find( '.controls .annotation-display' ).text( annotation );
    },

    /** In this override, convert the list-items tag to a table
     *      and add table header cells to indicate the dataset, annotation columns
     */
    renderItems : function( $whereTo ){
        $whereTo = $whereTo || this.$el;

        // convert to table
        $whereTo.find( '.list-items' )
            .replaceWith( $( '<table/>' ).addClass( 'list-items' ) );

        // render rows/contents and prepend headers
        var views = _super.prototype.renderItems.call( this, $whereTo );
        this.$list( $whereTo )
            .prepend( $( '<tr/>' ).addClass( 'headers' ).append([
                $( '<th/>' ).text( _l( 'Dataset' ) ),
                $( '<th/>' ).text( _l( 'Annotation' ) )
            ]));
        return views;
    },

    // ------------------------------------------------------------------------ sub-views
    /** In this override, wrap the content view in a table row
     *      with the content in the left td and annotation/extra-info in the right
     */
    _attachItems : function( $whereTo ){
        var self = this;
        console.log( '_attachItems:', $whereTo.find( '> .list-items' ) );
        console.log( '_attachItems:', $whereTo, this.$list( $whereTo ) );
        this.$list( $whereTo ).append( this.views.map( function( view ){
            return self._wrapViewInRow( view );
        }));
        return this;
    },

    _wrapViewInRow : function( view ){
        //TODO:?? possibly make this more flexible: instead of annotation use this._additionalInfo()
        // build a row around the dataset with the std itemView in the first cell and the annotation in the next
        var stateClass = _.find( view.el.classList, function( c ){ return ( /^state\-/ ).test( c ); });
        var annotation = view.model.get( 'annotation' ) || '';
        return $( '<tr/>' ).append([
                $( '<td/>' ).addClass( 'contents-container' ).append( view.$el )
                    // visually match the cell bg to the dataset at runtime (prevents the empty space)
                    // (getting bg via jq on hidden elem doesn't work on chrome/webkit - so use states)
                    //.css( 'background-color', view.$el.css( 'background-color' ) ),
                    .addClass( stateClass? stateClass.replace( '-', '-color-' ): '' ),
                $( '<td/>' ).addClass( 'additional-info' ).text( annotation )
            ]);
    },

    /**  */
    bulkAppendItemViews : function( collection, response, options ){
//TODO: duplication
        //PRECONDITION: response is an array of contguous content models
        console.log( "bulkAppendItemViews:", collection, response, options );
        if( !response || !response.length ){ return; }
        var self = this;

        // find where to insert the block
        // note: don't use filteredCollection since we may be searching and the first model may not match search
        // TODO: when Backbone > 1.1: self.collection.findIndex
        var firstModelIndex = self.collection.models.findIndex( function( m ){
            return m.id === response[0].type_id;
        });
        console.log( 'firstModelIndex:', firstModelIndex );

        var $viewEls = [];
        response.forEach( function( modelJSON ){
            var model = self.collection.get( modelJSON.type_id );
            if( !self._filterItem( model ) ){ return; }

            var view = self._createItemView( model );
            self.views.push( view );
            $viewEls.push( self._wrapViewInRow( view.render( 0 ) ) );
            // TODO: not attached *yet* actually
            self.trigger( 'view:attached', view );
            self.trigger( 'view:attached:rendered' );
        });
        if( $viewEls.length ){
            self.$emptyMessage().hide();
            self.$list().append( $viewEls );
            self._insertIntoListAt( firstModelIndex, $viewEls );
        }
    },

    // ------------------------------------------------------------------------ panel events
    /** event map */
    events : _.extend( _.clone( _super.prototype.events ), {
        // clicking on any part of the row will expand the items
        'click tr' : function( ev ){
            $( ev.currentTarget ).find( '.title-bar' ).click();
        },
        // prevent propagation on icon btns so they won't bubble up to tr and toggleBodyVisibility
        'click .icon-btn' : function( ev ){
            ev.stopPropagation();
            // stopProp will prevent bootstrap from getting the click needed to open a dropdown
            //  in the case of metafile download buttons - workaround here
            var $currTarget = $( ev.currentTarget );
            if( $currTarget.size() && $currTarget.attr( 'data-toggle' ) === 'dropdown' ){
                $currTarget.dropdown( 'toggle' );
            }
        }
    }),

    // ........................................................................ misc
    /** Return a string rep of the history */
    toString    : function(){
        return 'AnnotatedHistoryView(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


//==============================================================================
    return {
        AnnotatedHistoryView        : AnnotatedHistoryView
    };
});
