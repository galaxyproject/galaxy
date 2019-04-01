/** This is the run workflow tool form view. */
import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import Utils from "utils/utils";
import Deferred from "utils/deferred";
import Ui from "mvc/ui/ui-misc";
import Form from "mvc/form/form-view";
import FormData from "mvc/form/form-data";
import ToolFormBase from "mvc/tool/tool-form-base";
import Modal from "mvc/ui/ui-modal";
import Webhooks from "mvc/webhooks";
import WorkflowIcons from "mvc/workflow/workflow-icons";

var View = Backbone.View.extend({
    initialize: function(options) {
        let Galaxy = getGalaxyInstance();
        this.modal = Galaxy.modal || new Modal.View();
        this.model = (options && options.model) || new Backbone.Model(options);
        this.deferred = new Deferred();
        if (options && options.active_tab) {
            this.active_tab = options.active_tab;
        }
        this.setElement(
            $("<div/>")
                .addClass("ui-form-composite")
                .append((this.$message = $("<div/>").addClass("mb-4")))
                .append((this.$header = $("<div/>")))
                .append((this.$steps = $("<div/>")))
        );
        $("body").append(this.$el);
        this._configure();
        this.render();
    },

    /** Configures form/step options for each workflow step */
    _configure: function() {
        var self = this;
        let Galaxy = getGalaxyInstance();
        this.forms = [];
        this.steps = [];
        this.links = [];
        this.parms = [];
        _.each(this.model.get("steps"), (step, i) => {
            Galaxy.emit.debug("tool-form-composite::initialize()", `${i} : Preparing workflow step.`);
            var icon = WorkflowIcons[step.step_type];
            var title = `${parseInt(i + 1)}: ${step.step_label || step.step_name}`;
            if (step.annotation) {
                title += ` - ${step.annotation}`;
            }
            if (step.step_version) {
                title += ` (Galaxy Version ${step.step_version})`;
            }
            step = Utils.merge(
                {
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
                    cls: "ui-portlet-section",
                    hide_operations: true,
                    needs_refresh: false,
                    always_refresh: step.step_type != "tool"
                },
                step
            );
            self.steps[i] = step;
            self.links[i] = [];
            self.parms[i] = {};
        });

        // build linear index of step input pairs
        _.each(this.steps, (step, i) => {
            FormData.visitInputs(step.inputs, (input, name) => {
                self.parms[i][name] = input;
            });
        });

        // iterate through data input modules and collect linked sub steps
        _.each(this.steps, (step, i) => {
            _.each(step.output_connections, output_connection => {
                _.each(self.steps, (sub_step, j) => {
                    if (sub_step.step_index === output_connection.input_step_index) {
                        self.links[i].push(sub_step);
                    }
                });
            });
        });

        // convert all connected data inputs to hidden fields with proper labels,
        // and track the linked source step
        _.each(this.steps, (step, i) => {
            _.each(self.steps, (sub_step, j) => {
                var connections_by_name = {};
                _.each(step.output_connections, connection => {
                    if (sub_step.step_index === connection.input_step_index) {
                        connections_by_name[connection.input_name] = connection;
                    }
                });
                _.each(self.parms[j], (input, name) => {
                    var connection = connections_by_name[name];
                    if (connection) {
                        input.type = "hidden";
                        input.help = input.step_linked ? `${input.help}, ` : "";
                        input.help += `Output dataset '${connection.output_name}' from step ${parseInt(i) + 1}`;
                        input.step_linked = input.step_linked || [];
                        input.step_linked.push({ index: step.index, step_type: step.step_type });
                    }
                });
            });
        });

        // identify and configure workflow parameters
        var wp_count = 0;
        this.wp_inputs = {};

        function _ensureWorkflowParameter(wp_name) {
            return (self.wp_inputs[wp_name] = self.wp_inputs[wp_name] || {
                label: wp_name,
                name: wp_name,
                type: "text",
                color: `hsl( ${++wp_count * 100}, 70%, 30% )`,
                style: "ui-form-wp-source",
                links: []
            });
        }

        function _handleWorkflowParameter(value, callback) {
            var re = /\$\{(.+?)\}/g;
            var match;
            while ((match = re.exec(String(value)))) {
                var wp_name = match[1];
                callback(_ensureWorkflowParameter(wp_name));
            }
        }
        _.each(this.steps, (step, i) => {
            _.each(self.parms[i], (input, name) => {
                _handleWorkflowParameter(input.value, wp_input => {
                    wp_input.links.push(step);
                    input.wp_linked = true;
                    input.type = "text";
                    input.backdrop = true;
                    input.style = "ui-form-wp-target";
                });
            });
            _.each(step.replacement_parameters, wp_name => {
                _ensureWorkflowParameter(wp_name);
            });
        });

        // select fields are shown for dynamic fields if all putative data inputs are available,
        // or if an explicit reference is specified as data_ref and available
        _.each(this.steps, (step, i) => {
            if (step.step_type == "tool") {
                var data_resolved = true;
                FormData.visitInputs(step.inputs, (input, name, context) => {
                    var is_runtime_value = input.value && input.value.__class__ == "RuntimeValue";
                    var is_data_input = ["data", "data_collection"].indexOf(input.type) != -1;
                    var data_ref = context[input.data_ref];
                    if (input.step_linked && !self._isDataStep(input.step_linked)) {
                        data_resolved = false;
                    }
                    if (input.options && ((input.options.length == 0 && !data_resolved) || input.wp_linked)) {
                        input.is_workflow = true;
                    }
                    if (data_ref) {
                        input.is_workflow =
                            (data_ref.step_linked && !self._isDataStep(data_ref.step_linked)) || input.wp_linked;
                    }
                    if (
                        is_data_input ||
                        (input.value && input.value.__class__ == "RuntimeValue" && !input.step_linked)
                    ) {
                        step.collapsed = false;
                    }
                    if (is_runtime_value) {
                        input.value = null;
                    }
                    input.flavor = "workflow";
                    if (!is_runtime_value && !is_data_input && input.type !== "hidden" && !input.wp_linked) {
                        if (input.optional || (!Utils.isEmpty(input.value) && input.value !== "")) {
                            input.collapsible_value = input.value;
                            input.collapsible_preview = true;
                        }
                    }
                });
            }
        });
    },

    render: function() {
        var self = this;
        this.deferred.reset();
        this._renderHeader();
        this._renderMessage();
        this._renderParameters();
        this._renderHistory();
        this._renderUseCachedJob();
        this._renderResourceParameters();
        _.each(this.steps, step => {
            self._renderStep(step);
        });
    },

    /** Render header */
    _renderHeader: function() {
        var self = this;
        this.execute_btn = new Ui.Button({
            icon: "fa-check",
            title: _l("Run workflow"),
            cls: "btn btn-primary",
            onclick: function() {
                self._execute();
            }
        });
        this.$header
            .addClass("h4")
            .empty()
            .append(`<b>Workflow: ${this.model.get("name")}<b>`)
            .append(this.execute_btn.$el.addClass("float-right mt-3"));
    },

    /** Render message */
    _renderMessage: function() {
        this.$message.empty();
        if (this.model.get("has_upgrade_messages")) {
            this.$message.append(
                new Ui.Message({
                    message:
                        "Some tools in this workflow may have changed since it was last saved or some errors were found. The workflow may still run, but any new options will have default values. Please review the messages below to make a decision about whether the changes will affect your analysis.",
                    status: "warning",
                    persistent: true,
                    fade: false
                }).$el
            );
        }
        var step_version_changes = this.model.get("step_version_changes");
        if (step_version_changes && step_version_changes.length > 0) {
            this.$message.append(
                new Ui.Message({
                    message:
                        "Some tools are being executed with different versions compared to those available when this workflow was last saved because the other versions are not or no longer available on this Galaxy instance. To upgrade your workflow and dismiss this message simply edit the workflow and re-save it.",
                    status: "warning",
                    persistent: true,
                    fade: false
                }).$el
            );
        }
    },

    /** Render workflow parameters */
    _renderParameters: function() {
        var self = this;
        this.wp_form = null;
        if (!_.isEmpty(this.wp_inputs)) {
            this.wp_form = new Form({
                title: "<b>Workflow Parameters</b>",
                inputs: this.wp_inputs,
                cls: "ui-portlet-section",
                onchange: function() {
                    _.each(self.wp_form.input_list, (input_def, i) => {
                        _.each(input_def.links, step => {
                            self._refreshStep(step);
                        });
                    });
                }
            });
            this._append(this.$steps.empty(), this.wp_form.$el);
        }
    },

    /** Render workflow parameters */
    _renderHistory: function() {
        this.history_form = new Form({
            cls: "ui-portlet-section",
            title: "<b>History Options</b>",
            inputs: [
                {
                    type: "conditional",
                    name: "new_history",
                    test_param: {
                        name: "check",
                        label: "Send results to a new history",
                        type: "boolean",
                        value: "false",
                        help: ""
                    },
                    cases: [
                        {
                            value: "true",
                            inputs: [
                                {
                                    name: "name",
                                    label: "History name",
                                    type: "text",
                                    value: this.model.get("name")
                                }
                            ]
                        }
                    ]
                }
            ]
        });
        this._append(this.$steps, this.history_form.$el);
    },

    /** Render Workflow Options */
    _renderResourceParameters: function() {
        this.workflow_resource_parameters_form = null;
        if (!_.isEmpty(this.model.get("workflow_resource_parameters"))) {
            this.workflow_resource_parameters_form = new Form({
                cls: "ui-portlet-section",
                title: "<b>Workflow Resource Options</b>",
                inputs: this.model.get("workflow_resource_parameters")
            });
            this._append(this.$steps, this.workflow_resource_parameters_form.$el);
        }
    },

    /** Render job caching option */
    _renderUseCachedJob: function() {
        let Galaxy = getGalaxyInstance();
        var extra_user_preferences = {};
        if (Galaxy.user.attributes.preferences && "extra_user_preferences" in Galaxy.user.attributes.preferences) {
            extra_user_preferences = JSON.parse(Galaxy.user.attributes.preferences.extra_user_preferences);
        }
        var display_use_cached_job_checkbox =
            "use_cached_job|use_cached_job_checkbox" in extra_user_preferences
                ? extra_user_preferences["use_cached_job|use_cached_job_checkbox"]
                : false;
        this.display_use_cached_job_checkbox = display_use_cached_job_checkbox === "true";
        if (this.display_use_cached_job_checkbox) {
            this.job_options_form = new Form({
                cls: "ui-portlet-section",
                title: "<b>Job re-use Options</b>",
                inputs: [
                    {
                        type: "conditional",
                        name: "use_cached_job",
                        test_param: {
                            name: "check",
                            label: "BETA: Attempt to reuse jobs with identical parameters?",
                            type: "boolean",
                            value: "false",
                            help: "This may skip executing jobs that you have already run."
                        }
                    }
                ]
            });
            this._append(this.$steps, this.job_options_form.$el);
        }
    },

    /** Render step */
    _renderStep: function(step) {
        let Galaxy = getGalaxyInstance();
        var self = this;
        var form = null;
        this.deferred.execute(promise => {
            self.$steps.addClass("ui-steps");
            if (step.step_type == "tool") {
                step.postchange = function(process, form) {
                    var current_state = {
                        tool_id: step.id,
                        tool_version: step.version,
                        inputs: $.extend(true, {}, form.data.create())
                    };
                    form.wait(true);
                    Galaxy.emit.debug("tool-form-composite::postchange()", "Sending current state.", current_state);
                    Utils.request({
                        type: "POST",
                        url: `${getAppRoot()}api/tools/${step.id}/build`,
                        data: current_state,
                        success: function(data) {
                            form.update(data);
                            form.wait(false);
                            Galaxy.emit.debug("tool-form-composite::postchange()", "Received new model.", data);
                            process.resolve();
                        },
                        error: function(response) {
                            Galaxy.emit.debug("tool-form-composite::postchange()", "Refresh request failed.", response);
                            process.reject();
                        }
                    });
                };
                form = new ToolFormBase(step);
                if (step.post_job_actions && step.post_job_actions.length) {
                    form.portlet.append(
                        $("<div/>")
                            .addClass("ui-form-element-disabled")
                            .append(
                                $("<div/>")
                                    .addClass("ui-form-title")
                                    .html("<b>Job Post Actions</b>")
                            )
                            .append(
                                $("<div/>")
                                    .addClass("ui-form-preview")
                                    .html(
                                        _.reduce(
                                            step.post_job_actions,
                                            (memo, value) => `${memo} ${value.short_str}`,
                                            ""
                                        )
                                    )
                            )
                    );
                }
            } else {
                var is_simple_input = ["data_input", "data_collection_input"].indexOf(step.step_type) != -1;
                _.each(step.inputs, input => {
                    input.flavor = "module";
                    input.hide_label = is_simple_input;
                });
                form = new Form(
                    Utils.merge(
                        {
                            title: step.fixed_title,
                            onchange: function() {
                                _.each(self.links[step.index], link => {
                                    self._refreshStep(link);
                                });
                            },
                            inputs:
                                step.inputs && step.inputs.length > 0
                                    ? step.inputs
                                    : [
                                          {
                                              type: "hidden",
                                              name: "No options available.",
                                              ignore: null
                                          }
                                      ]
                        },
                        step
                    )
                );
                if (step.step_label) {
                    form.$el.attr("step-label", step.step_label);
                }
            }
            self.forms[step.index] = form;
            self._append(self.$steps, form.$el);
            if (step.needs_refresh) {
                self._refreshStep(step);
            }
            form.portlet[!self.show_progress ? "enable" : "disable"]();
            if (self.show_progress) {
                self.execute_btn.model.set({
                    wait: true,
                    wait_text: "Preparing...",
                    percentage: ((step.index + 1) * 100.0) / self.steps.length
                });
            }
            Galaxy.emit.debug("tool-form-composite::initialize()", `${step.index} : Workflow step state ready.`, step);
            window.setTimeout(() => {
                promise.resolve();
            }, 0);
        });
    },

    /** Refreshes step values from source step values */
    _refreshStep: function(step) {
        var self = this;
        var form = this.forms[step.index];
        if (form) {
            _.each(self.parms[step.index], (input, name) => {
                if (input.step_linked || input.wp_linked) {
                    var field = form.field_list[form.data.match(name)];
                    if (field) {
                        var new_value;
                        if (input.step_linked) {
                            new_value = { values: [] };
                            _.each(input.step_linked, source_step => {
                                if (self._isDataStep(source_step)) {
                                    var value = self.forms[source_step.index].data.create().input;
                                    if (value) {
                                        _.each(value.values, v => {
                                            new_value.values.push(v);
                                        });
                                    }
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
                            while ((match = re.exec(input.value))) {
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
    _refreshHistory: function() {
        let Galaxy = getGalaxyInstance();
        var self = this;
        var history = Galaxy && Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model;
        if (this._refresh_history) {
            window.clearTimeout(this._refresh_history);
        }
        if (history) {
            history.refresh().success(() => {
                if (history.numOfUnfinishedShownContents() === 0) {
                    self._refresh_history = window.setTimeout(() => {
                        self._refreshHistory();
                    }, history.UPDATE_DELAY);
                }
            });
        }
    },

    /** Build remaining steps */
    _execute: function() {
        var self = this;
        this.show_progress = true;
        this._enabled(false);
        this.deferred.execute(promise => {
            window.setTimeout(() => {
                promise.resolve();
                self._submit();
            }, 0);
        });
    },

    /** Validate and submit workflow */
    _submit: function() {
        let Galaxy = getGalaxyInstance();
        var self = this;
        var history_form_data = this.history_form.data.create();
        var job_def = {
            new_history_name: history_form_data["new_history|name"] ? history_form_data["new_history|name"] : null,
            history_id: !history_form_data["new_history|name"] ? this.model.get("history_id") : null,
            resource_params: this.workflow_resource_parameters_form
                ? this.workflow_resource_parameters_form.data.create()
                : {},
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
        if (this.display_use_cached_job_checkbox) {
            job_def.use_cached_job = this.job_options_form.data.create()["use_cached_job|check"] === "true";
        }
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
                var input_def = form.input_list[input_id];
                if (!input_def.step_linked) {
                    if (this._isDataStep(step)) {
                        validated = input_value && input_value.values && input_value.values.length > 0;
                    } else {
                        validated =
                            input_def.optional ||
                            (input_def.is_workflow && input_value !== "") ||
                            (!input_def.is_workflow && input_value !== null);
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
            Utils.request({
                type: "POST",
                url: `${getAppRoot()}api/workflows/${this.model.id}/invocations`,
                data: job_def,
                success: function(response) {
                    Galaxy.emit.debug("tool-form-composite::submit", "Submission successful.", response);
                    self.$el.children().hide();
                    self.$el.append(self._templateSuccess(response));

                    // Show Webhook if job is running
                    if ($.isArray(response) && response.length > 0) {
                        self.$el.append($("<div/>", { id: "webhook-view" }));
                        new Webhooks.WebhookView({
                            type: "workflow",
                            toolId: job_def.tool_id,
                            toolVersion: job_def.tool_version
                        });
                    }

                    self._refreshHistory();
                },
                error: function(response) {
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
                            title: _l("Workflow submission failed"),
                            body: self._templateError(job_def, response && response.err_msg),
                            buttons: {
                                Close: function() {
                                    self.modal.hide();
                                }
                            }
                        });
                    }
                },
                complete: function() {
                    self._enabled(true);
                }
            });
        }
    },

    /** Append new dom to body */
    _append: function($container, $el) {
        $container.append("<p/>").append($el);
    },

    /** Set enabled/disabled state */
    _enabled: function(enabled) {
        this.execute_btn.model.set({
            wait: !enabled,
            wait_text: "Sending...",
            percentage: -1
        });
        if (this.wp_form) {
            this.wp_form.portlet[enabled ? "enable" : "disable"]();
        }
        if (this.history_form) {
            this.history_form.portlet[enabled ? "enable" : "disable"]();
        }
        _.each(this.forms, form => {
            if (form) {
                form.portlet[enabled ? "enable" : "disable"]();
            }
        });
    },

    /** Is data input module/step */
    _isDataStep: function(steps) {
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
    _templateSuccess: function(response) {
        let Galaxy = getGalaxyInstance();
        if ($.isArray(response) && response.length > 0) {
            let timesExecuted = "";
            // Default destination blurb, used for a single execution, same history.
            let destinationBlurb =
                "You can check the status of queued jobs and view the resulting data by refreshing the History pane, if this has not already happened automatically.";
            let newHistoryTarget =
                (response[0].history_id &&
                    Galaxy.currHistoryPanel &&
                    Galaxy.currHistoryPanel.model.id != response[0].history_id) ||
                false;
            if (response.length > 1) {
                // Executed more than one time, build blurb but skip history link.
                timesExecuted = `<em> - ${response.length} times</em>`;
                if (newHistoryTarget) {
                    destinationBlurb = `This workflow will generate results in multiple histories.  You can observe progress in the <a href="${getAppRoot()}history/view_multiple">history multi-view</a>.`;
                }
            } else if (newHistoryTarget) {
                // Single execution, with a destination other than the
                // current history.  Present a link.
                destinationBlurb = `This workflow will generate results in a new history. <a href="${getAppRoot()}history/switch_to_history?hist_id=${
                    response[0].history_id
                }">Switch to that history now</a>.`;
            }
            return $(`
                <div class="donemessagelarge">
                    <p>
                        Successfully invoked workflow <b>${Utils.sanitize(this.model.get("name"))}</b>${timesExecuted}.
                    </p>
                    <p>
                        ${destinationBlurb}
                    </p>
                </div>`);
        } else {
            return this._templateError(response, "Invalid success response. No invocations found.");
        }
    },

    _templateError: function(response, err_msg) {
        return $("<div/>")
            .addClass("errormessagelarge")
            .append(
                $("<p/>").text(
                    `The server could not complete the request. Please contact the Galaxy Team if this error persists. ${JSON.stringify(
                        err_msg
                    ) || ""}`
                )
            )
            .append($("<pre/>").text(JSON.stringify(response, null, 4)));
    }
});
export default {
    View: View
};
