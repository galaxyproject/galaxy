/* This is the regular tool form */

import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import Utils from "utils/utils";
import Ui from "mvc/ui/ui-misc";
import Modal from "mvc/ui/ui-modal";
import ToolFormBase from "mvc/tool/tool-form-base";
import Webhooks from "mvc/webhooks";
import Vue from "vue";
import ToolEntryPoints from "components/ToolEntryPoints/ToolEntryPoints";
import ToolRecommendation from "components/ToolRecommendation";
import { Toast } from "ui/toast";

const View = Backbone.View.extend({
    initialize: function (options) {
        const Galaxy = getGalaxyInstance();
        this.modal = Galaxy.modal || new Modal.View();
        this.form = new ToolFormBase(
            Utils.merge(
                {
                    listen_to_history: true,
                    always_refresh: false,
                    buildmodel: (process, form) => {
                        const options = form.model.attributes;

                        // build request url
                        let build_url = "";
                        let build_data = {};
                        const job_id = options.job_id;
                        if (job_id) {
                            build_url = `${getAppRoot()}api/jobs/${job_id}/build_for_rerun`;
                        } else {
                            build_url = `${getAppRoot()}api/tools/${options.id}/build`;
                            build_data = $.extend({}, Galaxy.params);
                            build_data["tool_id"] && delete build_data["tool_id"];
                        }
                        options.version && (build_data["tool_version"] = options.version);

                        // get initial model
                        Utils.get({
                            url: build_url,
                            data: build_data,
                            success: (data) => {
                                if (!data.display) {
                                    window.location = getAppRoot();
                                    return;
                                }

                                const user_version = options.id.replace(/.*\//, "");
                                if (!data.versions.includes(user_version)) {
                                    Toast.error(
                                        `Specified version is not found! Using ${data.version} instead`,
                                        "Error",
                                        {
                                            closeButton: true,
                                            timeOut: 10000,
                                            tapToDismiss: false,
                                        }
                                    );
                                }

                                form.model.set(data);
                                this._customize(form);
                                Galaxy.emit.debug("tool-form-base::_buildModel()", "Initial tool model ready.", data);
                                process.resolve();
                            },
                            error: (response, status) => {
                                const error_message = (response && response.err_msg) || "Uncaught error.";
                                if (status == 401) {
                                    window.location = `${getAppRoot()}user/login?${$.param({
                                        redirect: `${getAppRoot()}?tool_id=${options.id}`,
                                    })}`;
                                } else if (form.$el.is(":empty")) {
                                    form.$el.prepend(
                                        new Ui.Message({
                                            message: error_message,
                                            status: "danger",
                                            persistent: true,
                                        }).$el
                                    );
                                } else {
                                    Galaxy.modal &&
                                        Galaxy.modal.show({
                                            title: _l("Tool request failed"),
                                            body: error_message,
                                            buttons: {
                                                Close: () => {
                                                    Galaxy.modal.hide();
                                                },
                                            },
                                        });
                                }
                                Galaxy.emit.debug(
                                    "tool-form-base::_buildModel()",
                                    "Initial tool model request failed.",
                                    response
                                );
                                process.reject();
                            },
                        });
                    },
                    postchange: (process, form) => {
                        const current_state = {
                            tool_id: form.model.get("id"),
                            tool_version: form.model.get("version"),
                            inputs: $.extend(true, {}, form.data.create()),
                        };
                        form.wait(true);
                        Galaxy.emit.debug("tool-form::postchange()", "Sending current state.", current_state);
                        Utils.request({
                            type: "POST",
                            url: `${getAppRoot()}api/tools/${form.model.get("id")}/build`,
                            data: current_state,
                            success: (data) => {
                                form.update(data);
                                form.wait(false);
                                Galaxy.emit.debug("tool-form::postchange()", "Received new model.", data);
                                process.resolve();
                            },
                            error: (response) => {
                                Galaxy.emit.debug("tool-form::postchange()", "Refresh request failed.", response);
                                process.reject();
                            },
                        });
                    },
                },
                options
            )
        );
        this.deferred = this.form.deferred;
        this.setElement("<div/>");
        this.$el.append(this.form.$el);
    },

    _customize: function (form) {
        const Galaxy = getGalaxyInstance();
        const options = form.model.attributes;
        var inputs = options.inputs;
        /* only append notification interface if
           Galaxy has the server mail configured
        */
        if (Galaxy.config.server_mail_configured && !Galaxy.user.isAnonymous()) {
            inputs.push({
                name: `send_email_notification`,
                label: _l("Email notification"),
                type: "boolean",
                value: "false",
                ignore: "false",
                help: _l("Send an email notification when the job completes."),
            });
        }

        // build execute button
        const execute_button = new Ui.Button({
            icon: "fa-check",
            tooltip: `Execute: ${options.name} (${options.version})`,
            title: _l("Execute"),
            cls: "btn btn-primary",
            wait_cls: "btn btn-info",
            onclick: () => {
                execute_button.wait();
                form.portlet.disable();
                this.submit(options, () => {
                    execute_button.unwait();
                    form.portlet.enable();
                });
            },
        });
        options.buttons = { execute: execute_button };

        // remap feature
        if (options.job_id && options.job_remap) {
            let label;
            let help;
            if (options.job_remap === "job_produced_collection_elements") {
                label = "Replace elements in collection ?";
                help =
                    "The previous run of this tool failed. Use this option to replace the failed element(s) in the dataset collection that were produced during the previous tool run.";
            } else {
                label = "Resume dependencies from this job ?";
                help =
                    "The previous run of this tool failed and other tools were waiting for it to finish successfully. Use this option to resume those tools using the new output(s) of this tool run.";
            }
            options.inputs.push({
                label: label,
                name: "rerun_remap_job_id",
                type: "select",
                display: "radio",
                ignore: "__ignore__",
                value: "__ignore__",
                options: [
                    ["Yes", options.job_id],
                    ["No", "__ignore__"],
                ],
                help: help,
            });
        }

        // Job Re-use Options
        let extra_user_preferences = {};
        if (Galaxy.user.attributes.preferences && "extra_user_preferences" in Galaxy.user.attributes.preferences) {
            extra_user_preferences = JSON.parse(Galaxy.user.attributes.preferences.extra_user_preferences);
        }
        const use_cached_job =
            "use_cached_job|use_cached_job_checkbox" in extra_user_preferences
                ? extra_user_preferences["use_cached_job|use_cached_job_checkbox"]
                : false;
        if (use_cached_job === "true") {
            options.inputs.push({
                label: "BETA: Attempt to re-use jobs with identical parameters ?",
                help: "This may skip executing jobs that you have already run",
                name: "use_cached_job",
                type: "select",
                display: "radio",
                ignore: "__ignore__",
                value: "__ignore__",
                options: [
                    ["No", false],
                    ["Yes", true],
                ],
            });
        }
    },

    /** Submit a regular job.
     * @param{dict}     options   - Specifies tool id and version
     * @param{function} callback  - Called when request has completed
     */
    submit: function (options, callback) {
        const Galaxy = getGalaxyInstance();
        const history_id = Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model.id;
        const job_def = {
            history_id: history_id,
            tool_id: options.id,
            tool_version: options.version,
            inputs: this.form.data.create(),
        };
        this.form.trigger("reset");
        if (!this.validate(job_def)) {
            Galaxy.emit.debug("tool-form::submit()", "Submission canceled. Validation failed.");
            callback && callback();
            return;
        }
        if (options.action !== `${getAppRoot()}tool_runner/index`) {
            const $f = $("<form/>").attr({
                action: options.action,
                method: options.method,
                enctype: options.enctype,
            });
            _.each(job_def.inputs, (value, key) => {
                $f.append($("<input/>").attr({ name: key, value: value }));
            });
            $f.hide().appendTo("body").submit().remove();
            callback && callback();
            return;
        }
        Galaxy.emit.debug("tool-form::submit()", "Validation complete.", job_def);
        Utils.request({
            type: "POST",
            url: `${getAppRoot()}api/tools`,
            data: job_def,
            success: (response) => {
                callback && callback();
                this.$el.children().hide();
                if (response.produces_entry_points) {
                    for (const job of response.jobs) {
                        const toolEntryPointsInstance = Vue.extend(ToolEntryPoints);
                        const vm = document.createElement("div");
                        this.$el.append(vm);
                        const instance = new toolEntryPointsInstance({
                            propsData: {
                                jobId: job.id,
                            },
                        });
                        instance.$mount(vm);
                    }
                }
                this.$el.append(this._templateSuccess(response, job_def));
                const enable_tool_recommendations = Galaxy.config.enable_tool_recommendations;
                if (enable_tool_recommendations === true || enable_tool_recommendations === "true") {
                    // show tool recommendations
                    const ToolRecommendationInstance = Vue.extend(ToolRecommendation);
                    const vm = document.createElement("div");
                    this.$el.append(vm);
                    const instance = new ToolRecommendationInstance({
                        propsData: {
                            toolId: job_def.tool_id,
                        },
                    });
                    instance.$mount(vm);
                }
                this.$el.parent().scrollTop(0);
                // Show Webhook if job is running
                if (response.jobs && response.jobs.length > 0) {
                    this.$el.append($("<div/>", { id: "webhook-view" }));
                    new Webhooks.WebhookView({
                        type: "tool",
                        toolId: job_def.tool_id,
                    });
                }
                if (Galaxy.currHistoryPanel) {
                    this.form.stopListening(Galaxy.currHistoryPanel.collection);
                    Galaxy.currHistoryPanel.refreshContents();
                }
            },
            error: (response) => {
                callback && callback();
                Galaxy.emit.debug("tool-form::submit", "Submission failed.", response);
                let input_found = false;
                if (response && response.err_data) {
                    const error_messages = this.form.data.matchResponse(response.err_data);
                    for (const input_id in error_messages) {
                        this.form.highlight(input_id, error_messages[input_id]);
                        input_found = true;
                        break;
                    }
                }
                if (!input_found) {
                    this.modal.show({
                        title: _l("Job submission failed"),
                        body: this._templateError(job_def, response && response.err_msg),
                        buttons: {
                            Close: () => {
                                this.modal.hide();
                            },
                        },
                    });
                }
            },
        });
    },

    /** Validate job dictionary.
     * @param{dict}     job_def   - Job execution dictionary
     */
    validate: function (job_def) {
        const Galaxy = getGalaxyInstance();
        const job_inputs = job_def.inputs;
        let batch_n = -1;
        let batch_src = null;
        for (const job_input_id in job_inputs) {
            const input_value = job_inputs[job_input_id];
            const input_id = this.form.data.match(job_input_id);
            const input_field = this.form.field_list[input_id];
            const input_def = this.form.input_list[input_id];
            if (!input_id || !input_def || !input_field) {
                Galaxy.emit.debug("tool-form::validate()", "Retrieving input objects failed.");
                continue;
            }
            if (!input_def.optional && input_value == null && input_def.type != "hidden") {
                this.form.highlight(input_id);
                return false;
            }
            if (input_field.validate) {
                const message = input_field.validate();
                if (message) {
                    this.form.highlight(input_id, message);
                    return false;
                }
            }
            if (input_value && input_value.batch) {
                const n = input_value.values.length;
                const src = n > 0 && input_value.values[0] && input_value.values[0].src;
                if (src) {
                    if (batch_src === null) {
                        batch_src = src;
                    } else if (batch_src !== src) {
                        this.form.highlight(
                            input_id,
                            "Please select either dataset or dataset list fields for all batch mode fields."
                        );
                        return false;
                    }
                }
                if (batch_n === -1) {
                    batch_n = n;
                } else if (batch_n !== n) {
                    this.form.highlight(
                        input_id,
                        `Please make sure that you select the same number of inputs for all batch mode fields. This field contains <b>${n}</b> selection(s) while a previous field contains <b>${batch_n}</b>.`
                    );
                    return false;
                }
            }
        }
        return true;
    },

    _getInputs: function (job_def) {
        const inputs = [];
        const index = {};
        for (const i in job_def.inputs) {
            const input = job_def.inputs[i];
            if (input && $.isArray(input.values)) {
                for (const j of input.values) {
                    if (j.src && !index[j.id]) {
                        inputs.push(j);
                        index[j.id] = true;
                    }
                }
            }
        }
        return inputs;
    },

    _templateRow: function (list, title) {
        let blurb = "";
        if (list.length > 0) {
            blurb += `<p>${title}:</p>`;
            list.sort((a, b) => {
                b.hid - a.hid;
            });
            blurb += `<ul>`;
            for (const item of list) {
                const rowString = `${item.hid}: ${_.escape(item.name)}`;
                blurb += `<li><b>${rowString}</b></li>`;
            }
            blurb += `</ul>`;
        }
        return blurb;
    },

    _templateSuccess: function (response, job_def) {
        const njobs = response && response.jobs ? response.jobs.length : 0;
        if (njobs > 0) {
            const inputs = this._getInputs(job_def);
            const ninputs = inputs.length;
            const noutputs = response.outputs.length;
            const njobsText = njobs > 1 ? `${njobs} jobs` : `1 job`;
            const ninputsText = ninputs > 1 ? `${ninputs} inputs` : `this input`;
            const noutputsText = noutputs > 1 ? `${noutputs} outputs` : `this output`;
            const tool_name = this.form.model.get("name");
            return `<div class="donemessagelarge">
                        <p>
                            Executed <b>${tool_name}</b> and successfully added ${njobsText} to the queue.
                        </p>
                        ${this._templateRow(inputs, `The tool uses ${ninputsText}`)}
                        ${this._templateRow(response.outputs, `It produces ${noutputsText}`)}
                        <p>
                            You can check the status of queued jobs and view the resulting data by refreshing the History panel. When the job has been run the status will change from 'running' to 'finished' if completed successfully or 'error' if problems were encountered.
                        </p>
                    </div>`;
        } else {
            return this._templateError(response, "Invalid success response. No jobs found.");
        }
    },

    _templateError: function (response, err_msg) {
        return $("<div/>")
            .addClass("errormessagelarge")
            .append(
                $("<p/>").text(
                    `The server could not complete the request. Please contact the Galaxy Team if this error persists. ${
                        err_msg || ""
                    }`
                )
            )
            .append($("<pre/>").text(JSON.stringify(response, null, 4)));
    },
});

export default {
    View: View,
};
