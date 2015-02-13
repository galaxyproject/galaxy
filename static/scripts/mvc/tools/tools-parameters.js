/**
    This class creates input elements. New input parameter types should be added to the types dictionary.
*/
define(['utils/utils',
        'mvc/ui/ui-misc',
        'mvc/tools/tools-select-content',
        'mvc/ui/ui-color-picker'],
    function(Utils, Ui, SelectContent, ColorPicker) {

    // create form view
    return Backbone.Model.extend({
        /** Available parameter types */
        types: {
            'text'              : '_fieldText',
            'select'            : '_fieldSelect',
            'data_column'       : '_fieldSelect',
            'genomebuild'       : '_fieldSelect',
            'data'              : '_fieldData',
            'data_collection'   : '_fieldData',
            'integer'           : '_fieldSlider',
            'float'             : '_fieldSlider',
            'boolean'           : '_fieldBoolean',
            'drill_down'        : '_fieldDrilldown',
            'color'             : '_fieldColor',
            'hidden'            : '_fieldHidden',
            'hidden_data'       : '_fieldHidden',
            'baseurl'           : '_fieldHidden',
        },
        
        // initialize
        initialize: function(app, options) {
            this.app = app;
        },

        /** Returns an input field for a given field type
        */
        create: function(input_def) {
            // add regular/default value if missing
            if (input_def.value === undefined) {
                input_def.value = null;
            }
            if (input_def.default_value === undefined) {
                input_def.default_value = input_def.value;
            }

            // field wrapper
            var field = null;

            // get field class
            var fieldClass = this.types[input_def.type];
            if (fieldClass && typeof(this[fieldClass]) === 'function') {
                field = this[fieldClass].call(this, input_def);
            }
            
            // identify field type
            if (!field) {
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
            if (!this.app.options.is_dynamic) {
                input_def.info = 'Data input \'' + input_def.name + '\' (' + Utils.textify(input_def.extensions.toString()) + ')';
                input_def.value = null;
                return this._fieldHidden(input_def);
            }
            var self = this;
            return new SelectContent.View(this.app, {
                id          : 'field-' + input_def.id,
                extensions  : input_def.extensions,
                optional    : input_def.optional,
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
            // show text field in if dynamic fields are disabled e.g. in workflow editor
            if (!this.app.options.is_dynamic && input_def.is_dynamic) {
                return this._fieldText(input_def);
            }

            // customize properties
            if (input_def.type == 'data_column') {
                input_def.error_text = 'Missing columns in referenced dataset.'
            }
            if (input_def.type == 'genomebuild') {
                input_def.searchable = true;
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
            // show text field in if dynamic fields are disabled e.g. in workflow editor
            if (!this.app.options.is_dynamic && input_def.is_dynamic) {
                return this._fieldText(input_def);
            }
            
            // create drill down field
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
            // field replaces e.g. a select field
            if (input_def.options) {
                // show text area if selecting multiple entries is allowed
                input_def.area = input_def.multiple;

                // validate value
                if (!Utils.validate(input_def.value)) {
                    input_def.value = '';
                } else {
                    if (input_def.value instanceof Array) {
                        input_def.value = value.toString();
                    } else {
                        input_def.value = String(input_def.value).replace(/[\[\]'"\s]/g, '');
                        if (input_def.multiple) {
                            input_def.value = input_def.value.replace(/,/g, '\n');
                        }
                    }
                }
            }

            // create input element
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
        },

        /** Color picker field
        */
        _fieldColor : function(input_def) {
            var self = this;
            return new ColorPicker(this.app, {
                id          : 'field-' + input_def.id,
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
