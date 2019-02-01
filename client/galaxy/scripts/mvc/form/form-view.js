/**
    This is the main class of the form plugin. It is referenced as 'app' in lower level modules.
*/
import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
import Portlet from "mvc/ui/ui-portlet";
import Ui from "mvc/ui/ui-misc";
import FormSection from "mvc/form/form-section";
import FormData from "mvc/form/form-data";
import { getGalaxyInstance } from "app";

export default Backbone.View.extend({
    initialize: function(options) {
        this.model = new Backbone.Model({
            initial_errors: false,
            cls: "ui-portlet",
            icon: null,
            always_refresh: true,
            status: "warning",
            hide_operations: false,
            onchange: function() {}
        }).set(options);
        this.setElement("<div/>");
        this.render();
    },

    /** Update available options */
    update: function(new_model) {
        var self = this;
        this.data.matchModel(new_model, (node, input_id) => {
            var field = self.field_list[input_id];
            if (field.update) {
                field.update(node);
                field.trigger("change");
                let Galaxy = getGalaxyInstance();
                Galaxy.emit.debug("form-view::update()", `Updating input: ${input_id}`);
            }
        });
    },

    /** Set form into wait mode */
    wait: function(active) {
        for (var i in this.input_list) {
            var field = this.field_list[i];
            var input = this.input_list[i];
            if (input.is_dynamic && field.wait && field.unwait) {
                field[active ? "wait" : "unwait"]();
            }
        }
    },

    /** Highlight and scroll to input element (currently only used for error notifications) */
    highlight: function(input_id, message, silent) {
        var input_element = this.element_list[input_id];
        if (input_element) {
            input_element.error(message || "Please verify this parameter.");
            this.portlet.expand();
            this.trigger("expand", input_id);
            if (!silent) {
                var $panel = this.$el
                    .parents()
                    .filter(function() {
                        return ["auto", "scroll"].indexOf($(this).css("overflow")) != -1;
                    })
                    .first();
                $panel.animate(
                    {
                        scrollTop: $panel.scrollTop() + input_element.$el.offset().top - $panel.position().top - 120
                    },
                    500
                );
            }
        }
    },

    /** Highlights errors */
    errors: function(options) {
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
    render: function() {
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
        if (this.model.get("initial_errors")) {
            this.errors(this.model.attributes);
        }
        // add listener which triggers on checksum change, and reset the form input wrappers
        var current_check = this.data.checksum();
        this.on("change", input_id => {
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
            _.each(self.element_list, input_element => {
                input_element.reset();
            });
        });
        return this;
    },

    /** Renders/appends dom elements of the form */
    _renderForm: function() {
        $(".tooltip").remove();
        var options = this.model.attributes;
        this.message = new Ui.UnescapedMessage();
        this.section = new FormSection.View(this, {
            inputs: options.inputs
        });
        this.portlet = new Portlet.View({
            icon: options.icon,
            title: options.title,
            title_id: options.title_id,
            operations: !options.hide_operations && options.operations,
            cls: options.cls,
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
        let Galaxy = getGalaxyInstance();
        Galaxy.emit.debug("form-view::initialize()", "Completed");
    }
});
