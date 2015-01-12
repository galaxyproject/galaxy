/**
    This is the main class of the tool form plugin. It is referenced as 'app' in all lower level modules.
*/
define(['utils/utils', 'mvc/tools/tools-form-base'],
    function(Utils, ToolFormBase) {

    // create form view
    var View = ToolFormBase.extend({
        initialize: function(options) {
            this.workflow = true;
            ToolFormBase.prototype.initialize.call(this, options);
        },
        
        /** Builds a new model through api call and recreates the entire form
        */
        _buildModel: function() {
        },
        
        /** Request a new model for an already created tool form and updates the form inputs
        */
        _updateModel: function() {
            // create the request dictionary
            var self = this;
            var current_state = this.tree.finalize();
            
            // log tool state
            console.debug('tools-form-workflow::_refreshForm() - Refreshing states.');
            console.debug(current_state);
            
            // register process
            var process_id = this.deferred.register();

            // build model url for request
            var model_url = galaxy_config.root + 'workflow/editor_form_post?tool_id=' + this.options.id;
            
            // post job
            Utils.request({
                type    : 'GET',
                url     : model_url,
                data    : current_state,
                success : function(node) {
                    parent.update_node(node);
                    
                    // process completed
                    self.deferred.done(process_id);
            
                    // log success
                    console.debug('tools-form::_refreshForm() - States refreshed.');
                    console.debug(node);
                },
                error   : function(response) {
                    // process completed
                    self.deferred.done(process_id);
                    
                    // log error
                    console.debug('tools-form::_refreshForm() - Refresh request failed.');
                    console.debug(response);
                }
            });
        }
    });

    return {
        View: View
    };
});
