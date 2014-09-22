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
        this.current = 'hda';
        
        // create button
        this.button_new = new Ui.RadioButton.View({
            value   : this.current,
            data    : [ { icon: 'fa-file-o', label : 'Select datasets', value : 'hda'  },
                        { icon: 'fa-files-o', label : 'Select a collection',  value : 'hdca' }],
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
    
    /** Return the currently selected dataset values */
    value : function () {
        // identify select element
        var select = null;
        switch(this.current) {
            case 'hda':
                select = this.select_datasets;
                break;
            case 'hdca':
                select = this.select_collection;
                break;
        }
        
        // transform into an array
        var id_list = select.value();
        if (!(id_list instanceof Array)) {
            id_list = [id_list];
        }
        
        // prepare result dict
        var result = {
            batch   : !this.options.multiple,
            values  : []
        }
        
        // append to dataset ids
        for (var i in id_list) {
            result.values.push({
                id  : id_list[i],
                src : this.current
            });
        }
        
        // return
        return result;
    },
    
    /** Validate current selection
    */
    validate: function() {
        switch(this.current) {
            case 'hda':
                return this.select_datasets.validate();
            case 'hdca':
                return this.select_collection.validate();
        }
    },
    
    /** Refreshes data selection view */
    refresh: function() {
        switch (this.current) {
            case 'hda':
                this.select_datasets.$el.fadeIn();
                this.select_collection.$el.hide();
                break;
            case 'hdca':
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
