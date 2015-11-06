// dependencies
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/ui/ui-tabs', 'mvc/tools/tools-template'],
        function(Utils, Ui, Tabs, ToolTemplate) {

// hda/hdca content selector ui element
var View = Backbone.View.extend({
    // initialize
    initialize : function(app, options) {
        // link app and options
        this.app = app;
        this.options = options;

        // track current history elements
        this.history = {};


        // link this
        var self = this;

        // add element
        this.setElement('<div class="ui-select-content"/>');

        // list of select fieldsFormSection
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
        var extensions = Utils.textify(options.extensions);
        var hda_error = 'No dataset available.';
        if (extensions) {
            hda_error = 'No ' + extensions + ' dataset available.';
        }
        var hdca_error = 'No dataset list available.';
        if (extensions) {
            hdca_error = 'No ' + extensions + ' dataset collection available.';
        }

        // add single dataset selector
        if (this.mode == 'single') {
            radio_buttons.push({
                icon    : 'fa-file-o',
                value   : 'single',
                tooltip : 'Single dataset'
            });
            this.select_single = new Ui.Select.View({
                optional    : options.optional,
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
            radio_buttons.push({
                icon    : 'fa-files-o',
                value   : 'multiple',
                tooltip : 'Multiple datasets'
            });
            this.select_multiple = new Ui.Select.View({
                multiple    : true,
                searchable  : false,
                optional    : options.optional,
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
        if (this.mode == 'single' || this.mode == 'multiple' || this.mode == 'collection') {
            radio_buttons.push({
                icon    : 'fa-folder-o',
                value   : 'collection',
                tooltip : 'Dataset collection'
            });
            this.select_collection = new Ui.Select.View({
                error_text  : hdca_error,
                optional    : options.optional,
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
        this.$batch = $(this.template_batch());

        // number of radio buttons
        var n_buttons = _.size(this.list);

        // add button to dom
        var button_width = 0;
        if (n_buttons > 1) {
            this.$el.append(this.button_type.$el);
            button_width = Math.max(0, _.size(this.list) * 35) + 'px';
        }

        // append field elements
        for (var i in this.list) {
            this.$el.append(this.list[i].field.$el.css({
                'margin-left': button_width
            }));
        }

        // append batch message
        this.$el.append(this.$batch.css({
            'margin-left': button_width
        }));

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
        // update a particular select field
        var self = this;
        function _update(field, options) {
            if (field) {
                // identify available options
                var select_options = [];
                for (var i in options) {
                    var item = options[i];
                    select_options.push({
                        label: item.hid + ': ' + item.name,
                        value: item.id
                    });
                    // backup to local history
                    self.history[item.id + '_' + item.src] = item;
                }
                // update field
                field.update(select_options);
            }
        }

        // update available options
        _update(this.select_single, options.hda);
        _update(this.select_multiple, options.hda);
        _update(this.select_collection, options.hdca);
    },

    /** Return the currently selected dataset values */
    value : function (new_value) {
        // update current value
        if (new_value !== undefined) {
            if (new_value && new_value.values) {
                try {
                    // create list with values
                    var list = [];
                    for (var i in new_value.values) {
                        list.push(new_value.values[i].id);
                    }
                    
                    // identify suitable select field
                    if (new_value && new_value.values.length > 0 && new_value.values[0].src == 'hdca') {
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
                } catch (err) {
                    Galaxy.emit.debug('tools-select-content::value()', 'Skipped.');
                }
            } else {
                for (var i in this.list) {
                    this.list[i].field.value(null);
                }
            }
        }

        // refresh view
        this.refresh();

        // validate value
        var id_list = this._select().value();
        if (id_list === null) {
            return null;
        }

        // transform into an array
        if (!(id_list instanceof Array)) {
            id_list = [id_list];
        }

        // check if value exists
        if (id_list.length === 0) {
            return null;
        }

        // prepare result dict
        var result = {
            batch   : this._batch(),
            values  : []
        }

        // append to dataset ids
        for (var i in id_list) {
            var details = this.history[id_list[i] + '_' + this.list[this.current].type];
            if (details) {
                result.values.push(details);
            } else {
                return null;
            }
        }

        // sort by history ids
        result.values.sort(function(a, b){
            return a.hid - b.hid;
        });

        // return
        return result;
    },

    /** Refreshes data selection view */
    refresh: function() {
        this.button_type.value(this.current);
        for (var i in this.list) {
            var $el = this.list[i].field.$el;
            if (this.current == i) {
                $el.show();
            } else {
                $el.hide();
            }
        }
        if (this._batch()) {
            this.$batch.show();
        } else {
            this.$batch.hide();
        }
    },

    /** Assists in selecting the current field */
    _select: function() {
        return this.list[this.current].field;
    },

    /** Assists in identifying the batch mode */
    _batch: function() {
        if (this.current == 'collection') {
            var hdca = this.history[this._select().value() + '_hdca'];
            if (hdca && hdca.map_over_type) {
                return true;
            }
        }
        if (this.current != 'single') {
            if (this.mode == 'single') {
                return true;
            }
        }
        return false;
    },

    /** Batch message template */
    template_batch: function() {
        return  '<div class="ui-table-form-info">' +
                    '<i class="fa fa-sitemap" style="font-size: 1.2em; padding: 2px 5px;"/>' +
                    'This is a batch mode input field. A separate job will be triggered for each dataset.' +
                '</div>';
    }
});

return {
    View: View
}

});
