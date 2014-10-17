// dependencies
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/ui/ui-tabs', 'mvc/tools/tools-template'], function(Utils, Ui, Tabs, ToolTemplate) {

var View = Backbone.View.extend({
    // initialize
    initialize : function(app, options) {
        // configure options
        this.options = options;
        
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
        var datasets = app.content.filterType({
            src             : 'hda',
            extensions      : options.extensions
        });

        // configure options fields
        var dataset_options = [];
        for (var i in datasets) {
            dataset_options.push({
                label: datasets[i].hid + ': ' + datasets[i].name,
                value: datasets[i].id
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
        var collections = app.content.filterType({
            src             : 'hdca',
            extensions      : options.extensions
        });
        
        // configure options fields
        var collection_options = [];
        for (var i in collections) {
            collection_options.push({
                label: collections[i].hid + ': ' + collections[i].name,
                value: collections[i].id
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
        
        // check for batch mode
        if (!this.options.multiple) {
            this.$el.append(ToolTemplate.batchMode());
        }
        
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
    value : function (dict) {
        // update current value
        if (dict !== undefined) {
            try {
                // set source
                this.current = dict.values[0].src;
                this.refresh();
                
                // create list
                var list = [];
                for (var i in dict.values) {
                    list.push(dict.values[i].id);
                }
                
                // identify select element
                switch(this.current) {
                    case 'hda':
                        this.select_datasets.value(list);
                        break;
                    case 'hdca':
                        this.select_collection.value(list[0]);
                        break;
                }
                
                // check if value has been set
                var select = this._select();
                if (!select.validate()) {
                    select.value(select.first());
                }
            } catch (err) {
                console.debug('tools-select-content::value() - Skipped.');
            }
        }
        
        // transform into an array
        var id_list = this._select().value();
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
        return this._select().validate();
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
    },
    
    /** Assists in selecting the current field */
    _select: function() {
        switch(this.current) {
            case 'hdca':
                return this.select_collection;
            default:
                return this.select_datasets;
        }
    }
});

return {
    View: View
}

});
