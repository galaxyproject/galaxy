/**
    This class handles job submissions and validations.
*/
define(['utils/utils', 'mvc/tools/tools-template'], function(Utils, ToolTemplate) {
return {
    submit: function(form, options, callback) {
        // link this
        var self = this;

        // create job definition for submission to tools api
        var job_def = {
            tool_id         : options.id,
            tool_version    : options.version,
            inputs          : form.data.create()
        }

        // reset
        form.trigger('reset');

        // validate job definition
        if (!this._validation(form, job_def)) {
            Galaxy.emit.debug('tools-jobs::submit()', 'Submission canceled. Validation failed.');
            callback && callback();
            return;
        }

        // debug
        Galaxy.emit.debug('tools-jobs::submit()', 'Validation complete.', job_def);

        // post job
        Utils.request({
            type    : 'POST',
            url     : galaxy_config.root + 'api/tools',
            data    : job_def,
            success : function(response) {
                callback && callback();
                form.$el.replaceWith( ToolTemplate.success( response ) );
                // begin checking the history for updates
                self._refreshHdas();
            },
            error   : function(response) {
                callback && callback();
                Galaxy.emit.debug('tools-jobs::submit', 'Submission failed.', response);
                if (response && response.err_data) {
                    var error_messages = form.data.matchResponse(response.err_data);
                    for (var input_id in error_messages) {
                        form.highlight(input_id, error_messages[input_id]);
                        break;
                    }
                } else {
                    form.modal.show({
                        title   : 'Job submission failed',
                        body    : ( response && response.err_msg ) || ToolTemplate.error( job_def ),
                        buttons : {
                            'Close' : function() {
                                form.modal.hide();
                            }
                        }
                    });
                }
            }
        });
    },

    /** Validate job definition
    */
    _validation: function(form, job_def) {
        // get input parameters
        var job_inputs = job_def.inputs;

        // counter for values declared in batch mode
        var batch_n = -1;
        var batch_src = null;

        // validation
        for (var job_input_id in job_inputs) {
            // get current value
            var input_value = job_inputs[job_input_id];

            // collect input field properties
            var input_id = form.data.match(job_input_id);
            var input_field = form.field_list[input_id];
            var input_def = form.input_list[input_id];

            // check if objects where properly identified
            if (!input_id || !input_def || !input_field) {
                Galaxy.emit.debug('tools-jobs::_validation()', 'Retrieving input objects failed.');
                continue;
            }

            // validate non-optional fields
            if (!input_def.optional && input_value == null) {
                form.highlight(input_id);
                return false;
            }

            // check if input field is in batch mode
            if (input_value && input_value.batch) {
                // get values
                var n = input_value.values.length;

                // get source
                var src = null;
                if (n > 0) {
                    src = input_value.values[0] && input_value.values[0].src;
                }

                // check source type
                if (src) {
                    if (batch_src === null) {
                        batch_src = src;
                    } else {
                        if (batch_src !== src) {
                            form.highlight(input_id, 'Please select either dataset or dataset list fields for all batch mode fields.');
                            return false;
                        }
                    }
                }

                // check number of inputs
                if (batch_n === -1) {
                    batch_n = n;
                } else {
                    if (batch_n !== n) {
                        form.highlight(input_id, 'Please make sure that you select the same number of inputs for all batch mode fields. This field contains <b>' + n + '</b> selection(s) while a previous field contains <b>' + batch_n + '</b>.');
                        return false;
                    }
                }
            }
        }

        // return validation result
        return true;
    },

    /** Refreshes the history panel
    */
    _refreshHdas: function(detailIds, options) {
        if (parent.Galaxy && parent.Galaxy.currHistoryPanel) {
            parent.Galaxy.currHistoryPanel.refreshContents(detailIds, options);
        }
    }
};

});
