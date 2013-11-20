// =============================================================================
/**
 *  Scatterplot display control UI as a backbone view
 *      handles:
 *          fetching the data (if needed)
 *          computing and displaying data stats
 *          controls for pagination of data (if needed)
 */
var ScatterplotView = Backbone.View.extend({
    //TODO: should be a view on visualization(revision) model

    defaults : {
        metadata : {
            dataLines : undefined
        },

        pagination : {
            currPage    : 0,
            perPage     : 3000
        },

        width   : 400,
        height  : 400,

        margin : {
            top     : 16,
            right   : 16,
            bottom  : 40,
            left    : 54
        },

        x : {
            ticks   : 10,
            label   : 'X'
        },
        y : {
            ticks   : 10,
            label   : 'Y'
        },

        datapointSize   : 4,
        animDuration    : 500
    },

    initialize : function( attributes ){
        this.config = _.extend( _.clone( this.defaults ), attributes.config || {});
        this.dataset = attributes.dataset;
        //console.debug( this + '.config:', this.config );
    },

    updateConfig : function( newConfig ){
        //console.log( this + '.updateConfig:', newConfig );
        this.config = this.config || {};
        //TODO: validate here
        _.extend( this.config, newConfig );
        //TODO: implement rerender flag
    },

    fetchData : function(){
//TODO: doesn't work bc it's rendered in render()...
        this.showLoadingIndicator( 'getting data' );
        //console.debug( 'currPage', this.config.pagination.currPage );
        var view = this;
//TODO: very tied to datasets - should be generalized eventually
            xhr = jQuery.getJSON( '/api/datasets/' + this.dataset.id, {
                data_type   : 'raw_data',
                provider    : 'dataset-column',
                limit       : this.config.pagination.perPage,
                offset      : ( this.config.pagination.currPage * this.config.pagination.perPage )
            });
        xhr.done( function( data ){
            view.renderData( data.data );
        });
        xhr.fail( function( xhr, status, message ){
            alert( 'Error loading data:\n' + xhr.responseText );
            console.error( xhr, status, message );
        });
        xhr.always( function(){
            view.hideLoadingIndicator();
        });
        return xhr;
    },

    render : function( data ){
        this.$el.addClass( 'scatterplot-display' ).html([
            '<div class="controls clear"></div>',
            '<div class="loading-indicator">',
                '<span class="fa fa-spinner fa-spin"></span>',
                '<span class="loading-indicator-message"></span>',
            '</div>',
            '<svg/>', //TODO: id
            '<div class="stats-display"></div>'
        ].join( '' ));
        this.$el.children().hide();

        if( data ){
            this.renderData( data );
        }
        return this;
    },

    showLoadingIndicator : function( message, speed ){
        // display the loading indicator over the tab panels if hidden, update message (if passed)
//TODO: move loading indicator into data-info-text
        message = message || '';
        speed = speed || 'fast';
        var $indicator = this.$el.find( '.loading-indicator' );

        if( message ){ $indicator.find( '.loading-indicator-message' ).text( message ); }
        if( !$indicator.is( ':visible' ) ){
            this.toggleStats( false );
            $indicator.css({ left: ( this.config.width / 2 ), top: this.config.height / 2 }).show();
        }
    },

    hideLoadingIndicator : function( speed ){
        speed = speed || 'fast';
        this.$el.find( '.loading-indicator' ).hide();
    },

    renderData : function( data ){
        this.$el.find( '.controls' ).empty().append( this.renderControls( data ) ).show();
        this.renderPlot( data );
        this.getStats( data );
    },

    renderControls : function( data ){
        var view = this;
        var $left  = $( '<div class="left"></div>' ),
            $right = $( '<div class="right"></div>' );

        $left.append([
            this.renderPrevNext( data ),
            this.renderPagination( data )
        ]);
        $right.append([
            this.renderLineInfo( data ),
            $( '<button>Stats</button>' ).addClass( 'stats-toggle-btn' )
                .click( function(){
                    view.toggleStats();
                }),
            $( '<button>Redraw</button>' ).addClass( 'rerender-btn' )
                .click( function(){
                    view.renderPlot( data );
                })
        ]);
        return [ $left, $right ];
    },

    renderLineInfo : function( data ){
        var totalLines = this.dataset.metadata_data_lines || 'an unknown number of',
            lineStart  = ( this.config.pagination.currPage * this.config.pagination.perPage ),
            lineEnd    = lineStart + data.length;
        return $( '<p/>' ).addClass( 'scatterplot-data-info' )
           .text([ 'Displaying lines', lineStart + 1, 'to', lineEnd, 'of', totalLines, 'lines' ].join( ' ' ));
    },

    renderPrevNext : function( data ){
        // this is cra-zazy
        if( !data
        ||  ( this.config.pagination.currPage === 0 && data.length < this.config.pagination.perPage ) ){ return null; }

        function makePage$Li( text ){
            return $([ '<li><a href="javascript:void(0);">', text, '</a></li>' ].join( '' ));
        }
//TODO: cache numPages/numLines in config
        var view = this,
            dataLines = this.dataset.metadata_data_lines,
            numPages = ( dataLines )?( Math.ceil( dataLines / this.config.pagination.perPage ) ):( undefined );
        //console.debug( 'data:', this.dataset.metadata_data_lines, 'numPages:', numPages );

        // prev next buttons
        var $prev = makePage$Li( 'Prev' ).click( function(){
                    if( view.config.pagination.currPage > 0 ){
                        view.config.pagination.currPage -= 1;
                        view.fetchData();
                    }
                }),
            $next = makePage$Li( 'Next' ).click( function(){
                    if( !numPages || view.config.pagination.currPage < ( numPages - 1 ) ){
                        view.config.pagination.currPage += 1;
                        view.fetchData();
                    }
                }),
            $prevNextList = $( '<ul/>' ).addClass( 'pagination data-prev-next' )
                .append([ $prev, $next ]);

        if( view.config.pagination.currPage === 0 ){
            $prev.addClass( 'disabled' );
        }
        if( numPages && view.config.pagination.currPage === ( numPages - 1 ) ){
            $next.addClass( 'disabled' );
        }
        return $prevNextList;
    },

    renderPagination : function( data ){
        // this is cra-zazy
        if( !data
        ||  ( this.config.pagination.currPage === 0 && data.length < this.config.pagination.perPage ) ){ return null; }

        function makePage$Li( text ){
            return $([ '<li><a href="javascript:void(0);">', text, '</a></li>' ].join( '' ));
        }
//TODO: cache numPages/numLines in config
        var view = this,
            dataLines = this.dataset.metadata_data_lines,
            numPages = ( dataLines )?( Math.ceil( dataLines / this.config.pagination.perPage ) ):( undefined );
        //console.debug( 'data:', this.dataset.metadata_data_lines, 'numPages:', numPages );

        // page numbers (as separate control)
        //var $paginationContainer = $( '<div/>' ).addClass( 'pagination-container' ),
        var $pagesList = $( '<ul/>' ).addClass( 'pagination data-pages' );
        function pageNumClick( ev ){
            view.config.pagination.currPage = $( this ).data( 'page' );
            view.fetchData();
        }
        for( var i=0; i<numPages; i+=1 ){
            // add page data for later event handling
            var $pageLi = makePage$Li( i + 1 ).attr( 'data-page', i ).click( pageNumClick );
            if( i === this.config.pagination.currPage ){
                $pageLi.addClass( 'active' );
            }
            $pagesList.append( $pageLi );
        }
        // placing the pages list in an extra container allows us to set a max-width and scroll if overflow
        //$paginationContainer.append( $pagesList );
        //return $paginationContainer;
        return $pagesList;
    },

    renderPlot : function( data ){
        this.toggleStats( false );
        var $svg = this.$el.find( 'svg' );
        $svg.off().empty().show();
        scatterplot( $svg.get( 0 ), this.config, data );
    },

    getStats : function( data ){
        var view = this;
            meanWorker = new Worker( '/plugins/visualizations/scatterplot/static/worker-stats.js' );
        meanWorker.postMessage({
            data    : data,
            keys    : [ this.config.xColumn, this.config.yColumn ]
        });
        meanWorker.onerror = function( event ){
            meanWorker.terminate();
        };
        meanWorker.onmessage = function( event ){
            view.renderStats( event.data );
        };
    },

    renderStats : function( stats, error ){
        //console.debug( 'renderStats:', stats, error );
        //console.debug( JSON.stringify( stats, null, '  ' ) );
        var $statsTable = this.$el.find( '.stats-display' );

        var xLabel = this.config.x.label, yLabel = this.config.y.label,
            $table = $( '<table/>' ).addClass( 'table' )
                .append([ '<thead><th></th><th>', xLabel, '</th><th>', yLabel, '</th></thead>' ].join( '' ))
                .append( _.map( stats, function( stat, key ){
                    return $([ '<tr><td>', key, '</td><td>', stat[0], '</td><td>', stat[1], '</td></tr>' ].join( '' ));
                }));
        $statsTable.empty().append( $table );
    },

    toggleStats : function( showStats ){
        var $statsDisplay = this.$el.find( '.stats-display' );
        showStats = ( showStats === undefined )?( $statsDisplay.is( ':hidden' ) ):( showStats );
        if( showStats ){
            this.$el.find( 'svg' ).hide();
            $statsDisplay.show();
            this.$el.find( '.controls .stats-toggle-btn' ).text( 'Plot' );
        } else {
            $statsDisplay.hide();
            this.$el.find( 'svg' ).show();
            this.$el.find( '.controls .stats-toggle-btn' ).text( 'Stats' );
        }
    },

    toString : function(){
        return 'ScatterplotView()';
    }
});
