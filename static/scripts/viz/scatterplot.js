/* =============================================================================
todo:
    outside this:
        BUG: visualization menu doesn't disappear
        BUG?: get column_names (from datatype if necessary)
        BUG: single vis in popupmenu should have tooltip with that name NOT 'Visualizations'
    
    ??: maybe better to do this with a canvas...
    
    move renderScatter plot to obj, possibly view?
    
    fix x axis - adjust ticks when tick labels are long - move odds down and extend tick line
    
    provide callback in view to load data incrementally - for large sets
    
    paginate
        handle rerender
        use endpoint (here and on the server (fileptr))
    fetch (new?) data
        handle rerender
        
    selectable list of preset column comparisons (rnaseq etc.)
    multiple plots on one page (small multiples)
    
    where are bad dataprovider params handled? api/datasets?
        
    config changes to the graph
    render stats on the data (max, min, count)
    render warning on long data (> maxDataPoints)
        adjust endpoint
    
    loading indicator
    
    download svg -> base64 encode
    dress up ui
 
    incorporate glyphs, glyph state renderers
 
    validate columns selection (here or server)

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
    var plot = this,
        GUESS_AT_SVG_CHAR_WIDTH = 10,
        GUESS_AT_SVG_CHAR_HEIGHT = 12,
        PADDING = 8,
        X_LABEL_TOO_LONG_AT = 5;
        
    //this.debugging = true;
    this.log = function(){
        if( this.debugging && console && console.debug ){
            var args = Array.prototype.slice.call( arguments );
            args.unshift( this.toString() );
            console.debug.apply( null, args );
        }
    };
    this.log( 'new TwoVarScatterplot:', config );
    
    // ........................................................ set up chart config
    // config will default to these values when not passed in
    //NOTE: called on new
    this.defaults = {
        id : 'TwoVarScatterplot',
        containerSelector : 'body',
        maxDataPoints : 30000,
        bubbleRadius : 4,
        entryAnimDuration : 500,
        //TODO: no effect?
        xNumTicks : 10,
        yNumTicks : 10,
        xAxisLabelBumpY : 40,
        yAxisLabelBumpX : -35,
        width : 500,
        height : 500,
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
    
    this.updateConfig = function( newConfig ){
        _.extend( this.config, newConfig );
    };
    
    // ........................................................ helpers
    this.toString = function(){
        return this.config.id;
    };
    this.translateStr = function( x, y ){
        return 'translate(' + x + ',' + y + ')';
    };
    this.rotateStr = function( d, x, y ){
        return 'rotate(' + d + ',' + x + ',' + y + ')';
    };

    // ........................................................ initial element creation
    //NOTE: called on new
    this.svg = d3.select( this.config.containerSelector )
        .append( "svg:svg" ).attr( "class", "chart" ).style( 'display', 'none' );
    this.content = this.svg.append( "svg:g" ).attr( "class", "content" );
    
    this.xAxis = this.content.append( 'g' ).attr( 'class', 'axis' ).attr( 'id', 'x-axis' );
    this.xAxisLabel = this.xAxis.append( 'text' ).attr( 'class', 'axis-label' ).attr( 'id', 'x-axis-label' );
    
    this.yAxis = this.content.append( 'g' ).attr( 'class', 'axis' ).attr( 'id', 'y-axis' );
    this.yAxisLabel = this.yAxis.append( 'text' ).attr( 'class', 'axis-label' ).attr( 'id', 'y-axis-label' );
    
    this.log( 'built svg:', d3.selectAll( 'svg' ) );
    
    this.adjustChartDimensions = function(){
        this.svg
            .attr( "width",  this.config.width +  ( this.config.marginRight + this.config.marginLeft ) )
            .attr( "height", this.config.height + ( this.config.marginTop   + this.config.marginBottom ) )
            // initial is hidden - show it
            .style( 'display', 'block' );
            
        // move content group away from margins
        this.content = this.svg.select( "g.content" )       
            .attr( "transform", this.translateStr( this.config.marginLeft, this.config.marginTop ) );
    };
    
    // ........................................................ data and scales
    this.preprocessData = function( data ){
        // set a cap on the data, limit to first n points
        return data.slice( 0, this.config.maxDataPoints );
    };
    
    this.setUpDomains = function( xCol, yCol ){
        this.xMin = this.config.xMin || d3.min( xCol );
        this.xMax = this.config.xMax || d3.max( xCol );
        this.yMin = this.config.yMin || d3.min( yCol );
        this.yMax = this.config.yMax || d3.max( yCol );
    };
    
    this.setUpScales = function(){
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
        // origin: bottom, left
        //TODO: incoporate top, right
        this.xAxisFn = d3.svg.axis()
            .scale( this.xScale )
            .ticks( this.config.xNumTicks )
            .orient( 'bottom' );
        this.xAxis// = content.select( 'g#x-axis' )
            .attr( 'transform', this.translateStr( 0, this.config.height ) )
            .call( this.xAxisFn );
        this.log( 'xAxis:', this.xAxis );
        
        //TODO: this isn't reliable with -/+ ranges - better to go thru each tick
        this.xLongestLabel = d3.max( _.map( [ this.xMin, this.xMax ],
                                     function( number ){ return ( String( number ) ).length; } ) );
        this.log( 'xLongestLabel:', this.xLongestLabel );
        
        if( this.xLongestLabel >= X_LABEL_TOO_LONG_AT ){
            //TODO: adjust ticks when tick labels are long - move odds down and extend tick line
            // (for now) hide them
            this.xAxis.selectAll( 'g' ).filter( ':nth-child(odd)' ).style( 'display', 'none' );
        }
        
        this.xAxisLabel// = xAxis.select( 'text#x-axis-label' )
            .attr( 'x', this.config.width / 2 )
            .attr( 'y', this.config.xAxisLabelBumpY )
            .attr( 'text-anchor', 'middle' )
            .text( this.config.xLabel );
        this.log( 'xAxisLabel:', this.xAxisLabel );
    };

    this.setUpYAxis = function(){
        this.yAxisFn = d3.svg.axis()
            .scale( this.yScale )
            .ticks( this.config.yNumTicks )
            .orient( 'left' );
        this.yAxis// = content.select( 'g#y-axis' )
            .call( this.yAxisFn );
        this.log( 'yAxis:', this.yAxis );
    
        this.yLongestLabel = d3.max( _.map( [ this.yMin, this.yMax ],
                                     function( number ){ return ( String( number ) ).length; } ) );
        this.log( 'yLongestLabel:', this.yLongestLabel );
        
        //TODO: ugh ... so clumsy
        //TODO: this isn't reliable with -/+ ranges - better to go thru each tick
        var neededY = this.yLongestLabel * GUESS_AT_SVG_CHAR_WIDTH + ( PADDING );
            
        // increase width for xLongerStr, increase margin for y
        //TODO??: (or transform each number: 2k)
        if( this.config.yAxisLabelBumpX > -( neededY ) ){
            this.config.yAxisLabelBumpX = -( neededY );
        }
        if( this.config.marginLeft < neededY ){
            this.config.marginLeft = neededY + GUESS_AT_SVG_CHAR_HEIGHT;
            // update dimensions, translations
            this.adjustChartDimensions();
        }
        this.log( 'this.config.yAxisLableBumpx, this.config.marginLeft:',
                  this.config.yAxisLabelBumpX, this.config.marginLeft );
        
        this.yAxisLabel// = yAxis.select( 'text#y-axis-label' )
            .attr( 'x', this.config.yAxisLabelBumpX )
            .attr( 'y', this.config.height / 2 )
            .attr( 'text-anchor', 'middle' )
            .attr( 'transform', this.rotateStr( -90, this.config.yAxisLabelBumpX, this.config.height / 2 ) )
            .text( this.config.yLabel );
        this.log( 'yAxisLabel:', this.yAxisLabel ); 
    };
    
    // ........................................................ grid lines
    this.renderGrid = function(){
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
        this.log( 'vGridLines:', this.vGridLines ); 

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
        this.log( 'hGridLines:', this.hGridLines );
    };
    
    // ........................................................ data points
    //TODO: these to config ...somehow
    //TODO: use these in renderDatapoints ...somehow
    this.glyphEnterState = function( d3Elem ){
        
    };
    this.glyphFinalState = function( d3Elem ){
        
    };
    this.glyphExitState = function( d3Elem ){
        
    };
    
    this.renderDatapoints = function( xCol, yCol ){
        
        var xPosFn = function( d, i ){
            return plot.xScale( xCol[ i ] );
        };
        var yPosFn = function( d, i ){
            return plot.yScale( yCol[ i ] );
        };
    
        // select all existing glyphs and compare to incoming data
        //  enter() will yield those glyphs that need to be added
        //  exit() will yield existing glyphs that need to be removed
        this.datapoints = this.content.selectAll( ".glyph" )
            .data( xCol );
            
        // enter - new data to be added as glyphs: give them a 'entry' position and style
        this.datapoints.enter()
            .append( "svg:circle" ).attr( "class", "glyph" )
                // start all bubbles at corner...
                .attr( "cx", xPosFn )
                .attr( "cy", 0 )
                .attr( "r", 0 );
        
        // for all existing glyphs and those that need to be added: transition anim to final state
        this.datapoints
            // ...animate to final position
            .transition().duration( this.config.entryAnimDuration )
                .attr( "cx", xPosFn )
                .attr( "cy", yPosFn )            
                .attr( "r", this.config.bubbleRadius );
        
        // glyphs that need to be removed: transition to from normal state to 'exit' state, remove from DOM
        this.datapoints.exit()
            .transition().duration( this.config.entryAnimDuration )
                .attr( "cy", this.config.height )
                .attr( "r", 0 )
                .style( "fill-opacity", 0 )
            .remove();
        
        this.log( this.datapoints, 'glyphs rendered' );
    };
    
    this.render = function( xCol, yCol ){
        //pre: columns passed are numeric
        this.log( 'renderScatterplot', xCol.length, yCol.length, this.config );
        
        //pre: xCol.len == yCol.len
        //TODO: ^^ isn't necessarily true with current ColumnDataProvider
        xCol = this.preprocessData( xCol );
        yCol = this.preprocessData( yCol );
        this.log( 'xCol len', xCol.length, 'yCol len', yCol.length );
        
        //TODO: compute min, max on server.
        this.setUpDomains( xCol, yCol );
        this.log( 'xMin, xMax, yMin, yMax:', this.xMin, this.xMax, this.yMin, this.yMax );
        
        this.setUpScales();
        this.adjustChartDimensions();
    
        this.setUpXAxis();
        this.setUpYAxis();
        
        this.renderGrid();
        this.renderDatapoints( xCol, yCol );
        //TODO: on hover red line to axes, display values
    };
}

//// ugh...this seems like the wrong way to use models
//var ScatterplotModel = BaseModel.extend( LoggableMixin ).extend({
//    logger        : console
//});

var ScatterplotView = BaseView.extend( LoggableMixin ).extend({
    //logger        : console,
    tagName     : 'form',
    className     : 'scatterplot-settings-form',
    
    events : {
        'click #render-button' : 'renderScatterplot'
    },
    
    initialize : function( attributes ){
        if( !attributes.dataset ){
            throw( "ScatterplotView requires a dataset" );
        } else {
            this.dataset = attributes.dataset;
        }
        this.apiDatasetsURL = attributes.apiDatasetsURL;
        this.chartConfig = attributes.chartConfig || {};
        this.log( 'this.chartConfig:', this.chartConfig );
        
        this.plot = new TwoVarScatterplot( this.chartConfig );
    },
    
    render : function(){
        //TODO: to template
        var view = this,
            html = '',
            columnHtml = '';
        // build column select controls for each x, y (based on name if available)
        // ugh...hafta preprocess 
        this.dataset.metadata_column_types = this.dataset.metadata_column_types.split( ', ' );
        _.each( this.dataset.metadata_column_types, function( type, index ){
            // use only numeric columns
            if( type === 'int' || type === 'float' ){
                var name = 'column ' + index;
                // label with the name if available
                if( view.dataset.metadata_column_names ){
                    name = view.dataset.metadata_column_names[ index ];
                }
                columnHtml += '<option value="' + index + '">' + name + '</column>';
            }
        });
        
        // column selector containers
        html += '<div id="x-column-input">';
        html += '<label for="">Data column for X: </label><select name="x-column">' + columnHtml + '</select>';
        html += '</div>';
        
        html += '<div id="y-column-input">';
        html += '<label for="">Data column for Y: </label><select name="y-column">' + columnHtml + '</select>';
        html += '</div>';
        
        html += '<input id="render-button" type="button" value="Draw" />';
        html += '<div class="clear"></div>';
        
        //TODO: other vals: max_vals, start_val, pagination
        
        this.$el.append( html );
        this.$el.find( '#render-button' );
        return this;
    },
    
    renderScatterplot : function(){
        var view = this,
            url = this.apiDatasetsURL + '/' + this.dataset.id + '?data_type=raw_data&';
            xSelector = this.$el.find( '[name="x-column"]' ),
            xVal = xSelector.val(),
            xName = xSelector.children( '[value="' + xVal + '"]' ).text(),
            ySelector = this.$el.find( '[name="y-column"]' ),
            yVal = ySelector.val(),
            yName = ySelector.children( '[value="' + yVal + '"]' ).text();
            //TODO
        this.log( xName, yName );
        this.chartConfig.xLabel = xName;
        this.chartConfig.yLabel = yName;
        //TODO: alter directly
        view.plot.updateConfig( this.chartConfig );

        //TODO: validate columns - minimally: we can assume either set by selectors or via a good query string
        //TODO: other vals: max, start, page
        //TODO: chart config
        
        url += jQuery.param({
            columns : '[' + [ xVal, yVal ] + ']'
        });
        this.log( 'url:', url );
        
        jQuery.ajax({
            url : url,
            dataType : 'json',
            success : function( response ){
                view.endpoint = response.endpoint;
                view.plot.render(
                    // pull apart first two regardless of number of columns
                    _.map( response.data, function( columns ){ return columns[0]; } ),
                    _.map( response.data, function( columns ){ return columns[1]; } )
                );
            },
            error : function( xhr, status, error ){
                alert( 'ERROR:' + status + '\n' + error );
            }
        });
    }
});

