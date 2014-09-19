// dependencies
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/ui/ui-tabs'], function(Utils, Ui, Tabs) {

var View = Backbone.View.extend({
    // initialize
    initialize : function(app, options) {
        // link this
        var self = this;
        
        // add element
        this.setElement('<div/>');
        
        // current selection
        this.current = 'dataset';
        
        // create button
        this.button_new = new Ui.RadioButton.View({
            value   : this.current,
            data    : [ { icon: 'fa-file-o', label : 'Select datasets', value : 'dataset'  },
                        { icon: 'fa-files-o', label : 'Select a collection',  value : 'collection' }],
            onchange: function(value) {
                self.current = value;
                self.refresh();
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
        
        // add elements to dom
        this.$el.append(Utils.wrap(this.button_new.$el));
        this.$el.append(this.select_datasets.$el);
        this.$el.append(this.select_collection.$el);
        
        // refresh view
        this.refresh();
        
        // add change event. fires on trigger
        this.on('change', function() {
            if (options.onchange) {
                options.onchange(self.value());
            }
        });
    },
    
    // value
    value : function () {
        switch(this.current) {
            case 'dataset':
                return this.select_datasets.value();
            case 'collection':
                return this.select_collection.value();
        }
    },
    
    // render
    update: function(options) {
        this.select.update(options);
    },
    
    // refresh
    refresh: function() {
        switch (this.current) {
            case 'dataset':
                this.select_datasets.$el.fadeIn();
                this.select_collection.$el.hide();
                break;
            case 'collection':
                this.select_datasets.$el.hide();
                this.select_collection.$el.fadeIn();
                break;
        }
    }
});

return {
    View: View
}

});
