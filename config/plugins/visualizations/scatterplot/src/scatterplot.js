/* =============================================================================
todo:
    outside this:
        BUG: setting width, height in plot controls doesn't re-interpolate data locations!!
        BUG?: get metadata_column_names (from datatype if necessary)
        BUG: single vis in popupmenu should have tooltip with that name NOT 'Visualizations'
    
    wire label setters, anim setter
    
    TwoVarScatterplot:
        ??: maybe better to do this with a canvas...
        save as visualization
        to seperate file?
        remove underscore dependencies
        add interface to change values (seperate)?
        download svg -> base64 encode
        incorporate glyphs, glyph state renderers
        
    ScatterplotSettingsForm:
        some css bug that lowers the width of settings form when plot-controls tab is open
            causes chart to shift
        what can be abstracted/reused for other graphs?
        avoid direct manipulation of this.plot
        allow option to put plot into seperate tab of interface (for small multiples)
    
        provide callback in view to load data incrementally - for large sets
            paginate
                handle rerender
                use endpoint (here and on the server (fileptr))
            fetch (new?) data
                handle rerender
            use d3.TSV?
            render warning on long data (> maxDataPoints)
                adjust endpoint
        
        selectable list of preset column comparisons (rnaseq etc.)
            how to know what sort of Tabular the data is?
        smarter about headers
        validate columns selection (here or server)

        set stats column names by selected columns
        move chart into tabbed area...
        
    Scatterplot.mako:
        multiple plots on one page (small multiples)
        ?? ensure svg styles thru d3 or css?
            d3: configable (easily)
            css: standard - better maintenance
            ? override at config

============================================================================= */
/**
 *  Two Variable scatterplot visualization using d3
 *      Uses semi transparent circles to show density of data in x, y grid
 *      usage :
 *          var plot = new TwoVarScatterplot({ containerSelector : 'div#my-plot', ... })
 *          plot.render( xColumnData, yColumnData );
 *
 *  depends on: d3, underscore
 */
function TwoVarScatterplot( config ){
    var TICK_LINE_AND_PADDING = 10,
        GUESS_AT_SVG_CHAR_WIDTH = 7,
        GUESS_AT_SVG_CHAR_HEIGHT = 10,
        PADDING = 8,
        X_LABEL_TOO_LONG_AT = 5;
        
    // set up logging
    //this.debugging = true;
    this.log = function(){
        if( this.debugging && console && console.debug ){
            var args = Array.prototype.slice.call( arguments );
            args.unshift( this.toString() );
            console.debug.apply( console, args );
        }
    };
    this.log( 'new TwoVarScatterplot:', config );
    
    // ........................................................ set up chart config
    // config will default to these values when not passed in
    //NOTE: called on new
    this.defaults = {
        id : 'TwoVarScatterplot',
        containerSelector : 'body',
        //TODO??: needed?
        maxDataPoints : 30000,
        datapointSize : 4,
        animDuration : 500,
        //TODO: variable effect (not always exactly # of ticks set to)
        xNumTicks : 10,
        yNumTicks : 10,
        xAxisLabelBumpY : 40,
        yAxisLabelBumpX : -40,
        width   : 400,
        height  : 400,
        //TODO: anyway to make this a sub-obj?
        marginTop : 50,
        marginRight : 50,
        marginBottom : 50,
        marginLeft : 50,
        
        xMin : null,
        xMax : null,
        yMin : null,
        yMax : null,
        
        xLabel : "X",
        yLabel : "Y"
    };
    this.config = _.extend( {}, this.defaults, config );
    this.log( 'intial config:', this.config );
    
    this.updateConfig = function( newConfig, rerender ){
        // setter for chart config
        //TODO: validate here
        _.extend( this.config, newConfig );
        this.log( this + '.updateConfig:', this.config );
        //TODO: implement rerender flag
    };
    
    // ........................................................ helpers
    this.toString = function(){
        return this.config.id;
    };
    // conv. methods for svg transforms
    this.translateStr = function( x, y ){
        return 'translate(' + x + ',' + y + ')';
    };
    this.rotateStr = function( d, x, y ){
        return 'rotate(' + d + ',' + x + ',' + y + ')';
    };

    // ........................................................ initial element creation
    this.adjustChartDimensions = function( top, right, bottom, left ){
        //this.log( this + '.adjustChartDimensions', arguments );
        top = top || 0;
        right = right || 0;
        bottom = bottom || 0;
        left = left || 0;
        this.svg
            .attr( "width",  this.config.width  + ( this.config.marginRight  + right )
                                                + ( this.config.marginLeft   + left ) )
            .attr( "height", this.config.height + ( this.config.marginTop    + top )
                                                + ( this.config.marginBottom + bottom ) )
            // initial is hidden - show it
            .style( 'display', 'block' );
            
        // move content group away from margins
        //TODO: allow top, right axis
        this.content = this.svg.select( "g.content" )
            .attr( "transform", this.translateStr( this.config.marginLeft + left, this.config.marginTop + top ) );
    };
    
    // ........................................................ data and scales
    this.preprocessData = function( data, min, max ){
        //this.log( this + '.preprocessData', arguments );
        //TODO: filter by min, max if set
        
        // set a cap on the data, limit to first n points
        return ( data.length > this.config.maxDataPoints )? ( data.slice( 0, this.config.maxDataPoints ) ): ( data );
    };
    
    this.findMinMaxes = function( xCol, yCol, meta ){
        //this.log( this + '.findMinMaxes', arguments );
        // configuration takes priority, otherwise meta (from the server) if passed, last-resort: compute it here
        this.xMin = this.config.xMin || ( meta )?( meta[0].min ):( d3.min( xCol ) );
        this.xMax = this.config.xMax || ( meta )?( meta[0].max ):( d3.max( xCol ) );
        this.yMin = this.config.yMin || ( meta )?( meta[1].min ):( d3.min( yCol ) );
        this.yMax = this.config.yMax || ( meta )?( meta[1].max ):( d3.max( yCol ) );
    };
    
    this.setUpScales = function(){
        //this.log( this + '.setUpScales', arguments );
        // Interpolation for x, y based on data domains
        this.xScale = d3.scale.linear()
                .domain([ this.xMin, this.xMax ])
                .range([ 0, this.config.width ]),
        this.yScale = d3.scale.linear()
                .domain([ this.yMin, this.yMax ])
                .range([ this.config.height, 0 ]);
    };
    
    // ........................................................ axis and ticks
    this.setUpXAxis = function(){
        //this.log( this + '.setUpXAxis', arguments );
        // origin: bottom, left
        //TODO: incoporate top, right
        this.xAxisFn = d3.svg.axis()
            .scale( this.xScale )
            .ticks( this.config.xNumTicks )
            .orient( 'bottom' );
        this.xAxis// = content.select( 'g#x-axis' )
            .attr( 'transform', this.translateStr( 0, this.config.height ) )
            .call( this.xAxisFn );
        //this.log( 'xAxis:', this.xAxis );
        
        //TODO: adjust ticks when tick labels are long - move odds down and extend tick line
        // (for now) hide them
        var xLongestTickLabel = d3.max( _.map( [ this.xMin, this.xMax ],
                                     function( number ){ return ( String( number ) ).length; } ) );
        //this.log( 'xLongestTickLabel:', xLongestTickLabel );
        if( xLongestTickLabel >= X_LABEL_TOO_LONG_AT ){
            this.xAxis.selectAll( 'g' ).filter( ':nth-child(odd)' ).style( 'display', 'none' );
        }
        
        this.log( 'this.config.xLabel:', this.config.xLabel );
        this.xAxisLabel// = xAxis.select( 'text#x-axis-label' )
            .attr( 'x', this.config.width / 2 )
            .attr( 'y', this.config.xAxisLabelBumpY )
            .attr( 'text-anchor', 'middle' )
            .text( this.config.xLabel );
        this.log( 'xAxisLabel:', this.xAxisLabel );
    };

    this.setUpYAxis = function(){
        //this.log( this + '.setUpYAxis', arguments );
        this.yAxisFn = d3.svg.axis()
            .scale( this.yScale )
            .ticks( this.config.yNumTicks )
            .orient( 'left' );
        this.yAxis// = content.select( 'g#y-axis' )
            .call( this.yAxisFn );
        //this.log( 'yAxis:', this.yAxis );
    
        // a too complicated section for increasing the left margin when tick labels are long
        // get the tick labels for the y axis
        var yTickLabels = this.yAxis.selectAll( 'text' ).filter( function( e, i ){ return i !== 0; } );
        this.log( 'yTickLabels:', yTickLabels );
        
        // get the longest label length (or 0 if no labels)
        this.yLongestLabel = d3.max(
            //NOTE: d3 returns an nested array - use the plain array inside ([0])
            yTickLabels[0].map( function( e, i ){
                return ( d3.select( e ).text() ).length;
            })
        ) || 0;
        //this.log( 'yLongestLabel:', this.yLongestLabel );
        //TODO: lose the guessing if possible
        var neededY = TICK_LINE_AND_PADDING + ( this.yLongestLabel * GUESS_AT_SVG_CHAR_WIDTH )
                    + PADDING + GUESS_AT_SVG_CHAR_HEIGHT;
        //this.log( 'neededY:', neededY );
            
        // increase width for yLongerStr, increase margin for y
        //TODO??: (or transform each number: 2k)
        this.config.yAxisLabelBumpX = -( neededY - GUESS_AT_SVG_CHAR_HEIGHT );
        if( this.config.marginLeft < neededY ){
            var adjusting = ( neededY ) - this.config.marginLeft;
            adjusting = ( adjusting < 0 )?( 0 ):( adjusting );
            //this.log( 'adjusting:', adjusting );
            
            // update dimensions, translations
            this.adjustChartDimensions( 0, 0, 0, adjusting );
        }
        //this.log( 'this.config.yAxisLableBumpx, this.config.marginLeft:',
        //          this.config.yAxisLabelBumpX, this.config.marginLeft );
        
        this.yAxisLabel// = yAxis.select( 'text#y-axis-label' )
            .attr( 'x', this.config.yAxisLabelBumpX )
            .attr( 'y', this.config.height / 2 )
            .attr( 'text-anchor', 'middle' )
            .attr( 'transform', this.rotateStr( -90, this.config.yAxisLabelBumpX, this.config.height / 2 ) )
            .text( this.config.yLabel );
        //this.log( 'yAxisLabel:', this.yAxisLabel );
    };
    
    // ........................................................ grid lines
    this.renderGrid = function(){
        //this.log( this + '.renderGrid', arguments );
        // VERTICAL
        // select existing
        this.vGridLines = this.content.selectAll( 'line.v-grid-line' )
            .data( this.xScale.ticks( this.xAxisFn.ticks()[0] ) );
            
        // append any extra lines needed (more ticks)
        this.vGridLines.enter().append( 'svg:line' )
            .classed( 'grid-line v-grid-line', true );
            
        // update the attributes of existing and appended
        this.vGridLines
            .attr( 'x1', this.xScale )
            .attr( 'y1', 0 )
            .attr( 'x2', this.xScale )
            .attr( 'y2', this.config.height );
            
        // remove unneeded (less ticks)
        this.vGridLines.exit().remove();
        //this.log( 'vGridLines:', this.vGridLines );

        // HORIZONTAL
        this.hGridLines = this.content.selectAll( 'line.h-grid-line' )
            .data( this.yScale.ticks( this.yAxisFn.ticks()[0] ) );
            
        this.hGridLines.enter().append( 'svg:line' )
            .classed( 'grid-line h-grid-line', true );
        
        this.hGridLines
            .attr( 'x1', 0 )
            .attr( 'y1', this.yScale )
            .attr( 'x2', this.config.width )
            .attr( 'y2', this.yScale );
            
        this.hGridLines.exit().remove();
        //this.log( 'hGridLines:', this.hGridLines );
    };
    
    // ........................................................ data points
    this.renderDatapoints = function( xCol, yCol, ids ){
        this.log( this + '.renderDatapoints', arguments );
        var count = 0,
            plot = this,
            xPosFn = function( d, i ){
                //if( d ){ this.log( 'x.data:', newXCol[ i ], 'plotted:', plot.xScale( newXCol[ i ] ) ); }
                return plot.xScale( xCol[ i ] );
            },
            yPosFn = function( d, i ){
                //if( d ){ this.log( 'y.data:', newYCol[ i ], 'plotted:', plot.yScale( newYCol[ i ] ) ); }
                return plot.yScale( yCol[ i ] );
            };

        //this.datapoints = this.addDatapoints( xCol, yCol, ids, ".glyph" );
        var datapoints = this.content.selectAll( '.glyph' ).data( xCol );

        // enter - NEW data to be added as glyphs: give them a 'entry' position and style
        count = 0;
        datapoints.enter()
            .append( 'svg:circle' )
                .each( function(){ count += 1; } )
                .classed( "glyph", true )
                .attr( "cx", 0 )
                .attr( "cy", this.config.height )
                // start all bubbles small...
                .attr( "r", 0 );
        this.log( count, ' new glyphs created' );
        
        // for all EXISTING glyphs and those that need to be added: transition anim to final state
        count = 0;
        datapoints
            // ...animate to final position
            .transition().duration( this.config.animDuration )
                .each( function(){ count += 1; } )
                .attr( "cx", xPosFn )
                .attr( "cy", yPosFn )
                .attr( "r", plot.config.datapointSize );
        this.log( count, ' existing glyphs transitioned' );
        
        // events
        // glyphs that need to be removed: transition to from normal state to 'exit' state, remove from DOM
        datapoints.exit()
            .each( function(){ count += 1; } )
            .transition().duration( this.config.animDuration )
                .attr( "cy", this.config.height )
                .attr( "r", 0 )
            .remove();
        this.log( count, ' glyphs removed' );

        this._addDatapointEventhandlers( datapoints, xCol, yCol, ids );
    };

    this._addDatapointEventhandlers = function( datapoints, xCol, yCol, ids ){
        var plot = this;
        datapoints
            //TODO: remove magic numbers
            .on( 'mouseover', function( d, i ){
                var datapoint = d3.select( this );
                datapoint
                    .style( 'fill', 'red' )
                    .style( 'fill-opacity', 1 );
                
                // create horiz, vert lines to axis
                plot.content.append( 'line' )
                    .attr( 'stroke', 'red' )
                    .attr( 'stroke-width', 1 )
                    // start not at center, but at the edge of the circle - to prevent mouseover thrashing
                    .attr( 'x1', datapoint.attr( 'cx' ) - plot.config.datapointSize )
                    .attr( 'y1', datapoint.attr( 'cy' ) )
                    .attr( 'x2', 0 )
                    .attr( 'y2', datapoint.attr( 'cy' ) )
                    .classed( 'hoverline', true );

                // if the vertical hoverline
                if( datapoint.attr( 'cy' ) < plot.config.height ){
                    plot.content.append( 'line' )
                        .attr( 'stroke', 'red' )
                        .attr( 'stroke-width', 1 )
                        .attr( 'x1', datapoint.attr( 'cx' ) )
                        .attr( 'y1', datapoint.attr( 'cy' ) + plot.config.datapointSize )
                        .attr( 'x2', datapoint.attr( 'cx' ) )
                        .attr( 'y2', plot.config.height )
                        .classed( 'hoverline', true );
                }

                var datapointWindowPos = $( this ).offset();
                plot.datapointInfoBox = plot.infoBox(
                    datapointWindowPos.top, datapointWindowPos.left,
                    plot.infoHtml( xCol[ i ], yCol[ i ], ( ids )?( ids[ i ] ):( undefined ) )
                );
                $( 'body' ).append( plot.datapointInfoBox );
            })
            .on( 'mouseout', function(){
                d3.select( this )
                    .style( 'fill', 'black' )
                    .style( 'fill-opacity', 0.2 );
                plot.content.selectAll( '.hoverline' ).remove();
                if( plot.datapointInfoBox ){
                    plot.datapointInfoBox.remove();
                }
            });
    },
    
    this.render = function( columnData, meta ){
        this.log( this + '.render', arguments );
        this.log( '\t config:', this.config );

        // prepare the data
        //pre: columns passed are numeric
        //pre: at least two columns are passed
        //assume: first column is x, second column is y, any remaining aren't used
        var xCol = columnData[0],
            yCol = columnData[1],
            ids = ( columnData.length > 2 )?( columnData[2] ):( undefined );
        //this.log( this + '.render', xCol.length, yCol.length, this.config );
        
        //pre: xCol.len == yCol.len
        xCol = this.preprocessData( xCol );
        yCol = this.preprocessData( yCol );
        this.log( 'xCol len', xCol.length, 'yCol len', yCol.length );
        
        this.findMinMaxes( xCol, yCol, meta );
        //this.log( 'xMin, xMax, yMin, yMax:', this.xMin, this.xMax, this.yMin, this.yMax );
        this.setUpScales();

        // find (or build if it doesn't exist) the svg dom infrastructure
        if( !this.svg ){ this.svg = d3.select( 'svg' ).attr( "class", "chart" ); }
        if( !this.content ){
            this.content = this.svg.append( "svg:g" ).attr( "class", "content" ).attr( 'id', this.config.id );
        }
        //this.log( 'svg:', this.svg );
        //this.log( 'content:', this.content );

        this.adjustChartDimensions();
        
        if( !this.xAxis ){ this.xAxis = this.content.append( 'g' ).attr( 'class', 'axis' ).attr( 'id', 'x-axis' ); }
        if( !this.xAxisLabel ){
            this.xAxisLabel = this.xAxis.append( 'text' ).attr( 'class', 'axis-label' ).attr( 'id', 'x-axis-label' );
        }
        //this.log( 'xAxis:', this.xAxis, 'xAxisLabel:', this.xAxisLabel );

        if( !this.yAxis ){ this.yAxis = this.content.append( 'g' ).attr( 'class', 'axis' ).attr( 'id', 'y-axis' ); }
        if( !this.yAxisLabel ){
            this.yAxisLabel = this.yAxis.append( 'text' ).attr( 'class', 'axis-label' ).attr( 'id', 'y-axis-label' );
        }
        //this.log( 'yAxis:', this.yAxis, 'yAxisLabel:', this.yAxisLabel );
        
        this.setUpXAxis();
        this.setUpYAxis();
        
        this.renderGrid();
        this.renderDatapoints( xCol, yCol, ids );
    };

    this.infoHtml = function( x, y, id ){
        var retDiv = $( '<div/>' );
        if( id ){
            $( '<div/>' ).text( id ).css( 'font-weight', 'bold' ).appendTo( retDiv );
        }
        $( '<div/>' ).text( x ).appendTo( retDiv );
        $( '<div/>' ).text( y ).appendTo( retDiv );
        return retDiv.html();
    };

    //TODO: html for now
    this.infoBox = function( top, left, html, adjTop, adjLeft ){
        adjTop  = adjTop  || 0;
        adjLeft = adjLeft || 20;
        var infoBox = $( '<div />' )
            .addClass( 'chart-info-box' )
            .css({
                'position'  : 'absolute',
                'top'       : top  + adjTop,
                'left'      : left + adjLeft
            });
        infoBox.html( html );
        return infoBox;
    };

}

//==============================================================================
