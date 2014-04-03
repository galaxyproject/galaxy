// =============================================================================
/**
 *  Two Variable scatterplot visualization using d3
 *      Uses semi transparent circles to show density of data in x, y grid
 *      usage :
 *          var plot = new scatterplot( $( 'svg' ).get(0), config, data )
 */
function scatterplot( renderTo, config, data ){
    //console.log( 'scatterplot', config );

    var translateStr = function( x, y ){
            return 'translate(' + x + ',' + y + ')';
        },
        rotateStr = function( d, x, y ){
            return 'rotate(' + d + ',' + x + ',' + y + ')';
        },
        getX = function( d, i ){
            //console.debug( d[ config.xColumn ] );
            return d[ config.xColumn ];
        },
        getY = function( d, i ){
            //console.debug( d[ config.yColumn ] );
            return d[ config.yColumn ];
        };

    // .................................................................... scales
    var stats = {
            x    : { extent: d3.extent( data, getX ) },
            y    : { extent: d3.extent( data, getY ) }
        };

    //TODO: set pan/zoom limits
    //  from http://stackoverflow.com/questions/10422738/limiting-domain-when-zooming-or-panning-in-d3-js
    //self.x.domain([Math.max(self.x.domain()[0], self.options.xmin), Math.min(self.x.domain()[1], self.options.xmax)]);
    //self.y.domain([Math.max(self.y.domain()[0], self.options.ymin), Math.min(self.y.domain()[1], self.options.ymax)]);
    var interpolaterFns = {
        x : d3.scale.linear()
            .domain( stats.x.extent )
            .range([ 0, config.width ]),
        y : d3.scale.linear()
            .domain( stats.y.extent )
            .range([ config.height, 0 ])
    };

    // .................................................................... main components
    var zoom = d3.behavior.zoom()
        .x( interpolaterFns.x )
        .y( interpolaterFns.y )
        .scaleExtent([ 1, 30 ])
        .scale( config.scale || 1 )
        .translate( config.translate || [ 0, 0 ] );

    //console.debug( renderTo );
    var svg = d3.select( renderTo )
        .attr( "class", "scatterplot" )
        //.attr( "width",  config.width  + ( config.margin.right + config.margin.left ) )
        .attr( "width",  '100%' )
        .attr( "height", config.height + ( config.margin.top + config.margin.bottom ) );

    var content = svg.append( "g" )
        .attr( "class", "content" )
        .attr( "transform", translateStr( config.margin.left, config.margin.top ) )
        .call( zoom );

    // a BIG gotcha - zoom (or any mouse/touch event in SVG?) requires the pointer to be over an object
    //  create a transparent rect to be that object here
    content.append( 'rect' )
        .attr( "class", "zoom-rect" )
        .attr( "width", config.width ).attr( "height", config.height )
        .style( "fill", "transparent" );

    //console.log( 'svg:', svg, 'content:', content );

    // .................................................................... axes
    var axis = { x : {}, y : {} };
    //console.log( 'xTicks:', config.xTicks );
    //console.log( 'yTicks:', config.yTicks );
    axis.x.fn = d3.svg.axis()
        .orient( 'bottom' )
        .scale( interpolaterFns.x )
        .ticks( config.xTicks )
        // this will convert thousands -> k, millions -> M, etc.
        .tickFormat( d3.format( 's' ) );

    axis.y.fn = d3.svg.axis()
        .orient( 'left' )
        .scale( interpolaterFns.y )
        .ticks( config.yTicks )
        .tickFormat( d3.format( 's' ) );

    axis.x.g = content.append( 'g' )
        .attr( 'class', 'x axis' )
        .attr( 'transform', translateStr( 0, config.height ) )
        .call( axis.x.fn );
    //console.log( 'axis.x.g:', axis.x.g );

    axis.y.g = content.append( 'g' )
        .attr( 'class', 'y axis' )
        .call( axis.y.fn );
    //console.log( 'axis.y.g:', axis.y.g );

    // ................................ axis labels
    var padding = 6;
    // x-axis label
    axis.x.label = svg.append( 'text' )
        .attr( 'id', 'x-axis-label' )
        .attr( 'class', 'axis-label' )
        .text( config.xLabel )
        // align to the top-middle
        .attr( 'text-anchor', 'middle' )
        .attr( 'dominant-baseline', 'text-after-edge' )
        .attr( 'x', ( config.width / 2 ) + config.margin.left )
        // place 4 pixels below the axis bounds
        .attr( 'y', ( config.height + config.margin.bottom + config.margin.top ) - padding );
    //console.log( 'axis.x.label:', axis.x.label );

//TODO: anchor to left of x margin/graph
    // y-axis label
    // place 4 pixels left of the axis.y.g left edge
    axis.y.label = svg.append( 'text' )
        .attr( 'id', 'y-axis-label' )
        .attr( 'class', 'axis-label' )
        .text( config.yLabel )
        // align to bottom-middle
        .attr( 'text-anchor', 'middle' )
        .attr( 'dominant-baseline', 'text-before-edge' )
        .attr( 'x', padding )
        .attr( 'y', config.height / 2 )
        // rotate around the alignment point
        .attr( 'transform', rotateStr( -90, padding, config.height / 2 ) );
    //console.log( 'axis.y.label:', axis.y.label );

    axis.redraw = function _redrawAxis(){
        svg.select( ".x.axis" ).call( axis.x.fn );
        svg.select( ".y.axis" ).call( axis.y.fn );
    };

    // .................................................................... grid
    function renderGrid(){
        var grid = { v : {}, h: {} };
        // vertical
        grid.v.lines = content.selectAll( 'line.v-grid-line' )
            // data are the axis ticks; enter, update, exit
            .data( interpolaterFns.x.ticks( axis.x.fn.ticks()[0] ) );
        // enter: append any extra lines needed (more ticks)
        grid.v.lines.enter()
            .append( 'svg:line' )
            .classed( 'grid-line v-grid-line', true );
        // update: set coords
        grid.v.lines
            .attr( 'x1', interpolaterFns.x )
            .attr( 'x2', interpolaterFns.x )
            .attr( 'y1', 0 )
            .attr( 'y2', config.height );
        // exit: just remove them
        grid.v.lines.exit().remove();
        //console.log( 'grid.v.lines:', grid.v.lines );

        // horizontal
        grid.h.lines = content.selectAll( 'line.h-grid-line' )
            .data( interpolaterFns.y.ticks( axis.y.fn.ticks()[0] ) );
        grid.h.lines.enter()
            .append( 'svg:line' )
            .classed( 'grid-line h-grid-line', true );
        grid.h.lines
            .attr( 'x1', 0 )
            .attr( 'x2', config.width )
            .attr( 'y1', interpolaterFns.y )
            .attr( 'y2', interpolaterFns.y );
        grid.h.lines.exit().remove();
        //console.log( 'grid.h.lines:', grid.h.lines );
        return grid;
    }
    var grid = renderGrid();

    //// .................................................................... datapoints
    var datapoints = content.selectAll( '.glyph' ).data( data )
        // enter - NEW data to be added as glyphs
        .enter().append( 'svg:circle' )
            .classed( "glyph", true )
            .attr( "cx", function( d, i ){ return interpolaterFns.x( getX( d, i ) ); })
            .attr( "cy", function( d, i ){ return interpolaterFns.y( getY( d, i ) ); })
            .attr( "r",  0 );

    // for all EXISTING glyphs and those that need to be added: transition anim to final state
    datapoints.transition().duration( config.animDuration )
        .attr( "r", config.datapointSize );
    //console.log( 'datapoints:', datapoints );

    function _redrawDatapointsClipped(){
        return datapoints
            //TODO: interpolates twice
            .attr( "cx", function( d, i ){ return interpolaterFns.x( getX( d, i ) ); })
            .attr( "cy", function( d, i ){ return interpolaterFns.y( getY( d, i ) ); })
            .style( 'display', 'block' )
            // filter out points now outside the graph content area and hide them
            .filter( function( d, i ){
                var cx = d3.select( this ).attr( "cx" ),
                    cy = d3.select( this ).attr( "cy" );
                if( cx < 0 || cx > config.width  ){ return true; }
                if( cy < 0 || cy > config.height ){ return true; }
                return false;
            }).style( 'display', 'none' );
    }
    _redrawDatapointsClipped();

    // .................................................................... behaviors
    function zoomed( scale, translateX, translateY ){
        //console.debug( 'zoom', this, zoom.scale(), zoom.translate() );

        // re-render axis, grid, and datapoints
        $( '.chart-info-box' ).remove();
        axis.redraw();
        _redrawDatapointsClipped();
        grid = renderGrid();

        $( svg.node() ).trigger( 'zoom.scatterplot', {
            scale       : zoom.scale(),
            translate   : zoom.translate()
        });
    }
    //TODO: programmatically set zoom/pan and save in config
    //TODO: set pan/zoom limits
    zoom.on( "zoom", zoomed );

    function infoBox( top, left, d ){
        // create an abs pos. element containing datapoint data (d) near the point (top, left)
        //  with added padding to clear the mouse pointer
        left += 8;
        return $([
            '<div class="chart-info-box" style="position: absolute">',
                (( config.idColumn !== undefined )?( '<div>' + d[ config.idColumn ] + '</div>' ):( '' )),
                '<div>', getX( d ), '</div>',
                '<div>', getY( d ), '</div>',
            '</div>'
        ].join( '' ) ).css({ top: top, left: left, 'z-index': 2 });
    }

    datapoints.on( 'mouseover', function( d, i ){
        var datapoint = d3.select( this );
        datapoint
            .classed( 'highlight', true )
            .style( 'fill', 'red' )
            .style( 'fill-opacity', 1 );

        // create horiz line to axis
        content.append( 'line' )
            .attr( 'stroke', 'red' )
            .attr( 'stroke-width', 1 )
            // start not at center, but at the edge of the circle - to prevent mouseover thrashing
            .attr( 'x1', datapoint.attr( 'cx' ) - config.datapointSize )
            .attr( 'y1', datapoint.attr( 'cy' ) )
            .attr( 'x2', 0 )
            .attr( 'y2', datapoint.attr( 'cy' ) )
            .classed( 'hoverline', true );

        // create vertical line to axis - if not on the x axis
        if( datapoint.attr( 'cy' ) < config.height ){
            content.append( 'line' )
                .attr( 'stroke', 'red' )
                .attr( 'stroke-width', 1 )
                .attr( 'x1', datapoint.attr( 'cx' ) )
                // attributes are strings so, (accrd. to js) '3' - 1 = 2 but '3' + 1 = '31': coerce
                .attr( 'y1', +datapoint.attr( 'cy' ) + config.datapointSize )
                .attr( 'x2', datapoint.attr( 'cx' ) )
                .attr( 'y2', config.height )
                .classed( 'hoverline', true );
        }

        // show the info box and trigger an event
        var bbox = this.getBoundingClientRect();
        $( 'body' ).append( infoBox( bbox.top, bbox.right, d ) );
        $( svg.node() ).trigger( 'mouseover-datapoint.scatterplot', [ this, d, i ] );
    });

    datapoints.on( 'mouseout', function(){
        // return the point to normal, remove hoverlines and info box
        d3.select( this )
            .classed( 'highlight', false )
            .style( 'fill', 'black' )
            .style( 'fill-opacity', 0.2 );
        content.selectAll( '.hoverline' ).remove();
        $( '.chart-info-box' ).remove();
    });
}

//==============================================================================
