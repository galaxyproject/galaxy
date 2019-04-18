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
    initialize: function() {
        let Galaxy = getGalaxyInstance();
        this.setElement("<div/>");
        this.model = new Backbone.Model({
            dataset_id: Galaxy.params.dataset_id
        });
        this.active_tab = "user";
        this.render();
    },

    // Fetch data for the selected dataset and
    render: function() {
        var data_url = `${getAppRoot()}api/datasets/${this.model.get("dataset_id")}`;

        Utils.get({
            url: data_url,
            success: dataset => {
                var job_url = `${getAppRoot()}api/jobs/${dataset.creating_job}?full=True`;
                Utils.get({
                    url: job_url,
                    success: job => {
                        this.render_error_page(dataset, job);
                        this.find_common_problems(job);
                    },
                    error: response => {
                        var error_response = {
                            status: "error",
                            message: "Error occurred while loading the job.",
                            persistent: true,
                            cls: "errormessage"
                        };
                        this.display_message(error_response, this.$(".response-message"));
                    }
                });
            },
            error: response => {
                var error_response = {
                    status: "error",
                    message: "Error occurred while loading the dataset.",
                    persistent: true,
                    cls: "errormessage"
                };
                this.display_message(error_response, this.$(".response-message"));
            }
        });
    },

    find_common_problems: function(job) {
        var job_url = `${getAppRoot()}api/jobs/${job.id}/common_problems`;
        Utils.get({
            url: job_url,
            success: common_problems => {
                this.render_common_problems(job, common_problems);
            },
            error: response => {
                console.log("error");
                console.log(response);
            }
        });
        return;
    },

    render_common_problems: function(job, common_problems) {
        const has_duplicate_inputs = common_problems.has_duplicate_inputs;
        const has_empty_inputs = common_problems.has_empty_inputs;
        if (has_duplicate_inputs || has_empty_inputs) {
            const reportEl = this.$el.find(".common_problems");
            reportEl.text("Detected Common Potential Problems");
            if (has_empty_inputs) {
                reportEl.after(`
                    <p>
                        The tool was executed with one or more empty input datasets, this isn't
                        always a problem and may not have been but frequently this is a source
                        of error.
                    <p>`);
            }
            if (has_duplicate_inputs) {
                reportEl.after(`
                    <p>
                        The tool was executed with one or more duplicate input datasets, this isn't
                        always a problem and may not have been but frequently this is a source
                        of error.
                    <p>`);
            }
        }
    },

    /** Render the view */
    render_error_page: function(dataset, job) {
        this.$el.empty().append(`
            ${this._templateHeader()}
            <h2>Dataset Error</h2>
            <p>An error occurred while running the tool <b>${job.tool_id}</b>.</p>
            ${this.job_summary(job)}
            <h3>Troubleshoot This Error</h3>
            <p>
                There are a number of help resources to self diagnose and
                correct problems.
                Start here: <a
                href="https://galaxyproject.org/support/tool-error/"
                target="_blank"> My job ended with an error. What can I do?</a>
            </p>

            <h3>Report This Error</h3>
            <p>
                Usually the local Galaxy administrators regularly review errors
                that occur on the server However, if you would like to provide
                additional information (such as what you were trying to do when
                the error occurred) and a contact e-mail address, we will be
                better able to investigate your problem and get back to you.
            </p>`);
        this.$el.append(this._getBugFormTemplate(dataset, job));
    },

    job_summary: function(job) {
        const tool_stderr = job.tool_stderr;
        const job_stderr = job.job_stderr;
        const job_messages = job.job_messages;
        if (!tool_stderr && !job_stderr && !job_messages) {
            return '<h3 class="common_problems"></h3>';
        }
        var message = "<h3>Error Details</h3>";
        if (job_messages) {
            message += "<p>Execution resulted in the following messages:</p>";
            for (let job_message of job_messages) {
                message += `<p><pre>${_.escape(job_message["desc"])}</pre></p>`;
            }
        }
        if (tool_stderr) {
            message += "<p>Tool generated the following standard error:</p>";
            message += `<pre class="code">${_.escape(tool_stderr)}</pre>`;
        }
        if (job_stderr) {
            message += "<p>Galaxy job runner generated the following standard error:</p>";
            message += `<pre class="code">${_.escape(job_stderr)}</pre>`;
        }
        message += `<h3 class="common_problems"></h3>`;
        return message;
    },

    /** Display actions messages */
    display_message: function(response, $el, doNotClear, safe) {
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
    _templateHeader: function() {
        return `<div class="page-container edit-attr"><div class="response-message"></div></div>`;
    },

    /** Convert tab template */
    _getBugFormTemplate: function(dataset, job) {
        let Galaxy = getGalaxyInstance();
        var inputs = [
            {
                help: _l("Your email address"),
                options: [],
                type: "text",
                name: "email",
                label: "Your email",
                value: Galaxy.user.get("email")
            },
            {
                help: _l(
                    "Any additional comments you can provide regarding what you were doing at the time of the bug."
                ),
                options: [],
                type: "text",
                area: true,
                name: "message",
                label: "Message"
            }
        ];

        // TODO
        /*
        if (false && response.any_public) {
            inputs.push({
                name: "public_consent",
                label: "Public Disclosure Consent",
                help:
                    "This Galaxy is configured to report to one or more error reporting backends that public to the world. By selecting 'yes', you acknowledge that this bug report will be made public.",
                value: String(Boolean(false)),
                options: [],
                type: "boolean"
            });
        }
        */

        var form = new Form({
            title: _l("Error Report"),
            inputs: inputs,
            buttons: {
                save: new Ui.Button({
                    icon: "fa-bug",
                    title: _l("Report"),
                    cls: "ui-button btn btn-primary",
                    floating: "clear",
                    onclick: () => {
                        var form_data = form.data.create();
                        var url = `${getAppRoot()}api/jobs/${job.id}/error`;
                        form_data.dataset_id = dataset.id;
                        this.submit(form_data, url);
                    }
                })
            }
        });
        return form.$el;
    },

    /** Make ajax request */
    submit: function(form_data, url) {
        // Some required metadata
        $.ajax({
            type: "POST",
            url: url,
            data: form_data,
            success: response => {
                // Clear out the div
                this.$el.empty().append(this._templateHeader());
                // And display the messages.
                response.messages.forEach(message => {
                    this.display_message(
                        {
                            status: message[1],
                            message: message[0],
                            persistent: true
                        },
                        this.$(".response-message"),
                        true,
                        true
                    );
                });
            },
            error: response => {
                var error_response = {
                    status: "error",
                    message: "Error occurred while saving. Please fill all the required fields and try again.",
                    persistent: true,
                    cls: "errormessage"
                };
                this.display_message(error_response, this.$(".response-message"));
            }
        });
    }
});

export default {
    View: View
};
