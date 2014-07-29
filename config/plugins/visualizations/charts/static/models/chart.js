// dependencies
define(['plugin/models/groups'], function(Groups) {

// model
return Backbone.Model.extend({
    // defaults
    defaults : {
        id              : null,
        title           : '',
        type            : '',
        date            : null,
        state           : '',
        state_info      : '',
        modified        : false,
        dataset_id      : '',
        dataset_id_job  : ''
    },
    
    // initialize
    initialize: function(options) {
        this.groups = new Groups();
        this.settings = new Backbone.Model();
    },
    
    // reset
    reset: function() {
        this.clear({silent: true}).set(this.defaults);
        this.groups.reset();
        this.settings.clear();
        this.trigger('reset', this);
    },
    
    // copy
    copy: function(new_chart) {
        // copy chart/groups
        var current = this;
        
        // set attributes
        current.clear({silent: true}).set(this.defaults);
        current.set(new_chart.attributes);
        
        // set nested models/collections
        current.settings = new_chart.settings.clone();
        current.groups.reset();
        new_chart.groups.each(function(group) {
            current.groups.add(group.clone());
        });
        
        // trigger change
        current.trigger('change', current);
    },
    
    // set state
    state: function(value, info) {
        // set status
        this.set('state', value);
        this.set('state_info', info);
        
        // trigger set state
        this.trigger('set:state');
        
        // log status
        console.debug('Chart:state() - ' + info + ' (' + value + ')');
    }
});

});