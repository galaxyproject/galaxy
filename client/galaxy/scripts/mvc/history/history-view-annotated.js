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
var AnnotatedHistoryView = _super.extend(/** @lends AnnotatedHistoryView.prototype */{

    className    : _super.prototype.className + ' annotated-history-panel',

    // ------------------------------------------------------------------------ panel rendering
    /** In this override, add the history annotation */
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
        $newRender.find( '> .controls .subtitle' ).text( annotation );
    },

    /** override to add headers to indicate the dataset, annotation columns */
    renderItems : function( $whereTo ){
        $whereTo = $whereTo || this.$el;
        _super.prototype.renderItems.call( this, $whereTo );

        var $controls = $whereTo.find( '> .controls' );
        $controls.find( '.contents-container.headers' ).remove();

        var $headers = $( '<div class="contents-container headers"/>' )
            .append([
                $( '<div class="history-content header"/>' ).text( _l( 'Dataset' ) ),
                $( '<div class="additional-info header"/>' ).text( _l( 'Annotation' ) )
            ]).appendTo( $controls );

        return self.views;
    },

    // ------------------------------------------------------------------------ sub-views
    /** override to wrap each subview */
    _renderItemView$el : function( view ){
        return $( '<div class="contents-container"/>' ).append([
            view.render(0).$el,
            $( '<div class="additional-info"/>' ).text( view.model.get( 'annotation' ) || '' )
        ]);
    },

    // ------------------------------------------------------------------------ panel events
    events : _.extend( _.clone( _super.prototype.events ), {
        // clicking on any part of the row will expand the items
        'click .contents-container' : function( ev ){
            ev.stopPropagation();
            $( ev.currentTarget ).find( '.list-item .title-bar' ).click();
        },
        // prevent propagation on icon btns so they won't bubble up to tr and toggleBodyVisibility
        'click .icon-btn' : function( ev ){
            ev.stopPropagation();
            // stopProp will prevent bootstrap from getting the click needed to open a dropdown
            //  in the case of metafile download buttons - workaround here
            var $currTarget = $( ev.currentTarget );
            if( $currTarget.length && $currTarget.attr( 'data-toggle' ) === 'dropdown' ){
                $currTarget.dropdown( 'toggle' );
            }
        }
    }),

    _clickSectionLink : function( ev ){
        var sectionNumber = $( ev.currentTarget ).parent().parent().data( 'section' );
        this.openSection( sectionNumber );
    },

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
