// dependencies
define(['plugin/charts/nvd3/common/wrapper'], function(NVD3) {

// widget
return Backbone.Model.extend({
    initialize: function(app, options) {
        options.type = 'multiBarChart';
        new NVD3(app, options);
    }
});

});