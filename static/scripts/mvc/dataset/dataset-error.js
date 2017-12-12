define("mvc/dataset/dataset-error", ["exports", "utils/localization", "utils/utils", "mvc/ui/ui-misc", "mvc/form/form-view"], function(exports, _localization, _utils, _uiMisc, _formView) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _localization2 = _interopRequireDefault(_localization);

    var _utils2 = _interopRequireDefault(_utils);

    var _uiMisc2 = _interopRequireDefault(_uiMisc);

    var _formView2 = _interopRequireDefault(_formView);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /** Dataset edit attributes view */
    var View = Backbone.View.extend({
        initialize: function initialize() {
            this.setElement("<div/>");
            this.model = new Backbone.Model({
                dataset_id: Galaxy.params.dataset_id
            });
            this.render();
        },

        // Fetch data for the selected dataset and
        render: function render() {
            var data_url = Galaxy.root + "api/datasets/" + this.model.get("dataset_id");

            var self = this;

            _utils2.default.get({
                url: data_url,
                success: function success(dataset) {
                    var job_url = Galaxy.root + "api/jobs/" + dataset.creating_job + "?full=True";
                    _utils2.default.get({
                        url: job_url,
                        success: function success(job) {
                            var job_url = Galaxy.root + "api/jobs/" + dataset.creating_job + "?full=True";
                            self.render_error_page(self, dataset, job);
                        },
                        error: function error(response) {
                            var error_response = {
                                status: "error",
                                message: "Error occured while loading the job.",
                                persistent: true,
                                cls: "errormessage"
                            };
                            self.display_message(error_response, self.$(".response-message"));
                        }
                    });
                },
                error: function error(response) {
                    var error_response = {
                        status: "error",
                        message: "Error occured while loading the dataset.",
                        persistent: true,
                        cls: "errormessage"
                    };
                    self.display_message(error_response, self.$(".response-message"));
                }
            });
        },

        /** Render the view */
        render_error_page: function render_error_page(self, dataset, job) {
            self.$el.empty().append(self._templateHeader());
            self.$el.append("<h2>Dataset Error</h2>");
            self.$el.append("<p>An error occured while running the tool <b>" + job.tool_id + "</b>.</p>");
            self.$el.append("<p>Tool execution generated the following messages:</p>");
            self.$el.append("<pre class=\"code\">" + job.stderr + "</pre>");
            self.$el.append("<h2>Report This Error</pre>");
            self.$el.append("<p>Usually the local Galaxy administrators regularly review errors that occur on the server. However, if you would like to provide additional information (such as what you were trying to do when the error occurred) and a contact e-mail address, we will be better able to investigate your problem and get back to you.</p>");
            self.$el.append(self._getBugFormTemplate(dataset, job));
        },

        /** Display actions messages */
        display_message: function display_message(response, $el, doNotClear, safe) {
            if (!safe) {
                if (doNotClear) {
                    $el.append(new _uiMisc2.default.Message(response).$el);
                } else {
                    $el.empty().html(new _uiMisc2.default.Message(response).$el);
                }
            } else {
                if (doNotClear) {
                    $el.append(new _uiMisc2.default.UnescapedMessage(response).$el);
                } else {
                    $el.empty().html(new _uiMisc2.default.UnescapedMessage(response).$el);
                }
            }
        },

        /** Main template */
        _templateHeader: function _templateHeader() {
            return '<div class="page-container edit-attr">' + '<div class="response-message"></div>' + "</div>";
        },

        /** Convert tab template */
        _getBugFormTemplate: function _getBugFormTemplate(dataset, job) {
            var self = this;
            var inputs = [{
                help: (0, _localization2.default)("Your email address"),
                options: [],
                type: "text",
                name: "email",
                label: "Your email",
                value: Galaxy.user.get("email")
            }, {
                help: (0, _localization2.default)("Any additional comments you can provide regarding what you were doing at the time of the bug."),
                options: [],
                type: "text",
                area: true,
                name: "message",
                label: "Message"
            }];

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

            var form = new _formView2.default({
                title: (0, _localization2.default)("Error Report"),
                inputs: inputs,
                buttons: {
                    save: new _uiMisc2.default.Button({
                        icon: "fa-bug",
                        title: (0, _localization2.default)("Report"),
                        cls: "ui-button btn btn-primary",
                        floating: "clear",
                        onclick: function onclick() {
                            var form_data = form.data.create();
                            var url = Galaxy.root + "api/jobs/" + job.id + "/error";
                            form_data.dataset_id = dataset.id;
                            self.submit(form_data, url);
                        }
                    })
                }
            });
            return form.$el;
        },

        /** Make ajax request */
        submit: function submit(form_data, url) {
            var self = this;
            // Some required metadata
            $.ajax({
                type: "POST",
                url: url,
                data: form_data,
                success: function success(response) {
                    // Clear out the div
                    self.$el.empty().append(self._templateHeader());
                    // And display the messages.
                    response.messages.forEach(function(message) {
                        self.display_message({
                            status: message[1],
                            message: message[0],
                            persistent: true
                        }, self.$(".response-message"), true, true);
                    });
                },
                error: function error(response) {
                    var error_response = {
                        status: "error",
                        message: "Error occured while saving. Please fill all the required fields and try again.",
                        persistent: true,
                        cls: "errormessage"
                    };
                    self.display_message(error_response, self.$(".response-message"));
                }
            });
        }
    });

    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/dataset/dataset-error.js.map
