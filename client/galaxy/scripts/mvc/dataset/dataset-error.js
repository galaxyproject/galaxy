import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import Utils from "utils/utils";
import Ui from "mvc/ui/ui-misc";
import Form from "mvc/form/form-view";

/** Dataset edit attributes view */
var View = Backbone.View.extend({
    initialize: function () {
        const Galaxy = getGalaxyInstance();
        this.setElement("<div/>");
        this.model = new Backbone.Model({
            dataset_id: Galaxy.params.dataset_id,
        });
        this.active_tab = "user";
        this.render();
    },

    // Fetch data for the selected dataset and
    render: function () {
        var data_url = `${getAppRoot()}api/datasets/${this.model.get("dataset_id")}`;
        Utils.get({
            url: data_url,
            success: (dataset) => {
                var job_url = `${getAppRoot()}api/jobs/${dataset.creating_job}?full=True`;
                Utils.get({
                    url: job_url,
                    success: (job) => {
                        this.render_error_page(dataset, job);
                        this.find_common_problems(job);
                    },
                    error: () => {
                        var error_response = {
                            status: "error",
                            message: "Error occurred while loading the job.",
                            persistent: true,
                            cls: "errormessage",
                        };
                        this.display_message(error_response, this.$(".response-message"));
                    },
                });
            },
            error: () => {
                var error_response = {
                    status: "error",
                    message: "Error occurred while loading the dataset.",
                    persistent: true,
                    cls: "errormessage",
                };
                this.display_message(error_response, this.$(".response-message"));
            },
        });
    },

    find_common_problems: function (job) {
        var job_url = `${getAppRoot()}api/jobs/${job.id}/common_problems`;
        Utils.get({
            url: job_url,
            success: (common_problems) => {
                this.render_common_problems(common_problems);
            },
            error: (response) => {
                console.log("error");
                console.log(response);
            },
        });
        return;
    },

    render_common_problems: function (common_problems) {
        const has_duplicate_inputs = common_problems.has_duplicate_inputs;
        const has_empty_inputs = common_problems.has_empty_inputs;
        if (has_duplicate_inputs || has_empty_inputs) {
            const reportEl = this.$el.find(".common_problems");
            reportEl.text("Detected Common Potential Problems");
            if (has_empty_inputs) {
                reportEl.after(`
                    <p>
                        The tool was executed with one or more empty input datasets. This frequently
                        results in tool errors due to problematic input choices.
                    <p>`);
            }
            if (has_duplicate_inputs) {
                reportEl.after(`
                    <p>
                        The tool was executed with one or more duplicate input datasets. This frequently
                        results in tool errors due to problematic input choices.
                    <p>`);
            }
        }
    },

    /** Render the view */
    render_error_page: function (dataset, job) {
        this.$el.empty().append(`
            ${this._templateHeader()}
            <h2>Dataset Error Report</h2>
            <p>An error occurred while running the tool <b>${job.tool_id}</b>.</p>
            ${this.job_summary(job)}
            <h3>Troubleshooting</h3>
            <p>
                There are a number of helpful resources to self diagnose and
                correct problems.
                <br>
                Start here:
                <b>
                    <a href="https://galaxyproject.org/support/tool-error/" target="_blank">
                        My job ended with an error. What can I do?
                    </a>
                </b>
            </p>`);
        this.$el.append("<h3>Issue Report</h3>").append(this._getBugFormTemplate(dataset, job));
    },

    job_summary: function (job) {
        const tool_stderr = job.tool_stderr;
        const job_stderr = job.job_stderr;
        const job_messages = job.job_messages;
        if (!tool_stderr && !job_stderr && !job_messages) {
            return '<h3 class="common_problems"></h3>';
        }
        var message = "<h3>Details</h3>";
        if (job_messages) {
            message += "<p>Execution resulted in the following messages:</p>";
            for (const job_message of job_messages) {
                message += `<p><pre>${_.escape(job_message["desc"])}</pre></p>`;
            }
        }
        if (tool_stderr) {
            message += "<p>Tool generated the following standard error:</p>";
            message += `<pre class="rounded code">${_.escape(tool_stderr)}</pre>`;
        }
        if (job_stderr) {
            message += "<p>Galaxy job runner generated the following standard error:</p>";
            message += `<pre class="code">${_.escape(job_stderr)}</pre>`;
        }
        message += `<h3 class="common_problems"></h3>`;
        return message;
    },

    /** Display actions messages */
    display_message: function (response, $el, doNotClear, safe) {
        if (!safe) {
            if (doNotClear) {
                $el.append(new Ui.Message(response).$el);
            } else {
                $el.empty().html(new Ui.Message(response).$el);
            }
        } else {
            if (doNotClear) {
                $el.append(new Ui.UnescapedMessage(response).$el);
            } else {
                $el.empty().html(new Ui.UnescapedMessage(response).$el);
            }
        }
    },

    /** Main template */
    _templateHeader: function () {
        return `<div class="page-container edit-attr"><div class="response-message"></div></div>`;
    },

    /** Convert tab template */
    _getBugFormTemplate: function (dataset, job) {
        const Galaxy = getGalaxyInstance();
        const userEmail = Galaxy.user.get("email");
        const form = new Form({
            inputs: [
                {
                    type: "text",
                    hidden: !!userEmail,
                    name: "email",
                    value: userEmail,
                    label: "Please provide your email:",
                },
                {
                    type: "text",
                    area: true,
                    name: "message",
                    label: "Please provide detailed information on the activities leading to this issue:",
                },
            ],
            buttons: {
                save: new Ui.Button({
                    icon: "fa-bug",
                    title: _l("Report"),
                    cls: "btn btn-primary",
                    floating: "clear",
                    onclick: () => {
                        var form_data = form.data.create();
                        var url = `${getAppRoot()}api/jobs/${job.id}/error`;
                        form_data.dataset_id = dataset.id;
                        this.submit(form_data, url);
                    },
                }),
            },
        });
        return form.$el;
    },

    /** Make ajax request */
    submit: function (form_data, url) {
        // Some required metadata
        $.ajax({
            type: "POST",
            url: url,
            data: form_data,
            success: (response) => {
                // Clear out the div
                this.$el.empty().append(this._templateHeader());
                // And display the messages.
                response.messages.forEach((message) => {
                    this.display_message(
                        {
                            status: message[1],
                            message: message[0],
                            persistent: true,
                        },
                        this.$(".response-message"),
                        true,
                        true
                    );
                });
            },
            error: () => {
                var error_response = {
                    status: "error",
                    message: "Error occurred while saving. Please fill all the required fields and try again.",
                    persistent: true,
                    cls: "errormessage",
                };
                this.display_message(error_response, this.$(".response-message"));
            },
        });
    },
});

export default {
    View: View,
};
