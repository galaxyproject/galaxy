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
	        text                        : ''
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
                    var axis_type = settings.get('x_axis_type');
                    if (axis_type == 'auto' || axis_type === undefined)
                        return this.value;
                    var format = d3.format(settings.get('x_axis_tick') + axis_type);
                    return format(this.value);
                },
                enabled                 : !(settings.get('x_axis_type') == 'hide')
            },
            gridLineWidth               : settings.get('x_axis_grid')
        },
        
        yAxis: {
            title: {
                text                    : settings.get('y_axis_label')
            },
            labels: {
                formatter               : function() {
                    var axis_type = settings.get('y_axis_type');
                    if (axis_type == 'auto' || axis_type === undefined)
                        return this.value;
                    var format = d3.format(settings.get('y_axis_tick') + axis_type);
                    return format(this.value);
                },
                enabled                 : !(settings.get('y_axis_type') == 'hide')
            },
            gridLineWidth               : settings.get('y_axis_grid')
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