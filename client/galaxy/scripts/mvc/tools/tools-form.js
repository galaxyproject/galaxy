/**
    This is the regular tool form.
*/
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/tools/tools-form-base', 'mvc/tools/tools-jobs'],
    function( Utils, Ui, ToolFormBase, ToolJobs ) {
    var View = ToolFormBase.extend({
        initialize: function( options ) {
            var self = this;
            ToolFormBase.prototype.initialize.call( this, Utils.merge({
                customize       : function( options ) {
                    // build execute button
                    options.buttons = {
                        execute : execute_btn = new Ui.Button({
                            icon     : 'fa-check',
                            tooltip  : 'Execute: ' + options.name + ' (' + options.version + ')',
                            title    : 'Execute',
                            cls      : 'btn btn-primary',
                            floating : 'clear',
                            onclick  : function() {
                                execute_btn.wait();
                                self.form.portlet.disable();
                                ToolJobs.submit( self.form, options, function() {
                                    execute_btn.unwait();
                                    self.form.portlet.enable();
                                } );
                            }
                        })
                    };

                    // remap feature
                    if ( options.job_id && options.job_remap ) {
                        options.inputs[ 'rerun_remap_job_id' ] = {
                            label       : 'Resume dependencies from this job',
                            name        : 'rerun_remap_job_id',
                            type        : 'select',
                            display     : 'radio',
                            ignore      : '__ignore__',
                            value       : '__ignore__',
                            options     : [ [ 'Yes', options.job_id ], [ 'No', '__ignore__' ] ],
                            help        : 'The previous run of this tool failed and other tools were waiting for it to finish successfully. Use this option to resume those tools using the new output(s) of this tool run.'
                        }
                    }
                }
            }, options ) );
        }
    });

    return {
        View: View
    };
});
