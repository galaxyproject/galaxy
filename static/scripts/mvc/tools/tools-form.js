/**
    This is the regular tool form.
*/
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/tools/tools-form-base', 'mvc/tools/tools-jobs'],
    function(Utils, Ui, ToolFormBase, ToolJobs) {

    // create form view
    var View = ToolFormBase.extend({
        // initialize
        initialize: function(options) {
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
