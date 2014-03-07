// dependencies
define(['plugin/charts/_nvd3/nvd3'], function(NVD3) {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options) {
        this.app        = app;
        this.options    = options;
    },
            
    // render
    draw : function(chart, request_dictionary)
    {
        var nvd3 = new NVD3(this.app, this.options);
        nvd3.draw(nv.models.lineWithFocusChart(), chart, request_dictionary);
    }
});

});