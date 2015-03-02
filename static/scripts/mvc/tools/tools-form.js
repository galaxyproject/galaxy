/**
    This is the regular tool form.
*/
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/tools/tools-form-base', 'mvc/tools/tools-jobs'],
    function(Utils, Ui, ToolFormBase, ToolJobs) {

    // create form view
    var View = ToolFormBase.extend({
        // initialize
        initialize: function(options) {
            // create options dictionary
            var self = this;
            options = Utils.merge(options, {
                update_url  : galaxy_config.root + 'api/tools/' + options.id + '/build',
                buttons     : {
                    execute : new Ui.Button({
                        icon     : 'fa-check',
                        tooltip  : 'Execute: ' + options.name,
                        title    : 'Execute',
                        cls      : 'btn btn-primary',
                        floating : 'clear',
                        onclick  : function() {
                            ToolJobs.submit(self.form, options);
                        }
                    })
                }
            });
            ToolFormBase.prototype.initialize.call(this, options);
        }
    });

    return {
        View: View
    };
});
