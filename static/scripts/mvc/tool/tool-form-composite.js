define("mvc/tool/tool-form-composite", ["exports", "utils/localization", "utils/utils", "utils/deferred", "mvc/ui/ui-misc", "mvc/form/form-view", "mvc/form/form-data", "mvc/tool/tool-form-base", "mvc/ui/ui-modal", "mvc/webhooks", "mvc/workflow/workflow-icons"], function(exports, _localization, _utils, _deferred, _uiMisc, _formView, _formData, _toolFormBase, _uiModal, _webhooks, _workflowIcons) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _localization2 = _interopRequireDefault(_localization);

    var _utils2 = _interopRequireDefault(_utils);

    var _deferred2 = _interopRequireDefault(_deferred);

    var _uiMisc2 = _interopRequireDefault(_uiMisc);

    var _formView2 = _interopRequireDefault(_formView);

    var _formData2 = _interopRequireDefault(_formData);

    var _toolFormBase2 = _interopRequireDefault(_toolFormBase);

    var _uiModal2 = _interopRequireDefault(_uiModal);

    var _webhooks2 = _interopRequireDefault(_webhooks);

    var _workflowIcons2 = _interopRequireDefault(_workflowIcons);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var View = Backbone.View.extend({
        initialize: function initialize(options) {
            var self = this;
            this.modal = parent.Galaxy.modal || new _uiModal2.default.View();
            this.model = options && options.model || new Backbone.Model(options);
            this.deferred = new _deferred2.default();
            this.setElement($("<div/>").addClass("ui-form-composite").append(this.$message = $("<div/>")).append(this.$header = $("<div/>")).append(this.$steps = $("<div/>")));
            $("body").append(this.$el);
            this._configure();
            this.render();
            $(window).resize(function() {
                self._refresh();
            });
        },

        /** Refresh height of scrollable div below header, handle scrolling by lazy loading steps */
        _refresh: function _refresh(step_index) {
            var margin = _.reduce(this.$el.children(), function(memo, child) {
                return memo + $(child).outerHeight();
            }, 0) - this.$steps.height() + 90;
            this.$steps.css("height", $(window).height() - margin);
        },

        /** Configures form/step options for each workflow step */
        _configure: function _configure() {
            var self = this;
            this.forms = [];
            this.steps = [];
            this.links = [];
            this.parms = [];
            _.each(this.model.get("steps"), function(step, i) {
                Galaxy.emit.debug("tool-form-composite::initialize()", i + " : Preparing workflow step.");
                var icon = _workflowIcons2.default[step.step_type];
                var title = parseInt(i + 1) + ": " + (step.step_label || step.step_name);
                if (step.annotation) {
                    title += " - " + step.annotation;
                }
                if (step.step_version) {
                    title += " (Galaxy Version " + step.step_version + ")";
                }
                step = _utils2.default.merge({
                    index: i,
                    fixed_title: _.escape(title),
                    icon: icon || "",
                    help: null,
                    citations: null,
                    collapsible: true,
                    collapsed: i > 0 && !self._isDataStep(step),
                    sustain_version: true,
                    sustain_repeats: true,
                    sustain_conditionals: true,
                    narrow: true,
                    text_enable: "Edit",
                    text_disable: "Undo",
                    cls_enable: "fa fa-edit",
                    cls_disable: "fa fa-undo",
                    errors: step.messages,
                    initial_errors: true,
                    cls: "ui-portlet-narrow",
                    hide_operations: true,
                    needs_refresh: false,
                    always_refresh: step.step_type != "tool"
                }, step);
                self.steps[i] = step;
                self.links[i] = [];
                self.parms[i] = {};
            });

            // build linear index of step input pairs
            _.each(this.steps, function(step, i) {
                _formData2.default.visitInputs(step.inputs, function(input, name) {
                    self.parms[i][name] = input;
                });
            });

            // iterate through data input modules and collect linked sub steps
            _.each(this.steps, function(step, i) {
                _.each(step.output_connections, function(output_connection) {
                    _.each(self.steps, function(sub_step, j) {
                        sub_step.step_index === output_connection.input_step_index && self.links[i].push(sub_step);
                    });
                });
            });

            // convert all connected data inputs to hidden fields with proper labels,
            // and track the linked source step
            _.each(this.steps, function(step, i) {
                _.each(self.steps, function(sub_step, j) {
                    var connections_by_name = {};
                    _.each(step.output_connections, function(connection) {
                        sub_step.step_index === connection.input_step_index && (connections_by_name[connection.input_name] = connection);
                    });
                    _.each(self.parms[j], function(input, name) {
                        var connection = connections_by_name[name];
                        if (connection) {
                            input.type = "hidden";
                            input.help = input.step_linked ? input.help + ", " : "";
                            input.help += "Output dataset '" + connection.output_name + "' from step " + (parseInt(i) + 1);
                            input.step_linked = input.step_linked || [];
                            input.step_linked.push(step);
                        }
                    });
                });
            });

            // identify and configure workflow parameters
            var wp_count = 0;
            this.wp_inputs = {};

            function _handleWorkflowParameter(value, callback) {
                var re = /\$\{(.+?)\}/g;
                var match;
                while (match = re.exec(String(value))) {
                    var wp_name = match[1];
                    callback(self.wp_inputs[wp_name] = self.wp_inputs[wp_name] || {
                        label: wp_name,
                        name: wp_name,
                        type: "text",
                        color: "hsl( " + ++wp_count * 100 + ", 70%, 30% )",
                        style: "ui-form-wp-source",
                        links: []
                    });
                }
            }
            _.each(this.steps, function(step, i) {
                _.each(self.parms[i], function(input, name) {
                    _handleWorkflowParameter(input.value, function(wp_input) {
                        wp_input.links.push(step);
                        input.wp_linked = true;
                        input.type = "text";
                        input.backdrop = true;
                        input.style = "ui-form-wp-target";
                    });
                });
                _.each(step.post_job_actions, function(pja) {
                    _.each(pja.action_arguments, function(arg) {
                        _handleWorkflowParameter(arg, function() {});
                    });
                });
            });

            // select fields are shown for dynamic fields if all putative data inputs are available,
            // or if an explicit reference is specified as data_ref and available
            _.each(this.steps, function(step, i) {
                if (step.step_type == "tool") {
                    var data_resolved = true;
                    _formData2.default.visitInputs(step.inputs, function(input, name, context) {
                        var is_runtime_value = input.value && input.value.__class__ == "RuntimeValue";
                        var is_data_input = ["data", "data_collection"].indexOf(input.type) != -1;
                        var data_ref = context[input.data_ref];
                        input.step_linked && !self._isDataStep(input.step_linked) && (data_resolved = false);
                        input.options && (input.options.length == 0 && !data_resolved || input.wp_linked) && (input.is_workflow = true);
                        data_ref && (input.is_workflow = data_ref.step_linked && !self._isDataStep(data_ref.step_linked) || input.wp_linked);
                        (is_data_input || input.value && input.value.__class__ == "RuntimeValue" && !input.step_linked) && (step.collapsed = false);
                        is_runtime_value && (input.value = input.default_value);
                        input.flavor = "workflow";
                        if (!is_runtime_value && !is_data_input && input.type !== "hidden" && !input.wp_linked) {
                            if (input.optional || !_utils2.default.isEmpty(input.value) && input.value !== "") {
                                input.collapsible_value = input.value;
                                input.collapsible_preview = true;
                            }
                        }
                    });
                }
            });
        },

        render: function render() {
            var self = this;
            this.deferred.reset();
            this._renderHeader();
            this._renderMessage();
            this._renderParameters();
            this._renderHistory();
            this._renderResourceParameters();
            _.each(this.steps, function(step) {
                self._renderStep(step);
            });
        },

        /** Render header */
        _renderHeader: function _renderHeader() {
            var self = this;
            this.execute_btn = new _uiMisc2.default.Button({
                icon: "fa-check",
                title: (0, _localization2.default)("Run workflow"),
                cls: "btn btn-primary",
                onclick: function onclick() {
                    self._execute();
                }
            });
            this.$header.addClass("ui-form-header").empty().append(new _uiMisc2.default.Label({
                title: "Workflow: " + this.model.get("name")
            }).$el).append(this.execute_btn.$el);
        },

        /** Render message */
        _renderMessage: function _renderMessage() {
            this.$message.empty();
            if (this.model.get("has_upgrade_messages")) {
                this.$message.append(new _uiMisc2.default.Message({
                    message: "Some tools in this workflow may have changed since it was last saved or some errors were found. The workflow may still run, but any new options will have default values. Please review the messages below to make a decision about whether the changes will affect your analysis.",
                    status: "warning",
                    persistent: true,
                    fade: false
                }).$el);
            }
            var step_version_changes = this.model.get("step_version_changes");
            if (step_version_changes && step_version_changes.length > 0) {
                this.$message.append(new _uiMisc2.default.Message({
                    message: "Some tools are being executed with different versions compared to those available when this workflow was last saved because the other versions are not or no longer available on this Galaxy instance. To upgrade your workflow and dismiss this message simply edit the workflow and re-save it.",
                    status: "warning",
                    persistent: true,
                    fade: false
                }).$el);
            }
        },

        /** Render workflow parameters */
        _renderParameters: function _renderParameters() {
            var self = this;
            this.wp_form = null;
            if (!_.isEmpty(this.wp_inputs)) {
                this.wp_form = new _formView2.default({
                    title: "<b>Workflow Parameters</b>",
                    inputs: this.wp_inputs,
                    cls: "ui-portlet-narrow",
                    onchange: function onchange() {
                        _.each(self.wp_form.input_list, function(input_def, i) {
                            _.each(input_def.links, function(step) {
                                self._refreshStep(step);
                            });
                        });
                    }
                });
                this._append(this.$steps.empty(), this.wp_form.$el);
            }
        },

        /** Render workflow parameters */
        _renderHistory: function _renderHistory() {
            this.history_form = new _formView2.default({
                cls: "ui-portlet-narrow",
                title: "<b>History Options</b>",
                inputs: [{
                    type: "conditional",
                    name: "new_history",
                    test_param: {
                        name: "check",
                        label: "Send results to a new history",
                        type: "boolean",
                        value: "false",
                        help: ""
                    },
                    cases: [{
                        value: "true",
                        inputs: [{
                            name: "name",
                            label: "History name",
                            type: "text",
                            value: this.model.get("name")
                        }]
                    }]
                }]
            });
            this._append(this.$steps, this.history_form.$el);
        },

        /** Render Workflow Options */
        _renderResourceParameters: function _renderResourceParameters() {
            this.workflow_resource_parameters_form = null;
            if (!_.isEmpty(this.model.get('workflow_resource_parameters'))) {
                this.workflow_resource_parameters_form = new _formView2.default({
                    cls: 'ui-portlet-narrow',
                    title: '<b>Workflow Resource Options</b>',
                    inputs: this.model.get('workflow_resource_parameters')
                });
                this._append(this.$steps, this.workflow_resource_parameters_form.$el);
            }
        },

        /** Render step */
        _renderStep: function _renderStep(step) {
            var self = this;
            var form = null;
            this.deferred.execute(function(promise) {
                self.$steps.addClass("ui-steps");
                if (step.step_type == "tool") {
                    step.postchange = function(process, form) {
                        var self = this;
                        var current_state = {
                            tool_id: step.id,
                            tool_version: step.version,
                            inputs: $.extend(true, {}, form.data.create())
                        };
                        form.wait(true);
                        Galaxy.emit.debug("tool-form-composite::postchange()", "Sending current state.", current_state);
                        _utils2.default.request({
                            type: "POST",
                            url: Galaxy.root + "api/tools/" + step.id + "/build",
                            data: current_state,
                            success: function success(data) {
                                form.update(data);
                                form.wait(false);
                                Galaxy.emit.debug("tool-form-composite::postchange()", "Received new model.", data);
                                process.resolve();
                            },
                            error: function error(response) {
                                Galaxy.emit.debug("tool-form-composite::postchange()", "Refresh request failed.", response);
                                process.reject();
                            }
                        });
                    };
                    form = new _toolFormBase2.default(step);
                    if (step.post_job_actions && step.post_job_actions.length) {
                        form.portlet.append($("<div/>").addClass("ui-form-element-disabled").append($("<div/>").addClass("ui-form-title").html("<b>Job Post Actions</b>")).append($("<div/>").addClass("ui-form-preview").html(_.reduce(step.post_job_actions, function(memo, value) {
                            return memo + " " + value.short_str;
                        }, ""))));
                    }
                } else {
                    var is_simple_input = ["data_input", "data_collection_input"].indexOf(step.step_type) != -1;
                    _.each(step.inputs, function(input) {
                        input.flavor = "module";
                        input.hide_label = is_simple_input;
                    });
                    form = new _formView2.default(_utils2.default.merge({
                        title: step.fixed_title,
                        onchange: function onchange() {
                            _.each(self.links[step.index], function(link) {
                                self._refreshStep(link);
                            });
                        },
                        inputs: step.inputs && step.inputs.length > 0 ? step.inputs : [{
                            type: "hidden",
                            name: "No options available.",
                            ignore: null
                        }]
                    }, step));
                }
                self.forms[step.index] = form;
                self._append(self.$steps, form.$el);
                self._refresh();
                step.needs_refresh && self._refreshStep(step);
                form.portlet[!self.show_progress ? "enable" : "disable"]();
                self.show_progress && self.execute_btn.model.set({
                    wait: true,
                    wait_text: "Preparing...",
                    percentage: (step.index + 1) * 100.0 / self.steps.length
                });
                Galaxy.emit.debug("tool-form-composite::initialize()", step.index + " : Workflow step state ready.", step);
                setTimeout(function() {
                    promise.resolve();
                }, 0);
            });
        },

        /** Refreshes step values from source step values */
        _refreshStep: function _refreshStep(step) {
            var self = this;
            var form = this.forms[step.index];
            if (form) {
                _.each(self.parms[step.index], function(input, name) {
                    if (input.step_linked || input.wp_linked) {
                        var field = form.field_list[form.data.match(name)];
                        if (field) {
                            var new_value = undefined;
                            if (input.step_linked) {
                                new_value = {
                                    values: []
                                };
                                _.each(input.step_linked, function(source_step) {
                                    if (self._isDataStep(source_step)) {
                                        var value = self.forms[source_step.index].data.create().input;
                                        value && _.each(value.values, function(v) {
                                            new_value.values.push(v);
                                        });
                                    }
                                });
                                if (!input.multiple && new_value.values.length > 0) {
                                    new_value = {
                                        values: [new_value.values[0]]
                                    };
                                }
                            } else if (input.wp_linked) {
                                new_value = input.value;
                                var re = /\$\{(.+?)\}/g;
                                var match;
                                while (match = re.exec(input.value)) {
                                    var wp_field = self.wp_form.field_list[self.wp_form.data.match(match[1])];
                                    var wp_value = wp_field && wp_field.value();
                                    if (wp_value) {
                                        new_value = new_value.split(match[0]).join(wp_value);
                                    }
                                }
                            }
                            if (new_value !== undefined) {
                                field.value(new_value);
                            }
                        }
                    }
                });
                form.trigger("change");
            } else {
                step.needs_refresh = true;
            }
        },

        /** Refresh the history after job submission while form is shown */
        _refreshHistory: function _refreshHistory() {
            var self = this;
            var history = parent.Galaxy && parent.Galaxy.currHistoryPanel && parent.Galaxy.currHistoryPanel.model;
            this._refresh_history && clearTimeout(this._refresh_history);
            if (history) {
                history.refresh().success(function() {
                    if (history.numOfUnfinishedShownContents() === 0) {
                        self._refresh_history = setTimeout(function() {
                            self._refreshHistory();
                        }, history.UPDATE_DELAY);
                    }
                });
            }
        },

        /** Build remaining steps */
        _execute: function _execute() {
            var self = this;
            this.show_progress = true;
            this._enabled(false);
            this.deferred.execute(function(promise) {
                setTimeout(function() {
                    promise.resolve();
                    self._submit();
                }, 0);
            });
        },

        /** Validate and submit workflow */
        _submit: function _submit() {
            var self = this;
            var history_form_data = this.history_form.data.create();
            var job_def = {
                new_history_name: history_form_data["new_history|name"] ? history_form_data["new_history|name"] : null,
                history_id: !history_form_data["new_history|name"] ? this.model.get("history_id") : null,
                resource_params: this.workflow_resource_parameters_form ? this.workflow_resource_parameters_form.data.create() : {},
                replacement_params: this.wp_form ? this.wp_form.data.create() : {},
                parameters: {},
                // Tool form will submit flat maps for each parameter
                // (e.g. "repeat_0|cond|param": "foo" instead of nested
                // data structures).
                parameters_normalized: true,
                // Tool form always wants a list of invocations back
                // so that inputs can be batched.
                batch: true
            };
            var validated = true;
            for (var i in this.forms) {
                var form = this.forms[i];
                var job_inputs = form.data.create();
                var step = self.steps[i];
                var step_index = step.step_index;
                form.trigger("reset");
                for (var job_input_id in job_inputs) {
                    var input_value = job_inputs[job_input_id];
                    var input_id = form.data.match(job_input_id);
                    var input_field = form.field_list[input_id];
                    var input_def = form.input_list[input_id];
                    if (!input_def.step_linked) {
                        if (this._isDataStep(step)) {
                            validated = input_value && input_value.values && input_value.values.length > 0;
                        } else {
                            validated = input_def.optional || input_def.is_workflow && input_value !== "" || !input_def.is_workflow && input_value !== null;
                        }
                        if (!validated) {
                            form.highlight(input_id);
                            break;
                        }
                        job_def.parameters[step_index] = job_def.parameters[step_index] || {};
                        job_def.parameters[step_index][job_input_id] = job_inputs[job_input_id];
                    }
                }
                if (!validated) {
                    break;
                }
            }
            if (!validated) {
                self._enabled(true);
                Galaxy.emit.debug("tool-form-composite::submit()", "Validation failed.", job_def);
            } else {
                Galaxy.emit.debug("tool-form-composite::submit()", "Validation complete.", job_def);
                _utils2.default.request({
                    type: "POST",
                    url: Galaxy.root + "api/workflows/" + this.model.id + "/invocations",
                    data: job_def,
                    success: function success(response) {
                        Galaxy.emit.debug("tool-form-composite::submit", "Submission successful.", response);
                        self.$el.children().hide();
                        self.$el.append(self._templateSuccess(response));

                        // Show Webhook if job is running
                        if ($.isArray(response) && response.length > 0) {
                            self.$el.append($("<div/>", {
                                id: "webhook-view"
                            }));
                            var WebhookApp = new _webhooks2.default.WebhookView({
                                urlRoot: Galaxy.root + "api/webhooks/workflow",
                                toolId: job_def.tool_id,
                                toolVersion: job_def.tool_version
                            });
                        }

                        self._refreshHistory();
                    },
                    error: function error(response) {
                        Galaxy.emit.debug("tool-form-composite::submit", "Submission failed.", response);
                        var input_found = false;
                        if (response && response.err_data) {
                            for (var i in self.forms) {
                                var form = self.forms[i];
                                var step_related_errors = response.err_data[form.model.get("step_index")];
                                if (step_related_errors) {
                                    var error_messages = form.data.matchResponse(step_related_errors);
                                    for (var input_id in error_messages) {
                                        form.highlight(input_id, error_messages[input_id]);
                                        input_found = true;
                                        break;
                                    }
                                }
                            }
                        }
                        if (!input_found) {
                            self.modal.show({
                                title: (0, _localization2.default)("Workflow submission failed"),
                                body: self._templateError(job_def, response && response.err_msg),
                                buttons: {
                                    Close: function Close() {
                                        self.modal.hide();
                                    }
                                }
                            });
                        }
                    },
                    complete: function complete() {
                        self._enabled(true);
                    }
                });
            }
        },

        /** Append new dom to body */
        _append: function _append($container, $el) {
            $container.append("<p/>").append($el);
        },

        /** Set enabled/disabled state */
        _enabled: function _enabled(enabled) {
            this.execute_btn.model.set({
                wait: !enabled,
                wait_text: "Sending...",
                percentage: -1
            });
            this.wp_form && this.wp_form.portlet[enabled ? "enable" : "disable"]();
            this.history_form && this.history_form.portlet[enabled ? "enable" : "disable"]();
            _.each(this.forms, function(form) {
                form && form.portlet[enabled ? "enable" : "disable"]();
            });
        },

        /** Is data input module/step */
        _isDataStep: function _isDataStep(steps) {
            var lst = $.isArray(steps) ? steps : [steps];
            for (var i = 0; i < lst.length; i++) {
                var step = lst[i];
                if (!step || !step.step_type || !step.step_type.startsWith("data")) {
                    return false;
                }
            }
            return true;
        },

        /** Templates */
        _templateSuccess: function _templateSuccess(response) {
            if ($.isArray(response) && response.length > 0) {
                return $("<div/>").addClass("donemessagelarge").append($("<p/>").html("Successfully invoked workflow <b>" + _utils2.default.sanitize(this.model.get("name")) + "</b>" + (response.length > 1 ? " <b>" + response.length + " times</b>" : "") + ".")).append($("<p/>").append("<b/>").text("You can check the status of queued jobs and view the resulting data by refreshing the History pane. When the job has been run the status will change from 'running' to 'finished' if completed successfully or 'error' if problems were encountered."));
            } else {
                return this._templateError(response, "Invalid success response. No invocations found.");
            }
        },

        _templateError: function _templateError(response, err_msg) {
            return $("<div/>").addClass("errormessagelarge").append($("<p/>").text("The server could not complete the request. Please contact the Galaxy Team if this error persists. " + (JSON.stringify(err_msg) || ""))).append($("<pre/>").text(JSON.stringify(response, null, 4)));
        }
    });
    /** This is the run workflow tool form view. */
    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/tool/tool-form-composite.js.map
