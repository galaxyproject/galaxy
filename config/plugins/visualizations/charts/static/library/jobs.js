/**
 *  This class handles job submissions to the charts tool.
 */
define( [ 'utils/utils' ], function( Utils ) {
    return Backbone.Model.extend({
        initialize: function( app, options ) {
            this.app = app;
            this.options = Utils.merge( options, this.optionsDefault );
        },
        
        /* Request job results */
        request: function( chart, settings_string, columns_string, success, error ) {
            var self = this;
            chart.state( 'wait', 'Requesting job results...' );
            var dataset_id_job = chart.get( 'dataset_id_job' );
            if (dataset_id_job != '') {
                self._wait( chart, success, error );
            } else {
                self._submit( chart, settings_string, columns_string, success, error );
            }
        },
        
        /* Remove previous data when re-running jobs */
        cleanup: function( chart ) {
            var self = this;
            var previous =  chart.get( 'dataset_id_job' );
            if (previous != '') {
                Utils.request({
                    type    : 'PUT',
                    url     : config.root + 'api/histories/none/contents/' + previous,
                    data    : { deleted: true },
                    success : function() {
                        self._refreshHdas();
                    }
                });
                chart.set( 'dataset_id_job', '' );
            }
        },
        
        // create job
        _submit: function(chart, settings_string, columns_string, success, error) {
            // link this
            var self = this;
            
            // backup chart details
            var chart_id            = chart.id;
            var chart_type          = chart.get('type');
            
            // get chart settings
            var chart_definition    = chart.definition;
           
            // configure tool
            data = {
                'tool_id'       : 'charts',
                'inputs'        : {
                    'input'     : {
                        'id'    : chart.get('dataset_id'),
                        'src'   : 'hda'
                    },
                    'module'    : chart_definition.execute,
                    'columns'   : columns_string,
                    'settings'  : settings_string
                }
            }
            
            // set chart state
            chart.state('wait', 'Sending job request...');
            
            // post job
            Utils.request({
                type    : 'POST',
                url     : config.root + 'api/tools',
                data    : data,
                success : function(response) {
                    if (!response.outputs || response.outputs.length == 0) {
                        chart.state('failed', 'Job submission failed. No response.');
                        
                        // call error
                        error && error();
                    } else {
                        // update galaxy history
                        self._refreshHdas();
            
                        // get dataset
                        var job = response.outputs[0];
                        
                        // check dataset
                        chart.state('wait', 'Your job has been queued. You may close the browser window. The job will run in the background.');
                        
                        // backup resulting dataset id
                        chart.set('dataset_id_job', job.id);
                        
                        // save
                        self.app.storage.save();
                        
                        // wait for job completion
                        self._wait(chart, success, error);
                    }
                },
                error   : function(response) {
                    var message = '';
                    if (response && response.message && response.message.data && response.message.data.input) {
                        message = response.message.data.input + '.';
                    }
                    
                    // update state
                    chart.state('failed', 'This visualization requires the \'charts\' tool. Please make sure it is installed. ' + message);
                    
                    // call error
                    error && error();
                          
                }
            });
        },
        
        /** Request job details */
        _wait: function( chart, success, error ) {
            var self = this;
            Utils.request({
                type    : 'GET',
                url     : config.root + 'api/datasets/' + chart.get( 'dataset_id_job' ),
                data    : {},
                success : function( dataset ) {
                    var ready = false;
                    switch ( dataset.state ) {
                        case 'ok':
                            chart.state( 'wait', 'Job completed successfully...' );
                            success && success( dataset );
                            ready = true;
                            break;
                        case 'error':
                            chart.state( 'failed', 'Job has failed. Please check the history for details.' );
                            error && error( dataset );
                            ready = true;
                            break;
                        case 'running':
                            chart.state( 'wait', 'Your job is running. You may close the browser window. The job will continue in the background.' );
                    }
                    if ( !ready ) {
                        setTimeout( function() {
                            self._wait( chart, success, error );
                        }, self.app.config.get( 'query_timeout' ) );
                    }
                }
            });
        },
        
        /** Refresh history panel */
        _refreshHdas: function() {
            Galaxy && Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.refreshContents();
        }
    });
});