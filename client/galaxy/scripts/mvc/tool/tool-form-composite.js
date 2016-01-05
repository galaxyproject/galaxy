/**
    This is the run workflow tool form.
*/
define([ 'utils/utils', 'mvc/ui/ui-misc', 'mvc/form/form-view', 'mvc/form/form-data', 'mvc/tool/tool-form-base' ],
    function( Utils, Ui, Form, FormData, ToolFormBase ) {
    var View = Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            this.workflow_id = options.id;
            this.forms = [];
            this.steps = [];
            this.links = [];

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

            // initialize steps and configure connections
            _.each( options.steps, function( step, i ) {
                Galaxy.emit.debug( 'tool-form-composite::initialize()', i + ' : Preparing workflow step.' );
                step = Utils.merge( {
                    name                    : 'Step ' + ( parseInt( i ) + 1 ) + ': ' + step.name,
                    icon                    : '',
                    help                    : null,
                    description             : step.annotation && ' - ' + step.annotation || step.description,
                    citations               : null,
                    needs_update            : true,
                    collapsible             : true,
                    collapsed               : i > 0,
                    sustain_version         : true,
                    sustain_repeats         : true,
                    sustain_conditionals    : true,
                    narrow                  : true,
                    text_enable             : 'Edit',
                    text_disable            : 'Undo',
                    cls_enable              : 'fa fa-edit',
                    cls_disable             : 'fa fa-undo'
                }, step );
                // convert all connected data inputs to hidden fields with proper labels
                _.each( options.steps, function( sub_step ) {
                    var connections_by_name = {};
                    _.each( step.output_connections, function( connection ) {
                        sub_step.step_id === connection.input_step_id && ( connections_by_name[ connection.input_name ] = connection );
                    });
                    FormData.matchIds( sub_step.inputs, connections_by_name, function( connection, input ) {
                        if ( !input.linked ) {
                            input.linked = step.step_type;
                            input.type = 'hidden';
                            input.help = '';
                        } else {
                            input.help += ', ';
                        }
                        input.help += 'Output dataset \'' + connection.output_name + '\' from step ' + ( parseInt( i ) + 1 );
                    });
                });
                self.steps[ i ] = step;
                self.links[ i ] = [];
            });

            // finalize configuration and build forms
            _.each( self.steps, function( step, i ) {
                var form = null;
                if ( String( step.step_type ).startsWith( 'data' ) ) {
                    form = new Form( Utils.merge({
                        title : '<b>' + step.name + '</b>',
                        onchange: function() {
                            var input_value = form.data.create().input;
                            _.each( self.links[ i ], function( link ) {
                                link.input.value ( input_value );
                                link.form.trigger( 'change' );
                            });
                        }
                    }, step ));
                } else if ( step.step_type == 'tool' ) {
                    // select fields are shown for dynamic fields if all putative data inputs are available
                    function visitInputs( inputs, data_resolved ) {
                        data_resolved === undefined && ( data_resolved = true );
                        _.each( inputs, function ( input ) {
                            if ( _.isObject( input ) ) {
                                if ( input.type ) {
                                    var is_data_input = [ 'data', 'data_collection' ].indexOf( input.type ) !== -1;
                                    var is_workflow_parameter = self._isWorkflowParameter( input.value );
                                    is_data_input && input.linked && !input.linked.startsWith( 'data' ) && ( data_resolved = false );
                                    input.options && ( ( input.options.length == 0 && !data_resolved ) || is_workflow_parameter ) && ( input.is_workflow = true );
                                    input.value && input.value.__class__ == 'RuntimeValue' && ( input.value = null );
                                    if ( !is_data_input && input.type !== 'hidden' && !is_workflow_parameter ) {
                                        if ( input.optional || ( Utils.validate( input.value ) && input.value !== '' ) ) {
                                            input.collapsible_value = input.value;
                                            input.collapsible_preview = true;
                                        }
                                    }
                                }
                                visitInputs( input, data_resolved );
                            }
                        });
                    };
                    visitInputs( step.inputs );
                    // or if a particular reference is specified and available
                    FormData.matchContext( step.inputs, 'data_ref', function( input, reference ) {
                        input.is_workflow = ( reference.linked && !reference.linked.startsWith( 'data' ) ) || self._isWorkflowParameter( input.value );
                    });
                    form = new ToolFormBase( step );
                }
                self.forms[ i ] = form;
            });

            // create index of data output links
            _.each( this.steps, function( step, i ) {
                _.each( step.output_connections, function( output_connection ) {
                    _.each( self.forms, function( form ) {
                        if ( form.options.step_id === output_connection.input_step_id ) {
                            var matched_input = form.field_list[ form.data.match( output_connection.input_name ) ];
                            matched_input && self.links[ i ].push( { input: matched_input, form: form } );
                        }
                    });
                });
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
            _.each( this.steps, function( step, i ) {
                var form = self.forms[ i ];
                self.$el.append( '<p/>' ).addClass( 'ui-margin-top' ).append( form.$el );
                if ( step.post_job_actions && step.post_job_actions.length ) {
                    form.portlet.append( $( '<div/>' ).addClass( 'ui-form-footer-info fa fa-bolt' ).append(
                        _.reduce( step.post_job_actions, function( memo, value ) {
                            return memo + ' ' + value.short_str;
                        }, '' ))
                    );
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
            _.each( this.forms, function( form, i ) {
                var job_inputs  = form.data.create();
                var step        = self.steps[ i ];
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
                    if ( String( step_type ).startsWith( 'data' ) ) {
                        if ( input_value && input_value.values && input_value.values.length > 0 ) {
                            job_def.inputs[ order_index ] = input_value.values[ 0 ];
                        } else if ( validated ) {
                            form.highlight( input_id );
                            validated = false;
                        }
                    } else {
                        if ( !String( input_def.type ).startsWith( 'data' ) ) {
                            if ( input_def.optional || input_def.is_workflow || input_value != null ) {
                                job_def.parameters[ step_id ][ job_input_id ] = input_value;
                            } else {
                                form.highlight( input_id );
                                validated = false;
                            }
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
