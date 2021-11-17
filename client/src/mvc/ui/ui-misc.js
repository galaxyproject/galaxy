/**
 *  This class contains backbone wrappers for basic ui elements such as Images, Labels, Buttons, Input fields etc.
 */
import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
import Select from "mvc/ui/ui-select-default";
import Options from "mvc/ui/ui-options";
import Drilldown from "mvc/ui/ui-drilldown";
import Buttons from "mvc/ui/ui-buttons";
import Modal from "mvc/ui/ui-modal";
import Switch from "mvc/ui/ui-switch";

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

export var NullableText = Backbone.View.extend({
    initialize: function (options) {
        this.model = (options && options.model) || new Backbone.Model().set(options);

        // Add text field
        this.text_input = new Input(options);

        // Add button that determines whether an optional value should be defined
        this.optional_button = new Switch({
            id: `optional-switch-${this.model.id}`,
        });

        // Create element
        this.setElement("<div/>");
        this.$el.append("<div>Set value for this optional select field?</div>");
        this.$el.append(this.optional_button.$el);
        this.$el.append(this.text_input.$el);

        // Determine true/false value of button based on initial value
        this.optional_button.model.set("value", this.text_input.model.get("value") === null ? "false" : "true");
        this.toggleButton();
        this.listenTo(this.optional_button.model, "change", this.toggleButton, this);
    },
    toggleButton: function () {
        const setOptional = this.optional_button.model.get("value");
        if (setOptional == "true") {
            // Enable text field, set value to `""` if the value is falsy and trigger change
            this.text_input.model.set("disabled", false);
            if (!this.text_input.model.get("value")) {
                this.text_input.model.set("value", "");
                this.model.get("onchange") && this.model.get("onchange")("");
            }
        } else {
            // Set text field to disabled, set model value to null and trigger change
            this.text_input.model.set("disabled", true);
            this.text_input.model.set("value", null);
            this.model.get("onchange") && this.model.get("onchange")(null);
        }
    },
    value: function (new_val) {
        const setOptional = this.optional_button.model.get("value");
        if (setOptional == "true") {
            new_val !== undefined && this.model.set("value", typeof new_val == "string" ? new_val : "");
        }
        return this.text_input.model.get("value");
    },
});

/** Creates an input element which switches between select and text field */
export var TextSelect = Backbone.View.extend({
    initialize: function (options) {
        this.select = new options.SelectClass.View(options);
        this.model = this.select.model;
        const textInputClass = options.optional ? NullableText : Input;
        this.text = new textInputClass({
            onchange: this.model.get("onchange"),
        });
        this.on("change", () => {
            if (this.model.get("onchange")) {
                this.model.get("onchange")(this.value());
            }
        });
        this.setElement($("<div/>").append(this.select.$el).append(this.text.$el));
        this.update(options);
    },
    wait: function () {
        this.select.wait();
    },
    unwait: function () {
        this.select.unwait();
    },
    value: function (new_val) {
        var element = this.textmode ? this.text : this.select;
        return element.value(new_val);
    },
    update: function (input_def) {
        var data = input_def.data;
        if (!data) {
            data = [];
            _.each(input_def.options, (option) => {
                data.push({ label: option[0], value: option[1] });
            });
        }
        var v = this.value();
        this.textmode = input_def.textable && (!Array.isArray(data) || data.length === 0);
        this.text.$el[this.textmode ? "show" : "hide"]();
        this.select.$el[this.textmode ? "hide" : "show"]();
        this.select.update({ data: data });
        this.value(v);
    },
});

/** Creates a upload element input field */
export var Upload = Backbone.View.extend({
    initialize: function (options) {
        var self = this;
        this.model = (options && options.model) || new Backbone.Model(options);
        this.setElement(
            $("<div/>")
                .append((this.$info = $("<div/>")))
                .append((this.$file = $("<input/>").attr("type", "file").addClass("mb-1")))
                .append((this.$text = $("<textarea/>").addClass("ui-textarea").attr("disabled", true)))
                .append((this.$wait = $("<i/>").addClass("fa fa-spinner fa-spin")))
        );
        this.listenTo(this.model, "change", this.render, this);
        this.$file.on("change", (e) => {
            self._readFile(e);
        });
        this.render();
    },
    value: function (new_val) {
        new_val !== undefined && this.model.set("value", new_val);
        return this.model.get("value");
    },
    render: function () {
        this.$el.attr("id", this.model.id);
        this.model.get("info") ? this.$info.show().text(this.model.get("info")) : this.$info.hide();
        this.model.get("value") ? this.$text.text(this.model.get("value")).show() : this.$text.hide();
        this.model.get("wait") ? this.$wait.show() : this.$wait.hide();
        return this;
    },
    _readFile: function (e) {
        var self = this;
        var file = e.target.files && e.target.files[0];
        if (file) {
            var reader = new FileReader();
            reader.onload = function () {
                self.model.set({ wait: false, value: this.result });
            };
            this.model.set({ wait: true, value: null });
            reader.readAsText(file);
        }
    },
});

/* Make more Ui stuff directly available at this namespace (for backwards
 * compatibility).  We should eliminate this practice, though, and just require
 * what we need where we need it, allowing for better package optimization.
 */

export const Button = Buttons.Button;
export const ButtonCheck = Buttons.ButtonCheck;
export const ButtonMenu = Buttons.ButtonMenu;
export const ButtonLink = Buttons.ButtonLink;
export const Checkbox = Options.Checkbox;
export const RadioButton = Options.RadioButton;
export const Radio = Options.Radio;
export { Select, Drilldown };

export default {
    Button: Buttons.Button,
    ButtonCheck: Buttons.ButtonCheck,
    ButtonMenu: Buttons.ButtonMenu,
    ButtonLink: Buttons.ButtonLink,
    Input: Input,
    Message: Message,
    UnescapedMessage: UnescapedMessage,
    Upload: Upload,
    Modal: Modal,
    RadioButton: Options.RadioButton,
    Checkbox: Options.Checkbox,
    Radio: Options.Radio,
    Switch: Switch,
    Select: Select,
    NullableText: NullableText,
    TextSelect: TextSelect,
    Drilldown: Drilldown,
};
