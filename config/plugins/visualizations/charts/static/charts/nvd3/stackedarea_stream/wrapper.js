// dependencies
define(['plugin/charts/nvd3/common/wrapper'], function(NVD3) {

// widget
return Backbone.Model.extend({
    initialize: function(app, options) {
        options.type = 'stackedAreaChart';
        options.makeConfig = function(nvd3_model) {
            nvd3_model.style('stream')
        };
        new NVD3(app, options);
    }
});

});