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
        $newRender.find( '.controls .annotation-display' ).text( annotation );
    },

    /** override to add table header cells to indicate the dataset, annotation columns */
    renderItems : function( $whereTo ){
        $whereTo = $whereTo || this.$el;
        _super.prototype.renderItems.call( this, $whereTo );
        var $headers = $( '<tr/>' ).addClass( 'headers' ).append([
                $( '<th/>' ).text( _l( 'Dataset' ) ),
                $( '<th/>' ).text( _l( 'Annotation' ) )
            ]);
        $headers = $( '<tbody/>' ).html( $headers );
        $whereTo.find( '> .list-items' ).prepend( $headers );
        return self.views;
    },

    // // ------------------------------------------------------------------------ sub-views
    /** override to wrap each subview in a row */
    _renderItemView$el : function( view ){
        //TODO:?? possibly make this more flexible: instead of annotation use this._additionalInfo()
        // build a row around the dataset with the std itemView in the first cell and the annotation in the next
        var stateClass = _.find( view.el.classList, function( c ){ return ( /^state\-/ ).test( c ); });
        var annotation = view.model.get( 'annotation' ) || '';
        return $( '<tr/>' ).append([
                $( '<td/>' ).addClass( 'contents-container' ).append( view.render(0).$el )
                    // visually match the cell bg to the dataset at runtime (prevents the empty space)
                    // (getting bg via jq on hidden elem doesn't work on chrome/webkit - so use states)
                    //.css( 'background-color', view.$el.css( 'background-color' ) ),
                    .addClass( stateClass? stateClass.replace( '-', '-color-' ): '' ),
                $( '<td/>' ).addClass( 'additional-info' ).text( annotation )
            ]);
    },

    // ------------------------------------------------------------------------ panel events
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


//------------------------------------------------------------------------------ TEMPLATES
AnnotatedHistoryView.prototype.templates = (function(){

    var mainTemplate = BASE_MVC.wrapTemplate([
        '<div>',
            '<div class="controls"></div>',
            '<table class="list-items"></table>',
            '<div class="empty-message infomessagesmall"></div>',
        '</div>'
    ]);

    var listItemsSectionTemplate = BASE_MVC.wrapTemplate([
        '<% if( section.number === view.model.contents.currentSection ){ %>',
            '<tbody class="list-items-section current-section" data-section="<%- section.number %>"></tbody>',
        '<% } else { %>',
            '<tbody class="list-items-section" data-section="<%- section.number %>">',
                '<tr><td><a class="list-items-section-link" href="javascript:void(0)">',
                    '<%- section.first %>  ', _l( "to" ), ' <%- section.last %>',
                '</a></td></tr>',
            '</tbody>',
        '<% } %>',
    ], 'section' );

    return _.extend( _.clone( _super.prototype.templates ), {
        el                      : mainTemplate,
        listItemsSection        : listItemsSectionTemplate
    });
}());


//==============================================================================
    return {
        AnnotatedHistoryView        : AnnotatedHistoryView
    };
});
