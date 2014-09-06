// dependencies
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/ui/ui-tabs'], function(Utils, Ui, Tabs) {

var View = Backbone.View.extend({
    // initialize
    initialize : function(app, options) {
        // link this
        var self = this;
    
        // get datasets
        var datasets = app.datasets.filterType();
        
        // configure options fields
        var select_data = [];
        for (var i in datasets) {
            select_data.push({
                label: datasets[i].get('name'),
                value: datasets[i].get('id')
            });
        }
        
        // create select field
        this.select = new Ui.Select.View({
            data        : select_data,
            value       : select_data[0].value,
            onchange    : function() {
                self.trigger('change');
            }
        });
        
        // create select field for multiple files
        this.select_multiple = new Ui.Select.View({
            multiple    : true,
            data        : select_data,
            value       : select_data[0].value,
            onchange    : function() {
                self.trigger('change');
            }
        });

        
        // create select field for multiple files
        this.select_collection = new Ui.Select.View({
            data        : select_data,
            value       : select_data[0].value,
            onchange    : function() {
                self.trigger('change');
            }
        });
                
        // add change event. fires on trigger
        this.on('change', function() {
            if (options.onchange) {
                options.onchange(self.value());
            }
        });
        
        // tabs
        this.tabs = new Tabs.View({
            onchange: function() {
                self.trigger('change');
            }
        });
        
        // add tab
        this.tabs.add({
            id      : 'single',
            title   : 'Select a dataset',
            $el     : this.select.$el
        });
        
        // add tab
        this.tabs.add({
            id      : 'multiple',
            title   : 'Select multiple datasets',
            $el     : this.select_multiple.$el
        });

        // add tab
        this.tabs.add({
            id      : 'collection',
            title   : 'Select a dataset collection',
            $el     : this.select_collection.$el
        });
        
        // add element
        this.setElement(this.tabs.$el);
    },
    
    // value
    value : function (new_value) {
        var current_tab = this.tabs.current();
        switch(current_tab) {
            case 'multiple' :
                return this.select_multiple.value();
            case 'collection' :
                return this.select_collection.value();
            default :
                return this.select.value();
        }
    },
    
    // render
    update: function(options) {
        this.select.update(options);
    }
});

return {
    View: View
}

});
