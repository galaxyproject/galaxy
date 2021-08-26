/**
    This is the main class of the form plugin. It is referenced as 'app' in lower level modules.
*/
import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
import FormSection from "mvc/form/form-section";
import FormData from "mvc/form/form-data";

export default Backbone.View.extend({
    initialize: function (options) {
        this.model = new Backbone.Model({
            initial_errors: false,
            always_refresh: true,
            onchange: function () {},
        }).set(options);
        this.setElement(options.el || "<div/>");
        this.render();
    },

    /** Update available options */
    update: function (inputs) {
        var self = this;
        this.data.matchModel(inputs, (node, input_id) => {
            var field = self.field_list[input_id];
            if (field.update) {
                field.update(node);
                field.trigger("change");
            }
        });
    },

    /** Set form into wait mode */
    wait: function (active) {
        for (var i in this.input_list) {
            var field = this.field_list[i];
            var input = this.input_list[i];
            if (input.is_dynamic && field.wait && field.unwait) {
                field[active ? "wait" : "unwait"]();
            }
        }
    },

    /** Highlight and scroll to input element (currently only used for error notifications) */
    highlight: function (input_id, message, silent) {
        var input_element = this.element_list[input_id];
        if (input_element) {
            input_element.error(message || "Please verify this option.");
            if (!silent) {
                var $panel = this.$el
                    .parents()
                    .filter(function () {
                        return ["auto", "scroll"].indexOf($(this).css("overflow")) != -1;
                    })
                    .first();
                $panel.animate(
                    {
                        scrollTop: $panel.scrollTop() + input_element.$el.offset().top - $panel.position().top - 120,
                    },
                    500
                );
            }
        }
    },

    /** Highlights errors */
    errors: function (details) {
        this.trigger("reset");
        if (details) {
            var error_messages = this.data.matchResponse(details);
            for (var input_id in this.element_list) {
                if (error_messages[input_id]) {
                    this.highlight(input_id, error_messages[input_id], true);
                }
            }
        }
    },

    /** Render tool form */
    render: function () {
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
        this.data = new FormData.Manager(this);
        this._renderForm();
        this.data.create();
        // add listener which triggers on checksum change, and reset the form input wrappers
        var current_check = this.data.checksum();
        this.on("change", (input_id) => {
            var input = self.input_list[input_id];
            if (!input || input.refresh_on_change || self.model.get("always_refresh")) {
                var new_check = self.data.checksum();
                if (new_check != current_check) {
                    current_check = new_check;
                    self.model.get("onchange")();
                }
            }
        });
        this.on("reset", () => {
            _.each(self.element_list, (input_element) => {
                input_element.reset();
            });
        });
        return this;
    },

    /** Renders/appends dom elements of the form */
    _renderForm: function () {
        $(".tooltip").remove();
        var options = this.model.attributes;
        this.section = new FormSection.View(this, {
            inputs: options.inputs,
        });
        this.$el.empty();
        if (options.inputs) {
            this.$el.append(this.section.$el);
        }
    },
});
