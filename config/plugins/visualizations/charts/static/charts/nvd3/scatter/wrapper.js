// dependencies
define(['plugin/charts/nvd3/common/wrapper'], function(NVD3) {

// widget
return Backbone.Model.extend({
    initialize: function(app, options) {
        options.type = 'scatterChart';
        options.makeConfig = function(nvd3_model) {
            nvd3_model.showDistX(true)
                  .showDistY(true)
                  .color(d3.scale.category10().range());
        };
        new NVD3(app, options);
    }
});

});