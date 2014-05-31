// dependencies
define([], function() {

// widget
return function(settings) {
    // highcharts configuration
    return {
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
            categories                  : settings.get('x_axis_categories'),
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
            tickPixelInterval           : 100
        },
        
        yAxis: {
            title: {
                text                    : settings.get('y_axis_label')
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
	}/*,
    
    // highcharts stacking
    hc_stacklabels: {
        enabled: true,
        style: {
            fontWeight: 'bold',
            color: (Highcharts.theme && Highcharts.theme.textColor) || 'gray'
        }
    },

    // initialize
    initialize: function(settings) {
        // stacking
        if (settings.get('x_stacked')) {
            this.hc_config.xAxis.stackLabels = this.hc_stacklabels;
            this.hc_config.plotOptions.column = {
                stacking    : 'normal',
                dataLabels  : {
                    enabled : true,
                    color: (Highcharts.theme && Highcharts.theme.dataLabelsColor) || 'white',
                    style: {
                        textShadow: '0 0 3px black, 0 0 3px black'
                    }
                }
            }
        }
        
        // stacking
        if (settings.get('y_stacked')) {
            this.hc_config.yAxis.stackLabels = this.hc_stacklabels;
            this.hc_config.plotOptions.column = {
                stacking    : 'normal'
            }
        }
        
        console.log(this.hc_config);
    }*/
};

});