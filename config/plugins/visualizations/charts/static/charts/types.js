// dependencies
define(['plugin/charts/bardiagram/config',
        //'plugin/charts/boxplot/config',
        'plugin/charts/histogram/config',
        'plugin/charts/horizontal/config',
        'plugin/charts/line/config',
        'plugin/charts/linewithfocus/config',
        'plugin/charts/piechart/config',
        'plugin/charts/scatterplot/config',
        'plugin/charts/stackedarea/config',
        ], function(bardiagram,
                    //boxplot,
                    histogram,
                    horizontal,
                    line,
                    linewithfocus,
                    piechart,
                    scatterplot,
                    stackedarea
            ) {

// widget
return Backbone.Model.extend(
{
    // types
    defaults: {
        'bardiagram' : bardiagram,
        //'boxplot' : boxplot,
        'horizontal' : horizontal,
        'histogram' : histogram,
        'line' : line,
        'linewithfocus' : linewithfocus,
        'piechart' : piechart,
        'scatterplot' : scatterplot,
        'stackedarea' : stackedarea
    }
});

});