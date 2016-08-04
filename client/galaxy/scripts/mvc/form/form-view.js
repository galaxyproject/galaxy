/**
    This is the main class of the form plugin. It is referenced as 'app' in all lower level modules.
*/
define(['utils/utils', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc', 'mvc/form/form-section', 'mvc/form/form-data'],
    function(Utils, Portlet, Ui, FormSection, FormData) {
    return Backbone.View.extend({
        initialize: function(options) {
            this.options = Utils.merge(options, {
                initial_errors  : false,
                cls             : 'ui-portlet-limited',
                icon            : null,
                always_refresh  : true
            });
            this.setElement('<div/>');
            this.render();
        },

        /** Update available options */
        update: function(new_model){
            var self = this;
            this.data.matchModel(new_model, function(node, input_id) {
                var input = self.input_list[input_id];
                if (input && input.options) {
                    if (!_.isEqual(input.options, node.options)) {
                        // backup new options
                        input.options = node.options;

                        // get/update field
                        var field = self.field_list[input_id];
                        if (field.update) {
                            var new_options = [];
                            if ((['data', 'data_collection', 'drill_down']).indexOf(input.type) != -1) {
                                new_options = input.options;
                            } else {
                                for (var i in node.options) {
                                    var opt = node.options[i];
                                    if (opt.length > 2) {
                                        new_options.push({
                                            'label': opt[0],
                                            'value': opt[1]
                                        });
                                    }
                                }
                            }
                            field.update(new_options);
                            field.trigger('change');
                            Galaxy.emit.debug('form-view::update()', 'Updating options for ' + input_id);
                        }
                    }
                }
            });
        },

        /** Set form into wait mode */
        wait: function(active) {
            for (var i in this.input_list) {
                var field = this.field_list[i];
                var input = this.input_list[i];
                if (input.is_dynamic && field.wait && field.unwait) {
                    if (active) {
                        field.wait();
                    } else {
                        field.unwait();
                    }
                }
            }
        },

        /** Highlight and scroll to input element (currently only used for error notifications)
        */
        highlight: function (input_id, message, silent) {
            var input_element = this.element_list[input_id];
            if (input_element) {
                input_element.error(message || 'Please verify this parameter.');
                this.portlet.expand();
                this.trigger('expand', input_id);
                if (!silent) {
                    var $panel = this.$el.parents().filter(function() {
                        return [ 'auto', 'scroll' ].indexOf( $( this ).css( 'overflow' ) ) != -1;
                    }).first();
                    $panel.animate( { scrollTop : $panel.scrollTop() + input_element.$el.offset().top - 120 }, 500 );
                }
            }
        },

        /** Highlights errors */
        errors: function(options) {
            this.trigger('reset');
            if (options && options.errors) {
                var error_messages = this.data.matchResponse(options.errors);
                for (var input_id in this.element_list) {
                    var input = this.element_list[input_id];
                    if (error_messages[input_id]) {
                        this.highlight(input_id, error_messages[input_id], true);
                    }
                }
            }
        },

        /** Modify onchange event handler */
        setOnChange: function( callback ) {
            this.options.onchange = callback;
        },

        /** Render tool form */
        render: function() {
            // link this
            var self = this;

            // reset events
            this.off('change');
            this.off('reset');

            // reset field list, which contains the input field elements
            this.field_list = {};

            // reset sequential input definition list, which contains the input definitions as provided from the api
            this.input_list = {};

            // reset input element list, which contains the dom elements of each input element (includes also the input field)
            this.element_list = {};

            // creates a json data structure from the input form
            this.data = new FormData.Manager(this);

            // create ui elements
            this._renderForm();

            // refresh data
            this.data.create();

            // show errors on startup
            if (this.options.initial_errors) {
                this.errors(this.options);
            }

            // add listener which triggers on checksum change
            var current_check = this.data.checksum();
            this.on('change', function( input_id ) {
                var input = self.input_list[ input_id ];
                if ( !input || input.refresh_on_change || self.options.always_refresh ) {
                    var new_check = self.data.checksum();
                    if ( new_check != current_check ) {
                        current_check = new_check;
                        self.options.onchange && self.options.onchange();
                    }
                }
            });

            // add reset listener
            this.on('reset', function() {
                for (var i in this.element_list) {
                    this.element_list[i].reset();
                }
            });
            return this;
        },

        /** Renders the UI elements required for the form */
        _renderForm: function() {
            // create message view
            this.message = new Ui.Message();

            // create tool form section
            this.section = new FormSection.View(this, {
                inputs : this.options.inputs
            });

            // remove tooltips
            $( '.tooltip' ).remove();

            // create portlet
            this.portlet = new Portlet.View({
                icon        : this.options.icon,
                title       : this.options.title,
                cls         : this.options.cls,
                operations  : this.options.operations,
                buttons     : this.options.buttons,
                collapsible : this.options.collapsible,
                collapsed   : this.options.collapsed
            });

            // append message
            this.portlet.append(this.message.$el);

            // append tool section
            this.portlet.append(this.section.$el);

            // start form
            this.$el.empty();
            this.$el.append(this.portlet.$el);

            // show message if available in model
            if (this.options.message) {
                this.message.update({
                    persistent  : true,
                    status      : 'warning',
                    message     : this.options.message
                });
            }

            // log
            Galaxy.emit.debug('form-view::initialize()', 'Completed');
        }
    });
});