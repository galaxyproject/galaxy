/**
    This class creates a tool form section and populates it with input elements. It also handles repeat blocks and conditionals by recursively creating new sub sections. New input elements can be plugged in by adding cases to the switch block defined in the _createField() function.
*/
define(['utils/utils', 'mvc/ui/ui-table', 'mvc/ui/ui-misc', 'mvc/ui/ui-portlet', 'mvc/tools/tools-repeat', 'mvc/tools/tools-select-content', 'mvc/tools/tools-input'],
    function(Utils, Table, Ui, Portlet, Repeat, SelectContent, InputElement) {

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
                this.add(this.inputs[i]);
            }
        },
        
        /** Add a new input element
        */
        add: function(input) {
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
                // customized section
                case 'section':
                    this._addSection(input_def);
                    break;
                // default single element row
                default:
                    this._addRow(input_def);
            }
        },
        
        /** Add a conditional block
        */
        _addConditional: function(input_def) {
            // link this
            var self = this;
            
            // copy identifier
            input_def.test_param.id = input_def.id;
            
            // build test parameter
            var field = this._addRow(input_def.test_param);
            
            // set onchange event for test parameter
            field.options.onchange = function(value) {
                // identify the selected case
                var selectedCase = self.app.tree.matchCase(input_def, value);
                
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
                        if (!case_def.inputs[j].hidden) {
                            nonhidden = true;
                            break;
                        }
                    }
                    
                    // show/hide sub form
                    if (i == selectedCase && nonhidden) {
                        section_row.fadeIn('fast');
                    } else {
                        section_row.hide();
                    }
                }
                
                // refresh form inputs
                self.app.trigger('refresh');
            };
            
            // add conditional sub sections
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
            
            // trigger refresh on conditional input field after all input elements have been created
            field.trigger('change');
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
                        self.app.trigger('refresh');
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
                    self.app.trigger('refresh');
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
            var input_element = new InputElement(this.app, {
                label   : input_def.title,
                help    : input_def.help,
                field   : repeat
            });
            
            // displays as grouped subsection
            input_element.$el.addClass('ui-table-form-section');
                
            // create table row
            this.table.add(input_element.$el);
            
            // append row to table
            this.table.append(input_def.id);
        },
        
        /** Add a customized section
        */
        _addSection: function(input_def) {
            // link this
            var self = this;
            
            // create sub section
            var sub_section = new View(self.app, {
                inputs  : input_def.inputs,
                cls     : 'ui-table-plain'
            });
            
            // delete button
            var button_visible = new Ui.ButtonIcon({
                icon    : 'fa-eye-slash',
                tooltip : 'Show/hide section',
                cls     : 'ui-button-icon-plain'
            });
            
            // create portlet for sub section
            var portlet = new Portlet.View({
                title       : input_def.label,
                cls         : 'ui-portlet-section',
                operations  : {
                    button_visible: button_visible
                }
            });
            portlet.append(sub_section.$el);
            
            // add event handler visibility button
            var visible = false;
            portlet.$content.hide();
            portlet.$header.css('cursor', 'pointer');
            portlet.$header.on('click', function() {
                if (visible) {
                    visible = false;
                    portlet.$content.hide();
                    button_visible.setIcon('fa-eye-slash');
                } else {
                    visible = true;
                    portlet.$content.fadeIn('fast');
                    button_visible.setIcon('fa-eye');
                }
            });
            
            // show sub section if requested
            if (input_def.expand) {
                portlet.$header.trigger('click');
            }
            
            // create table row
            this.table.add(portlet.$el);

            // append row to table
            this.table.append(input_def.id);
        },

        /** Add a single input field element
        */
        _addRow: function(input_def) {
            // get id
            var id = input_def.id;

            // create input field
            var field = this._createField(input_def);
            
            // add to field list
            this.app.field_list[id] = field;
            
            // create input field wrapper
            var input_element = new InputElement(this.app, {
                label           : input_def.label,
                defaultvalue    : input_def.defaultvalue,
                optional        : input_def.optional,
                help            : input_def.help,
                field           : field
            });
            
            // add to element list
            this.app.element_list[id] = input_element;
               
            // create table row
            this.table.add(input_element.$el);
            
            // append to table
            this.table.append(id);
            
            // hide row if neccessary
            if (input_def.hidden) {
                this.table.get(id).hide();
            }
            
            // return created field
            return field;
        },
        
        /** Returns an input field for a given field type
        */
        _createField: function(input_def) {
            // field wrapper
            var field = null;
            
            // identify field type
            switch(input_def.type) {
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
                
                // collection selector
                case 'data_collection':
                    field = this._fieldData(input_def);
                    break;
                    
                // data column
                case 'data_column':
                    input_def.error_text = 'Missing columns in referenced dataset.';
                    field = this._fieldSelect(input_def);
                    break;
                    
                // hidden field
                case 'hidden':
                    field = this._fieldHidden(input_def);
                    break;
                
                // hidden data field
                case 'hidden_data':
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
                    input_def.searchable = true;
                    field = this._fieldSelect(input_def);
                    break;
                
                // drill down field
                case 'drill_down':
                    field = this._fieldDrilldown(input_def);
                    break;
                
                // base url field
                case 'baseurl':
                    field = this._fieldHidden(input_def);
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
                    console.debug('tools-form::_addRow() : Auto matched field type (' + input_def.type + ').');
            }
            
            // set field value
            if (input_def.value !== undefined) {
                field.value(input_def.value);
            }
            
            // return field element
            return field;
        },
        
        /** Data input field
        */
        _fieldData : function(input_def) {
            if (this.app.workflow) {
                var extensions = Utils.textify(input_def.extensions.toString());
                input_def.info = 'Data input \'' + input_def.name + '\' (' + extensions + ')';
                return this._fieldHidden(input_def);
            }
            var self = this;
            return new SelectContent.View(this.app, {
                id          : 'field-' + input_def.id,
                extensions  : input_def.extensions,
                multiple    : input_def.multiple,
                type        : input_def.type,
                data        : input_def.options,
                onchange    : function() {
                    self.app.trigger('refresh');
                }
            });
        },
        
        /** Select/Checkbox/Radio options field
        */
        _fieldSelect : function (input_def) {
            // show text field in workflow
            if (this.app.workflow && input_def.is_dynamic) {
                if (!Utils.validate(input_def.value)) {
                    input_def.value = '';
                }
                return this._fieldText(input_def);
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
            var self = this;
            return new SelectClass.View({
                id          : 'field-' + input_def.id,
                data        : options,
                error_text  : input_def.error_text || 'No options available',
                multiple    : input_def.multiple,
                searchable  : input_def.searchable,
                onchange    : function() {
                    self.app.trigger('refresh');
                }
            });
        },
        
        /** Drill down options field
        */
        _fieldDrilldown : function (input_def) {
            var self = this;
            return new Ui.Drilldown.View({
                id          : 'field-' + input_def.id,
                data        : input_def.options,
                display     : input_def.display,
                onchange    : function() {
                    self.app.trigger('refresh');
                }
            });
        },
        
        /** Text input field
        */
        _fieldText : function(input_def) {
            var self = this;
            return new Ui.Input({
                id          : 'field-' + input_def.id,
                area        : input_def.area,
                onchange    : function() {
                    self.app.trigger('refresh');
                }
            });
        },
        
        /** Slider field
        */
        _fieldSlider: function(input_def) {
            var self = this;
            return new Ui.Slider.View({
                id          : 'field-' + input_def.id,
                precise     : input_def.type == 'float',
                min         : input_def.min,
                max         : input_def.max,
                onchange    : function() {
                    self.app.trigger('refresh');
                }
            });
        },
        
        /** Hidden field
        */
        _fieldHidden : function(input_def) {
            return new Ui.Hidden({
                id          : 'field-' + input_def.id,
                info        : input_def.info
            });
        },
        
        /** Boolean field
        */
        _fieldBoolean : function(input_def) {
            var self = this;
            return new Ui.RadioButton.View({
                id          : 'field-' + input_def.id,
                data        : [ { label : 'Yes', value : 'true'  },
                                { label : 'No',  value : 'false' }],
                onchange    : function() {
                    self.app.trigger('refresh');
                }
            });
        }
    });

    return {
        View: View
    };
});
