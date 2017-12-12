define("mvc/form/form-view", ["exports", "mvc/ui/ui-portlet", "mvc/ui/ui-misc", "mvc/form/form-section", "mvc/form/form-data"], function(exports, _uiPortlet, _uiMisc, _formSection, _formData) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });
    exports.View = undefined;

    var _uiPortlet2 = _interopRequireDefault(_uiPortlet);

    var _uiMisc2 = _interopRequireDefault(_uiMisc);

    var _formSection2 = _interopRequireDefault(_formSection);

    var _formData2 = _interopRequireDefault(_formData);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /**
        This is the main class of the form plugin. It is referenced as 'app' in lower level modules.
    */
    var View = exports.View = Backbone.View.extend({
        initialize: function initialize(options) {
            this.model = new Backbone.Model({
                initial_errors: false,
                cls: "ui-portlet-limited",
                icon: null,
                always_refresh: true,
                status: "warning",
                hide_operations: false,
                onchange: function onchange() {}
            }).set(options);
            this.setElement("<div/>");
            this.render();
        },

        /** Update available options */
        update: function update(new_model) {
            var self = this;
            this.data.matchModel(new_model, function(node, input_id) {
                var input = self.input_list[input_id];
                if (input && input.options) {
                    if (!_.isEqual(input.options, node.options)) {
                        input.options = node.options;
                        var field = self.field_list[input_id];
                        if (field.update) {
                            var new_options = [];
                            if (["data", "data_collection", "drill_down"].indexOf(input.type) != -1) {
                                new_options = input.options;
                            } else {
                                for (var i in node.options) {
                                    var opt = node.options[i];
                                    if (opt.length > 2) {
                                        new_options.push({
                                            label: opt[0],
                                            value: opt[1]
                                        });
                                    }
                                }
                            }
                            field.update(new_options);
                            field.trigger("change");
                            Galaxy.emit.debug("form-view::update()", "Updating options for " + input_id);
                        }
                    }
                }
            });
        },

        /** Set form into wait mode */
        wait: function wait(active) {
            for (var i in this.input_list) {
                var field = this.field_list[i];
                var input = this.input_list[i];
                if (input.is_dynamic && field.wait && field.unwait) {
                    field[active ? "wait" : "unwait"]();
                }
            }
        },

        /** Highlight and scroll to input element (currently only used for error notifications) */
        highlight: function highlight(input_id, message, silent) {
            var input_element = this.element_list[input_id];
            if (input_element) {
                input_element.error(message || "Please verify this parameter.");
                this.portlet.expand();
                this.trigger("expand", input_id);
                if (!silent) {
                    var $panel = this.$el.parents().filter(function() {
                        return ["auto", "scroll"].indexOf($(this).css("overflow")) != -1;
                    }).first();
                    $panel.animate({
                        scrollTop: $panel.scrollTop() + input_element.$el.offset().top - 120
                    }, 500);
                }
            }
        },

        /** Highlights errors */
        errors: function errors(options) {
            this.trigger("reset");
            if (options && options.errors) {
                var error_messages = this.data.matchResponse(options.errors);
                for (var input_id in this.element_list) {
                    if (error_messages[input_id]) {
                        this.highlight(input_id, error_messages[input_id], true);
                    }
                }
            }
        },

        /** Render tool form */
        render: function render() {
            var self = this;
            this.off("change");
            this.off("reset");
            // contains the dom field elements as created by the parameter factory i.e. form-parameters
            this.field_list = {};
            // contains input definitions/dictionaries as provided by the parameters to_dict() function through the api
            this.input_list = {};
            // contains the dom elements of each input element i.e. form-input which wraps the actual input field
            this.element_list = {};
            // converts the form into a json data structure
            this.data = new _formData2.default.Manager(this);
            this._renderForm();
            this.data.create();
            if (this.model.get("initial_errors")) {
                this.errors(this.model.attributes);
            }
            // add listener which triggers on checksum change, and reset the form input wrappers
            var current_check = this.data.checksum();
            this.on("change", function(input_id) {
                var input = self.input_list[input_id];
                if (!input || input.refresh_on_change || self.model.get("always_refresh")) {
                    var new_check = self.data.checksum();
                    if (new_check != current_check) {
                        current_check = new_check;
                        self.model.get("onchange")();
                    }
                }
            });
            this.on("reset", function() {
                _.each(self.element_list, function(input_element) {
                    input_element.reset();
                });
            });
            return this;
        },

        /** Renders/appends dom elements of the form */
        _renderForm: function _renderForm() {
            $(".tooltip").remove();
            var options = this.model.attributes;
            this.message = new _uiMisc2.default.UnescapedMessage();
            this.section = new _formSection2.default.View(this, {
                inputs: options.inputs
            });
            this.portlet = new _uiPortlet2.default.View({
                icon: options.icon,
                title: options.title,
                cls: options.cls,
                operations: !options.hide_operations && options.operations,
                buttons: options.buttons,
                collapsible: options.collapsible,
                collapsed: options.collapsed,
                onchange_title: options.onchange_title
            });
            this.portlet.append(this.message.$el);
            this.portlet.append(this.section.$el);
            this.$el.empty();
            if (options.inputs) {
                this.$el.append(this.portlet.$el);
            }
            if (options.message) {
                this.message.update({
                    persistent: true,
                    status: options.status,
                    message: options.message
                });
            }
            Galaxy.emit.debug("form-view::initialize()", "Completed");
        }
    });

    exports.default = View;
});
//# sourceMappingURL=../../../maps/mvc/form/form-view.js.map
