// dependencies
define(['models/group'], function(Group) {

// collection
return Backbone.Collection.extend(
{
    model: Group
});

});