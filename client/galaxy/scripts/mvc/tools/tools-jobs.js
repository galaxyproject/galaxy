/*
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
    
    // create job
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
                    var error_messages = self.app.tree.match(response.message.data);
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
    
    // refresh history panel
    _refreshHdas: function() {
        if (parent.Galaxy && parent.Galaxy.currHistoryPanel) {
            parent.Galaxy.currHistoryPanel.refreshContents();
        }
    }
});

});