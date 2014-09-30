// dependencies
define([], function() {

// model
var Model = Backbone.Model.extend({
    defaults: {
        extension       : 'auto',
        genome          : '?',
        url_paste       : '',
        status          : 'init',
        info            : null,
        file_mode       : 'local',
        file_size       : 0,
        file_type       : null,
        file_path       : '',
        percentage      : 0,
        
        // settings
        space_to_tabs   : false,
        to_posix_lines  : true
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
