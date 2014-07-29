// dependencies
define(['plugin/charts/nvd3/common/wrapper'], function(NVD3) {

// widget
return Backbone.Model.extend({
    initialize: function(app, options) {
        options.type = 'multiBarChart';
        options.makeConfig = function(nvd3_model) {
            nvd3_model.stacked(true);
        };
        new NVD3(app, options);
    }
});

});