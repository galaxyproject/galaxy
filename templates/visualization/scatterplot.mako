<%inherit file="/base.mako"/>

<%def name="stylesheets()">
${parent.stylesheets()}
${h.css( "history", "autocomplete_tagging", "trackster", "overcast/jquery-ui-1.8.5.custom", "library" )}

<style type="text/css">
* { margin: 0px, padding: 0px; }

.subtitle {
	margin-left: 1em;
	margin-top: -1em;
	color: grey;
	font-size: small;
}

.chart {
	/*shape-rendering: crispEdges;*/
}

.grid-line {
	fill: none;
	stroke: lightgrey;
	stroke-opacity: 0.5;
	shape-rendering: crispEdges;
	stroke-dasharray: 3, 3;
}

.axis path, .axis line {
	fill: none;
	stroke: black;
	shape-rendering: crispEdges;
}
.axis text {
	font-family: sans-serif;
	font-size: 12px;
}


circle.bubble {
	stroke: none;
	fill: black;
	fill-opacity: 0.2;
}
	
</style>
	
</%def>

<%def name="javascripts()">
${parent.javascripts()}
${h.js( "libs/d3" )}

<script type="text/javascript">
/* =============================================================================
todo:
	validate columns (here or server)
	send: type, column title/name in JSON
	

	move to obj, possibly view?
	fetch (new?) data
	config changes to the graph
	download svg (png?)
 
============================================================================= */
function translateStr( x, y ){
	return 'translate(' + x + ',' + y + ')';
}
function rotateStr( d, x, y ){
	return 'rotate(' + d + ',' + x + ',' + y + ')';
}

$(function() {
	// Constants
	var data = ${data},
		MAX_DATA_POINTS = 30000,
		BUBBLE_RADIUS = 5,
		ENTRY_ANIM_DURATION = 500,
		X_TICKS = 10, Y_TICKS = 10,
		X_AXIS_LABEL_BUMP_Y = 40,
		Y_AXIS_LABEL_BUMP_X = -35,
		WIDTH = 300,
		HEIGHT = 300,
		MARGIN= 50,
		xLabel = "Magnitude",
		yLabel = "Depth";
		
	// set a cap on the data, limit to first n points
	data = data.slice( 0, MAX_DATA_POINTS );
	
	// split the data into columns
	//TODO: compute min, max on server.
	var col1_data = data.map( function(e) { return e[0] }),
		col2_data = data.map( function(e) { return e[1] }),
		xMin = d3.min( col1_data ),
		xMax = d3.max( col1_data ),
		yMin = d3.min( col2_data ),
		yMax = d3.max( col2_data );
	console.log( 'col1_data:', col1_data );
	console.log( 'col2_data:', col2_data );
	console.log( 'xMin, xMax, yMin, yMax:', xMin, xMax, yMin, yMax );

	// Set up.
	d3.select( "body" ).append( "svg:svg" )
	  .attr( "width",  WIDTH +  ( MARGIN * 2 ) )
	  .attr( "height", HEIGHT + ( MARGIN * 2 ) )
	  .attr( "class", "chart" );

	// Scale for x, y based on data domains
	// origin: bottom, left
	var x_scale = d3.scale.linear()
			.domain([ xMin, xMax ])
			.range([ 0, WIDTH ]),
		y_scale = d3.scale.linear()
			.domain([ yMin, yMax ])
			.range([ HEIGHT, 0 ]);
	
	//	Selection of SVG, append group (will group our entire chart), give attributes
	// apply a group and transform all coords away from margins
	var chart = d3.select( ".chart" ).append( "svg:g" )		
		.attr( "class", "content" )
		.attr( "transform", translateStr( MARGIN, MARGIN ) );

	// axes
	var xAxisFn = d3.svg.axis()
		.scale( x_scale )
		.ticks( X_TICKS )
		.orient( 'bottom' );
	var xAxis = chart.append( 'g' ).attr( 'class', 'axis' ).attr( 'id', 'x-axis' )
		.attr( 'transform', translateStr( 0, HEIGHT ) )
		.call( xAxisFn )
	console.debug( 'xAxis:', xAxis ); window.xAxis = xAxis, window.xAxisFn = xAxisFn;
	
	var xAxisLabel = xAxis.append( 'text' ).attr( 'class', 'axis-label' ).attr( 'id', 'x-axis-label' )
		.attr( 'x', WIDTH / 2 )
		.attr( 'y', X_AXIS_LABEL_BUMP_Y )
		.attr( 'text-anchor', 'middle' )
		.text( xLabel );
	console.debug( 'xAxisLabel:', xAxisLabel ); window.xAxisLabel = xAxisLabel;

	var yAxisFn = d3.svg.axis()
		.scale( y_scale )
		.ticks( Y_TICKS )
		.orient( 'left' );
	var yAxis = chart.append( 'g' ).attr( 'class', 'axis' ).attr( 'id', 'y-axis' )
		.call( yAxisFn );
	console.debug( 'yAxis:', yAxis ); window.yAxis = yAxis, window.yAxisFn = yAxisFn;

	var yAxisLabel = yAxis.append( 'text' ).attr( 'class', 'axis-label' ).attr( 'id', 'y-axis-label' )
		.attr( 'x', Y_AXIS_LABEL_BUMP_X )
		.attr( 'y', HEIGHT / 2 )
		.attr( 'text-anchor', 'middle' )
		.attr( 'transform', rotateStr( -90, Y_AXIS_LABEL_BUMP_X, HEIGHT / 2 ) )
		.text( yLabel );
	console.debug( 'yAxisLabel:', yAxisLabel ); window.yAxisLabel = yAxisLabel;

	// grid lines
	var hGridLines = chart.selectAll( '.h-grid-line' )
			.data( x_scale.ticks( xAxisFn.ticks()[0] ) )
		.enter().append( 'svg:line' )
			.classed( 'grid-line h-grid-line', true )
			.attr( 'x1', x_scale ).attr( 'y1', 0 )
			.attr( 'x2', x_scale ).attr( 'y2', HEIGHT )
	console.debug( 'hGridLines:', hGridLines ); window.hGridLines = hGridLines;
	
	var vGridLines = chart.selectAll( '.v-grid-line' )
			.data( y_scale.ticks( yAxisFn.ticks()[0] ) )
		.enter().append( 'svg:line' )
			.classed( 'grid-line v-grid-line', true )
			.attr( 'x1', 0 )    .attr( 'y1', y_scale )
			.attr( 'x2', WIDTH ).attr( 'y2', y_scale )
	console.debug( 'vGridLines:', vGridLines ); window.vGridLines = vGridLines;
	
	// Functions used to render plot.
	var xPosFn = function( d, i ){
		return x_scale( col1_data[ i ] );
	};
	var yPosFn = function( d, i ){
		return y_scale( col2_data[ i ] );
	};

	// Create bubbles for each data point.
	chart.selectAll( "circle.bubble" )
		.data(data).enter()
		.append( "svg:circle" ).attr( "class", "bubble" )
			// start all bubbles at corner...
			.attr( "r", 0 )			
			.attr( "fill", "white" )
			// ...animate to final position
			.transition().duration( ENTRY_ANIM_DURATION )
				.attr("cx", xPosFn )
				.attr("cy", yPosFn )			
				.attr("r", BUBBLE_RADIUS);
				
	//TODO: on hover red line to axes, display values
});
</script>
</%def>

<%def name="body()">
    <h1 class="title">Scatterplot of '${title}':</h1>
    <h2 class="subtitle">${subtitle}</h2>
	
</%def>
