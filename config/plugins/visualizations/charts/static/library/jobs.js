// dependencies
define(['utils/utils'], function(Utils) {

/**
 *  This class handles job submissions to the charts tool.
 */
return Backbone.Model.extend({
    // initialize
    initialize: function(app, options) {
        // link app
        this.app = app;
        
        // link options
        this.options = Utils.merge(options, this.optionsDefault);
    },
    
    // request job results
    request: function(chart, settings_string, columns_string, success, error) {
        // link this
        var self = this;
        
        // set chart state
        chart.state('wait', 'Requesting job results...');
        
        // get dataset job id if already set
        var dataset_id_job = chart.get('dataset_id_job');
        if (dataset_id_job != '') {
            // wait for job completion
            self._wait(chart, success, error);
        } else {
            // post job
            self._submit(chart, settings_string, columns_string, success, error);
        }
    },
    
    // clean
    cleanup: function(chart) {
        // link this
        var self = this;
        
        // cleanup previous dataset file
        var previous =  chart.get('dataset_id_job');
        if (previous != '') {
            Utils.request('PUT', config.root + 'api/histories/none/contents/' + previous, { deleted: true }, function() {
                // update galaxy history
                self._refreshHdas();
            });
            
            // reset id
            chart.set('dataset_id_job', '');
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
        Utils.request('POST', config.root + 'api/tools', data,
            // success handler
            function(response) {
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
                    this.app.storage.save();
                    
                    // wait for job completion
                    self._wait(chart, success, error);
                }
            },
            // error handler
            function(response) {
                var message = '';
                if (response && response.message && response.message.data && response.message.data.input) {
                    message = response.message.data.input + '.';
                }
                
                // update state
                chart.state('failed', 'This visualization requires the \'charts\' tool. Please make sure it is installed. ' + message);
                
                // call error
                error && error();
                      
            }
        );
    },
    
    // request job details
    _wait: function(chart, success, error) {
        var self = this;
        Utils.request('GET', config.root + 'api/datasets/' + chart.get('dataset_id_job'), {}, function(dataset) {
            // check dataset state
            var ready = false;
            switch (dataset.state) {
                case 'ok':
                    // update state
                    chart.state('wait', 'Job completed successfully...');
                   
                    // execute success
                    success &&  success(dataset);
                   
                    // stop loop
                    ready = true;
                    break;
                case 'error':
                    // update state
                    chart.state('failed', 'Job has failed. Please check the history for details.');
                   
                    // call error
                    error && error(dataset);
                   
                    // stop loop
                    ready = true;
                    break;
                case 'running':
                    // wait
                    chart.state('wait', 'Your job is running. You may close the browser window. The job will continue in the background.');
            }
            
            // wait and try again
            if (!ready) {
                setTimeout(function() {
                    self._wait(chart, success, error);
                }, self.app.config.get('query_timeout'));
            }
        });
    },
    
    // refresh history panel
    _refreshHdas: function() {
        // update galaxy history
        if (Galaxy && Galaxy.currHistoryPanel) {
            Galaxy.currHistoryPanel.refreshContents();
        }
    }
});

});