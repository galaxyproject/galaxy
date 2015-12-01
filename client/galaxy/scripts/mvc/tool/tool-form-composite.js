/**
    This is the run workflow tool form.
*/
define([ 'utils/utils', 'mvc/ui/ui-misc', 'mvc/form/form-view', 'mvc/form/form-data', 'mvc/tool/tool-form-base' ],
    function( Utils, Ui, Form, FormData, ToolFormBase ) {
    var View = Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            this.workflow_id = options.id;
            this.forms = {};
            this.steps = {};

            // initialize elements
            this.setElement( '<div class="ui-form-composite"/>' );
            this.$header = $( '<div/>' ).addClass( 'ui-form-header' );
            this.$header.append( new Ui.Label({
                title    : 'Workflow: ' + options.name
            }).$el );
            this.$header.append( new Ui.Button({
                title    : 'Collapse',
                icon     : 'fa-angle-double-up',
                onclick  : function() { _.each( self.forms, function( form ) { form.portlet.collapse() }) }
            }).$el );
            this.$header.append( new Ui.Button({
                title    : 'Expand all',
                icon     : 'fa-angle-double-down',
                onclick  : function() { _.each( self.forms, function( form ) { form.portlet.expand() }) }
            }).$el );
            this.$el.append( this.$header );

            // configure steps and build form views
            _.each( options.steps, function( step, i ) {
                Galaxy.emit.debug( 'tool-form-composite::initialize()', i + ' : Preparing workflow step.' );
                step = Utils.merge( {
                    name                    : 'Step ' + ( parseInt( i ) + 1 ) + ': ' + step.name,
                    icon                    : '',
                    help                    : null,
                    description             : step.annotation && ' - ' + step.annotation || step.description,
                    citations               : null,
                    collapsible             : true,
                    collapsed               : i > 0,
                    sustain_version         : true,
                    sustain_repeats         : true,
                    sustain_conditionals    : true,
                    narrow                  : true,
                    text_enable             : 'Edit',
                    text_disable            : 'Undo',
                    cls_enable              : 'fa fa-edit',
                    cls_disable             : 'fa fa-undo',
                }, step );

                // build forms
                var form = null;
                if ( (['data_input', 'data_collection_input']).indexOf( step.step_type ) != -1 ) {
                    form = new Form( Utils.merge({
                        title : '<b>' + step.name + '</b>'
                    }, step ));
                } else if ( step.step_type == 'tool' ) {
                    // configure input elements
                    Utils.deepeach( step.inputs, function( input ) {
                        if ( input.type ) {
                            input.options && input.options.length == 0 && ( input.is_workflow = true );
                            if ( input.value && input.value.__class__ == 'RuntimeValue' ) {
                                input.value = null;
                            } else if ( [ 'data', 'data_collection' ].indexOf( input.type ) == -1 && !self._isWorkflowParameter( input.value ) ) {
                                input.collapsible_value = input.value;
                                input.collapsible_preview = true;
                            }
                        }
                    });
                    // replace referenced dataset input fields with labels
                    FormData.matchIds( step.inputs, step.input_connections_by_name, function( connection, input ) {
                        if( input ) {
                            input.type = 'hidden';
                            input.value = input.ignore = '';
                            input.options = null;
                            input.help = _.reduce( connection, function( memo, value ) {
                                memo && ( memo = memo + ', ' );
                                return memo + 'Output dataset \'' + value.output_name + '\' from step ' + value.order_index;
                            }, '' );
                        }
                    });
                    // match data references
                    FormData.matchContext( step.inputs, 'data_ref', function( input, reference ) {
                        input.is_workflow = !reference.options || self._isWorkflowParameter( input.value );
                    });
                    form = new ToolFormBase( step ).form;
                }

                // backup objects
                self.forms[ step.step_id ] = form;
                self.steps[ step.step_id ] = step;
            });

            // build workflow parameters
            var wp_fields = {};
            var wp_inputs = {};
            var wp_count = 0;
            var wp_style = function( wp_field, wp_color, wp_cls ) {
                var $wp_input = wp_field.$( 'input' );
                $wp_input.length === 0 && ( $wp_input = wp_field.$el );
                $wp_input.addClass( wp_cls ).css({ 'color': wp_color, 'border-color': wp_color });
            }
            _.each( this.steps, function( step, i ) {
                _.each( step.inputs, function( input ) {
                    var wp_name = self._isWorkflowParameter( input.value );
                    if ( wp_name ) {
                        var wp_field = self.forms[ i ].field_list[ input.id ];
                        var wp_element = self.forms[ i ].element_list[ input.id ];
                        wp_fields[ wp_name ] = wp_fields[ wp_name ] || [];
                        wp_fields[ wp_name ].push( wp_field );
                        wp_field.value( wp_name );
                        wp_element.disable( true );
                        wp_inputs[ wp_name ] = wp_inputs[ wp_name ] || {
                            type        : input.type,
                            is_workflow : input.options,
                            label       : wp_name,
                            name        : wp_name,
                            color       : 'hsl( ' + ( ++wp_count * 100 ) + ', 70%, 30% )'
                        };
                        wp_style( wp_field, wp_inputs[ wp_name ].color, 'ui-form-wp-target' );
                    }
                });
            });
            if ( !_.isEmpty( wp_inputs ) ) {
                var wp_form = new Form({ title: '<b>Workflow Parameters</b>', inputs: wp_inputs, onchange: function() {
                    _.each( wp_form.data.create(), function( wp_value, wp_name ) {
                        _.each( wp_fields[ wp_name ], function( wp_field ) {
                            wp_field.value( Utils.sanitize( wp_value ) || wp_name );
                        });
                    });
                }});
                _.each( wp_form.field_list, function( wp_field, i ) {
                    wp_style( wp_field, wp_form.input_list[ i ].color, 'ui-form-wp-source' );
                });
                this.$el.append( '<p/>' ).addClass( 'ui-margin-top' );
                this.$el.append( wp_form.$el );
            }

            // append elements
            _.each( self.steps, function( step, i ) {
                self.$el.append( '<p/>' ).addClass( 'ui-margin-top' );
                self.$el.append( self.forms[ i ].$el );
                if ( step.post_job_actions && step.post_job_actions.length ) {
                    self.$el.append( $( '<div/>' ).addClass( 'fa fa-bolt' ) )
                            .append( _.reduce( step.post_job_actions, function( memo, value ) {
                                return memo + ' ' + value.short_str;
                            }, '' ) );
                }
                Galaxy.emit.debug( 'tool-form-composite::initialize()', i + ' : Workflow step state ready.', step );
            });

            // add history form
            this.history_form = null;
            if ( !options.history_id ) {
                this.history_form = new Form({
                    inputs : [{
                        type        : 'conditional',
                        test_param  : {
                            name        : 'new_history',
                            label       : 'Send results to a new history',
                            type        : 'boolean',
                            value       : 'false',
                            help        : ''
                        },
                        cases       : [{
                            value   : 'true',
                            inputs  : [{
                                name    : 'new_history_name',
                                label   : 'History name',
                                type    : 'text',
                                value   : options.name
                            }]
                        }]
                    }]
                });
                this.$el.append( '<p/>' ).addClass( 'ui-margin-top' );
                this.$el.append( this.history_form.$el );
            }

            // add execute button
            this.$el.append( '<p/>' ).addClass( 'ui-margin-top' );
            this.execute_btn = new Ui.Button({
                icon     : 'fa-check',
                title    : 'Run workflow',
                cls      : 'btn btn-primary',
                floating : 'clear',
                onclick  : function() { self._execute() }
            });
            this.$el.append( this.execute_btn.$el );
            $( 'body' ).append( this.$el );
        },

        /** Execute workflow
        */
        _execute: function() {
            var self = this;
            var job_def = {
                inputs      : {},
                parameters  : {}
            };
            var validated = true;
            _.each( this.forms, function( form, key ) {
                var job_inputs  = form.data.create();
                var step        = self.steps[ key ];
                var step_id     = step.step_id;
                var step_type   = step.step_type;
                var order_index = step.order_index;
                job_def.parameters[ step_id ] = {};
                form.trigger( 'reset' );
                for ( var job_input_id in job_inputs ) {
                    var input_value = job_inputs[ job_input_id ];
                    var input_id    = form.data.match( job_input_id );
                    var input_field = form.field_list[ input_id ];
                    var input_def   = form.input_list[ input_id ];
                    if ( ( [ 'data_input', 'data_collection_input' ] ).indexOf( step_type ) != -1 ) {
                        if ( input_value && input_value.values && input_value.values.length > 0 ) {
                            job_def.inputs[ order_index ] = input_value.values[ 0 ];
                        } else if ( validated ) {
                            form.highlight( input_id );
                            validated = false;
                        }
                    } else {
                        if ( input_def.optional || input_def.is_workflow || input_value != null ) {
                            job_def.parameters[ step_id ][ job_input_id ] = input_value;
                        } else {
                            form.highlight( input_id );
                            validated = false;
                        }
                    }
                }
            });
            console.log( JSON.stringify( job_def ) );
            if ( !validated ) {
                self._enabled( true );
            } else {
                self._enabled( false );
                Galaxy.emit.debug( 'tools-form-composite::submit()', 'Validation complete.', job_def );
                Utils.request({
                    type    : 'POST',
                    url     : Galaxy.root + 'api/workflows/' + this.workflow_id + '/invocations',
                    data    : job_def,
                    success : function( response ) {
                        Galaxy.emit.debug( 'tool-form-composite::submit', 'Submission successful.', response );
                        parent.Galaxy && parent.Galaxy.currHistoryPanel && parent.Galaxy.currHistoryPanel.refreshContents();
                        console.log( response );
                    },
                    error   : function( response ) {
                        console.log( response );
                        if ( response && response.err_data ) {
                            var error_messages = form.data.matchResponse( response.err_data );
                            for ( var input_id in error_messages ) {
                                form.highlight( input_id, error_messages[ input_id ] );
                                break;
                            }
                        } else {
                            Galaxy.modal && Galaxy.modal.show({
                                title   : 'Job submission failed',
                                body    : ( response && response.err_msg ) || ToolTemplate.error( options.job_def ),
                                buttons : {
                                    'Close' : function() {
                                        Galaxy.modal.hide();
                                    }
                                }
                            });
                        }
                    },
                    complete: function() {
                        self._enabled( true );
                    }
                });
            }
        },

        /** Set enabled/disabled state
        */
        _enabled: function( enabled ) {
            if ( enabled ) { this.execute_btn.unwait() } else { this.execute_btn.wait() }
            if ( enabled ) { this.history_form.portlet.enable() } else { this.history_form.portlet.disable() }
            _.each( this.forms, function( form ) { if ( enabled ) {  form.portlet.enable() } else { form.portlet.disable() } });
        },

        /** Handle workflow parameter
        */
        _isWorkflowParameter: function( value ) {
            if ( String( value ).substring( 0, 1 ) === '$' ) {
                return Utils.sanitize( value.substring( 2,  value.length - 1 ) )
            }
        }
    });
    return {
        View: View
    };
});