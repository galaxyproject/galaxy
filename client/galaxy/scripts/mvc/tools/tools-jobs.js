/**
    This class handles job submissions and the error handling.
*/
define(['utils/utils'], function(Utils) {
return Backbone.Model.extend({
    // initialize
    initialize: function(app, options) {
        // link app
        this.app = app;
        
        // link options
        this.options = Utils.merge(options, this.optionsDefault);
    },
    
    /** Creates and submits a job request to the api
    */
    submit: function() {
        // link this
        var self = this;
        
        // create job definition for submission to tools api
        var job_def = {
            tool_id : this.app.options.id,
            inputs  : this.app.tree.finalize()
        }
        
        // reset
        this.app.reset();
        
        // validate job definition
        if (!this._validation(job_def)) {
            console.debug('tools-jobs::submit - Submission canceled. Validation failed.');
            return;
        }
        
        // post job
        Utils.request('POST', galaxy_config.root + 'api/tools', job_def,
            // success handler
            function(response) {
                if (!response.outputs || response.outputs.length == 0) {
                    console.debug(response);
                }
                self.app.message({
                    text : 'A job has been successfully added to the queue. You can check the status of queued jobs and view the resulting data by refreshing the History pane. When the job has been run the status will change from \'running\' to \'finished\' if completed successfully or \'error\' if problems were encountered.'
                });
                self._refreshHdas();
            },
            // error handler
            function(response) {
                console.debug(response);
                if (response && response.message && response.message.data) {
                    var error_messages = self.app.tree.matchResponse(response.message.data);
                    for (var id in error_messages) {
                        var error_text = error_messages[id];
                        if (!error_text) {
                            error_text = 'Please verify this parameter.';
                        }
                        self.app.element_list[id].error(error_text);
                    }
                }
            }
        );
    },
    
    /** Validate job definition
    */
    _validation: function(job_def) {
        // get input parameters
        var job_inputs = job_def.inputs;
        
        // validation flag
        var valid = true;
        
        // check inputs
        for (var job_input_id in job_inputs) {
            // collect input field properties
            var input = job_inputs[job_input_id];
            var input_id = this.app.tree.match(job_input_id);
            var input_field = this.app.field_list[input_id];
            
            // check field validation
            //if (input_field && input_field.validate && !input_field.validate()) {
                this.app.element_list[input_id].error('Please verify this parameter.');
                valid = false;
            //}
        }
        
        // return result
        return false;
    },
    
    /** Refreshes the history panel
    */
    _refreshHdas: function() {
        if (parent.Galaxy && parent.Galaxy.currHistoryPanel) {
            parent.Galaxy.currHistoryPanel.refreshContents();
        }
    }
});

});