define("mvc/ui/ui-options", ["exports", "utils/utils", "mvc/ui/ui-buttons"], function(exports, _utils, _uiButtons) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _utils2 = _interopRequireDefault(_utils);

    var _uiButtons2 = _interopRequireDefault(_uiButtons);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /** Base class for options based ui elements **/
    var Base = Backbone.View.extend({
        initialize: function initialize(options) {
            var self = this;
            this.model = options && options.model || new Backbone.Model({
                visible: true,
                data: [],
                id: _utils2.default.uid(),
                error_text: "No options available.",
                wait_text: "Please wait...",
                multiple: false,
                optional: false,
                onchange: function onchange() {}
            }).set(options);
            this.listenTo(this.model, "change:value", this._changeValue, this);
            this.listenTo(this.model, "change:wait", this._changeWait, this);
            this.listenTo(this.model, "change:data", this._changeData, this);
            this.listenTo(this.model, "change:visible", this._changeVisible, this);
            this.on("change", function() {
                self.model.get("onchange")(self.value());
            });
            this.render();
        },

        render: function render() {
            var self = this;
            this.$el.empty().removeClass().addClass("ui-options").append(this.$message = $("<div/>")).append(this.$menu = $("<div/>").addClass("ui-options-menu")).append(this.$options = $(this._template()));

            // add select/unselect all button
            this.all_button = null;
            if (this.model.get("multiple")) {
                this.all_button = new _uiButtons2.default.ButtonCheck({
                    onclick: function onclick() {
                        self.$("input").prop("checked", self.all_button.value() !== 0);
                        self.value(self._getValue());
                        self.trigger("change");
                    }
                });
                this.$menu.append(this.all_button.$el);
            }

            // finalize dom
            this._changeData();
            this._changeWait();
            this._changeVisible();
        },

        /** Update available options */
        update: function update(options) {
            this.model.set("data", options);
        },

        _changeData: function _changeData() {
            var self = this;
            this.$options.empty();
            if (this._templateOptions) {
                this.$options.append(this._templateOptions(this.model.get("data")));
            } else {
                _.each(this.model.get("data"), function(option) {
                    self.$options.append($(self._templateOption(option)).addClass("ui-option").tooltip({
                        title: option.tooltip,
                        placement: "bottom"
                    }));
                });
            }
            var self = this;
            this.$("input").on("change", function() {
                self.value(self._getValue());
                self.trigger("change");
            });
            this._changeValue();
            this._changeWait();
        },

        _changeVisible: function _changeVisible() {
            this.$el[this.model.get("visible") ? "show" : "hide"]();
        },

        _changeWait: function _changeWait() {
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

        _changeValue: function _changeValue() {
            this._setValue(this.model.get("value"));
            if (this._getValue() === null && !this.model.get("multiple") && !this.model.get("optional")) {
                this._setValue(this.first());
            }
            this.all_button && this.all_button.value($.isArray(this._getValue()) ? this._getValue().length : 0, this.length());
        },

        /** Return/Set current selection */
        value: function value(new_value) {
            new_value !== undefined && this.model.set("value", new_value);
            return this._getValue();
        },

        /** Return first available option */
        first: function first() {
            var options = this.$("input").first();
            return options.length > 0 ? options.val() : null;
        },

        /** Show a spinner indicating that the select options are currently loaded */
        wait: function wait() {
            this.model.set("wait", true);
        },

        /** Hide spinner indicating that the request has been completed */
        unwait: function unwait() {
            this.model.set("wait", false);
        },

        /** Returns the number of options */
        length: function length() {
            return this.$(".ui-option").length;
        },

        /** Set value to dom */
        _setValue: function _setValue(new_value) {
            var self = this;
            if (new_value !== undefined) {
                this.$("input").prop("checked", false);
                if (new_value !== null) {
                    var values = $.isArray(new_value) ? new_value : [new_value];
                    _.each(values, function(v) {
                        self.$("input[value=\"" + v + "\"]").first().prop("checked", true);
                    });
                }
            }
        },

        /** Return current selection */
        _getValue: function _getValue() {
            var selected = [];
            this.$(":checked").each(function() {
                selected.push($(this).val());
            });
            if (_utils2.default.isEmpty(selected)) {
                return null;
            }
            return this.model.get("multiple") ? selected : selected[0];
        },

        /** Show message instead if options */
        _messageShow: function _messageShow(text, status) {
            this.$message.show().removeClass().addClass("ui-message alert alert-" + status).html(text);
        },

        /** Main template function */
        _template: function _template() {
            return $("<div/>").addClass("ui-options-list");
        }
    });

    /** Iconized **/
    var BaseIcons = Base.extend({
        _templateOption: function _templateOption(pair) {
            var id = _utils2.default.uid();
            return $("<div/>").addClass("ui-option").append($("<input/>").attr({
                id: id,
                type: this.model.get("type"),
                name: this.model.id,
                value: pair.value
            })).append($("<label/>").addClass("ui-options-label").attr("for", id).html(pair.label));
        }
    });

    /** Radio button field **/
    var Radio = {};
    Radio.View = BaseIcons.extend({
        initialize: function initialize(options) {
            options.type = "radio";
            BaseIcons.prototype.initialize.call(this, options);
        }
    });

    /** Checkbox options field **/
    var Checkbox = {};
    Checkbox.View = BaseIcons.extend({
        initialize: function initialize(options) {
            options.type = "checkbox";
            options.multiple = true;
            BaseIcons.prototype.initialize.call(this, options);
        }
    });

    /** Radio button options field styled as classic buttons **/
    var RadioButton = {};
    RadioButton.View = Base.extend({
        initialize: function initialize(options) {
            Base.prototype.initialize.call(this, options);
        },

        /** Set current value */
        _setValue: function _setValue(new_value) {
            if (new_value !== undefined) {
                this.$("input").prop("checked", false);
                this.$("label").removeClass("active");
                this.$("[value=\"" + new_value + "\"]").prop("checked", true).closest("label").addClass("active");
            }
        },

        /** Template for a single option */
        _templateOption: function _templateOption(pair) {
            var $el = $("<label/>").addClass("btn btn-default");
            pair.icon && $el.append($("<i/>").addClass("fa").addClass(pair.icon).addClass(!pair.label && "no-padding"));
            $el.append($("<input/>").attr({
                type: "radio",
                name: this.model.id,
                value: pair.value
            }));
            pair.label && $el.append(pair.label);
            return $el;
        },

        /** Main template function */
        _template: function _template() {
            return $("<div/>").addClass("btn-group ui-radiobutton").attr("data-toggle", "buttons");
        }
    });

    exports.default = {
        Base: Base,
        BaseIcons: BaseIcons,
        Radio: Radio,
        RadioButton: RadioButton,
        Checkbox: Checkbox
    };
});
//# sourceMappingURL=../../../maps/mvc/ui/ui-options.js.map
