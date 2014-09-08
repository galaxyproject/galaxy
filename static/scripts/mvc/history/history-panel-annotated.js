define([
    "mvc/history/history-panel",
    "mvc/history/hda-li",
    "mvc/history/hdca-li",
    "mvc/base-mvc",
    "utils/localization"
], function( HPANEL, HDA_LI, HDCA_LI, BASE_MVC, _l ){
/* =============================================================================
TODO:

============================================================================= */
var _super = HPANEL.HistoryPanel;
// used in history/display.mako and history/embed.mako
/** @class View/Controller for a tabular view of the history model.
 *
 *  As ReadOnlyHistoryPanel, but with:
 *      history annotation always shown
 *      datasets displayed in a table:
 *          datasets in left cells, dataset annotations in the right
 */
var AnnotatedHistoryPanel = _super.extend(
/** @lends AnnotatedHistoryPanel.prototype */{

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
        this.$list( $whereTo ).append( this.views.map( function( view ){
            //TODO:?? possibly make this more flexible: instead of annotation use this._additionalInfo()
            // build a row around the dataset with the std itemView in the first cell and the annotation in the next
            var stateClass = _.find( view.el.classList, function( c ){ return ( /^state\-/ ).test( c ); }),
                annotation = view.model.get( 'annotation' ) || '',
                $tr = $( '<tr/>' ).append([
                    $( '<td/>' ).addClass( 'contents-container' ).append( view.$el )
                        // visually match the cell bg to the dataset at runtime (prevents the empty space)
                        // (getting bg via jq on hidden elem doesn't work on chrome/webkit - so use states)
                        //.css( 'background-color', view.$el.css( 'background-color' ) ),
                        .addClass( stateClass? stateClass.replace( '-', '-color-' ): '' ),
                    $( '<td/>' ).addClass( 'additional-info' ).text( annotation )
                ]);
            return $tr;
        }));
        return this;
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
        }
    }),

    // ........................................................................ misc
    /** Return a string rep of the history */
    toString    : function(){
        return 'AnnotatedHistoryPanel(' + (( this.model )?( this.model.get( 'name' )):( '' )) + ')';
    }
});


//==============================================================================
    return {
        AnnotatedHistoryPanel        : AnnotatedHistoryPanel
    };
});
