// dependencies
define(['utils/utils'], function(Utils) {

/**
 *  This class handles job submissions.
 */
return Backbone.Model.extend({
    // initialize
    initialize: function(app, options) {
        // link app
        this.app = app;
        
        // link options
        this.options = Utils.merge(options, this.optionsDefault);
    },
    
    // create job
    submit: function(data, success, error) {
        // link this
        var self = this;
        
        // post job
        Utils.request('POST', config.root + 'api/tools', data,
            // success handler
            function(response) {
                if (!response.outputs || response.outputs.length == 0) {
                    // call error
                    error && error();
                } else {
                    // update galaxy history
                    console.log(response);
                }
            },
            // error handler
            function(response) {
                var message = '';
                if (response && response.message && response.message.data && response.message.data.input) {
                    message = response.message.data.input + '.';
                }
                
                // call error
                error && error();
                      
            }
        );
    }
});

});