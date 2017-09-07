/* This is the regular tool form */
define([ 'utils/utils', 'mvc/ui/ui-misc', 'mvc/ui/ui-modal', 'mvc/tool/tool-form-base', 'mvc/webhooks' ],
    function( Utils, Ui, Modal, ToolFormBase, Webhooks ) {
    var View = Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            this.modal = parent.Galaxy.modal || new Modal.View();
            this.form = new ToolFormBase( Utils.merge({
                listen_to_history : true,
                always_refresh    : false,
                buildmodel: function( process, form ) {
                    var options = form.model.attributes;

                    // build request url
                    var build_url = '';
                    var build_data = {};
                    var job_id = options.job_id;
                    if ( job_id ) {
                        build_url = Galaxy.root + 'api/jobs/' + job_id + '/build_for_rerun';
                    } else {
                        build_url = Galaxy.root + 'api/tools/' + options.id + '/build';
                        build_data = $.extend( {}, Galaxy.params );
                        build_data[ 'tool_id' ] && ( delete build_data[ 'tool_id' ] );
                    }
                    options.version && ( build_data[ 'tool_version' ] = options.version );

                    // get initial model
                    Utils.get({
                        url     : build_url,
                        data    : build_data,
                        success : function( data ) {
                            if( !data.display ) {
                                window.location = Galaxy.root;
                                return;
                            }
                            form.model.set( data );
                            self._customize( form );
                            Galaxy.emit.debug('tool-form-base::_buildModel()', 'Initial tool model ready.', data);
                            process.resolve();
                        },
                        error   : function( response, status ) {
                            var error_message = ( response && response.err_msg ) || 'Uncaught error.';
                            if ( status == 401 ) {
                                window.location = Galaxy.root + 'user/login?' + $.param({ redirect : Galaxy.root + '?tool_id=' + options.id });
                            } else if ( form.$el.is( ':empty' ) ) {
                                form.$el.prepend( ( new Ui.Message({
                                    message     : error_message,
                                    status      : 'danger',
                                    persistent  : true,
                                    large       : true
                                }) ).$el );
                            } else {
                                Galaxy.modal && Galaxy.modal.show({
                                    title   : 'Tool request failed',
                                    body    : error_message,
                                    buttons : {
                                        'Close' : function() {
                                            Galaxy.modal.hide();
                                        }
                                    }
                                });
                            }
                            Galaxy.emit.debug( 'tool-form-base::_buildModel()', 'Initial tool model request failed.', response );
                            process.reject();
                        }
                    });
                },
                postchange          : function( process, form ) {
                    var current_state = {
                        tool_id         : form.model.get( 'id' ),
                        tool_version    : form.model.get( 'version' ),
                        inputs          : $.extend(true, {}, form.data.create())
                    }
                    form.wait( true );
                    Galaxy.emit.debug( 'tool-form::postchange()', 'Sending current state.', current_state );
                    Utils.request({
                        type    : 'POST',
                        url     : Galaxy.root + 'api/tools/' + form.model.get( 'id' ) + '/build',
                        data    : current_state,
                        success : function( data ) {
                            form.update( data );
                            form.wait( false );
                            Galaxy.emit.debug( 'tool-form::postchange()', 'Received new model.', data );
                            process.resolve();
                        },
                        error   : function( response ) {
                            Galaxy.emit.debug( 'tool-form::postchange()', 'Refresh request failed.', response );
                            process.reject();
                        }
                    });
                }
            }, options ) );
            this.deferred = this.form.deferred;
            this.setElement( '<div/>' );
            this.$el.append( this.form.$el );
        },

        _customize: function( form ) {
            var self = this;
            var options = form.model.attributes;
            // build execute button
            options.buttons = {
                execute: execute_btn = new Ui.Button({
                    icon     : 'fa-check',
                    tooltip  : 'Execute: ' + options.name + ' (' + options.version + ')',
                    title    : 'Execute',
                    cls      : 'btn btn-primary ui-clear-float',
                    wait_cls : 'btn btn-info ui-clear-float',
                    onclick  : function() {
                        execute_btn.wait();
                        form.portlet.disable();
                        self.submit( options, function() {
                            execute_btn.unwait();
                            form.portlet.enable();
                        } );
                    }
                })
            }
            // remap feature
            if ( options.job_id && options.job_remap ) {
                options.inputs.push({
                    label       : 'Resume dependencies from this job',
                    name        : 'rerun_remap_job_id',
                    type        : 'select',
                    display     : 'radio',
                    ignore      : '__ignore__',
                    value       : '__ignore__',
                    options     : [ [ 'Yes', options.job_id ], [ 'No', '__ignore__' ] ],
                    help        : 'The previous run of this tool failed and other tools were waiting for it to finish successfully. Use this option to resume those tools using the new output(s) of this tool run.'
                });
            }
        },

        /** Submit a regular job.
         * @param{dict}     options   - Specifies tool id and version
         * @param{function} callback  - Called when request has completed
         */
        submit: function( options, callback ) {
            var self = this;
            var job_def = {
                tool_id         : options.id,
                tool_version    : options.version,
                inputs          : this.form.data.create()
            }
            this.form.trigger( 'reset' );
            if ( !self.validate( job_def ) ) {
                Galaxy.emit.debug( 'tool-form::submit()', 'Submission canceled. Validation failed.' );
                callback && callback();
                return;
            }
            if ( options.action !== Galaxy.root + 'tool_runner/index' ) {
                var $f = $( '<form/>' ).attr( { action: options.action, method: options.method, enctype: options.enctype } );
                _.each( job_def.inputs, function( value, key ) { $f.append( $( '<input/>' ).attr( { 'name': key, 'value': value } ) ) } );
                $f.hide().appendTo( 'body' ).submit().remove();
                callback && callback();
                return;
            }
            Galaxy.emit.debug( 'tool-form::submit()', 'Validation complete.', job_def );
            Utils.request({
                type    : 'POST',
                url     : Galaxy.root + 'api/tools',
                data    : job_def,
                success : function( response ) {
                    callback && callback();
                    self.$el.children().hide();
                    self.$el.append( self._templateSuccess( response ) );
                    // Show Webhook if job is running
                    if ( response.jobs && response.jobs.length > 0 ) {
                        self.$el.append( $( '<div/>', { id: 'webhook-view' } ) );
                        var WebhookApp = new Webhooks.WebhookView({
                            urlRoot: Galaxy.root + 'api/webhooks/tool',
                            toolId: job_def.tool_id
                        });
                    }
                    parent.Galaxy && parent.Galaxy.currHistoryPanel && parent.Galaxy.currHistoryPanel.refreshContents();
                },
                error   : function( response ) {
                    callback && callback();
                    Galaxy.emit.debug( 'tool-form::submit', 'Submission failed.', response );
                    var input_found = false;
                    if ( response && response.err_data ) {
                        var error_messages = self.form.data.matchResponse( response.err_data );
                        for ( var input_id in error_messages ) {
                            self.form.highlight( input_id, error_messages[ input_id ]);
                            input_found = true;
                            break;
                        }
                    }
                    if ( !input_found ) {
                        self.modal.show({
                            title   : 'Job submission failed',
                            body    : self._templateError( job_def, response && response.err_msg ),
                            buttons : { 'Close' : function() { self.modal.hide() } }
                        });
                    }
                }
            });
        },

        /** Validate job dictionary.
         * @param{dict}     job_def   - Job execution dictionary
        */
        validate: function( job_def ) {
            var job_inputs  = job_def.inputs;
            var batch_n     = -1;
            var batch_src   = null;
            for ( var job_input_id in job_inputs ) {
                var input_value = job_inputs[ job_input_id ];
                var input_id    = this.form.data.match( job_input_id );
                var input_field = this.form.field_list[ input_id ];
                var input_def   = this.form.input_list[ input_id ];
                if ( !input_id || !input_def || !input_field ) {
                    Galaxy.emit.debug('tool-form::validate()', 'Retrieving input objects failed.');
                    continue;
                }
                if ( !input_def.optional && input_value == null ) {
                    this.form.highlight( input_id );
                    return false;
                }
                if ( input_value && input_value.batch ) {
                    var n = input_value.values.length;
                    var src = n > 0 && input_value.values[ 0 ] && input_value.values[ 0 ].src;
                    if ( src ) {
                        if ( batch_src === null ) {
                            batch_src = src;
                        } else if ( batch_src !== src ) {
                            this.form.highlight( input_id, 'Please select either dataset or dataset list fields for all batch mode fields.' );
                            return false;
                        }
                    }
                    if ( batch_n === -1 ) {
                        batch_n = n;
                    } else if ( batch_n !== n ) {
                        this.form.highlight( input_id, 'Please make sure that you select the same number of inputs for all batch mode fields. This field contains <b>' + n + '</b> selection(s) while a previous field contains <b>' + batch_n + '</b>.' );
                        return false;
                    }
                }
            }
            return true;
        },

        _templateSuccess: function( response ) {
            if ( response.jobs && response.jobs.length > 0 ) {
                var njobs = response.jobs.length;
                var njobs_text = njobs == 1 ? '1 job has' : njobs + ' jobs have';
                var $message = $( '<div/>' ).addClass( 'donemessagelarge' )
                                            .append( $( '<p/>' ).text( njobs_text + ' been successfully added to the queue - resulting in the following datasets:' ) );
                _.each( response.outputs, function( output ) {
                    $message.append( $( '<p/>' ).addClass( 'messagerow' ).append( $( '<b/>' ).text( output.hid + ': ' + output.name ) ) );
                });
                $message.append( $( '<p/>' ).append( '<b/>' ).text( 'You can check the status of queued jobs and view the resulting data by refreshing the History pane. When the job has been run the status will change from \'running\' to \'finished\' if completed successfully or \'error\' if problems were encountered.' ) );
                return $message;
            } else {
                return this._templateError( response, 'Invalid success response. No jobs found.' );
            }
        },

        _templateError: function( response, err_msg ) {
            return  $( '<div/>' ).addClass( 'errormessagelarge' )
                                 .append( $( '<p/>' ).text( 'The server could not complete the request. Please contact the Galaxy Team if this error persists. ' + ( err_msg || '' ) ) )
                                 .append( $( '<pre/>' ).text( JSON.stringify( response, null, 4 ) ) );
        }
    });

    return {
        View: View
    };
});