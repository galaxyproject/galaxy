define(['mvc/ui/ui-table', 'mvc/ui/ui-misc', 'mvc/ui/ui-tabs'], function(Table, Ui, Tabs) {

    // create form view
    var View = Backbone.View.extend({
        // initialize
        initialize: function(app, options) {
            // link app
            this.app = app;
            
            // link inputs
            this.inputs = options.inputs;
            
            // link datasets
            this.datasets = app.datasets;
            
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
            
            // model
            var data = new Backbone.Model();
            
            // load settings elements into table
            for (var id in this.inputs) {
                this._add(this.inputs[id], data);
            }
            
            // trigger change
            for (var id in this.app.field_list) {
                this.app.field_list[id].trigger('change');
            }
        },
        
        // add table row
        _add: function(inputs_def, data) {
            // link this
            var self = this;
            
            // identify field type
            var type = inputs_def.type;
            switch(type) {
                // conditional field
                case 'conditional':
                    // add label to input definition root
                    inputs_def.label = inputs_def.test_param.label;
                
                    // add id to input definition root
                    inputs_def.name = inputs_def.test_param.name;
                
                    // build options field
                    this._addRow('conditional', inputs_def, data);
                    
                    // add fields
                    for (var i in inputs_def.cases) {
                        // create sub section
                        var sub_section = new View(this.app, {
                            inputs  : inputs_def.cases[i].inputs,
                            cls     : 'ui-table-plain'
                        });
                        
                        // append sub section
                        this.table.add('');
                        this.table.add(sub_section.$el);
                        this.table.append(inputs_def.name + '_formsection_' + i);
                    }
                    break;
                // repeat block
                case 'repeat':
                    // create tab field
                    var tabs = new Tabs.View({
                        title_new       : 'Add Group',
                        onnew           : function() {
                            // create sub section
                            var sub_section = new View(self.app, {
                                inputs  : inputs_def.inputs,
                                cls     : 'ui-table-plain'
                            });
                            
                            // create id tag
                            var sub_section_id = inputs_def.name + '_formsection_' + tabs.size();
                        
                            // add new tab
                            tabs.add({
                                id              : sub_section_id,
                                title           : 'Repeat',
                                $el             : sub_section.$el,
                                ondel           : function() {
                                    tabs.del(sub_section_id);
                                }
                            });
                            
                            // show tab
                            tabs.show(sub_section_id);
                        }
                    });
                    
                    // append sub section
                    this.table.add(inputs_def.title);
                    this.table.add(tabs.$el);
                    this.table.append(inputs_def.name);
                    break;
                // default single element row
                default:
                    this._addRow(type, inputs_def, data);
            }
        },
        
        // add table row
        _addRow: function(field_type, inputs_def, data) {
            // get id
            var id = inputs_def.name;
            
            // field wrapper
            var field = null;
            
            // identify field type
            switch(field_type) {
                // text input field
                case 'text' :
                    field = this._field_text(inputs_def, data);
                    break;
                    
                // select field
                case 'select' :
                    field = this._field_select(inputs_def, data);
                    break;
                    
                // radiobox field
                case 'radiobutton' :
                    field = this._field_radio(inputs_def, data);
                    break;
                
                // dataset
                case 'data':
                    field = this._field_data(inputs_def, data);
                    break;
                
                // dataset column
                case 'data_column':
                    field = this._field_column(inputs_def, data);
                    break;
                
                // text area field
                case 'textarea' :
                    field = this._field_textarea(inputs_def, data);
                    break;
                    
                // conditional select field
                case 'conditional':
                    field = this._field_conditional(inputs_def, data);
                    break;
            }
            
            // check if field type was detected
            if (!field) {
                console.debug('tools-form::_addRow() : Unmatched field type (' + field_type + ').');
                return;
            }
            
            // set value
            if (!data.get(id)) {
                data.set(id, inputs_def.value);
            }
            field.value(data.get(id));
            
            // add to field list
            this.app.field_list[id] = field;
            
            // add to input definition into sequential list
            this.app.inputs_sequential[id] = inputs_def;
            
            // combine field and info
            var $input = $('<div/>');
            $input.append(field.$el);
            if (inputs_def.help) {
                $input.append('<div class="ui-table-form-info">' + inputs_def.help + '</div>');
            }
            
            // add row to table
            this.table.add('<span class="ui-table-form-title">' + inputs_def.label + '</span>', '25%');
            this.table.add($input);
            
            // add to table
            this.table.append(id);
            
            // show/hide
            if (inputs_def.hide) {
                this.table.get(id).hide();
            }
        },
        
        // text input field
        _field_text : function(inputs_def, data) {
            var id = inputs_def.name;
            return new Ui.Input({
                id          : 'field-' + id,
                value       : data.get(id),
                onchange    : function(value) {
                    data.set(id, value);
                }
            });
        },
        
        // text area
        _field_textarea : function(inputs_def, data) {
            var id = inputs_def.name;
            return new Ui.Textarea({
                id          : 'field-' + id,
                onchange    : function() {
                    data.set(id, field.value());
                }
            });
        },
        
        // conditional input field
        _field_conditional : function(inputs_def, data) {
            // link this
            var self = this;

            // configure options fields
            var options = [];
            for (var i in inputs_def.test_param.options) {
                var option = inputs_def.test_param.options[i];
                options.push({
                    label: option[0],
                    value: option[1]
                });
            }
            
            // select field
            var id = inputs_def.name;
            return new Ui.Select.View({
                id          : 'field-' + id,
                data        : options,
                value       : data.get(id),
                onchange    : function(value) {
                    // update value
                    data.set(id, value);
                    
                    // check value in order to hide/show options
                    for (var i in inputs_def.cases) {
                        // get case
                        var case_def = inputs_def.cases[i];
                        
                        // identify subsection name
                        var section_id = inputs_def.name + '_formsection_' + i;
                    
                        // identify row
                        var section_row = self.table.get(section_id);
                        
                        // check
                        if (case_def.value == value) {
                            section_row.show();
                        } else {
                            section_row.hide();
                        }
                    }
                }
            });
        },
        
        // data input field
        _field_data : function(inputs_def, data) {
            // link this
            var self = this;
            
            // get element id
            var id = inputs_def.name;
            
            // get datasets
            var datasets = this.datasets.filterType();
            
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
                onchange    : function(value) {
                    // update value
                    data.set(id, value);
                    
                    // find referenced columns
                    var column_list = _.where(self.app.inputs_sequential, {
                        data_ref    : id,
                        type        : 'data_column'
                    });
                    
                    // find selected dataset
                    var dataset = self.datasets.filter(value);
        
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
                        
                        // load column options
                        var columns = [];
                        for (var key in meta) {
                            // add to selection
                            columns.push({
                                'label' : 'Column: ' + (parseInt(key) + 1) + ' [' + meta[key] + ']',
                                'value' : key
                            });
                        }
                
                        // update referenced columns
                        for (var i in column_list) {
                            var column_field = self.app.field_list[column_list[i].name]
                            if (column_field) {
                                column_field.update(columns);
                                column_field.value(column_field.first());
                            }
                        }
                    } else {
                        // log failure
                        console.debug('tool-form::field_data() - FAILED: Could not find dataset ' + value + '.');
                    }
                }
            });
        },
        
        // column selection field
        _field_column : function (inputs_def, data) {
            var id = inputs_def.name;
            return new Ui.Select.View({
                id          : 'field-' + id,
                value       : data.get(id),
                onchange    : function(value) {
                    data.set(id, value);
                }
            });
        },

        // select field
        _field_select : function (inputs_def, data) {
            // configure options fields
            var options = [];
            for (var i in inputs_def.options) {
                var option = inputs_def.options[i];
                options.push({
                    label: option[0],
                    value: option[1]
                });
            }
            
            // identify display type
            var SelectClass = Ui.Select;
            if (inputs_def.display == 'checkboxes') {
                SelectClass = Ui.Checkbox;
            }
            
            // select field
            var id = inputs_def.name;
            return new SelectClass.View({
                id          : 'field-' + id,
                data        : options,
                value       : data.get(id),
                onchange    : function(value) {
                    data.set(id, value);
                }
            });
        },
        
        // radio field
        _field_radio : function(inputs_def, data) {
            var id = inputs_def.name;
            return new Ui.RadioButton({
                id          : 'field-' + id,
                data        : inputs_def.data,
                value       : data.get(id),
                onchange    : function(value) {
                    data.set(id, value);
                }
            });
        }
    });

    return {
        View: View
    };
});
