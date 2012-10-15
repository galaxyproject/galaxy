define([
    "../libs/underscore",
    
    "../mvc/base-mvc",
    "../utils/LazyDataLoader",
    "../templates/compiled/template-visualization-scatterplotControlForm",
    "../templates/compiled/template-visualization-statsTable",
    "../templates/compiled/template-visualization-chartSettings",
    
    "../libs/d3",
    
    "../libs/bootstrap",
    "../libs/jquery/jquery-ui-1.8.23.custom.min"
], function(){

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
        yAxisLabelBumpX : -35,
        width   : 500,
        height  : 500,
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
    
    this.updateConfig = function( newConfig, rerender ){
        // setter for chart config
        //TODO: validate here
        _.extend( this.config, newConfig );
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
    //NOTE: called on new
    this.svg = d3.select( this.config.containerSelector )
        .append( "svg:svg" ).attr( "class", "chart" );
        
    this.content = this.svg.append( "svg:g" ).attr( "class", "content" ).attr( 'id', this.config.id );
    
    this.xAxis = this.content.append( 'g' ).attr( 'class', 'axis' ).attr( 'id', 'x-axis' );
    this.xAxisLabel = this.xAxis.append( 'text' ).attr( 'class', 'axis-label' ).attr( 'id', 'x-axis-label' );
    
    this.yAxis = this.content.append( 'g' ).attr( 'class', 'axis' ).attr( 'id', 'y-axis' );
    this.yAxisLabel = this.yAxis.append( 'text' ).attr( 'class', 'axis-label' ).attr( 'id', 'y-axis-label' );
    
    //this.log( 'built svg:', d3.selectAll( 'svg' ) );
    
    this.adjustChartDimensions = function( top, right, bottom, left ){
        //this.log( this + '.adjustChartDimensions', arguments );
        top = top || 0;
        right = right || 0;
        bottom = bottom || 0;
        left = left || 0;
        this.svg
            .attr( "width",  this.config.width +  ( this.config.marginRight  + right ) + 
                                                  ( this.config.marginLeft   + left ) )
            .attr( "height", this.config.height + ( this.config.marginTop    + top ) +
                                                  ( this.config.marginBottom + bottom ) )
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
    
    this.setUpDomains = function( xCol, yCol, meta ){
        //this.log( this + '.setUpDomains', arguments );
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
        
        this.xLongestLabel = d3.max( _.map( [ this.xMin, this.xMax ],
                                     function( number ){ return ( String( number ) ).length; } ) );
        //this.log( 'xLongestLabel:', this.xLongestLabel );
        
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
        //this.log( 'xAxisLabel:', this.xAxisLabel );
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
    
        // get the tick labels for the y axis
        var yTickLabels = this.yAxis.selectAll( 'text' ).filter( function( e, i ){ return i !== 0; } );
        //this.log( 'yTickLabels:', yTickLabels );
        
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
    //TODO: these to config ...somehow
    //TODO: use these in renderDatapoints ...somehow
    this.glyphEnterState = function( d3Elem ){
        
    };
    this.glyphFinalState = function( d3Elem ){
        
    };
    this.glyphExitState = function( d3Elem ){
        
    };
    
    // initial render or complete re-render (REPLACE datapoints)
    this.renderDatapoints = function( xCol, yCol, ids ){
        this.log( this + '.renderDatapoints', arguments );
        var count = 0;
        
        this.datapoints = this.addDatapoints( xCol, yCol, ids, ".glyph" );
        
        // glyphs that need to be removed: transition to from normal state to 'exit' state, remove from DOM
        this.datapoints.exit()
            .each( function(){ count += 1; } )
            .transition().duration( this.config.animDuration )
                .attr( "cy", this.config.height )
                .attr( "r", 0 )
            .remove();
        this.log( count, ' glyphs removed' );
        
        //this.log( this.datapoints.length, ' glyphs in the graph' );
    };
    
    // adding points to existing
    this.addDatapoints = function( newXCol, newYCol, ids, selectorForExisting ){
        this.log( this + '.addDatapoints', arguments );
        // ADD datapoints to plot that's already rendered
        //  if selectorForExisting === undefined (as in not passed), addDatapoints won't update existing
        //  pass in the class ( '.glyph' ) to update exising datapoints
        var plot = this,
            count = 0,
            xPosFn = function( d, i ){
                //if( d ){ this.log( 'x.data:', newXCol[ i ], 'plotted:', plot.xScale( newXCol[ i ] ) ); }
                return plot.xScale( newXCol[ i ] );
            },
            yPosFn = function( d, i ){
                //if( d ){ this.log( 'y.data:', newYCol[ i ], 'plotted:', plot.yScale( newYCol[ i ] ) ); }
                return plot.yScale( newYCol[ i ] );
            };
    
        // select all existing glyphs and compare to incoming data
        //  enter() will yield those glyphs that need to be added
        var newDatapoints = this.content.selectAll( selectorForExisting );
        this.log( 'existing datapoints:', newDatapoints );
        newDatapoints = newDatapoints.data( newXCol );
            
        // enter - new data to be added as glyphs: give them a 'entry' position and style
        count = 0;
        newDatapoints.enter()
            .append( 'svg:circle' )
                .each( function(){ count += 1; } )
                .classed( "glyph", true )
                .attr( "cx", xPosFn )
                .attr( "cy", yPosFn )
                // start all bubbles small...
                .attr( "r", 0 );
        this.log( count, ' new glyphs created' );
        
        // for all existing glyphs and those that need to be added: transition anim to final state
        count = 0;
        newDatapoints
            // ...animate to final position
            .transition().duration( this.config.animDuration )
                .each( function(){ count += 1; } )
                .attr( "cx", xPosFn )
                .attr( "cy", yPosFn )
                .attr( "r", plot.config.datapointSize );
        this.log( count, ' existing glyphs transitioned' );
        
        // attach ids
        if( ids ){
            newDatapoints.attr( 'data', function( d, i ){ return ( ids[ i ] ); } );
        }

        // titles
        newDatapoints.attr( 'title', function( d, i ){
            return (( ids )?( ids[ i ] + ': ' ):( '' )) + newXCol[ i ] + ', ' + newYCol[ i ];
        });
        
        // events
        newDatapoints
            //TODO: remove magic numbers
            .on( 'mouseover', function(){
                var datapoint = d3.select( this );
                datapoint
                    .style( 'fill', 'red' )
                    .style( 'fill-opacity', 1 );
                
                // create horiz, vert lines to axis
                plot.content.append( 'line' )
                    .attr( 'stroke', 'red' )
                    .attr( 'stroke-width', 1 )
                    .attr( 'x1', datapoint.attr( 'cx' ) ).attr( 'y1', datapoint.attr( 'cy' ) )
                    .attr( 'x2', 0 ).attr( 'y2', datapoint.attr( 'cy' ) )
                    .classed( 'hoverline', true );
                plot.content.append( 'line' )
                    .attr( 'stroke', 'red' )
                    .attr( 'stroke-width', 1 )
                    .attr( 'x1', datapoint.attr( 'cx' ) ).attr( 'y1', datapoint.attr( 'cy' ) )
                    .attr( 'x2', datapoint.attr( 'cx' ) ).attr( 'y2', plot.config.height )
                    .classed( 'hoverline', true );
            })
            .on( 'mouseout', function(){
                d3.select( this )
                    .style( 'fill', 'black' )
                    .style( 'fill-opacity', 0.2 );
                    
                d3.selectAll( '.hoverline' ).remove();
            });
        
        return newDatapoints;
    };
    
    this.render = function( columnData, meta ){
        this.log( this + '.render', arguments );
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
        
        this.setUpDomains( xCol, yCol, meta );
        //this.log( 'xMin, xMax, yMin, yMax:', this.xMin, this.xMax, this.yMin, this.yMax );
        
        this.setUpScales();
        this.adjustChartDimensions();
    
        this.setUpXAxis();
        this.setUpYAxis();
        
        this.renderGrid();
        this.renderDatapoints( xCol, yCol, ids );
    };
}

//==============================================================================
/**
 *  Scatterplot control UI as a backbone view
 *      handles:
 *          getting the desired data
 *          configuring the plot display
 *          showing (general) statistics
 *
 *  initialize attributes REQUIRES a dataset and an apiDatasetsURL
 */
var ScatterplotControlForm = BaseView.extend( LoggableMixin ).extend({
    //logger      : console,
    className   : 'scatterplot-settings-form',
    
    dataLoadDelay : 500,
    dataLoadSize  : 3001,

    loadingIndicatorImage : 'loading_large_white_bg.gif',
    
    initialize : function( attributes ){
        if( this.logger ){ window.form = this; }
        
        this.dataset = null;
        this.chartConfig = null;
        this.plot = null;
        this.loader = null;

        this.$statsPanel = null;
        this.$chartSettingsPanel = null;
        this.$dataSettingsPanel = null;
        this.dataFetch = null;

        this.initializeFromAttributes( attributes );
        this.initializeChart( attributes );
        this.initializeDataLoader( attributes );
    },

    initializeFromAttributes : function( attributes ){
        // ensure certain vars we need are passed in attributes
        if( !attributes || !attributes.dataset ){
            throw( "ScatterplotView requires a dataset" );
        } else {
            this.dataset = attributes.dataset;
        }
        if( jQuery.type( this.dataset.metadata_column_types ) === 'string' ){
            this.dataset.metadata_column_types = this.dataset.metadata_column_types.split( ', ' );
        }
        this.log( 'dataset:', this.dataset );

        // passed from mako helper
        //TODO: integrate to galaxyPaths
        if( !attributes.apiDatasetsURL ){
            throw( "ScatterplotView requires a apiDatasetsURL" );
        } else {
            this.dataURL = attributes.apiDatasetsURL + '/' + this.dataset.id + '?';
        }
        this.log( 'this.dataURL:', this.dataURL );
    },

    initializeChart : function( attributes ){
        // set up the basic chart infrastructure and config (if any)
        this.chartConfig = attributes.chartConfig || {};
        if( this.logger ){ this.chartConfig.debugging = true; }
        this.log( 'initial chartConfig:', this.chartConfig );
        this.plot = new TwoVarScatterplot( this.chartConfig );
        this.chartConfig = this.plot.config;
    },

    initializeDataLoader : function( attributes ){
        // set up data loader
        var view = this;
        this.loader = new LazyDataLoader({
            logger  : ( this.logger )?( this.logger ):( null ),
            // we'll generate this when columns are chosen
            url     : null,
            start   : attributes.start || 0,
            //NOTE: metadata_data_lines can be null (so we won't know the total)
            total   : attributes.total || this.dataset.metadata_data_lines,
            delay   : this.dataLoadDelay,
            size    : this.dataLoadSize,

            buildUrl : function( start, size ){
                // currently VERY SPECIFIC to using data_providers.py start_val, max_vals params
                return this.url + '&' + jQuery.param({
                    start_val: start,
                    max_vals:  size
                });
            }
        });
        $( this.loader ).bind( 'error', function( event, status, error ){
            view.log( 'ERROR:', status, error );
            alert( 'ERROR fetching data:\n' + status + '\n' + error );
            view.hideLoadingIndicator();
        });
    },
    
    // ------------------------------------------------------------------------- CONTROLS RENDERING
    render : function(){
        // render the data/chart control forms (but not the chart)
        var view = this,
            formData = {
                config : this.chartConfig,
                allColumns : [],
                numericColumns : [],
                loadingIndicatorImagePath : galaxy_paths.get( 'image_path' ) + '/' + this.loadingIndicatorImage
            };
        
        // gather column indeces (from metadata_column_types) and names (from metadata_columnnames)
        _.each( this.dataset.metadata_column_types, function( type, index ){
            //TODO: using 0-based indeces
            // label with the name if available (fall back on 'column <index>')
            var name = 'column ' + ( index + 1 );
            if( view.dataset.metadata_column_names ){
                name = view.dataset.metadata_column_names[ index ];
            }
            
            // filter numeric columns to their own list
            if( type === 'int' || type === 'float' ){
                formData.numericColumns.push({ index: index, name: name });
            }
            formData.allColumns.push({ index: index, name: name });
        });
        
        //TODO: other vals: max_vals, start_val, pagination (plot-settings)
        
        // render template and set up panels, store refs
        this.$el.append( ScatterplotControlForm.templates.form( formData ) );
        this.$dataSettingsPanel  = this.$el.find( '.tab-pane#data-settings' );
        this.$chartSettingsPanel = this._render_chartSettings();
        this.$statsPanel         = this.$el.find( '.tab-pane#chart-stats' );
        
        //this.$el.find( 'ul.nav' ).find( 'a[href="#chart-settings"]' ).tab( 'show' );
        return this;
    },

    _render_chartSettings : function(){
        // chart settings panel
        var chartControl = this,
            $chartSettingsPanel = this.$el.find( '.tab-pane#chart-settings' ),
            // limits for controls (by control/chartConfig id)
            //TODO: move into TwoVarScatterplot
            controlRanges = {
                'datapointSize' : { min: 2, max: 10, step: 1 },
                'width'         : { min: 200, max: 800, step: 20 },
                'height'        : { min: 200, max: 800, step: 20 }
            };
            
        // render the html
        $chartSettingsPanel.append( ScatterplotControlForm.templates.chartSettings( this.chartConfig ) );
        
        // set up js on sliders
        $chartSettingsPanel.find( '.numeric-slider-input' ).each( function(){
            var $this = $( this ),
                $output = $this.find( '.slider-output' ),
                $slider = $this.find( '.slider' ),
                id = $this.attr( 'id' );
            //chartControl.log( 'slider set up', 'this:', $this, 'slider:', $slider, 'id', id );
                
            // what to do when the slider changes: update display and update chartConfig
            function onSliderChange(){
                var $this = $( this ),
                    newValue = $this.slider( 'value' );
                //chartControl.log( 'slider change', 'this:', $this, 'output:', $output, 'value', newValue );
                $output.text( newValue );
                //chartControl.chartConfig[ id ] = newValue;
            }
        
            $slider.slider( _.extend( controlRanges[ id ], {
                value   : chartControl.chartConfig[ id ],
                change  : onSliderChange,
                slide   : onSliderChange
            }));
        });
        
        return $chartSettingsPanel;
    },
    
    // ------------------------------------------------------------------------- EVENTS
    events : {
        'click #include-id-checkbox'            : 'toggleThirdColumnSelector',
        'click #data-settings #render-button'   : 'renderPlot',
        'click #chart-settings #render-button'  : 'changeChartSettings'
    },

    toggleThirdColumnSelector : function(){
        // show/hide the id selector on the data settings panel
        this.$el.find( 'select[name="ID"]' ).parent().toggle();
    },
    
    showLoadingIndicator : function( message, callback ){
        // display the loading indicator over the tab panels if hidden, update message (if passed)
        message = message || '';
        var indicator = this.$el.find( 'div#loading-indicator' );
            messageBox = indicator.find( '.loading-message' );
            
        if( indicator.is( ':visible' ) ){
            if( message ){
                messageBox.fadeOut( 'fast', function(){
                    messageBox.text( message );
                    messageBox.fadeIn( 'fast', callback );
                });
            } else {
                callback();
            }
            
        } else {
            if( message ){ messageBox.text( message ); }
            indicator.fadeIn( 'fast', callback );
        }
    },

    hideLoadingIndicator : function( callback ){
        this.$el.find( 'div#loading-indicator' ).fadeOut( 'fast', callback );
    },
    
    // ------------------------------------------------------------------------- GRAPH/STATS RENDERING
    renderPlot : function(){
        // fetch the data, (re-)render the chart
        //TODO: separate data fetch
        var view = this;

        // this is a complete re-render, so clear the prev. data
        view.data = null;
        view.meta = null;
        
        // update the chartConfig (here and plot) using graph settings
        //TODO: separate and improve (used in changeChartSettings too)
        _.extend( this.chartConfig, this.getGraphSettings() );
        this.log( 'this.chartConfig:', this.chartConfig );
        this.plot.updateConfig( this.chartConfig, false );
        
        // build the url with the current data settings
        this.loader.url   = this.dataURL + '&' + jQuery.param( this.getDataSettings() );
        this.log( 'this.loader, url:', this.loader.url, 'total:', this.loader.total );

        // bind the new data event to: aggregate data, update the chart and stats with new data
        $( this.loader ).bind( 'loaded.new', function( event, response ){
            view.log( view + ' loaded.new', response );

            // aggregate data and meta
            view.postProcessDataFetchResponse( response );
            view.log( 'postprocessed data:', view.data, 'meta:', view.meta );

            // update the graph and stats
            view.showLoadingIndicator( 'Rendering...', function(){
                view.$el.find( 'ul.nav' ).find( 'a[href="#chart-stats"]' ).tab( 'show' );

                view.plot.render( view.data, view.meta );
                view.renderStats( view.data, view.meta );
                view.hideLoadingIndicator();
            });
        });
        // when all data loaded - unbind (or we'll start doubling event handlers)
        $( this.loader ).bind( 'complete', function( event, data ){
            view.log( 'complete', data );
            $( view.loader ).unbind();
        });

        // begin loading the data
        view.showLoadingIndicator( 'Fetching data...', function(){ view.loader.load(); });
    },

    renderStats : function(){
        // render the stats table in the stats panel
        //TODO: there's a better way
        this.$statsPanel.html( ScatterplotControlForm.templates.statsTable({
            stats:  [
                { name: 'Count',    xval: this.meta[0].count,   yval: this.meta[1].count },
                { name: 'Min',      xval: this.meta[0].min,     yval: this.meta[1].min },
                { name: 'Max',      xval: this.meta[0].max,     yval: this.meta[1].max },
                { name: 'Sum',      xval: this.meta[0].sum,     yval: this.meta[1].sum },
                { name: 'Mean',     xval: this.meta[0].mean,    yval: this.meta[1].mean },
                { name: 'Median',   xval: this.meta[0].median,  yval: this.meta[1].median }
            ]
        }));
    },

    changeChartSettings : function(){
        // re-render the chart with new chart settings and OLD data
        var view = this;
            newGraphSettings = this.getGraphSettings();

        // update the chart config from the chartSettings panel controls
        this.log( 'newGraphSettings:', newGraphSettings );
        _.extend( this.chartConfig, newGraphSettings );
        this.log( 'this.chartConfig:', this.chartConfig );
        this.plot.updateConfig( this.chartConfig, false );

        // if there's current data, call plot.render with it (no data fetch)
        if( view.data && view.meta ){
            view.showLoadingIndicator( 'Rendering...', function(){
                view.plot.render( view.data, view.meta );
                view.hideLoadingIndicator();
            });

        // no current data, call renderPlot instead (which will fetch data)
        } else {
            this.renderPlot();
        }
    },

    // ------------------------------------------------------------------------- DATA AGGREGATION
    postProcessDataFetchResponse : function( response ){
        // the loader only returns new data - it's up to this to munge the fetches together properly
        //TODO: we're now storing data in two places: loader and here
        //  can't we reduce incoming data into loader.data[0]? are there concurrency problems?
        this.postProcessData( response.data );
        this.postProcessMeta( response.meta );
    },
    
    postProcessData : function( newData ){
        // stack the column data on top of each other into this.data
        var view = this;

        // if we already have data: aggregate
        if( view.data ){
            _.each( newData, function( newColData, colIndex ){
                //view.log( colIndex + ' data:', newColData );
                //TODO??: time, space efficiency of this?
                view.data[ colIndex ] = view.data[ colIndex ].concat( newColData );
            });
            
        // otherwise: assign (first load)
        } else {
            view.data = newData;
        }
    },

    postProcessMeta : function( newMeta ){
        // munge the meta data (stats) from the server fetches together
        //pre: this.data must be preprocessed (needed for medians)
        var view = this,
            colTypes = this.dataset.metadata_column_types;

        // if we already have meta: aggregate
        if( view.meta ){
            _.each( newMeta, function( newColMeta, colIndex ){
                var colMeta = view.meta[ colIndex ],
                    colType = colTypes[ colIndex ];
                view.log( colIndex + ' postprocessing meta:', newColMeta );
                //view.log( colIndex + ' old meta:',
                //    'min:',     colMeta.min,
                //    'max:',     colMeta.max,
                //    'sum:',     colMeta.sum,
                //    'mean:',    colMeta.mean,
                //    'median:',  colMeta.median
                //);

                //!TODO: at what point are we getting int/float overflow on these?!
                //??: need to be null safe?
                colMeta.count += ( newColMeta.count )?( newColMeta.count ):( 0 );
                view.log( colIndex, 'count:', colMeta.count );
                
                if( ( colType === 'int' ) || ( colType === 'float' ) ){
                    //view.log( colIndex + ' incoming meta:',
                    //    'min:',     newColMeta.min,
                    //    'max:',     newColMeta.max,
                    //    'sum:',     newColMeta.sum,
                    //    'mean:',    newColMeta.mean,
                    //    'median:',  newColMeta.median
                    //);

                    colMeta.min  = Math.min( newColMeta.min, colMeta.min );
                    colMeta.max  = Math.max( newColMeta.max, colMeta.max );
                    colMeta.sum  = newColMeta.sum + colMeta.sum;
                    colMeta.mean = ( colMeta.count )?( colMeta.sum / colMeta.count ):( null );

                    // median's a pain bc of sorting (requires the data as well)
                    var sortedCol = view.data[ colIndex ].slice().sort(),
                        middleIndex = Math.floor( sortedCol.length / 2 );

                    if( sortedCol.length % 2 === 0 ){
                        colMeta.median = ( ( sortedCol[ middleIndex ] + sortedCol[( middleIndex + 1 )] ) / 2 );

                    } else {
                        colMeta.median = sortedCol[ middleIndex ];
                    }

                    //view.log( colIndex + ' new meta:',
                    //    'min:',     colMeta.min,
                    //    'max:',     colMeta.max,
                    //    'sum:',     colMeta.sum,
                    //    'mean:',    colMeta.mean,
                    //    'median:',  colMeta.median
                    //);
                }
            });

        // otherwise: assign (first load)
        } else {
            view.meta = newMeta;
            view.log( 'initial meta:', view.meta );
        }
    },

    // ------------------------------------------------------------------------- GET DATA/GRAPH SETTINGS
    getDataSettings : function(){
        // parse the column values for both indeces (for the data fetch) and names (for the graph)
        var columnSelections = this.getColumnSelections(),
            columns = [];
        this.log( 'columnSelections:', columnSelections );
            
        //TODO: validate columns - minimally: we can assume either set by selectors or via a good query string

        // get column indices for params, include the desired ID column (if any)
        columns = [ columnSelections.X.colIndex, columnSelections.Y.colIndex ];
        if( this.$dataSettingsPanel.find( '#include-id-checkbox' ).attr( 'checked' ) ){
            columns.push( columnSelections.ID.colIndex );
        }
        
        //TODO: other vals: max, start, page
        
        var params = {
            data_type   : 'raw_data',
            columns     : '[' + columns + ']'
        };
        this.log( 'params:', params );
        return params;
    },

    getColumnSelections : function(){
        // gets the current user-selected values for which columns to fetch from the data settings panel
        // returns a map: { column-select name (eg. X) : { colIndex : column-selector val,
        //                                                 colName : selected option text }, ... }
        var selections = {};
        this.$dataSettingsPanel.find( 'div.column-select select' ).each( function(){
            var $this   = $( this ),
                val     = $this.val();
            selections[ $this.attr( 'name' ) ] = {
                colIndex : val,
                colName  : $this.children( '[value="' + val + '"]' ).text()
            };
        });
        return selections;
    },

    getGraphSettings : function(){
        // gets the user-selected chartConfig from the chart settings panel
        var settings = {},
            colSelections = this.getColumnSelections();
        //this.log( 'colSelections:', colSelections );

        //TODO: simplify with keys and loop
        settings.datapointSize = this.$chartSettingsPanel.find( '#datapointSize.numeric-slider-input' )
            .find( '.slider' ).slider( 'value' );
        settings.width = this.$chartSettingsPanel.find( '#width.numeric-slider-input' )
            .find( '.slider' ).slider( 'value' );
        settings.height = this.$chartSettingsPanel.find( '#height.numeric-slider-input' )
            .find( '.slider' ).slider( 'value' );

        // update axes labels using chartSettings inputs (if not at defaults), otherwise the selects' colName
        //TODO: a little confusing
        var chartSettingsXLabel = this.$chartSettingsPanel.find( 'input#X-axis-label' ).val(),
            chartSettingsYLabel = this.$chartSettingsPanel.find( 'input#Y-axis-label' ).val();
        settings.xLabel = ( chartSettingsXLabel === 'X' )?
                            ( colSelections.X.colName ):( chartSettingsXLabel );
        settings.yLabel = ( chartSettingsYLabel === 'Y' )?
                            ( colSelections.Y.colName ):( chartSettingsYLabel );

        settings.animDuration = 10;
        if( this.$chartSettingsPanel.find( '#animDuration.checkbox-input' ).is( ':checked' ) ){
            settings.animDuration = 500;
        }

        this.log( 'graphSettings:', settings );
        return settings;
    },

    toString : function(){
        return 'ScatterplotControlForm(' + this.dataset.id + ')';
    }
});

ScatterplotControlForm.templates = {
    form            : Handlebars.templates[ 'template-visualization-scatterplotControlForm' ],
    statsTable      : Handlebars.templates[ 'template-visualization-statsTable' ],
    chartSettings   : Handlebars.templates[ 'template-visualization-chartSettings' ]
};

//==============================================================================
return {
    LazyDataLoader          : LazyDataLoader,
    TwoVarScatterplot       : TwoVarScatterplot,
    ScatterplotControlForm  : ScatterplotControlForm
};});
