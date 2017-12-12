define("mvc/ui/ui-misc", ["exports", "mvc/ui/ui-select-default", "mvc/ui/ui-slider", "mvc/ui/ui-options", "mvc/ui/ui-drilldown", "mvc/ui/ui-buttons", "mvc/ui/ui-modal"], function(exports, _uiSelectDefault, _uiSlider, _uiOptions, _uiDrilldown, _uiButtons, _uiModal) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });
    exports.Drilldown = exports.Slider = exports.Select = exports.Radio = exports.RadioButton = exports.Checkbox = exports.ButtonLink = exports.ButtonMenu = exports.ButtonCheck = exports.ButtonIcon = exports.Button = exports.Upload = exports.Hidden = exports.Input = exports.UnescapedMessage = exports.Message = exports.Label = undefined;

    var _uiSelectDefault2 = _interopRequireDefault(_uiSelectDefault);

    var _uiSlider2 = _interopRequireDefault(_uiSlider);

    var _uiOptions2 = _interopRequireDefault(_uiOptions);

    var _uiDrilldown2 = _interopRequireDefault(_uiDrilldown);

    var _uiButtons2 = _interopRequireDefault(_uiButtons);

    var _uiModal2 = _interopRequireDefault(_uiModal);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /** Label wrapper */
    /**
     *  This class contains backbone wrappers for basic ui elements such as Images, Labels, Buttons, Input fields etc.
     */
    var Label = exports.Label = Backbone.View.extend({
        tagName: "label",
        initialize: function initialize(options) {
            this.model = options && options.model || new Backbone.Model(options);
            this.tagName = options.tagName || this.tagName;
            this.setElement($("<" + this.tagName + "/>"));
            this.listenTo(this.model, "change", this.render, this);
            this.render();
        },
        title: function title(new_title) {
            this.model.set("title", new_title);
        },
        value: function value() {
            return this.model.get("title");
        },
        render: function render() {
            this.$el.removeClass().addClass("ui-label").addClass(this.model.get("cls")).html(this.model.get("title"));
            return this;
        }
    });

    /** Displays messages used e.g. in the tool form */
    var Message = exports.Message = Backbone.View.extend({
        initialize: function initialize(options) {
            this.model = options && options.model || new Backbone.Model({
                message: null,
                status: "info",
                cls: "",
                persistent: false,
                fade: true
            }).set(options);
            this.listenTo(this.model, "change", this.render, this);
            this.render();
        },
        update: function update(options) {
            this.model.set(options);
        },
        render: function render() {
            this.$el.removeClass().addClass("ui-message").addClass(this.model.get("cls"));
            var status = this.model.get("status");
            if (this.model.get("large")) {
                this.$el.addClass((status == "success" && "done" || status == "danger" && "error" || status) + "messagelarge");
            } else {
                this.$el.addClass("alert").addClass("alert-" + status);
            }
            if (this.model.get("message")) {
                this.$el.html(this.messageForDisplay());
                this.$el[this.model.get("fade") ? "fadeIn" : "show"]();
                this.timeout && window.clearTimeout(this.timeout);
                if (!this.model.get("persistent")) {
                    var self = this;
                    this.timeout = window.setTimeout(function() {
                        self.model.set("message", "");
                    }, 3000);
                }
            } else {
                this.$el.fadeOut();
            }
            return this;
        },
        messageForDisplay: function messageForDisplay() {
            return _.escape(this.model.get("message"));
        }
    });

    var UnescapedMessage = exports.UnescapedMessage = Message.extend({
        messageForDisplay: function messageForDisplay() {
            return this.model.get("message");
        }
    });

    /** Renders an input element used e.g. in the tool form */
    var Input = exports.Input = Backbone.View.extend({
        initialize: function initialize(options) {
            this.model = options && options.model || new Backbone.Model({
                type: "text",
                placeholder: "",
                disabled: false,
                readonly: false,
                visible: true,
                cls: "",
                area: false,
                color: null,
                style: null
            }).set(options);
            this.tagName = this.model.get("area") ? "textarea" : "input";
            this.setElement($("<" + this.tagName + "/>"));
            this.listenTo(this.model, "change", this.render, this);
            this.render();
        },
        events: {
            input: "_onchange"
        },
        value: function value(new_val) {
            new_val !== undefined && this.model.set("value", typeof new_val === "string" ? new_val : "");
            return this.model.get("value");
        },
        render: function render() {
            var self = this;
            this.$el.removeClass().addClass("ui-" + this.tagName).addClass(this.model.get("cls")).addClass(this.model.get("style")).attr("id", this.model.id).attr("type", this.model.get("type")).attr("placeholder", this.model.get("placeholder")).css("color", this.model.get("color") || "").css("border-color", this.model.get("color") || "");
            var datalist = this.model.get("datalist");
            if ($.isArray(datalist) && datalist.length > 0) {
                this.$el.autocomplete({
                    source: function source(request, response) {
                        response(self.model.get("datalist"));
                    },
                    change: function change() {
                        self._onchange();
                    }
                });
            }
            if (this.model.get("value") !== this.$el.val()) {
                this.$el.val(this.model.get("value"));
            }
            _.each(["readonly", "disabled"], function(attr_name) {
                self.model.get(attr_name) ? self.$el.attr(attr_name, true) : self.$el.removeAttr(attr_name);
            });
            this.$el[this.model.get("visible") ? "show" : "hide"]();
            return this;
        },
        _onchange: function _onchange() {
            this.value(this.$el.val());
            this.model.get("onchange") && this.model.get("onchange")(this.model.get("value"));
        }
    });

    /** Creates a hidden element input field used e.g. in the tool form */
    var Hidden = exports.Hidden = Backbone.View.extend({
        initialize: function initialize(options) {
            this.model = options && options.model || new Backbone.Model(options);
            this.setElement($("<div/>").append(this.$info = $("<div/>")).append(this.$hidden = $("<div/>")));
            this.listenTo(this.model, "change", this.render, this);
            this.render();
        },
        value: function value(new_val) {
            new_val !== undefined && this.model.set("value", new_val);
            return this.model.get("value");
        },
        render: function render() {
            this.$el.attr("id", this.model.id);
            this.$hidden.val(this.model.get("value"));
            this.model.get("info") ? this.$info.show().text(this.model.get("info")) : this.$info.hide();
            return this;
        }
    });

    /** Creates a upload element input field */
    var Upload = exports.Upload = Backbone.View.extend({
        initialize: function initialize(options) {
            var self = this;
            this.model = options && options.model || new Backbone.Model(options);
            this.setElement($("<div/>").append(this.$info = $("<div/>")).append(this.$file = $("<input/>").attr("type", "file").addClass("ui-margin-bottom")).append(this.$text = $("<textarea/>").addClass("ui-textarea").attr("disabled", true)).append(this.$wait = $("<i/>").addClass("fa fa-spinner fa-spin")));
            this.listenTo(this.model, "change", this.render, this);
            this.$file.on("change", function(e) {
                self._readFile(e);
            });
            this.render();
        },
        value: function value(new_val) {
            new_val !== undefined && this.model.set("value", new_val);
            return this.model.get("value");
        },
        render: function render() {
            this.$el.attr("id", this.model.id);
            this.model.get("info") ? this.$info.show().text(this.model.get("info")) : this.$info.hide();
            this.model.get("value") ? this.$text.text(this.model.get("value")).show() : this.$text.hide();
            this.model.get("wait") ? this.$wait.show() : this.$wait.hide();
            return this;
        },
        _readFile: function _readFile(e) {
            var self = this;
            var file = e.target.files && e.target.files[0];
            if (file) {
                var reader = new FileReader();
                reader.onload = function() {
                    self.model.set({
                        wait: false,
                        value: this.result
                    });
                };
                this.model.set({
                    wait: true,
                    value: null
                });
                reader.readAsText(file);
            }
        }
    });

    /* Make more Ui stuff directly available at this namespace (for backwards
     * compatibility).  We should eliminate this practice, though, and just require
     * what we need where we need it, allowing for better package optimization.
     */

    var Button = exports.Button = _uiButtons2.default.ButtonDefault;
    var ButtonIcon = exports.ButtonIcon = _uiButtons2.default.ButtonIcon;
    var ButtonCheck = exports.ButtonCheck = _uiButtons2.default.ButtonCheck;
    var ButtonMenu = exports.ButtonMenu = _uiButtons2.default.ButtonMenu;
    var ButtonLink = exports.ButtonLink = _uiButtons2.default.ButtonLink;
    var Checkbox = exports.Checkbox = _uiOptions2.default.Checkbox;
    var RadioButton = exports.RadioButton = _uiOptions2.default.RadioButton;
    var Radio = exports.Radio = _uiOptions2.default.Radio;
    exports.Select = _uiSelectDefault2.default;
    exports.Slider = _uiSlider2.default;
    exports.Drilldown = _uiDrilldown2.default;
    exports.default = {
        Button: _uiButtons2.default.ButtonDefault,
        ButtonIcon: _uiButtons2.default.ButtonIcon,
        ButtonCheck: _uiButtons2.default.ButtonCheck,
        ButtonMenu: _uiButtons2.default.ButtonMenu,
        ButtonLink: _uiButtons2.default.ButtonLink,
        Input: Input,
        Label: Label,
        Message: Message,
        UnescapedMessage: UnescapedMessage,
        Upload: Upload,
        Modal: _uiModal2.default,
        RadioButton: _uiOptions2.default.RadioButton,
        Checkbox: _uiOptions2.default.Checkbox,
        Radio: _uiOptions2.default.Radio,
        Select: _uiSelectDefault2.default,
        Hidden: Hidden,
        Slider: _uiSlider2.default,
        Drilldown: _uiDrilldown2.default
    };
});
//# sourceMappingURL=../../../maps/mvc/ui/ui-misc.js.map
