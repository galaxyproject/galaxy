// dependencies
define([], function() {

// widget
return Backbone.Model.extend(
{
    // types
    defaults: {
        'bardiagram' : {
            title : 'Bar diagram',
            data  : {
                y : {
                    title   : 'Values for y-axis'
                }
            }
        },
        'horizontal' : {
            title : 'Bar diagram (horizontal)',
            data  : {
                y : {
                    title   : 'Values for y-axis'
                }
            }
        },
        'line' : {
            title : 'Line chart',
            data  : {
                y : {
                    title   : 'Values for y-axis'
                }
            }
        },
        'linewithfocus' : {
            title : 'Line chart (with focus)',
            data  : {
                y : {
                    title   : 'Values for y-axis'
                }
            }
        },
        'piechart' : {
            title : 'Pie chart',
            data  : {
                y : {
                    title   : 'Values for y-axis'
                }
            }
        },
        'scatterplot' : {
            title : 'Scatter plot',
            data  : {
                x : {
                    title   : 'Values for x-axis'
                },
                y : {
                    title   : 'Values for y-axis'
                }
            }
        },
        'stackedarea' : {
            title : 'Stacked area',
            data  : {
                y : {
                    title   : 'Values for y-axis'
                }
            }
        }
    }
});

});