// dependencies
define(['models/chart'], function(Chart) {

// collection
return Backbone.Collection.extend(
{
    model: Chart
});

});