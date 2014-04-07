// dependencies
define(['utils/utils'], function(Utils) {

// widget
return Backbone.Model.extend(
{
    // initialize
    initialize: function(app, options) {
        // link app
        this.app = app;
        
        // link options
        this.options = Utils.merge(options, this.optionsDefault);
    },
    
    // clean
    cleanup: function(chart) {
        // cleanup previous dataset file
        var previous =  chart.get('dataset_id_job');
        if (previous != '') {
            var self = this;
            Utils.request('PUT', config.root + 'api/histories/none/contents/' + previous, { deleted: true }, function() {
                // update galaxy history
                self._refreshHdas();
            });
            
            // reset id
            chart.set('dataset_id_job', '');
        }
    },
    
    // create job
    submit: function(chart, settings_string, columns_string, success, error) {
        // link this
        var self = this;
        
        // backup chart details
        var chart_id        = chart.id;
        var chart_type      = chart.get('type');
        
        // get chart settings
        var chart_settings  = this.app.types.get(chart_type);
       
        // configure tool
        data = {
            'tool_id'       : 'chartskit',
            'inputs'        : {
                'input'     : {
                    'id'    : chart.get('dataset_id'),
                    'src'   : 'hda'
                },
                'module'    : chart_type,
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
                    chart.state('wait', 'Job has been queued...');
                    
                    // backup resulting dataset id
                    chart.set('dataset_id_job', job.id);
                    
                    // save
                    this.app.storage.save();
                      
                    // wait for job completion
                    self._loop(job.id, function(job) {
                        switch (job.state) {
                            case 'ok':
                                // update state
                                chart.state('wait', 'Job completed successfully...');
                               
                                // execute success
                                success(job);
                               
                                // stop loop
                                return true;
                            case 'error':
                                // update state
                                chart.state('failed', 'Job has failed. Please check the history for details.');
                               
                                // call error
                                error && error();
                               
                                // stop loop
                                return true;
                            case 'running':
                                // wait
                                chart.state('wait', 'Job is running...');
                               
                                // continue loop
                                return false;
                        }
                    });
                }
            },
            // error handler
            function(response) {
                var message = '';
                if (response && response.message && response.message.data && response.message.data.input) {
                    message = response.message.data.input + '.';
                }
                // update state
                chart.state('failed', 'This visualization requires the Charts-Kit. Please make sure it is installed. ' + message);
                
                // call error
                error && error();
                      
            }
        );
    },
    
    // request job details
    _loop: function(id, callback) {
        var self = this;
        Utils.request('GET', config.root + 'api/datasets/' + id, {}, function(job) {
            if (!callback(job)) {
                setTimeout(function() { self._loop(id, callback); }, self.app.config.get('query_timeout'));
            }
        });
    },
    
    // refresh history panel
    _refreshHdas: function() {
        // update galaxy history
        if (Galaxy && Galaxy.currHistoryPanel) {
            Galaxy.currHistoryPanel.refreshHdas();
        }
    }
});

});