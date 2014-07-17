// dependencies
define(['plugin/charts/jqplot/common/wrapper'], function(Plot) {

// widget
return Backbone.Model.extend({
    initialize: function(app, options) {
        new Plot(app, options);
    }
});

});