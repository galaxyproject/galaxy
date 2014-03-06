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
    
    // create job
    submit: function(chart, request_string, callback) {
        // link this
        var self = this;
        
        // backup chart details
        var chart_id        = chart.id;
        var chart_type      = chart.get('type');
        
        // get chart settings
        var chart_settings  = this.app.types.get(chart_type);
       
        // configure tool
        data = {
            'tool_id'       : 'rkit',
            'history_id'    : chart.get('history_id'),
            'inputs'        : {
                'input'     : chart.get('dataset_hid'),
                'module'    : chart_type,
                'options'   : request_string
            }
        }
        
        // cleanup previous dataset file
        var previous =  chart.get('dataset_id_job');
        if (previous) {
            Utils.request('PUT', config.root + 'api/histories/' + chart.get('history_id') + '/contents/' + previous, { deleted: true });
        }
        
        // set chart state
        chart.state('submit', 'Sending job request...');
        
        // post job
        Utils.request('POST', config.root + 'api/tools', data,
            // success handler
            function(response) {
                if (!response.outputs || response.outputs.length == 0) {
                    chart.state('failed', 'Job submission failed. No response.');
                } else {
                    // update galaxy history
                    if (Galaxy && Galaxy.currHistoryPanel) {
                        Galaxy.currHistoryPanel.refreshHdas();
                    }
        
                    // get dataset
                    var job = response.outputs[0];
                    
                    // check dataset
                    chart.state('queued', 'Job has been queued...');
                    
                    // backup resulting dataset id
                    chart.set('dataset_id_job', job.id);
                    
                    // wait for job completion
                    self._loop(job.id, function(job) {
                        switch (job.state) {
                            case 'ok':
                                chart.state('success', 'Job completed successfully...');
                                callback(job);
                                return true;
                            case 'error':
                                chart.state('failed', 'Job has failed. Please check the history for details.');
                                return true;
                            case 'running':
                                chart.state('running', 'Job is running...');
                                return false;
                        }
                    });
                }
            },
            // error handler
            function(response) {
                chart.state('failed', 'Job submission failed. Please make sure that \'R-kit\' is installed.');
            }
        );
    },
    
    // request job details
    _loop: function(id, callback) {
        var self = this;
        Utils.request('GET', config.root + 'api/jobs/' + id, {}, function(job) {
            if (!callback(job)) {
                setTimeout(function() { self._loop(id, callback); }, self.app.config.get('query_timeout'));
            }
        });
    }
});

});