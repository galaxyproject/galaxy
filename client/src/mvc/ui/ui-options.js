/** Base class for options based ui elements **/
import $ from "jquery";
import Backbone from "backbone";
import _ from "underscore";
import Utils from "utils/utils";
import Buttons from "mvc/ui/ui-buttons";

var Base = Backbone.View.extend({
    initialize: function (options) {
        this.model =
            (options && options.model) ||
            new Backbone.Model({
                visible: true,
                cls: null,
                data: [],
                id: Utils.uid(),
                error_text: "No options available.",
                wait_text: "Please wait...",
                multiple: false,
                optional: false,
                onchange: () => {},
            }).set(options);
        this.listenTo(this.model, "change:value", this._changeValue, this);
        this.listenTo(this.model, "change:wait", this._changeWait, this);
        this.listenTo(this.model, "change:data", this._changeData, this);
        this.listenTo(this.model, "change:visible", this._changeVisible, this);
        this.listenTo(this, "change", () => {
            this.model.get("onchange")(this.value());
        });
        this.render();
    },

    render: function () {
        var self = this;
        this.$el
            .empty()
            .removeClass()
            .addClass("ui-options")
            .addClass(this.model.get("cls"))
            .append((this.$message = $("<div/>").addClass("mt-2")))
            .append((this.$menu = $("<div/>").addClass("ui-options-menu")))
            .append((this.$options = $(this._template())));

        // add select/unselect all button
        this.all_button = null;
        if (this.model.get("multiple")) {
            this.all_button = new Buttons.ButtonCheck({
                onclick: function () {
                    self.$("input").prop("checked", self.all_button.value() !== 0);
                    self.value(self._getValue());
                    self.trigger("change");
                },
            });
            this.$menu.append(this.all_button.$el);
        }

        // finalize dom
        this._changeData();
        this._changeWait();
        this._changeVisible();
    },

    /** Update available options */
    update: function (input_def) {
        if (input_def.data) {
            this.model.set("data", input_def.data);
        }
    },

    _changeData: function () {
        var self = this;
        this.$options.empty();
        if (this._templateOptions) {
            this.$options.append(this._templateOptions(this.model.get("data")));
        } else {
            _.each(this.model.get("data"), (option) => {
                self.$options.append(
                    $(self._templateOption(option))
                        .addClass("ui-option")
                        .tooltip({
                            title: option.tooltip || "",
                            placement: "bottom",
                        })
                );
            });
        }
        this.$("input").on("change", () => {
            self.value(self._getValue());
            self.trigger("change");
        });
        this._changeValue();
        this._changeWait();
    },

    _changeVisible: function () {
        this.$el[this.model.get("visible") ? "show" : "hide"]();
    },

    _changeWait: function () {
        if (this.model.get("wait")) {
            if (this.length() === 0) {
                this._messageShow(this.model.get("wait_text"), "info");
                this.$options.hide();
                this.$menu.hide();
            }
        } else {
            if (this.length() === 0) {
                this._messageShow(this.model.get("error_text"), "danger");
                this.$options.hide();
                this.$menu.hide();
            } else {
                this.$message.hide();
                this.$options.css("display", "inline-block");
                this.$menu.show();
            }
        }
    },

    _changeValue: function () {
        this._setValue(this.model.get("value"));
        if (this._getValue() === null && !this.model.get("multiple") && !this.model.get("optional")) {
            this._setValue(this.first());
        }
        if (this.all_button) {
            this.all_button.value(Array.isArray(this._getValue()) ? this._getValue().length : 0, this.length());
        }
    },

    /** Return/Set current selection */
    value: function (new_value) {
        if (new_value !== undefined) {
            this.model.set("value", new_value);
        }
        return this._getValue();
    },

    /** Return first available option */
    first: function () {
        var options = this.$("input").first();
        return options.length > 0 ? options.val() : null;
    },

    /** Show a spinner indicating that the select options are currently loaded */
    wait: function () {
        this.model.set("wait", true);
    },

    /** Hide spinner indicating that the request has been completed */
    unwait: function () {
        this.model.set("wait", false);
    },

    /** Returns the number of options */
    length: function () {
        return this.$(".ui-option").length;
    },

    /** Shows the options */
    show: function () {
        this.model.set("visible", true);
    },

    /** Hides the options */
    hide: function () {
        this.model.set("visible", false);
    },

    /** Set value to dom */
    _setValue: function (new_value) {
        var self = this;
        if (new_value !== undefined) {
            this.$("input").prop("checked", false);
            if (new_value !== null) {
                var values = Array.isArray(new_value) ? new_value : [new_value];
                _.each(values, (v) => {
                    self.$(`input[value="${v}"]`).first().prop("checked", true);
                });
            }
        }
    },

    /** Return current selection */
    _getValue: function () {
        var selected = [];
        this.$(":checked").each(function () {
            selected.push($(this).val());
        });
        if (Utils.isEmpty(selected)) {
            return null;
        }
        return this.model.get("multiple") ? selected : selected[0];
    },

    /** Show message instead if options */
    _messageShow: function (text, status) {
        this.$message.show().removeClass().addClass(`alert alert-${status}`).html(text);
    },

    /** Main template function */
    _template: function () {
        return $("<div/>").addClass("ui-options-list");
    },
});

/** Iconized **/
var BaseIcons = Base.extend({
    _templateOption: function (pair) {
        var id = Utils.uid();
        return $("<div/>")
            .addClass("ui-option")
            .addClass(this.model.get("cls_option"))
            .append(
                $("<input/>").attr({
                    id: id,
                    type: this.model.get("type"),
                    name: this.model.id,
                    value: pair.value,
                })
            )
            .append($("<label/>").addClass("ui-options-label").attr("for", id).html(pair.label));
    },
});

/** Radio button field **/
var Radio = {};
Radio.View = BaseIcons.extend({
    initialize: function (options) {
        options.type = "radio";
        BaseIcons.prototype.initialize.call(this, options);
    },
});

/** Checkbox options field **/
var Checkbox = {};
Checkbox.View = BaseIcons.extend({
    initialize: function (options) {
        options.type = "checkbox";
        options.multiple = true;
        BaseIcons.prototype.initialize.call(this, options);
    },
});

/** Radio button options field styled as classic buttons **/
var RadioButton = {};
RadioButton.View = Base.extend({
    initialize: function (options) {
        Base.prototype.initialize.call(this, options);
    },

    /** Set current value */
    _setValue: function (new_value) {
        if (new_value !== undefined) {
            this.$("input").prop("checked", false);
            this.$("label").removeClass("active");
            this.$(`[value="${new_value}"]`).prop("checked", true).closest("label").addClass("active");
        }
    },

    /** Template for a single option */
    _templateOption: function (pair) {
        var $el = $("<label/>").attr("role", "button");
        if (pair.icon) {
            $el.append(
                $("<i/>")
                    .addClass("fa")
                    .addClass(pair.icon)
                    .addClass(!pair.label && "no-padding")
            );
        }
        $el.append(
            $("<input/>")
                .attr({
                    type: "radio",
                    name: this.model.id,
                    value: pair.value,
                })
                .hide()
        );
        if (pair.label) {
            $el.append(pair.label);
        }
        return $el;
    },

    /** Main template function */
    _template: function () {
        return $("<div/>").addClass("ui-radiobutton");
    },
});

export default {
    Base: Base,
    BaseIcons: BaseIcons,
    Radio: Radio,
    RadioButton: RadioButton,
    Checkbox: Checkbox,
};
