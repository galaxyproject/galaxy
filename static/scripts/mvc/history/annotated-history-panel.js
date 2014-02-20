define([
    "mvc/dataset/hda-model",
    "mvc/dataset/hda-base",
    "mvc/history/readonly-history-panel"
], function( hdaModel, hdaBase, readonlyPanel ){
/* =============================================================================
TODO:

============================================================================= */
/** @class View/Controller for a tabular view of the history model.
 *  @name AnnotatedHistoryPanel
 *
 *  As ReadOnlyHistoryPanel, but with:
 *      history annotation always shown
 *      datasets displayed in a table:
 *          datasets in left cells, dataset annotations in the right
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var AnnotatedHistoryPanel = readonlyPanel.ReadOnlyHistoryPanel.extend(
/** @lends HistoryPanel.prototype */{

    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,

    className    : 'annotated-history-panel',

    /** class to use for constructing the HDA views */
    HDAViewClass : hdaBase.HDABaseView,

    // ------------------------------------------------------------------------ panel rendering
    renderModel : function( ){
        // huh?
        this.$el.addClass( this.className );
        var $newRender = readonlyPanel.ReadOnlyHistoryPanel.prototype.renderModel.call( this ),
        // move datasets from div to table
            $datasetsList = $newRender.find( this.datasetsSelector ),
            $datasetsTable = $( '<table/>' ).addClass( 'datasets-list datasets-table' );
        $datasetsTable.append( $datasetsList.children() );
        $newRender.find( this.datasetsSelector ).replaceWith( $datasetsTable );
        //TODO: it's possible to do this with css only, right?

        // add history annotation under subtitle
        $newRender.find( '.history-subtitle' ).after( this.renderHistoryAnnotation() );

        // hide search button, move search bar beneath controls (instead of above title), show, and set up
        $newRender.find( '.history-search-btn' ).hide();
        $newRender.find( '.history-controls' ).after( $newRender.find( '.history-search-controls' ).show() );
        this.setUpSearchInput( $newRender.find( '.history-search-input' ) );

        return $newRender;
    },

    renderHistoryAnnotation : function(){
        var annotation = this.model.get( 'annotation' );
        if( !annotation ){ return null; }
        return $([
            '<div class="history-annotation">', annotation, '</div>'
        ].join( '' ));
    },

    renderHdas : function( $whereTo ){
        $whereTo = $whereTo || this.$el;
        var hdaViews = readonlyPanel.ReadOnlyHistoryPanel.prototype.renderHdas.call( this, $whereTo );
        $whereTo.find( this.datasetsSelector ).prepend( $( '<tr/>' ).addClass( 'headers' ).append([
            $( '<th/>' ).text( _l( 'Dataset' ) ),
            $( '<th/>' ).text( _l( 'Annotation' ) )
        ]));
        return hdaViews;
    },

    // ------------------------------------------------------------------------ hda sub-views
    attachHdaView : function( hdaView, $whereTo ){
        $whereTo = $whereTo || this.$el;
        // build a row around the dataset with the std hdaView in the first cell and the annotation in the next
        var stateClass = _.find( hdaView.el.classList, function( c ){ return ( /^state\-/ ).test( c ); }),
            annotation = hdaView.model.get( 'annotation' ) || '',
            $tr = $( '<tr/>' ).addClass( 'dataset-row' ).append([
                $( '<td/>' ).addClass( 'dataset-container' ).append( hdaView.$el )
                    // visually match the cell bg to the dataset at runtime (prevents the empty space)
                    // (getting bg via jq on hidden elem doesn't work on chrome/webkit - so use states)
                    //.css( 'background-color', hdaView.$el.css( 'background-color' ) ),
                    .addClass( stateClass? stateClass.replace( '-', '-color-' ): '' ),
                $( '<td/>' ).addClass( 'additional-info' ).text( annotation )
            ]);
        $whereTo.find( this.datasetsSelector ).append( $tr );
    },

    // ------------------------------------------------------------------------ panel events
    /** event map */
    events : _.extend( _.clone( readonlyPanel.ReadOnlyHistoryPanel.prototype.events ), {
        'click tr' : function( ev ){
            //if( !ev.target.hasAttribute( 'href' ) ){
                $( ev.currentTarget ).find( '.dataset-title-bar' ).click();
            //}
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
