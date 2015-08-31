/**
    This is the regular tool form.
*/
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/tools/tools-form-base', 'mvc/tools/tools-jobs'],
    function(Utils, Ui, ToolFormBase, ToolJobs) {

    // create form view
    var View = ToolFormBase.extend({
        // initialize
        initialize: function(options) {
            // execute button
            var self = this;
            var execute = new Ui.Button({
                icon     : 'fa-check',
                tooltip  : 'Execute: ' + options.name,
                title    : 'Execute',
                cls      : 'btn btn-primary',
                floating : 'clear',
                onclick  : function() {
                    execute.wait();
                    self.form.portlet.disable();
                    ToolJobs.submit(self.form, self.options, function() {
                        execute.unwait();
                        self.form.portlet.enable();
                    });
                }
            });
            // add remap button
            if (options.job_id && options.job_remap) {
                options.inputs['rerun_remap_job_id'] = {
                    label       : 'Resume dependencies from this job',
                    name        : 'rerun_remap_job_id',
                    type        : 'select',
                    display     : 'radio',
                    ignore      : '__ignore__',
                    value       : '__ignore__',
                    options     : [['Yes', options.job_id], ['No', '__ignore__']],
                    help        : 'The previous run of this tool failed and other tools were waiting for it to finish successfully. Use this option to resume those tools using the new output(s) of this tool run.'
                }
            }
            // create options dictionary
            options = Utils.merge(options, {
                buttons     : {
                    execute : execute
                }
            });
            ToolFormBase.prototype.initialize.call(this, options);
        }
    });

    return {
        View: View
    };
});
