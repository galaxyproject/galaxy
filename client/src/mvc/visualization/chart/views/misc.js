/**
 *  This class contains backbone wrappers for basic ui elements such as Images, Labels, Buttons, Input fields etc.
 */
import Backbone from "backbone";
import $ from "jquery";
import Modal from "mvc/ui/ui-modal";
import _ from "underscore";

import Buttons from "./buttons";

/** Displays messages used e.g. in the tool form */
export var Message = Backbone.View.extend({
    initialize: function (options) {
        this.model =
            (options && options.model) ||
            new Backbone.Model({
                message: null,
                status: "info",
                cls: "",
                persistent: false,
                fade: true,
            }).set(options);
        this.listenTo(this.model, "change", this.render, this);
        if (options && options.active_tab) {
            this.active_tab = options.active_tab;
        }
        this.render();
    },
    update: function (options) {
        this.model.set(options);
    },
    render: function () {
        var status = this.model.get("status");
        this.$el.removeClass().addClass(`alert alert-${status} mt-2`).addClass(this.model.get("cls"));
        if (this.model.get("message")) {
            this.$el.html(this.messageForDisplay());
            this.$el[this.model.get("fade") ? "fadeIn" : "show"]();
            this.timeout && window.clearTimeout(this.timeout);
            if (!this.model.get("persistent")) {
                var self = this;
                this.timeout = window.setTimeout(() => {
                    self.model.set("message", "");
                }, 3000);
            }
        } else {
            this.$el.hide();
        }
        return this;
    },
    messageForDisplay: function () {
        return _.escape(this.model.get("message"));
    },
});

export var UnescapedMessage = Message.extend({
    messageForDisplay: function () {
        return this.model.get("message");
    },
});

/** Renders an input element used e.g. in the tool form */
export var Input = Backbone.View.extend({
    initialize: function (options) {
        this.model =
            (options && options.model) ||
            new Backbone.Model({
                type: "text",
                placeholder: "",
                disabled: false,
                readonly: false,
                visible: true,
                cls: "",
                area: false,
                color: null,
                style: null,
            }).set(options);
        this.tagName = this.model.get("area") ? "textarea" : "input";
        this.setElement($(`<${this.tagName}/>`));
        this.listenTo(this.model, "change", this.render, this);
        this.render();
    },
    events: {
        input: "_onchange",
    },
    value: function (new_val) {
        new_val !== undefined && this.model.set("value", typeof new_val === "string" ? new_val : "");
        return this.model.get("value");
    },
    render: function () {
        var self = this;
        this.$el
            .removeClass()
            .addClass(`ui-${this.tagName}`)
            .addClass(this.model.get("cls"))
            .addClass(this.model.get("style"))
            .attr("id", this.model.id)
            .attr("type", this.model.get("type"))
            .attr("placeholder", this.model.get("placeholder"))
            .css("color", this.model.get("color") || "")
            .css("border-color", this.model.get("color") || "");
        var datalist = this.model.get("datalist");
        if (Array.isArray(datalist) && datalist.length > 0) {
            this.$el.autocomplete({
                source: self.model.get("datalist"),
                change: function () {
                    self._onchange();
                },
            });
        }
        if (this.model.get("value") !== this.$el.val()) {
            this.$el.val(this.model.get("value"));
        }
        _.each(["readonly", "disabled"], (attr_name) => {
            self.model.get(attr_name) ? self.$el.attr(attr_name, true) : self.$el.removeAttr(attr_name);
        });
        this.$el[this.model.get("visible") ? "show" : "hide"]();
        return this;
    },
    _onchange: function () {
        this.value(this.$el.val());
        this.model.get("onchange") && this.model.get("onchange")(this.model.get("value"));
    },
});

/* Make more Ui stuff directly available at this namespace (for backwards
 * compatibility).  We should eliminate this practice, though, and just require
 * what we need where we need it, allowing for better package optimization.
 */

export const Button = Buttons.Button;
export const ButtonMenu = Buttons.ButtonMenu;

export default {
    Button: Buttons.Button,
    ButtonMenu: Buttons.ButtonMenu,
    Input: Input,
    Message: Message,
    UnescapedMessage: UnescapedMessage,
    Modal: Modal,
};
