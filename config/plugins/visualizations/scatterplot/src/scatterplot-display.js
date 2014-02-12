// =============================================================================
/**
 *  Scatterplot display control UI as a backbone view
 *      handles:
 *          fetching the data (if needed)
 *          computing and displaying data stats
 *          controls for pagination of data (if needed)
 */
var ScatterplotDisplay = Backbone.View.extend({

    initialize : function( attributes ){
        this.data = null,
        this.dataset = attributes.dataset;
        this.calcNumPages();
    },

    calcNumPages : function(){
        var config = this.model.get( 'config' );
        this.lineCount = this.dataset.metadata_data_lines,
        this.numPages = ( this.lineCount )?( Math.ceil( this.lineCount / config.pagination.perPage ) ):( undefined );
        if( !this.lineCount || this.numPages === undefined ){
            console.warn( 'no data total found' );
        }
    },

    fetchData : function(){
//TODO: doesn't work bc it's rendered in render()...
        this.showLoadingIndicator( 'getting data' );
        //console.debug( 'currPage', this.config.pagination.currPage );
        var view = this,
            config = this.model.get( 'config' ),
//TODO: very tied to datasets - should be generalized eventually
            xhr = jQuery.getJSON( '/api/datasets/' + this.dataset.id, {
                data_type   : 'raw_data',
                provider    : 'dataset-column',
                limit       : config.pagination.perPage,
                offset      : ( config.pagination.currPage * config.pagination.perPage )
            });
        xhr.done( function( data ){
            view.data = data.data;
            view.trigger( 'data:fetched', view );
            view.renderData();
        });
        xhr.fail( function( xhr, status, message ){
            console.error( xhr, status, message );
            view.trigger( 'data:error', view );
            alert( 'Error loading data:\n' + xhr.responseText );
        });
        return xhr;
    },

    showLoadingIndicator : function(){
        // display the loading indicator over the tab panels if hidden, update message (if passed)
        this.$el.find( '.scatterplot-data-info' ).html([
            '<div class="loading-indicator">',
                '<span class="fa fa-spinner fa-spin"></span>',
                '<span class="loading-indicator-message">loading...</span>',
            '</div>'
        ].join( '' ));
    },

    template : function(){
        var html = [
            '<div class="controls clear">',
                '<div class="left">',
                '</div>',
                '<div class="right">',
                    '<p class="scatterplot-data-info"></p>',
                    '<button class="stats-toggle-btn">Stats</button>',
                    '<button class="rerender-btn">Redraw</button>',
                '</div>',
            '</div>',
            '<svg/>', //TODO: id
            '<div class="stats-display"></div>'
        ].join( '' );
        return html;
    },

    render : function(){
        this.$el.addClass( 'scatterplot-display' ).html( this.template() );
        if( this.data ){
            this.renderData();
        }
        return this;
    },

    renderData : function(){
        this.renderLeftControls();
        this.renderRightControls();
        this.renderPlot( this.data );
        this.getStats();
    },

    renderLeftControls : function(){
        if( this.lineCount ){
            this.$el.find( '.controls .left' ).empty().append( this.renderPagination() );
        } else {
            this.$el.find( '.controls .left' ).empty().append( this.renderPrevNext() );
        }
        return this;
    },

    renderRightControls : function(){
        var view = this;
        this.setLineInfo( this.data );
        // clear prev. handlers due to closure around data
        this.$el.find( '.stats-toggle-btn' )
            .off().click( function(){
                view.toggleStats();
            });
        this.$el.find( '.rerender-btn' )
            .off().click( function(){
                view.resetZoom();
                view.renderPlot( this.data );
            });
    },

    /** render and show the d3 plot into the svg node of the view */
    renderPlot : function(){
        var view = this,
            $svg = this.$el.find( 'svg' );
        // turn off stats, clear previous svg, and make it visible
        this.toggleStats( false );
        $svg.off().empty().show()
            // set up listeners for events from plot
            .on( 'zoom.scatterplot', function( ev, zoom ){
                //TODO: possibly throttle this
                //console.debug( 'zoom.scatterplot', zoom.scale, zoom.translate );
                view.model.set( 'config', zoom );
            });
        //TODO: may not be necessary to off/on this more than the initial on
        // call the sep. d3 function to generate the plot
        scatterplot( $svg.get( 0 ), this.model.get( 'config' ), this.data );
    },

    setLineInfo : function( data, contents ){
        if( data ){
            var config = this.model.get( 'config' ),
                totalLines = this.lineCount || 'an unknown total',
                lineStart  = config.pagination.currPage * config.pagination.perPage,
                lineEnd    = lineStart + data.length;
            this.$el.find( '.controls p.scatterplot-data-info' )
               .text([ lineStart + 1, 'to', lineEnd, 'of', totalLines ].join( ' ' ));
        } else {
            this.$el.find( '.controls p.scatterplot-data-info' ).html( contents || '' );
        }

        return this;
    },

    resetZoom : function( scale, translate ){
        scale = ( scale !== undefined )?( scale ):( 1 );
        translate = ( translate !== undefined )?( translate ):( [ 0, 0 ] );
        this.model.set( 'config', { scale: scale, translate: translate } );
        return this;
    },

    // ------------------------------------------------------------------------ data pagination
//TODO: to pagination control
    goToPage : function( page ){
        var pagination = this.model.get( 'config' ).pagination;
        //console.debug( 'goToPage', page, pagination, this.numPages );
        if( page <= 0 ){ page = 0; }
        if( this.numPages && page >= this.numPages ){ page = this.numPages - 1; }
        if( page === pagination.currPage ){ return this; }

        //console.debug( '\t going to page ' + page )
        pagination.currPage = page;
        this.model.set( 'config', { pagination: pagination });
        this.resetZoom();
        this.fetchData();
        return this;
    },

    nextPage : function(){
        var currPage = this.model.get( 'config' ).pagination.currPage;
        return this.goToPage( currPage + 1 );
    },

    prevPage : function(){
        var currPage = this.model.get( 'config' ).pagination.currPage;
        return this.goToPage( currPage - 1 );
    },

    /** render previous and next pagination buttons */
    renderPrevNext : function(){
        var config = this.model.get( 'config' );
        // if there's no data or there's less than one page of data - return null
        if( !this.data ){ return null; }
        if( config.pagination.currPage === 0 && this.data.length < config.pagination.perPage ){ return null; }

        var view = this,
            $prev = $( '<li><a href="javascript:void(0);">Prev</a></li>' )
                .click( function(){ view.prevPage(); }),
            $next = $( '<li><a href="javascript:void(0);">Next</a></li>' )
                .click( function(){ view.nextPage(); });

        // disable if it either end
        if( config.pagination.currPage === 0 ){
            $prev.addClass( 'disabled' );
        }
        if( this.numPages && config.pagination.currPage === ( this.numPages - 1 ) ){
            $next.addClass( 'disabled' );
        }
        return $( '<ul/>' ).addClass( 'pagination data-prev-next' ).append([ $prev, $next ]);
    },

    /** render page links for each possible page (if we can) */
    renderPagination : function(){
        var config = this.model.get( 'config' );
        // if there's no data, no page count, or there's less than one page of data - return null
        if( !this.data ){ return null; }
        if( !this.numPages ){ return null; }
        if( config.pagination.currPage === 0 && this.data.length < config.pagination.perPage ){ return null; }

        var view = this,
            $pagesList = $( '<ul/>' ).addClass( 'pagination data-pages' );
            pageNumClick = function( ev ){
                view.goToPage( $( this ).data( 'page' ) );
            };

        for( var i=0; i<this.numPages; i+=1 ){
            // add html5 data tag 'page' for later click event handler use
            var $pageLi = $([ '<li><a href="javascript:void(0);">', i + 1, '</a></li>' ].join( '' ))
                    .attr( 'data-page', i ).click( pageNumClick );
            // highlight the current page
            if( i === config.pagination.currPage ){
                $pageLi.addClass( 'active' );
            }
            $pagesList.append( $pageLi );
        }
        return $pagesList;
    },

    // ------------------------------------------------------------------------ statistics display
    /** create a webworker to calc stats for data given */
    getStats : function(){
        if( !this.data ){ return; }
        var view = this,
            config = this.model.get( 'config' ),
            meanWorker = new Worker( '/plugins/visualizations/scatterplot/static/worker-stats.js' );
        meanWorker.postMessage({
            data    : this.data,
            keys    : [ config.xColumn, config.yColumn ]
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
        var config = this.model.get( 'config' ),
            $statsTable = this.$el.find( '.stats-display' ),
            xLabel = config.x.label, yLabel = config.y.label,
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
