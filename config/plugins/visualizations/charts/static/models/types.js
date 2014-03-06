// dependencies
define([], function() {

// widget
return Backbone.Model.extend(
{
    // types
    defaults: {
        'bardiagram' : {
            title   : 'Bar diagram',
            columns : {
                y : {
                    title   : 'Values for y-axis'
                }
            }
        },
        'histogram' : {
            title   : 'Histogram',
            mode    : 'execute',
            columns : {
                y : {
                    title   : 'Derive frequencies'
                }
            }
        },
        'horizontal' : {
            title   : 'Bar diagram (horizontal)',
            columns : {
                y : {
                    title   : 'Values for y-axis'
                }
            }
        },
        'line' : {
            title   : 'Line chart',
            columns : {
                y : {
                    title   : 'Values for y-axis'
                }
            }
        },
        'linewithfocus' : {
            title   : 'Line chart (with focus)',
            columns : {
                y : {
                    title   : 'Values for y-axis'
                }
            }
        },
        'piechart' : {
            title   : 'Pie chart',
            columns : {
                y : {
                    title   : 'Values for y-axis'
                }
            }
        },
        'scatterplot' : {
            title   : 'Scatter plot',
            columns : {
                x : {
                    title   : 'Values for x-axis'
                },
                y : {
                    title   : 'Values for y-axis'
                }
            }
        },
        'stackedarea' : {
            title   : 'Stacked area',
            columns : {
                y : {
                    title   : 'Values for y-axis'
                }
            }
        }
    }
});

});