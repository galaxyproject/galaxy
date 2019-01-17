/**
    This class creates a form input element wrapper
*/
import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
export default Backbone.View.extend({
    initialize: function(app, options) {
        this.app = app;
        this.app_options = app.model ? app.model.attributes : {};
        this.field = (options && options.field) || new Backbone.View();
        this.model =
            (options && options.model) ||
            new Backbone.Model({
                text_enable: this.app_options.text_enable || "Enable",
                text_disable: this.app_options.text_disable || "Disable",
                text_connected_enable: this.app_options.text_connected_enable || "Add connection to module",
                text_connected_disable: this.app_options.text_connected_disable || "Remove connection from module",
                cls_enable: this.app_options.cls_enable || "fa fa-caret-square-o-down",
                cls_disable: this.app_options.cls_disable || "fa fa-caret-square-o-up",
                always_refresh: this.app_options.always_refresh
            }).set(options);

        // set element and link components
        this.setElement(this._template());
        this.$field = this.$(".ui-form-field");
        this.$info = this.$(".ui-form-info");
        this.$preview = this.$(".ui-form-preview");
        this.$collapsible = this.$(".ui-form-collapsible");
        this.$collapsible_text = this.$(".ui-form-collapsible-text");
        this.$collapsible_icon = this.$(".ui-form-collapsible-icon");
        this.$connected_icon = this.$(".ui-form-connected-icon");
        this.$title = this.$(".ui-form-title");
        this.$title_text = this.$(".ui-form-title-text");
        this.$error_text = this.$(".ui-form-error-text");
        this.$error = this.$(".ui-form-error");
        this.$backdrop = this.$(".ui-form-backdrop");

        // add field element
        this.$field.prepend(this.field.$el);

        // decide wether to expand or collapse fields
        var collapsible_value = this.model.get("collapsible_value");
        var value = JSON.stringify(this.model.get("value"));
        this.field.connected = value == JSON.stringify({ __class__: "ConnectedValue" });
        this.field.collapsed =
            this.field.connected ||
            (collapsible_value !== undefined &&
                JSON.stringify(this.model.get("value")) == JSON.stringify(collapsible_value));
        this.listenTo(this.model, "change", this.render, this);
        this.render();

        // add click handler
        var self = this;
        this.$collapsible_icon.on("click", () => {
            self.field.collapsed = !self.field.collapsed;
            self.field.connected = false;
            app.trigger && app.trigger("change");
            self.render();
        });
        this.$connected_icon.on("click", () => {
            self.field.connected = !self.field.connected;
            self.field.collapsed = self.field.connected;
            app.trigger && app.trigger("change");
            self.render();
        });

        // hide error on value change
        if (this.field.model && !this.model.get("always_refresh")) {
            this.listenTo(this.field.model, "change:value", () => {
                self.reset();
            });
        }

        // add error listener
        if (this.field.model) {
            this.listenTo(this.field.model, "error", message => {
                if (message) {
                    this.error(message);
                } else {
                    this.reset();
                }
            });
        }
    },

    /** Set backdrop for input element */
    backdrop: function() {
        this.model.set("backdrop", true);
    },

    /** Set error text */
    error: function(text) {
        this.model.set("error_text", text);
    },

    /** Reset this view */
    reset: function() {
        !this.model.get("fixed") && this.model.set("error_text", null);
    },

    render: function() {
        // render help
        $(".tooltip").hide();
        var help_text = this.model.get("help", "");
        var help_argument = this.model.get("argument");
        if (help_argument && help_text.indexOf(`(${help_argument})`) == -1) {
            help_text += ` (${help_argument})`;
        }
        this.$info.html(help_text);
        // render visibility
        this.$el[this.model.get("hidden") ? "hide" : "show"]();
        // render preview view for collapsed fields
        // allow at least newlines to render properly after escape
        const html = _.escape(this.model.get("text_value")).replace(/\n/g, "<br />");
        this.$preview[
            (this.field.collapsed && this.model.get("collapsible_preview")) || this.model.get("disabled")
                ? "show"
                : "hide"
        ]().html(html);
        // render error messages
        var error_text = this.model.get("error_text");
        this.$error[error_text ? "show" : "hide"]();
        this.$el[error_text ? "addClass" : "removeClass"]("alert alert-danger");
        this.$error_text.html(error_text);
        // render backdrop
        this.$backdrop[this.model.get("backdrop") ? "show" : "hide"]();
        // render input field
        this.field.collapsed || this.model.get("disabled") ? this.$field.hide() : this.$field.show();
        // render input field color and style
        this.field.model &&
            this.field.model.set({
                color: this.model.get("color"),
                style: this.model.get("style")
            });
        // render collapsible options
        const connected = this.field.connected;
        const collapsible =
            !this.field.collapsible_disabled &&
            !this.model.get("disabled") &&
            this.model.get("collapsible_value") !== undefined;
        const connectable = collapsible && this.model.get("connectable");
        if (collapsible || connectable) {
            var collapsible_state = this.field.collapsed ? "enable" : "disable";
            this.$title_text.hide();
            this.$collapsible.show();
            this.$collapsible_text.text(this.model.get("label"));
            if (collapsible && !connected) {
                this.$collapsible_icon
                    .removeClass()
                    .addClass("icon ui-form-collapsible-icon")
                    .addClass(this.model.get(`cls_${collapsible_state}`))
                    .tooltip("dispose")
                    .attr("data-original-title", this.model.get(`text_${collapsible_state}`))
                    .tooltip({ placement: "bottom" })
                    .show();
            } else {
                this.$collapsible_icon.hide();
            }
            if (connectable) {
                const connected_icon_style = this.field.connected ? "fa fa-times" : "fa fa-arrows-h";
                const connected_icon_margin = !connected && collapsible ? "ml-1" : "";
                const connected_collapsible_state = this.field.connected ? "disable" : "enable";
                this.$connected_icon
                    .removeClass()
                    .addClass("icon ui-form-connected-icon")
                    .addClass(connected_icon_style)
                    .addClass(connected_icon_margin)
                    .tooltip("dispose")
                    .attr("data-original-title", this.model.get(`text_connected_${connected_collapsible_state}`))
                    .tooltip({ placement: "bottom" })
                    .show();
            } else {
                this.$connected_icon.hide();
            }
        } else {
            this.$title_text.show().text(this.model.get("label"));
            this.$collapsible.hide();
        }
    },

    _template: function() {
        return $("<div/>")
            .addClass("ui-form-element")
            .append(
                $("<div/>")
                    .addClass("ui-form-error")
                    .append($("<span/>").addClass("fa fa-arrow-down mr-1"))
                    .append($("<span/>").addClass("ui-form-error-text"))
            )
            .append(
                $("<div/>")
                    .addClass("ui-form-title")
                    .append(
                        $("<div/>")
                            .addClass("ui-form-collapsible")
                            .append($("<i/>").addClass("ui-form-collapsible-icon"))
                            .append($("<i/>").addClass("ui-form-connected-icon"))
                            .append($("<span/>").addClass("ui-form-collapsible-text ml-1"))
                    )
                    .append($("<span/>").addClass("ui-form-title-text"))
            )
            .append(
                $("<div/>")
                    .addClass("ui-form-field")
                    .append($("<span/>").addClass("ui-form-info form-text text-muted"))
                    .append($("<div/>").addClass("ui-form-backdrop"))
            )
            .append($("<div/>").addClass("ui-form-preview"));
    }
});
