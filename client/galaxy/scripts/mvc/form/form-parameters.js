/**
    This class creates input elements. New input parameter types should be added to the types dictionary.
*/
define(['utils/utils',
        'mvc/ui/ui-misc',
        'mvc/ui/ui-select-content',
        'mvc/ui/ui-select-library',
        'mvc/ui/ui-select-ftp',
        'mvc/ui/ui-color-picker'],
    function( Utils, Ui, SelectContent, SelectLibrary, SelectFtp, ColorPicker ) {

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
            'library_data'      : '_fieldLibrary',
            'ftpfile'           : '_fieldFtp'
        },

        initialize: function( app, options ) {
            this.app = app;
        },

        /** Returns an input field for a given field type
        */
        create: function( input_def ) {
            var fieldClass = this.types[ input_def.type ];
            var field = typeof( this[ fieldClass ] ) === 'function' ? this[ fieldClass ].call( this, input_def ) : null;
            if ( !field ) {
                this.app.incompatible = true;
                field = input_def.options ? this._fieldSelect( input_def ) : this._fieldText( input_def );
                Galaxy.emit.debug('form-parameters::_addRow()', 'Auto matched field type (' + input_def.type + ').');
            }
            input_def.value === undefined && ( input_def.value = null );
            field.value( input_def.value );
            return field;
        },

        /** Data input field
        */
        _fieldData: function( input_def ) {
            var self = this;
            return new SelectContent.View({
                id          : 'field-' + input_def.id,
                extensions  : input_def.extensions,
                optional    : input_def.optional,
                multiple    : input_def.multiple,
                type        : input_def.type,
                data        : input_def.options,
                onchange    : function() {
                    self.app.trigger( 'change' );
                }
            });
        },

        /** Select/Checkbox/Radio options field
        */
        _fieldSelect: function ( input_def ) {
            // show text field e.g. in workflow editor
            if( input_def.is_workflow ) {
                return this._fieldText( input_def );
            }

            // customize properties
            if ( input_def.type == 'data_column' ) {
                input_def.error_text = 'Missing columns in referenced dataset.'
            }

            // configure options fields
            var options = [];
            _.each( input_def.options, function( option ) {
                options.push( { label: option[ 0 ], value: option[ 1 ] } );
            });

            // identify display type
            var SelectClass = Ui.Select;
            switch ( input_def.display ) {
                case 'checkboxes':
                    SelectClass = Ui.Checkbox;
                    break;
                case 'radio':
                    SelectClass = Ui.Radio;
                    break;
            }

            // create select field
            var self = this;
            return new SelectClass.View({
                id          : 'field-' + input_def.id,
                data        : options,
                error_text  : input_def.error_text || 'No options available',
                multiple    : input_def.multiple,
                optional    : input_def.optional,
                searchable  : input_def.searchable,
                onchange    : function() {
                    self.app.trigger( 'change' );
                }
            });
        },

        /** Drill down options field
        */
        _fieldDrilldown: function ( input_def ) {
            // show text field e.g. in workflow editor
            if( input_def.is_workflow ) {
                return this._fieldText( input_def );
            }

            // create drill down field
            var self = this;
            return new Ui.Drilldown.View({
                id          : 'field-' + input_def.id,
                data        : input_def.options,
                display     : input_def.display,
                onchange    : function() {
                    self.app.trigger( 'change' );
                }
            });
        },

        /** Text input field
        */
        _fieldText: function( input_def ) {
            // field replaces e.g. a select field
            if ( input_def.options ) {
                input_def.area = input_def.multiple;
                if ( !Utils.validate( input_def.value ) ) {
                    input_def.value = null;
                } else {
                    if ( $.isArray( input_def.value ) ) {
                        var str_value = '';
                        for ( var i in input_def.value ) {
                            str_value += String( input_def.value[ i ] );
                            if ( !input_def.multiple ) {
                                break;
                            }
                            str_value += '\n';
                        }
                        input_def.value = str_value;
                    }
                }
            }
            // create input element
            var self = this;
            return new Ui.Input({
                id          : 'field-' + input_def.id,
                area        : input_def.area,
                onchange    : function( new_value ) {
                    input_def.onchange ? input_def.onchange( new_value ) : self.app.trigger( 'change' );
                }
            });
        },

        /** Slider field
        */
        _fieldSlider: function( input_def ) {
            var self = this;
            return new Ui.Slider.View({
                id          : 'field-' + input_def.id,
                precise     : input_def.type == 'float',
                is_workflow : input_def.is_workflow,
                min         : input_def.min,
                max         : input_def.max,
                onchange    : function() {
                    self.app.trigger( 'change' );
                }
            });
        },

        /** Hidden field
        */
        _fieldHidden: function( input_def ) {
            return new Ui.Hidden({
                id          : 'field-' + input_def.id,
                info        : input_def.info
            });
        },

        /** Boolean field
        */
        _fieldBoolean: function( input_def ) {
            var self = this;
            return new Ui.RadioButton.View({
                id          : 'field-' + input_def.id,
                data        : [ { label : 'Yes', value : 'true'  },
                                { label : 'No',  value : 'false' }],
                onchange    : function() {
                    self.app.trigger( 'change' );
                }
            });
        },

        /** Color picker field
        */
        _fieldColor: function( input_def ) {
            var self = this;
            return new ColorPicker({
                id          : 'field-' + input_def.id,
                onchange    : function() {
                    self.app.trigger( 'change' );
                }
            });
        },

        /** Library dataset field
        */
        _fieldLibrary: function( input_def ) {
            var self = this;
            return new SelectLibrary.View({
                id          : 'field-' + input_def.id,
                optional    : input_def.optional,
                multiple    : input_def.multiple,
                onchange    : function() {
                    self.app.trigger( 'change' );
                }
            });
        },

        /** FTP file field
        */
        _fieldFtp: function( input_def ) {
            var self = this;
            return new SelectFtp.View({
                id          : 'field-' + input_def.id,
                optional    : input_def.optional,
                multiple    : input_def.multiple,
                onchange    : function() {
                    self.app.trigger( 'change' );
                }
            });
        }
    });

    return {
        View: View
    };
});
