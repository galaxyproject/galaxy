// dependencies
define([], function() {

// highcharts configuration
return function(chart) {

    // get chart settings
    var settings = chart.settings;

    // initialize config object
    var hc_config = {
        chart: {
	        type                        : '',
            zoomType                    : 'xy'
	    },
	    
	    title: {
	        text                        : chart.get('title')
	    },
	    
	    legend: {
	        enabled                     : settings.get('legend_enabled') == undefined || settings.get('legend_enabled') == 'true'
	    },
        
        credits: {
            enabled                     : false
        },
        
        xAxis: {
            title: {
                text                    : settings.get('x_axis_label')
            },
            stackLabels: {
                    enabled: false,
                    style: {
                        fontWeight      : 'bold',
                        color           : (Highcharts.theme && Highcharts.theme.textColor) || 'gray'
                    }
                },
            labels: {
                formatter               : function() {
                    if (settings.get('x_axis_type') == 'auto')
                        return this.value;
                    var format = d3.format(settings.get('x_axis_tick') + settings.get('x_axis_type'));
                    return format(this.value);
                },
                enabled                 : !(settings.get('x_axis_type') == 'hide')
            },
            tickPixelInterval           : 100
        },
        
        yAxis: {
            title: {
                text                    : settings.get('y_axis_label')
            },
            labels: {
                formatter               : function() {
                    if (settings.get('y_axis_type') == 'auto')
                        return this.value;
                    var format = d3.format(settings.get('y_axis_tick') + settings.get('y_axis_type'));
                    return format(this.value);
                },
                enabled                 : !(settings.get('y_axis_type') == 'hide')
            }
        },
        plotOptions: {
            series: {
                animation               : false,
                stacking                : settings.get('plotoptions_series_stacking')
            },
            column: {
                stacking                : settings.get('plotoptions_column_stacking')
            },
            area: {
                stacking                : settings.get('plotoptions_area_stacking'),
                lineColor               : '#ffffff',
                lineWidth               : 1,
                marker: {
                    lineWidth           : 1,
                    lineColor           : '#ffffff'
                }
            },
            pie: {
                allowPointSelect        : true,
                cursor                  : 'pointer',
                dataLabels: {
                    enabled             : false,
                    distance            : -1
                }
            }
        },
       
        series: []
	}
    
    // callback
    return hc_config;
};

});