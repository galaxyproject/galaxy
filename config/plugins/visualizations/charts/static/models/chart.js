// dependencies
define(['plugin/models/groups', 'mvc/visualization/visualization-model'], function(Groups) {


// model
return Backbone.Model.extend(
{
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
        
        // link status handler
        var self = this;
        this.on('change:state', function() {
            // check status
            var state = self.get('state');
            if (self.ready(state)) {
                self.trigger('ready');
            }
            
            // log
            console.debug(state + ' : ' + self.get('state_info'));
        });
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
    
    state: function(value, info) {
        this.set('state_info', info);
        this.set('state', value);
    },
    
    ready: function() {
        return  (this.get('state') == 'ok') ||
                (this.get('state') == 'failed') ||
                (this.get('state') == 'initialized');
    },
    
    editable: function() {
        return  (this.get('state') == 'ok') ||
                (this.get('state') == 'failed');
    },
    
    deferred: function(callback) {
        if (!this.ready()) {
            this.once('ready', function() {
                callback();
            });
        } else {
            callback();
        }
    }
});

});