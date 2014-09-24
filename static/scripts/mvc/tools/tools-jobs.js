/**
    This class handles job submissions and the error handling.
*/
define(['utils/utils', 'mvc/tools/tools-template'], function(Utils, ToolTemplate) {
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
        console.log(job_def);
        
        // post job
        Utils.request('POST', galaxy_config.root + 'api/tools', job_def,
            // success handler
            function(response) {
                self.app.message(ToolTemplate.success(response));
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
        
        // link this
        var self = this;
        
        /** Highlight and scroll to error */
        function foundError (input_id, message) {
            // get input field
            var input_element = self.app.element_list[input_id];
            
            // mark error
            input_element.error(message || 'Please verify this parameter.');
            
            // set flag
            if (valid) {
                // scroll to first input element
                $(self.app.container).animate({
                    scrollTop: input_element.$el.offset().top - 20
                }, 500);
                
                // set error flag
                valid = false;
            }
        }
        
        // counter for values declared in batch mode
        var n_values = -1;
        
        // validation
        for (var job_input_id in job_inputs) {
            // get current value
            var input_value = job_inputs[job_input_id];
            
            // collect input field properties
            var input_id = this.app.tree.match(job_input_id);
            var input_field = this.app.field_list[input_id];
            var input_def = this.app.input_list[input_id];
            
            // check basic field validation
            if (input_def && !input_def.optional && input_field && input_field.validate && !input_field.validate()) {
                foundError(input_id);
            }
            
            // check if input field is in batch mode
            if (input_value.batch) {
                var n = input_value.values.length;
                if (n_values === -1) {
                    n_values = n;
                } else {
                    if (n_values !== n) {
                        foundError(input_id, 'Please make sure that you select the same number of inputs for all batch mode fields. This field contains <b>' + n + '</b> selection(s) while a previous field contains <b>' + n_values + '</b>.');
                    }
                }
            }
            
        }
        
        // return result
        return valid;
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