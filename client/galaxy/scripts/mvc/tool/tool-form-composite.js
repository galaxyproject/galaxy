/** This is the run workflow tool form view. */
define([ 'utils/utils', 'utils/deferred', 'mvc/ui/ui-misc', 'mvc/form/form-view', 'mvc/form/form-data', 'mvc/tool/tool-form-base', 'mvc/ui/ui-modal' ],
    function( Utils, Deferred, Ui, Form, FormData, ToolFormBase, Modal ) {
    var View = Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            this.modal = parent.Galaxy.modal || new Modal.View();
            this.model = options && options.model || new Backbone.Model( options );
            this.deferred = new Deferred();
            this.setElement( $( '<div/>' ).addClass( 'ui-form-composite' )
                                          .append( this.$message      = $( '<div/>' ) )
                                          .append( this.$header       = $( '<div/>' ) )
                                          .append( this.$steps        = $( '<div/>' ) ) );
            $( 'body' ).append( this.$el );
            this._configure();
            this.render();
            this._refresh();
            this.$el.on( 'click', function() { self._refresh() } );
            $( window ).resize( function() { self._refresh() } );
        },

        /** Refresh height of scrollable div below header */
        _refresh: function() {
            var margin = _.reduce( this.$el.children(), function( memo, child ) {
                return memo + $( child ).outerHeight();
            }, 0 ) - this.$steps.height() + 25;
            this.$steps.css( 'height', $( window ).height() - margin );
        },

        /** Configures form/step options for each workflow step */
        _configure: function() {
            var self = this;
            this.forms = [];
            this.steps = [];
            this.links = [];
            this.parms = [];
            _.each( this.model.get( 'steps' ), function( step, i ) {
                Galaxy.emit.debug( 'tool-form-composite::initialize()', i + ' : Preparing workflow step.' );
                step = Utils.merge( {
                    index                   : i,
                    name                    : 'Step ' + ( parseInt( i ) + 1 ) + ': ' + step.name,
                    icon                    : '',
                    help                    : null,
                    description             : step.annotation && ' - ' + step.annotation || step.description,
                    citations               : null,
                    collapsible             : true,
                    collapsed               : i > 0 && !self._isDataStep( step ),
                    sustain_version         : true,
                    sustain_repeats         : true,
                    sustain_conditionals    : true,
                    narrow                  : true,
                    text_enable             : 'Edit',
                    text_disable            : 'Undo',
                    cls_enable              : 'fa fa-edit',
                    cls_disable             : 'fa fa-undo',
                    errors                  : step.messages,
                    initial_errors          : true,
                    cls                     : 'ui-portlet-narrow',
                    hide_operations         : true,
                    needs_refresh           : false,
                    always_refresh          : step.step_type != 'tool'
                }, step );
                self.steps[ i ] = step;
                self.links[ i ] = [];
                self.parms[ i ] = {};
            });

            // build linear index of step input pairs
            _.each( this.steps, function( step, i ) {
                FormData.visitInputs( step.inputs, function( input, name ) {
                    self.parms[ i ][ name ] = input;
                });
            });

            // iterate through data input modules and collect linked sub steps
            _.each( this.steps, function( step, i ) {
                _.each( step.output_connections, function( output_connection ) {
                    _.each( self.steps, function( sub_step, j ) {
                        sub_step.step_id === output_connection.input_step_id && self.links[ i ].push( sub_step );
                    });
                });
            });

            // convert all connected data inputs to hidden fields with proper labels,
            // and track the linked source step
            _.each( this.steps, function( step, i ) {
                _.each( self.steps, function( sub_step, j ) {
                    var connections_by_name = {};
                    _.each( step.output_connections, function( connection ) {
                        sub_step.step_id === connection.input_step_id && ( connections_by_name[ connection.input_name ] = connection );
                    });
                    _.each( self.parms[ j ], function( input, name ) {
                        var connection = connections_by_name[ name ];
                        if ( connection ) {
                            input.type = 'hidden';
                            input.help = input.step_linked ? input.help + ', ' : '';
                            input.help += 'Output dataset \'' + connection.output_name + '\' from step ' + ( parseInt( i ) + 1 );
                            input.step_linked = input.step_linked || [];
                            input.step_linked.push( step );
                        }
                    });
                });
            });

            // identify and configure workflow parameters
            var wp_count = 0;
            this.wp_inputs = {};
            function _handleWorkflowParameter( value, callback ) {
                var wp_name = self._isWorkflowParameter( value );
                wp_name && callback( self.wp_inputs[ wp_name ] = self.wp_inputs[ wp_name ] || {
                    label   : wp_name,
                    name    : wp_name,
                    type    : 'text',
                    color   : 'hsl( ' + ( ++wp_count * 100 ) + ', 70%, 30% )',
                    style   : 'ui-form-wp-source',
                    links   : []
                });
            }
            _.each( this.steps, function( step, i ) {
                _.each( self.parms[ i ], function( input, name ) {
                    _handleWorkflowParameter( input.value, function( wp_input ) {
                        wp_input.links.push( step );
                        input.wp_linked = wp_input.name;
                        input.color     = wp_input.color;
                        input.type      = 'text';
                        input.value     = null;
                        input.backdrop  = true;
                        input.style     = 'ui-form-wp-target';
                    });
                });
                _.each( step.post_job_actions, function( pja ) {
                    _.each( pja.action_arguments, function( arg ) {
                        _handleWorkflowParameter( arg, function() {} );
                    });
                });
            });

            // select fields are shown for dynamic fields if all putative data inputs are available,
            // or if an explicit reference is specified as data_ref and available
            _.each( this.steps, function( step, i ) {
                if ( step.step_type == 'tool' ) {
                    var data_resolved = true;
                    FormData.visitInputs( step.inputs, function ( input, name, context ) {
                        var is_data_input = ([ 'data', 'data_collection' ]).indexOf( input.type ) != -1;
                        var data_ref = context[ input.data_ref ];
                        input.step_linked && !self._isDataStep( input.step_linked ) && ( data_resolved = false );
                        input.options && ( ( input.options.length == 0 && !data_resolved ) || input.wp_linked ) && ( input.is_workflow = true );
                        data_ref && ( input.is_workflow = ( data_ref.step_linked && !self._isDataStep( data_ref.step_linked ) ) || input.wp_linked );
                        ( is_data_input || ( input.value && input.value.__class__ == 'RuntimeValue' && !input.step_linked ) ) && ( step.collapsed = false );
                        input.value && input.value.__class__ == 'RuntimeValue' && ( input.value = null );
                        input.flavor = 'workflow';
                        if ( !is_data_input && input.type !== 'hidden' && !input.wp_linked ) {
                            if ( input.optional || ( !Utils.isEmpty( input.value ) && input.value !== '' ) ) {
                                input.collapsible_value = input.value;
                                input.collapsible_preview = true;
                            }
                        }
                    });
                }
            });
        },

        render: function() {
            var self = this;
            this.deferred.reset();
            this._renderHeader();
            this._renderMessage();
            this._renderParameters();
            this._renderHistory();
            _.each ( this.steps, function( step, i ) { self._renderStep( step, i ) } );
            this.deferred.execute( function() { self.execute_btn.unwait();
                                                self.execute_btn.model.set( { wait_text: 'Sending...', percentage: -1 } ); } );
        },

        /** Render header */
        _renderHeader: function() {
            var self = this;
            this.execute_btn = new Ui.Button({
                icon        : 'fa-check',
                title       : 'Run workflow',
                cls         : 'btn btn-primary',
                wait        : true,
                wait_text   : 'Preparing...',
                onclick     : function() { self._execute() }
            });
            this.$header.addClass( 'ui-form-header' ).empty()
                        .append( new Ui.Label( { title: 'Workflow: ' + this.model.get( 'name' ) } ).$el )
                        .append( this.execute_btn.$el );
        },

        /** Render message */
        _renderMessage: function() {
            this.$message.empty();
            if ( this.model.get( 'has_upgrade_messages' ) ) {
                this.$message.append( new Ui.Message( {
                    message     : 'Some tools in this workflow may have changed since it was last saved or some errors were found. The workflow may still run, but any new options will have default values. Please review the messages below to make a decision about whether the changes will affect your analysis.',
                    status      : 'warning',
                    persistent  : true,
                    fade        : false
                } ).$el );
            }
        },

        /** Render workflow parameters */
        _renderParameters: function() {
            var self = this;
            this.wp_form = null;
            if ( !_.isEmpty( this.wp_inputs ) ) {
                this.wp_form = new Form({ title: '<b>Workflow Parameters</b>', inputs: this.wp_inputs, cls: 'ui-portlet-narrow', onchange: function() {
                        _.each( self.wp_form.input_list, function( input_def, i ) {
                            _.each( input_def.links, function( step ) { self._refreshStep( step ) } );
                        });
                    }
                });
                this._append( this.$steps.empty(), this.wp_form.$el );
            }
        },

        /** Render workflow parameters */
        _renderHistory: function() {
            this.history_form = null;
            if ( !this.model.get( 'history_id' ) ) {
                this.history_form = new Form({
                    cls    : 'ui-portlet-narrow',
                    title  : '<b>History Options</b>',
                    inputs : [{
                        type        : 'conditional',
                        name        : 'new_history',
                        test_param  : {
                            name        : 'check',
                            label       : 'Send results to a new history',
                            type        : 'boolean',
                            value       : 'false',
                            help        : ''
                        },
                        cases       : [{
                            value   : 'true',
                            inputs  : [{
                                name    : 'name',
                                label   : 'History name',
                                type    : 'text',
                                value   : this.model.get( 'name' )
                            }]
                        }]
                    }]
                });
                this._append( this.$steps, this.history_form.$el );
            }
        },

        /** Render step */
        _renderStep: function( step, i ) {
            var self = this;
            var form = null;
            var current = null;
            self.$steps.addClass( 'ui-steps' );
            this.deferred.execute( function( promise ) {
                current = promise;
                if ( step.step_type == 'tool' ) {
                    form = new ToolFormBase( step );
                    if ( step.post_job_actions && step.post_job_actions.length ) {
                        form.portlet.append( $( '<div/>' ).addClass( 'ui-form-element-disabled' )
                            .append( $( '<div/>' ).addClass( 'ui-form-title' ).html( 'Job Post Actions' ) )
                            .append( $( '<div/>' ).addClass( 'ui-form-preview' ).html(
                                _.reduce( step.post_job_actions, function( memo, value ) {
                                    return memo + ' ' + value.short_str;
                                }, '' ) ) )
                            );
                    }
                } else {
                    _.each( step.inputs, function( input ) { input.flavor = 'module' } );
                    form = new Form( Utils.merge({
                        title    : '<b>' + step.name + '</b>',
                        onchange : function() { _.each( self.links[ i ], function( link ) { self._refreshStep( link ) } ) }
                    }, step ) );
                }
                self.forms[ i ] = form;
                self._append( self.$steps, form.$el );
                step.needs_refresh && self._refreshStep( step );
                self._resolve( form.deferred, promise );
                self.execute_btn.model.set( 'percentage', ( i + 1 ) * 100.0 / self.steps.length );
                Galaxy.emit.debug( 'tool-form-composite::initialize()', i + ' : Workflow step state ready.', step );
            } );
        },

        /** This helps with rendering lazy loaded steps */
        _resolve: function( deferred, promise ) {
            var self = this;
            setTimeout( function() {
                if ( deferred && deferred.ready() || !deferred ) {
                    promise.resolve();
                } else {
                    self._resolve( deferred, promise );
                }
            }, 0 );
        },

        /** Refreshes step values from source step values */
        _refreshStep: function( step ) {
            var self = this;
            var form = this.forms[ step.index ];
            if ( form ) {
                _.each( self.parms[ step.index ], function( input, name ) {
                    if ( input.step_linked || input.wp_linked ) {
                        var field = form.field_list[ form.data.match( name ) ];
                        if ( field ) {
                            var new_value = undefined;
                            if ( input.step_linked ) {
                                new_value = { values: [] };
                                _.each( input.step_linked, function( source_step ) {
                                    if ( self._isDataStep( source_step ) ) {
                                        value = self.forms[ source_step.index ].data.create().input;
                                        value && _.each( value.values, function( v ) { new_value.values.push( v ) } );
                                    }
                                });
                                if ( !input.multiple && new_value.values.length > 0 ) {
                                    new_value = { values: [ new_value.values[ 0 ] ] };
                                }
                            } else if ( input.wp_linked ) {
                                var wp_field = self.wp_form.field_list[ self.wp_form.data.match( input.wp_linked ) ];
                                wp_field && ( new_value = wp_field.value() );
                            }
                            if ( new_value !== undefined ) {
                                field.value( new_value );
                            }
                        }
                    }
                });
                form.trigger( 'change' );
            } else {
                step.needs_refresh = true;
            }
        },

        /** Execute workflow */
        _execute: function() {
            var self = this;
            this._enabled( false );
            var job_def = {
                new_history_name    : this.history_form.data.create()[ 'new_history|name' ],
                replacement_params  : this.wp_form ? this.wp_form.data.create() : {},
                inputs              : {}
            };
            var validated = true;
            for ( var i in this.forms ) {
                var form = this.forms[ i ];
                var job_inputs  = form.data.create();
                var step        = self.steps[ i ];
                var step_id     = step.step_id;
                form.trigger( 'reset' );
                for ( var job_input_id in job_inputs ) {
                    var input_value = job_inputs[ job_input_id ];
                    var input_id    = form.data.match( job_input_id );
                    var input_field = form.field_list[ input_id ];
                    var input_def   = form.input_list[ input_id ];
                    if ( !input_def.step_linked ) {
                        if ( this._isDataStep( step ) ) {
                            validated = input_value && input_value.values && input_value.values.length > 0;
                        } else {
                            validated = input_def.optional || ( input_def.is_workflow && input_value !== '' ) || ( !input_def.is_workflow && input_value !== null );
                        }
                        if ( !validated ) {
                            form.highlight( input_id );
                            break;
                        }
                        job_def.inputs[ step_id ] = job_def.inputs[ step_id ] || {};
                        job_def.inputs[ step_id ][ job_input_id ] = job_inputs[ job_input_id ];
                    }
                }
                if ( !validated ) {
                    break;
                }
            }
            if ( !validated ) {
                self._enabled( true );
                Galaxy.emit.debug( 'tool-form-composite::submit()', 'Validation failed.', job_def );
            } else {
                Galaxy.emit.debug( 'tool-form-composite::submit()', 'Validation complete.', job_def );
                Utils.request({
                    type    : 'POST',
                    url     : Galaxy.root + 'api_internal/workflows/' + this.model.id + '/run',
                    data    : job_def,
                    success : function( response ) {
                        Galaxy.emit.debug( 'tool-form-composite::submit', 'Submission successful.', response );
                        self.$el.empty().append( self._templateSuccess( response ) );
                        parent.Galaxy && parent.Galaxy.currHistoryPanel && parent.Galaxy.currHistoryPanel.refreshContents();
                    },
                    error   : function( response ) {
                        Galaxy.emit.debug( 'tool-form-composite::submit', 'Submission failed.', response );
                        if ( response && response.err_data ) {
                            for ( var i in self.forms ) {
                                var form = self.forms[ i ];
                                var step_related_errors = response.err_data[ form.options.step_id ];
                                if ( step_related_errors ) {
                                    var error_messages = form.data.matchResponse( step_related_errors );
                                    for ( var input_id in error_messages ) {
                                        form.highlight( input_id, error_messages[ input_id ] );
                                        break;
                                    }
                                }
                            }
                        } else {
                            self.modal.show({
                                title   : 'Job submission failed',
                                body    : self._templateError( response && response.err_msg || job_def ),
                                buttons : {
                                    'Close' : function() {
                                        self.modal.hide();
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

        /** Append new dom to body */
        _append: function( $container, $el ) {
            $container.append( '<p/>' ).addClass( 'ui-margin-top' ).append( $el );
        },

        /** Set enabled/disabled state */
        _enabled: function( enabled ) {
            if ( enabled ) { this.execute_btn.unwait() } else { this.execute_btn.wait() }
            if ( enabled ) { this.history_form.portlet.enable() } else { this.history_form.portlet.disable() }
            _.each( this.forms, function( form ) { if ( enabled ) {  form.portlet.enable() } else { form.portlet.disable() } });
        },

        /** Handle workflow parameter */
        _isWorkflowParameter: function( value ) {
            if ( String( value ).substring( 0, 1 ) === '$' ) {
                return Utils.sanitize( value.substring( 2,  value.length - 1 ) )
            }
        },

        /** Is data input module/step */
        _isDataStep: function( steps ) {
            lst = $.isArray( steps ) ? steps : [ steps ] ;
            for ( var i = 0; i < lst.length; i++ ) {
                var step = lst[ i ];
                if ( !step || !step.step_type || !step.step_type.startsWith( 'data' ) ) {
                    return false;
                }
            }
            return true;
        },

        /** Templates */
        _templateSuccess: function( response ) {
            if ( response && response.length > 0 ) {
                var $message = $( '<div/>' ).addClass( 'donemessagelarge' )
                                .append( $( '<p/>' ).text( 'Successfully ran workflow \'' + this.model.get( 'name' ) + '\' and datasets will appear as jobs are created - you may need to refresh your history panel to see these.' ) );
                for ( var i in response ) {
                    var invocation = response[ i ];
                    var $invocation = $( '<div/>' ).addClass( 'workflow-invocation-complete' );
                    invocation.history && $invocation.append( $( '<p/>' ).text( 'These datasets will appear in a new history: ' )
                                                     .append( $( '<a/>' ).addClass( 'new-history-link' )
                                                                         .attr( 'data-history-id', invocation.history.id )
                                                                         .attr( 'target', '_top' )
                                                                         .attr( 'href', '/history/switch_to_history?hist_id=' + invocation.history.id )
                                                                         .text( invocation.history.name ) ) );
                    _.each( invocation.outputs, function( output ) {
                        $invocation.append( $( '<div/>' ).addClass( 'messagerow' ).html( '<b>' + output.hid + '</b>: ' + output.name ) );
                    });
                    $message.append( $invocation );
                }
                return $message;
            } else {
                return this._templateError( response );
            }
        },

        _templateError: function( response ) {
            return  $( '<div/>' ).addClass( 'errormessagelarge' )
                .append( $( '<p/>' ).text( 'The server could not complete the request. Please contact the Galaxy Team if this error persists.' ) )
                .append( $( '<pre/>' ).text( JSON.stringify( response, null, 4 ) ) );
        }
    });
    return {
        View: View
    };
});
