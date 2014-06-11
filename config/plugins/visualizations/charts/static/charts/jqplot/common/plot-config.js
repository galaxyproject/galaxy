// dependencies
define([], function() {

// highcharts configuration
return function(chart) {

    // get chart settings
    var settings = chart.settings;
    var plot_config = {
        enablePlugins: true,
        seriesColors: function() {
            var colors = [];
            var colorScale = d3.scale.category20();
            for (var i = 0; i < chart.groups.length; i++) {
                colors.push(colorScale(i));
            }
            return colors;
        }(),
       
        seriesDefaults: {
            renderer                : $.jqplot.LineRenderer,
            //lineWidth               : 1,                    // Width of the line in pixels.
            shadow                  : false,                // show shadow or not.
            showLine                : true,                 // whether to render the line segments or not.
       
            // Show point labels to the right ('e'ast) of each bar.
            // edgeTolerance of -15 allows labels flow outside the grid
            // up to 15 pixels.  If they flow out more than that, they 
            // will be hidden.
            //pointLabels             : { show: true, location: 'e', edgeTolerance: -15 },
            // Rotate the bar shadow as if bar is lit from top right.
            //shadowAngle             : 135,
            // Here's where we tell the chart it is oriented horizontally.
            rendererOptions: {
                shadowDepth         : 0,
                //barDirection      : 'horizontal',
                //barPadding        : 5,
                //barMargin         : 2,
                //barWidth            : Math.max(0.5 / chart.groups.length, 2),
                barWidth            : 10,
                //fillToZero        : true,
                //stackedValue      : true
            },
            markerRenderer          : $.jqplot.MarkerRenderer,
            markerOptions: {
                show                : false,                // wether to show data point markers.
                style               : 'filledCircle',       // circle, diamond, square, filledCircle.
                                                            // filledDiamond or filledSquare.
                lineWidth           : 0,                    // width of the stroke drawing the marker.
                size                : 10,                   // size (diameter, edge length, etc.) of the marker.
                shadow              : false,                // wether to draw shadow on marker or not.
                shadowAngle         : 45,                   // angle of the shadow.  Clockwise from x axis.
                shadowOffset        : 1,                    // offset from the line of the shadow,
                shadowDepth         : 3,                    // Number of strokes to make when drawing shadow.  Each stroke
                                                            // offset by shadowOffset from the last.
                shadowAlpha         : 0.07                  // Opacity of the shadow
            }
        },
       
        // Custom labels for the series are specified with the "label"
        // option on the series option.  Here a series option object
        // is specified for each series.
        series: [],
       
        axesDefaults: {
            labelRenderer           : $.jqplot.CanvasAxisLabelRenderer,
            labelOptions: {
                fontSize            : '12pt',
                textColor           : '#000000'
            },
            tickRenderer            : $.jqplot.CanvasAxisTickRenderer ,
            tickOptions: {
                fontSize            : '12pt',
                textColor           : '#000000'
            }
        },
    
        axes: {
            // Use a category axis on the x axis and use our custom ticks.
            xaxis: {
                label               : chart.settings.get('x_axis_label'),
                tickRenderer        : $.jqplot.CanvasAxisTickRenderer,
                tickOptions: {
                    angle           : -30
                },
                tickInterval        : 1,
                pad                 : 0
            },
            // Pad the y axis just a little so bars can get close to, but
            // not touch, the grid boundaries.  1.2 is the default padding.
            yaxis: {
                label               : chart.settings.get('y_axis_label'),
                tickOptions         : {},
                pad                 : 0
                //tickOptions       : {formatString: '$%d'},
                //padding             : 1.2,
                //autoscale:true
            }
        },
       
        grid: {
            background              : '#FFFFFF',
            borderWidth             : 0,
            shadow                  : false
        },
       
        cursor: {
            show                    : true,
            zoom                    : true,
            showTooltip             : false,
            style                   : 'pointer'
        },
        highlighter: {
            show                    : true,
            showMarker              : false,
            tooltipAxes             : 'xy'
        }
    };
    
    // Show the legend and put it outside the grid, but inside the
    // plot container, shrinking the grid to accomodate the legend.
    // A value of "outside" would not shrink the grid and allow
    // the legend to overflow the container.
    if (chart.settings.get('show_legend') == 'true') {
        plot_config.legend = {
            renderer                : $.jqplot.EnhancedLegendRenderer,
            show                    : true,
            placement               : 'outsideGrid',
            location                : 'n',
            rendererOptions: {
                textColor           : '#000000',
                fontSize            : '12pt',
                border              : 'none',
                shadowAlpha         : 1,
                background          : 'rgba(255, 255, 255, 0.9)',
                fontFamily          : 'Arial',
                numberRows          : 1
            }
        };
    }
    
    // callback
    return plot_config;
};

});