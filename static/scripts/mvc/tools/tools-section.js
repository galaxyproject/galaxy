define(['utils/utils', 'mvc/ui/ui-table', 'mvc/ui/ui-misc', 'mvc/ui/ui-tabs'],
    function(Utils, Table, Ui, Tabs) {

    // create form view
    var View = Backbone.View.extend({
        // initialize
        initialize: function(app, options) {
            // link app
            this.app = app;
            
            // link inputs
            this.inputs = options.inputs;
            
            // add table class for tr tag
            // this assist in transforming the form into a json structure
            options.cls_tr = 'section-row';
            
            // create table
            this.table = new Table.View(options);
            
            // configure portlet and form table
            this.setElement(this.table.$el);
            
            // render tool section
            this.render();
        },
        
        // update
        render: function() {
            // reset table
            this.table.delAll();
            
            // load settings elements into table
            for (var i in this.inputs) {
                this._add(this.inputs[i]);
            }
        },
        
        // add table row
        _add: function(input) {
            // link this
            var self = this;
            
            // clone definition
            var input_def = jQuery.extend(true, {}, input);
            
            // create unique id
            input_def.id = Utils.uuid();
    
            // add to sequential list of inputs
            this.app.input_list[input_def.id] = input_def;
            
            // identify field type
            var type = input_def.type;
            switch(type) {
                // conditional field
                case 'conditional':
                    this._addConditional(input_def);
                    break;
                // repeat block
                case 'repeat':
                    this._addRepeat(input_def);
                    break;
                // default single element row
                default:
                    this._addRow(type, input_def);
            }
        },
        
        // add conditional block
        _addConditional: function(input_def) {
            // add label to input definition root
            input_def.label = input_def.test_param.label;
        
            // add value to input definition root
            input_def.value = input_def.test_param.value;
        
            // build options field
            this._addRow('conditional', input_def);
            
            // add fields
            for (var i in input_def.cases) {
                // create id tag
                var sub_section_id = input_def.id + '-section-' + i;
                
                // create sub section
                var sub_section = new View(this.app, {
                    inputs  : input_def.cases[i].inputs,
                    cls     : 'ui-table-plain'
                });
                
                // append sub section
                this.table.add('');
                this.table.add(sub_section.$el);
                this.table.append(sub_section_id);
            }
        },
        
        // add repeat block
        _addRepeat: function(input_def) {
            // link this
            var self = this;
            
            //
            // create tab field
            //
            var tabs = new Tabs.View({
                title_new       : 'Add ' + input_def.title,
                max             : input_def.max,
                onnew           : function() {
                    // create id tag
                    var sub_section_id = input_def.id + '-section-' + Utils.uuid();
                
                    // create sub section
                    var sub_section = new View(self.app, {
                        inputs  : input_def.inputs,
                        cls     : 'ui-table-plain'
                    });
                    
                    // add new tab
                    tabs.add({
                        id              : sub_section_id,
                        title           : input_def.title,
                        $el             : sub_section.$el,
                        ondel           : function() {
                            // delete tab
                            tabs.del(sub_section_id);
                            
                            // retitle tabs
                            tabs.retitle(input_def.title);
                            
                            // trigger refresh
                            self.app.refresh();
                        }
                    });
                    
                    // retitle tabs
                    tabs.retitle(input_def.title);
                            
                    // show tab
                    tabs.show(sub_section_id);
            
                    // trigger refresh
                    self.app.refresh();
                }
            });
            
            //
            // add min number of tabs
            //
            for (var i = 0; i < input_def.min; i++) {
                // create id tag
                var sub_section_id = input_def.id + '-section-' + Utils.uuid();
            
                // create sub section
                var sub_section = new View(self.app, {
                    inputs  : input_def.inputs,
                    cls     : 'ui-table-plain'
                });
                
                // add tab
                tabs.add({
                    id      : sub_section_id,
                    title   : input_def.title,
                    $el     : sub_section.$el
                });
            }
            
            // retitle tabs
            tabs.retitle(input_def.title);
            
            // append sub section
            this.table.add('');
            this.table.add(tabs.$el);
            this.table.append(input_def.id);
        },
        
        // add table row
        _addRow: function(field_type, input_def) {
            // get id
            var id = input_def.id;
            
            // field wrapper
            var field = null;
            
            // identify field type
            switch(field_type) {
                // text input field
                case 'text' :
                    field = this._field_text(input_def);
                    break;
                    
                // select field
                case 'select' :
                    field = this._field_select(input_def);
                    break;
                    
                // dataset
                case 'data':
                    field = this._field_data(input_def);
                    break;
                
                // dataset column
                case 'data_column':
                    field = this._field_column(input_def);
                    break;
                    
                // conditional select field
                case 'conditional':
                    field = this._field_conditional(input_def);
                    break;
                
                // hidden field
                case 'hidden':
                    field = this._field_hidden(input_def);
                    break;
                
                // integer field
                case 'integer':
                    field = this._field_slider(input_def);
                    break;
                
                // float field
                case 'float':
                    field = this._field_slider(input_def);
                    break;
                                    
                // boolean field
                case 'boolean':
                    field = this._field_boolean(input_def);
                    break;
                    
                // default
                default:
                    field = this._field_text(input_def);
                    console.debug('tools-form::_addRow() : Unmatched field type (' + field_type + ').');
            }
            
            // set field value
            if (input_def.value !== undefined) {
                field.value(input_def.value);
            }
            
            // add to field list
            this.app.field_list[id] = field;
            
            // combine field and info
            var $input = $('<div/>');
            $input.append(field.$el);
            if (input_def.help) {
                $input.append('<div class="ui-table-form-info">' + input_def.help + '</div>');
            }
            
            // create table row
            this.table.add('<span class="ui-table-form-title">' + input_def.label + '</span>', '20%');
            this.table.add($input);
            
            // append to table
            this.table.append(id);
        },
        
        // conditional input field
        _field_conditional : function(input_def) {
            // link this
            var self = this;

            // configure options fields
            var options = [];
            for (var i in input_def.test_param.options) {
                var option = input_def.test_param.options[i];
                options.push({
                    label: option[0],
                    value: option[1]
                });
            }
            
            // select field
            return new Ui.Select.View({
                id          : 'field-' + input_def.id,
                data        : options,
                onchange    : function(value) {
                    // check value in order to hide/show options
                    for (var i in input_def.cases) {
                        // get case
                        var case_def = input_def.cases[i];
                        
                        // identify subsection name
                        var section_id = input_def.id + '-section-' + i;
                        
                        // identify row
                        var section_row = self.table.get(section_id);
                        
                        // check if non-hidden elements exist
                        var nonhidden = false;
                        for (var j in case_def.inputs) {
                            var type = case_def.inputs[j].type;
                            if (type && type !== 'hidden') {
                                nonhidden = true;
                                break;
                            }
                        }
                        
                        // show/hide sub form
                        if (case_def.value == value && nonhidden) {
                            section_row.fadeIn('fast');
                        } else {
                            section_row.hide();
                        }
                    }
                }
            });
        },
        
        // data input field
        _field_data : function(input_def) {
            // link this
            var self = this;
            
            // get element id
            var id = input_def.id;
            
            // get datasets
            var datasets = this.app.datasets.filterType();
            
            // configure options fields
            var options = [];
            for (var i in datasets) {
                options.push({
                    label: datasets[i].get('name'),
                    value: datasets[i].get('id')
                });
            }
            
            // select field
            return new Ui.Select.View({
                id          : 'field-' + id,
                data        : options,
                value       : options[0].value,
                multiple    : input_def.multiple,
                onchange    : function(value) {
                    // pick the first dataset if multiple might be selected
                    // TODO: iterate over all datasets and filter common/consistent columns
                    if (input_def.multiple) {
                        value = value[0];
                    }
                    
                    // get referenced columns
                    var column_list = self.app.tree.findReferences(id, 'data_column');
                    
                    // find selected dataset
                    var dataset = self.app.datasets.filter(value);
        
                    // check dataset
                    if (dataset && column_list.length > 0) {
                        // log selection
                        console.debug('tool-form::field_data() - Selected dataset ' + value + '.');
                    
                        // get meta data
                        var meta = dataset.get('metadata_column_types');
                    
                        // check meta data
                        if (!meta) {
                            console.debug('tool-form::field_data() - FAILED: Could not find metadata for dataset ' + value + '.');
                        }
                        
                        // update referenced columns
                        for (var i in column_list) {
                            // get column input/field
                            var column_input = self.app.input_list[column_list[i]];
                            var column_field = self.app.field_list[column_list[i]];
                            if (!column_input || !column_field) {
                                console.debug('tool-form::field_data() - FAILED: Column not found.');
                            }
                        
                            // is numerical?
                            var numerical = column_input.numerical;
                            
                            // identify column options
                            var columns = [];
                            for (var key in meta) {
                                // get column type
                                var column_type = meta[key];
                                
                                // add to selection
                                if (column_type == 'int' || column_type == 'float' || !numerical) {
                                    columns.push({
                                        'label' : 'Column: ' + (parseInt(key) + 1) + ' [' + meta[key] + ']',
                                        'value' : key
                                    });
                                }
                            }
                            
                            // update field
                            if (column_field) {
                                column_field.update(columns);
                                if (!column_field.exists(column_field.value())) {
                                    column_field.value(column_field.first());
                                }
                            }
                        }
                    } else {
                        // log failure
                        console.debug('tool-form::field_data() - FAILED: Could not find dataset ' + value + '.');
                    }
                }
            });
        },
        
        // select field
        _field_select : function (input_def) {
            // configure options fields
            var options = [];
            for (var i in input_def.options) {
                var option = input_def.options[i];
                options.push({
                    label: option[0],
                    value: option[1]
                });
            }
            
            // identify display type
            var SelectClass = Ui.Select;
            switch (input_def.display) {
                case 'checkboxes':
                    SelectClass = Ui.Checkbox;
                    break;
                case 'radio':
                    SelectClass = Ui.RadioButton;
                    break;
            }
            
            // force checkboxes if multiple has been selected
            if (input_def.multiple) {
                SelectClass = Ui.Checkbox;
            }
            
            // select field
            return new SelectClass.View({
                id      : 'field-' + input_def.id,
                data    : options
            });
        },

        // column selection field
        _field_column : function (input_def) {
            return new Ui.Select.View({
                id      : 'field-' + input_def.id,
                multiple: input_def.multiple
            });
        },

        // text input field
        _field_text : function(input_def) {
            return new Ui.Input({
                id      : 'field-' + input_def.id,
                area    : input_def.area
            });
        },
        
        // integer field
        _field_slider: function(input_def) {
            return new Ui.Slider.View({
                id      : 'field-' + input_def.id,
                min     : input_def.min || 0,
                max     : input_def.max || 1000,
                decimal : input_def.type == 'float'
            });
        },
        
        // hidden field
        _field_hidden : function(input_def) {
            return new Ui.Hidden({
                id      : 'field-' + input_def.id
            });
        },
        
        // boolean field
        _field_boolean : function(input_def) {
            return new Ui.RadioButton.View({
                id      : 'field-' + input_def.id,
                data    : [ { label : 'Yes', value : true  },
                            { label : 'No',  value : false }]
            });
        }
    });

    return {
        View: View
    };
});
