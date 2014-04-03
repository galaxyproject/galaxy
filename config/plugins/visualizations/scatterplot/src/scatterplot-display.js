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
        this.lineCount = this.dataset.metadata_data_lines || null;
    },

    fetchData : function(){
        this.showLoadingIndicator();
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
            // no need to hide loading indicator, line info will write over that
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
                '<div class="right">',
                    '<p class="scatterplot-data-info"></p>',
                    '<button class="stats-toggle-btn">Stats</button>',
                    '<button class="rerender-btn">Redraw</button>',
                '</div>',
                '<div class="left">',
                    '<div class="page-control"></div>',
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
        var display = this,
            config = this.model.get( 'config' );

        this.$el.find( '.controls .left .page-control' ).pagination({
            startingPage : config.pagination.currPage,
            perPage      : config.pagination.perPage,
            totalDataSize: this.lineCount,
            currDataSize : this.data.length

        //TODO: move to named function and remove only named
        }).off().on( 'pagination.page-change', function( event, page ){
            //console.debug( 'pagination:page-change', page );
            config.pagination.currPage = page;
            display.model.set( 'config', { pagination: config.pagination });
            //console.debug( pagination, display.model.get( 'config' ).pagination );
            display.resetZoom();
            display.fetchData();
        });
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
            xLabel = config.xLabel, yLabel = config.yLabel,
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
