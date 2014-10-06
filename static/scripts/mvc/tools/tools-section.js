/*
    This class creates a tool form section and populates it with input elements. It also handles repeat blocks and conditionals by recursively creating new sub sections. New input elements can be plugged in by adding cases to the switch block defined in the _addRow() function.
*/
define(['utils/utils', 'mvc/ui/ui-table', 'mvc/ui/ui-misc', 'mvc/tools/tools-repeat', 'mvc/tools/tools-select-dataset'],
    function(Utils, Table, Ui, Repeat, SelectDataset) {

    // input field element wrapper
    var InputElement = Backbone.View.extend({
        // initialize input wrapper
        initialize: function(options) {
            this.setElement(this._template(options));
        },
        
        // set error text
        error: function(text) {
            // set text
            this.$el.find('.ui-table-form-error-text').html(text);
            this.$el.find('.ui-table-form-error').fadeIn();
        },
        
        // reset
        reset: function() {
            this.$el.find('.ui-table-form-error').hide();
        },
        
        // template
        _template: function(options) {
            // create table element
            var $input = $('<div class="ui-table-element"/>');
            
            // add error
            $input.append('<div class="ui-table-form-error ui-error"><span class="fa fa-arrow-down"/><span class="ui-table-form-error-text"></div>');
            
            // add label
            if (options.label) {
                $input.append('<div class="ui-table-form-title-strong">' + options.label + '</div>');
            }
            
            // add input element
            $input.append(options.$el);
            
            // add help
            if (options.help) {
                $input.append('<div class="ui-table-form-info">' + options.help + '</div>');
            }
            
            // return input element
            return $input;
        }
    });

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
            var table_row = this._addRow('conditional', input_def);
            
            // add fields
            for (var i in input_def.cases) {
                // create id tag
                var sub_section_id = input_def.id + '-section-' + i;
                
                // create sub section
                var sub_section = new View(this.app, {
                    inputs  : input_def.cases[i].inputs,
                    cls     : 'ui-table-plain'
                });
                
                // displays as grouped subsection
                sub_section.$el.addClass('ui-table-form-section');
                
                // create table row
                this.table.add(sub_section.$el);
                
                // append to table
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
            var repeat = new Repeat.View({
                title_new       : input_def.title,
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
                    repeat.add({
                        id              : sub_section_id,
                        title           : input_def.title,
                        $el             : sub_section.$el,
                        ondel           : function() {
                            // delete repeat block
                            repeat.del(sub_section_id);
                            
                            // retitle repeat block
                            repeat.retitle(input_def.title);
                            
                            // trigger refresh
                            self.app.refresh();
                        }
                    });
                    
                    // retitle repeat blocks
                    repeat.retitle(input_def.title);
                            
                    // trigger refresh
                    self.app.refresh();
                }
            });
            
            //
            // add min number of repeat blocks
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
                repeat.add({
                    id      : sub_section_id,
                    title   : input_def.title,
                    $el     : sub_section.$el
                });
            }
            
            // retitle repeat block
            repeat.retitle(input_def.title);
            
            // create input field wrapper
            var input_element = new InputElement({
                label       : input_def.title,
                help        : input_def.help,
                $el         : repeat.$el
            });
            
            // displays as grouped subsection
            input_element.$el.addClass('ui-table-form-section');
                
            // create table row
            this.table.add(input_element.$el);
            
            // append row to table
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
                    field = this._field_select(input_def);
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
            }
            
            // pick a generic field if specific mapping failed
            if (!field) {
                if (input_def.options) {
                    // assign select field
                    field = this._field_select(input_def);
                } else {
                    // assign text field
                    field = this._field_text(input_def);
                }
                
                // log
                console.debug('tools-form::_addRow() : Auto matched field type (' + field_type + ').');
            }
            
            // set field value
            if (input_def.value !== undefined) {
                field.value(input_def.value);
            }
            
            // add to field list
            this.app.field_list[id] = field;
            
            // create input field wrapper
            var input_element = new InputElement({
                label : input_def.label,
                help  : input_def.help,
                $el   : field.$el
            });
            
            // add to element list
            this.app.element_list[id] = input_element;
               
            // create table row
            this.table.add(input_element.$el);
            
            // append to table
            this.table.append(id);
            
            // return table row
            return this.table.get(id)
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
            
            // select field
            return new SelectDataset.View(this.app, {
                id          : 'field-' + id,
                extensions  : input_def.extensions,
                multiple    : input_def.multiple,
                onchange    : function(value) {
                    // pick the first dataset if multiple might be selected
                    // TODO: iterate over all datasets and filter common/consistent columns
                    if (value instanceof Array) {
                        value = value[0];
                    }
                    
                    // get referenced columns
                    var column_list = self.app.tree.references(id, 'data_column');
                    
                    // find selected dataset
                    var dataset = self.app.datasets.filter(value);
        
                    // meta data
                    var meta = null;
        
                    // check dataset
                    if (dataset && column_list.length > 0) {
                        // log selection
                        console.debug('tool-form::field_data() - Selected dataset ' + value + '.');
                    
                        // get meta data
                        meta = dataset.get('metadata_column_types');
                    
                        // check meta data
                        if (!meta) {
                            console.debug('tool-form::field_data() - FAILED: Could not find metadata for dataset ' + value + '.');
                        }
                    } else {
                        // log failure
                        console.debug('tool-form::field_data() - FAILED: Could not find dataset ' + value + '.');
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
                            
                            // column index
                            var column_index = (parseInt(key) + 1);
                            
                            // column type label
                            var column_label = 'Text';
                            if (column_type == 'int' || column_type == 'float') {
                                column_label = 'Number';
                            }
                            
                            // add to selection
                            if (column_type == 'int' || column_type == 'float' || !numerical) {
                                columns.push({
                                    'label' : 'Column: ' + column_index + ' [' + column_label + ']',
                                    'value' : column_index
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
                    SelectClass = Ui.Radio;
                    break;
            }
            
            // select field
            return new SelectClass.View({
                id      : 'field-' + input_def.id,
                data    : options,
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
        
        // slider field
        _field_slider: function(input_def) {
            // calculate step size
            var step = 1;
            if (input_def.type == 'float') {
                step = (input_def.max - input_def.min) / 10000;
            }
            
            // create slider
            return new Ui.Slider.View({
                id      : 'field-' + input_def.id,
                min     : input_def.min || 0,
                max     : input_def.max || 1000,
                step    : step
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
                data    : [ { label : 'Yes', value : 'true'  },
                            { label : 'No',  value : 'false' }]
            });
        }
    });

    return {
        View: View
    };
});
