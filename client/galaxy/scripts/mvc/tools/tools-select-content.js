// dependencies
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/ui/ui-tabs', 'mvc/tools/tools-template'], function(Utils, Ui, Tabs, ToolTemplate) {

var View = Backbone.View.extend({
    // initialize
    initialize : function(app, options) {
        // link app and options
        this.app = app;
        this.options = options;
        
        // link this
        var self = this;
        
        // add element
        this.setElement('<div/>');
        
        // list of select fields
        this.list = {};
        
        // radio button options
        var radio_buttons = [];
        
        // identify selector type
        if (options.type == 'data_collection') {
            this.mode = 'collection';
        } else {
            if (options.multiple) {
                this.mode = 'multiple';
            } else {
                this.mode = 'single';
            }
        }
        
        // set initial state
        this.current = this.mode;
        this.list = {};
        
        // error messages
        var extensions = options.extensions.toString();
        if (extensions) {
            extensions = extensions.replace(',', ', ');
            var pos = extensions.lastIndexOf(', ');
            if (pos != -1) {
                extensions = extensions.substr(0, pos) + ' or ' + extensions.substr(pos+1);
            }
        }
        var hda_error = 'No dataset available.';
        if (extensions) {
            hda_error = 'No ' + extensions + ' dataset available.';
        }
        var hdca_error = 'No dataset list available.';
        if (extensions) {
            hdca_error = 'No ' + extensions + ' dataset list available.';
        }
        
        // add single dataset selector
        if (this.mode == 'single') {
            radio_buttons.push({icon: 'fa-file-o', label : 'Single dataset', value : 'single'});
            this.select_single = new Ui.Select.View({
                error_text  : hda_error,
                onchange    : function() {
                    self.trigger('change');
                }
            });
            this.list['single'] = {
                field: this.select_single,
                type : 'hda'
            };
        }
        
        // add multiple dataset selector
        if (this.mode == 'single' || this.mode == 'multiple') {
            radio_buttons.push({icon: 'fa-files-o', label : 'Multiple datasets', value : 'multiple'  });
            this.select_multiple = new Ui.Select.View({
                multiple    : true,
                error_text  : hda_error,
                onchange    : function() {
                    self.trigger('change');
                }
            });
            this.list['multiple'] = {
                field: this.select_multiple,
                type : 'hda'
            };
        }
        
        // add collection selector
        if (this.mode == 'single' || this.mode == 'collection') {
            radio_buttons.push({icon: 'fa-folder-o', label : 'List of datasets',  value : 'collection' });
            this.select_collection = new Ui.Select.View({
                error_text  : hdca_error,
                onchange    : function() {
                    self.trigger('change');
                }
            });
            this.list['collection'] = {
                field: this.select_collection,
                type : 'hdca'
            };
        }
        
        // create button
        this.button_type = new Ui.RadioButton.View({
            value   : this.current,
            data    : radio_buttons,
            onchange: function(value) {
                self.current = value;
                self.refresh();
                self.trigger('change');
            }
        });
        
        // add batch mode information
        this.$batch = $(ToolTemplate.batchMode());
        
        // add elements to dom
        if (_.size(this.list) > 1) {
            this.$el.append(Utils.wrap(this.button_type.$el));
        }
        for (var i in this.list) {
            this.$el.append(this.list[i].field.$el);
        }
        this.$el.append(this.$batch);
        
        // update options
        this.update(options.data);
        
        // set initial value
        if (this.options.value !== undefined) {
            this.value(this.options.value);
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
    
    /** Indicate that select fields are being updated */
    wait: function() {
        for (var i in this.list) {
            this.list[i].field.wait();
        }
    },
    
    /** Indicate that the options update has been completed */
    unwait: function() {
        for (var i in this.list) {
            this.list[i].field.unwait();
        }
    },
    
    /** Update content selector */
    update: function(options) {
        // identify dataset options
        var dataset_options = [];
        for (var i in options.hda) {
            var hda = options.hda[i];
            dataset_options.push({
                label: hda.hid + ': ' + hda.name,
                value: hda.id
            });
        }
        
        // identify collection options
        var collection_options = [];
        for (var i in options.hdca) {
            var hdca = options.hdca[i];
            collection_options.push({
                label: hdca.hid + ': ' + hdca.name,
                value: hdca.id
            });
        }
        
        // update selection fields
        this.select_single && this.select_single.update(dataset_options);
        this.select_multiple && this.select_multiple.update(dataset_options);
        this.select_collection && this.select_collection.update(collection_options);
        
        // add to content list
        this.app.content.add(options);
    },
    
    /** Return the currently selected dataset values */
    value : function (dict) {
        // update current value
        if (dict && dict.values) {
            try {
                // create list
                var list = [];
                for (var i in dict.values) {
                    list.push(dict.values[i].id);
                }
                
                // identify suitable select field
                if (dict && dict.values.length > 0 && dict.values[0].src == 'hcda') {
                    this.current = 'collection';
                    this.select_collection.value(list[0]);
                } else {
                    if (this.mode == 'multiple') {
                        this.current = 'multiple';
                        this.select_multiple.value(list);
                    } else {
                        this.current = 'single';
                        this.select_single.value(list[0]);
                    }
                }
                this.refresh();
        
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
            batch   : this.mode == 'single' && this.current != 'single',
            values  : []
        }
        
        // append to dataset ids
        for (var i in id_list) {
            result.values.push({
                id  : id_list[i],
                src : this.list[this.current].type
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
        for (var i in this.list) {
            var $el = this.list[i].field.$el;
            if (this.current == i) {
                $el.show();
            } else {
                $el.hide();
            }
        }
        if (this.mode == 'single' && this.current != 'single') {
            this.$batch.show();
        } else {
            this.$batch.hide();
        }
    },
    
    /** Assists in selecting the current field */
    _select: function() {
        return this.list[this.current].field;
    }
});

return {
    View: View
}

});
