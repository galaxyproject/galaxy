// dependencies
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/ui/ui-tabs'], function(Utils, Ui, Tabs) {

var View = Backbone.View.extend({
    // initialize
    initialize : function(app, options) {
        // link this
        var self = this;
        
        // tabs
        this.tabs = new Tabs.View({
            onchange: function() {
                self.trigger('change');
            }
        });
        
        //
        // datasets
        //
        var datasets = app.datasets.filterType({
            content_type    : 'dataset',
            data_types      : options.extensions
        });

        // configure options fields
        var dataset_options = [];
        for (var i in datasets) {
            dataset_options.push({
                label: datasets[i].get('name'),
                value: datasets[i].get('id')
            });
        }
        
        // select field
        this.select_datasets = new Ui.Select.View({
            multiple    : true,
            data        : dataset_options,
            value       : dataset_options[0] && dataset_options[0].value,
            onchange    : function() {
                self.trigger('change');
            }
        });
        
        // add tab
        this.tabs.add({
            id      : 'datasets',
            title   : 'Select datasets',
            $el     : this.select_datasets.$el
        });
        
        //
        // collections
        //
        var collections = app.datasets.filterType({
            content_type    : 'collection',
            data_types      : options.extensions
        });
        
        // configure options fields
        var collection_options = [];
        for (var i in collections) {
            collection_options.push({
                label: collections[i].get('name'),
                value: collections[i].get('id')
            });
        }
        
        // create select field for collections
        this.select_collection = new Ui.Select.View({
            data        : collection_options,
            value       : collection_options[0] && collection_options[0].value,
            onchange    : function() {
                self.trigger('change');
            }
        });
        
        // add tab
        this.tabs.add({
            id      : 'collection',
            title   : 'Select a dataset collection',
            $el     : this.select_collection.$el
        });
        
        // add element
        this.setElement(this.tabs.$el);
        
        // add change event. fires on trigger
        this.on('change', function() {
            if (options.onchange) {
                options.onchange(self.value());
            }
        });
    },
    
    // value
    value : function (new_value) {
        var current_tab = this.tabs.current();
        switch(current_tab) {
            case 'datasets':
                return this.select_datasets.value();
            case 'collection':
                return this.select_collection.value();
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
