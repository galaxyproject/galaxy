/**
    This class creates a tool form section and populates it with input elements. It also handles repeat blocks and conditionals by recursively creating new sub sections. New input elements can be plugged in by adding cases to the switch block defined in the _addRow() function.
*/
define(['utils/utils', 'mvc/ui/ui-table', 'mvc/ui/ui-misc', 'mvc/tools/tools-repeat', 'mvc/tools/tools-select-content', 'mvc/tools/tools-input'],
    function(Utils, Table, Ui, Repeat, SelectContent, InputElement) {

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
        
        /** Render section view
        */
        render: function() {
            // reset table
            this.table.delAll();
            
            // load settings elements into table
            for (var i in this.inputs) {
                this._add(this.inputs[i]);
            }
        },
        
        /** Add a new input element
        */
        _add: function(input) {
            // link this
            var self = this;
            
            // clone definition
            var input_def = jQuery.extend(true, {}, input);
            
            // create unique id
            input_def.id = input.id = Utils.uuid();
    
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
        
        /** Add a conditional block
        */
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
        
        /** Add a repeat block
        */
        _addRepeat: function(input_def) {
            // link this
            var self = this;
            
            // block index
            var block_index = 0;
            
            // helper function to create new repeat blocks
            function create (inputs, deleteable) {
                // create id tag
                var sub_section_id = input_def.id + '-section-' + (block_index++);
            
                // enable/disable repeat delete button
                var ondel = null;
                if (deleteable) {
                    ondel = function() {
                        // delete repeat block
                        repeat.del(sub_section_id);
                        
                        // retitle repeat block
                        repeat.retitle(input_def.title);
                        
                        // trigger refresh
                        self.app.refresh();
                    }
                }
                    
                // create sub section
                var sub_section = new View(self.app, {
                    inputs  : inputs,
                    cls     : 'ui-table-plain'
                });
                
                // add tab
                repeat.add({
                    id      : sub_section_id,
                    title   : input_def.title,
                    $el     : sub_section.$el,
                    ondel   : ondel
                });
                
                // retitle repeat block
                repeat.retitle(input_def.title);
            }
            
            //
            // create repeat block element
            //
            var repeat = new Repeat.View({
                title_new       : input_def.title,
                max             : input_def.max,
                onnew           : function() {
                    // create
                    create(input_def.inputs, true);
                            
                    // trigger refresh
                    self.app.refresh();
                }
            });
            
            //
            // add parsed/minimum number of repeat blocks
            //
            var n_min   = input_def.min;
            var n_cache = _.size(input_def.cache);
            for (var i = 0; i < Math.max(n_cache, n_min); i++) {
                // select input source
                var inputs = null;
                if (i < n_cache) {
                    inputs = input_def.cache[i];
                } else {
                    inputs = input_def.inputs;
                }
                
                // create repeat block
                create(inputs, i >= n_min);
            }
            
            // create input field wrapper
            var input_element = new InputElement({
                label       : input_def.title,
                help        : input_def.help,
                field       : repeat
            });
            
            // displays as grouped subsection
            input_element.$el.addClass('ui-table-form-section');
                
            // create table row
            this.table.add(input_element.$el);
            
            // append row to table
            this.table.append(input_def.id);
        },
        
        /** Add a single field element
        */
        _addRow: function(field_type, input_def) {
            // get id
            var id = input_def.id;

            // field wrapper
            var field = null;
            
            // identify field type
            switch(field_type) {
                // text input field
                case 'text' :
                    field = this._fieldText(input_def);
                    break;
                    
                // select field
                case 'select' :
                    field = this._fieldSelect(input_def);
                    break;
                    
                // data selector
                case 'data':
                    field = this._fieldData(input_def);
                    break;
                
                // data column
                case 'data_column':
                    input_def.is_dynamic = false;
                    field = this._fieldSelect(input_def);
                    break;
                    
                // conditional select field
                case 'conditional':
                    field = this._fieldConditional(input_def);
                    break;
                
                // hidden field
                case 'hidden':
                    field = this._fieldHidden(input_def);
                    break;
                
                // integer field
                case 'integer':
                    field = this._fieldSlider(input_def);
                    break;
                
                // float field
                case 'float':
                    field = this._fieldSlider(input_def);
                    break;
                                    
                // boolean field
                case 'boolean':
                    field = this._fieldBoolean(input_def);
                    break;
                    
                // genome field
                case 'genomebuild':
                    field = this._fieldSelect(input_def);
                    break;
                    
                // field not found
                default:
                    // flag
                    this.app.incompatible = true;
                    
                    // with or without options
                    if (input_def.options) {
                        // assign select field
                        field = this._fieldSelect(input_def);
                    } else {
                        // assign text field
                        field = this._fieldText(input_def);
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
                label       : input_def.label,
                optional    : input_def.optional,
                help        : input_def.help,
                field       : field
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
        
        /** Conditional input field selector
        */
        _fieldConditional : function(input_def) {
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
        
        /** Data input field
        */
        _fieldData : function(input_def) {
            // link this
            var self = this;
            
            // get element id
            var id = input_def.id;
            
            // select field
            return new SelectContent.View(this.app, {
                id          : 'field-' + id,
                extensions  : input_def.extensions,
                multiple    : input_def.multiple,
                onchange    : function(dict) {
                    // rebuild the form
                    if (self.app.is_dynamic) {
                        self.app.rebuild();
                    }
                    
                    // pick the first content only (todo: maybe collect multiple meta information)
                    var content_def     = dict.values[0];
                    var content_id      = content_def.id;
                    var content_src     = content_def.src;
                    
                    // get referenced columns
                    var column_list = self.app.tree.references(id, 'data_column');
                    
                    // check data column list
                    if (column_list.length <= 0) {
                        console.debug('tool-form::field_data() -  Data column parameters unavailable.');
                        return;
                    }
                    
                    // set wait mode
                    for (var i in column_list) {
                        var column_field = self.app.field_list[column_list[i]];
                        column_field.wait && column_field.wait();
                    }
                    
                    // find selected content
                    self.app.content.getDetails({
                        id      : content_id,
                        src     : content_src,
                        success : function(content) {
                            // meta data
                            var meta = null;
                            
                            // check content
                            if (content) {
                                // log selection
                                console.debug('tool-form::field_data() - Selected content ' + content_id + '.');
                            
                                // select the first dataset to represent collections
                                if (content_src == 'hdca' && content.elements && content.elements.length > 0) {
                                    content = content.elements[0].object;
                                }
                            
                                // get meta data
                                meta = content.metadata_column_types;
                            
                                // check meta data
                                if (!meta) {
                                    console.debug('tool-form::field_data() - FAILED: Could not find metadata for content ' + content_id + '.');
                                }
                            } else {
                                console.debug('tool-form::field_data() - FAILED: Could not find content ' + content_id + '.');
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
                                    column_field.show();
                                }
                            }
                        }
                    });
                }
            });
        },
        
        /** Select/Checkbox/Radio options field
        */
        _fieldSelect : function (input_def) {
            // check compatibility
            if (input_def.is_dynamic) {
                this.app.is_dynamic = true;
            }
            
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
        
        /** Text input field
        */
        _fieldText : function(input_def) {
            return new Ui.Input({
                id      : 'field-' + input_def.id,
                area    : input_def.area
            });
        },
        
        /** Slider field
        */
        _fieldSlider: function(input_def) {
            // create slider
            return new Ui.Slider.View({
                id      : 'field-' + input_def.id,
                precise : input_def.type == 'float',
                min     : input_def.min,
                max     : input_def.max
            });
        },
        
        /** Hidden field
        */
        _fieldHidden : function(input_def) {
            return new Ui.Hidden({
                id      : 'field-' + input_def.id
            });
        },
        
        /** Boolean field
        */
        _fieldBoolean : function(input_def) {
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
