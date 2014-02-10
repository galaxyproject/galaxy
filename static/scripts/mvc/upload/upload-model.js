// dependencies
define([], function() {

// model
var Model = Backbone.Model.extend({
    defaults: {
        extension       : 'auto',
        genome          : '?',
        url_paste       : '',
        space_to_tabs   : false,
        status          : 'init',
        info            : null
    }
});

// collection
var Collection = Backbone.Collection.extend({
    model: Model
});

// return
return {
    Model: Model,
    Collection : Collection
};

});
