define("mvc/ui/ui-portlet", ["exports", "utils/utils", "mvc/ui/ui-misc"], function(exports, _utils, _uiMisc) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });
    exports.View = undefined;

    var _utils2 = _interopRequireDefault(_utils);

    var _uiMisc2 = _interopRequireDefault(_uiMisc);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var View = exports.View = Backbone.View.extend({
        visible: false,
        initialize: function initialize(options) {
            var self = this;
            this.model = options && options.model || new Backbone.Model({
                id: _utils2.default.uid(),
                cls: "ui-portlet",
                title: "",
                icon: "",
                buttons: null,
                body: null,
                scrollable: true,
                nopadding: false,
                operations: null,
                collapsible: false,
                collapsible_button: false,
                collapsed: false,
                onchange_title: null
            }).set(options);
            this.setElement(this._template());

            // link all dom elements
            this.$body = this.$(".portlet-body");
            this.$title_text = this.$(".portlet-title-text");
            this.$title_icon = this.$(".portlet-title-icon");
            this.$header = this.$(".portlet-header");
            this.$content = this.$(".portlet-content");
            this.$backdrop = this.$(".portlet-backdrop");
            this.$buttons = this.$(".portlet-buttons");
            this.$operations = this.$(".portlet-operations");

            // add body to component list
            this.model.get("body") && this.append(this.model.get("body"));

            // add icon for collapsible option
            this.collapsible_button = new _uiMisc2.default.ButtonIcon({
                icon: "fa-eye",
                tooltip: "Collapse/Expand",
                cls: "ui-button-icon-plain",
                onclick: function onclick() {
                    self[self.collapsed ? "expand" : "collapse"]();
                }
            });
            this.render();
        },

        render: function render() {
            var self = this;
            var options = this.model.attributes;
            this.$el.removeClass().addClass(options.cls).attr("id", options.id);
            this.$header[options.title ? "show" : "hide"]();
            this.$title_text.html(options.title);
            _.each([this.$content, this.$body], function($el) {
                $el[options.nopadding ? "addClass" : "removeClass"]("no-padding");
            });

            // render title icon
            if (options.icon) {
                this.$title_icon.removeClass().addClass("portlet-title-icon fa").addClass(options.icon).show();
            } else {
                this.$title_icon.hide();
            }

            // make portlet collapsible
            this.$title_text[options.collapsible ? "addClass" : "removeClass"]("no-highlight collapsible").off();
            if (options.collapsible) {
                this.$title_text.on("click", function() {
                    self[self.collapsed ? "expand" : "collapse"]();
                });
                options.collapsed ? this.collapse() : this.expand();
            }

            // allow title editing
            this.$title_text.prop("disabled", !options.onchange_title);
            options.onchange_title && this.$title_text.make_text_editable({
                on_finish: function on_finish(new_title) {
                    options.onchange_title(new_title);
                }
            });

            // render buttons
            if (options.buttons) {
                this.$buttons.empty().show();
                $.each(this.model.get("buttons"), function(name, item) {
                    item.$el.prop("id", name);
                    self.$buttons.append(item.$el);
                });
            } else {
                this.$buttons.hide();
            }

            // render operations
            this.$operations.empty;
            if (options.collapsible_button) {
                this.$operations.append(this.collapsible_button.$el);
            }
            if (options.operations) {
                $.each(options.operations, function(name, item) {
                    item.$el.prop("id", name);
                    self.$operations.append(item.$el);
                });
            }
            return this;
        },

        /** Append new doms to body */
        append: function append($el) {
            this.$body.append($el);
        },

        /** Remove all content */
        empty: function empty() {
            this.$body.empty();
        },

        /** Return header element */
        header: function header() {
            return this.$header;
        },

        /** Return body element */
        body: function body() {
            return this.$body;
        },

        /** Show portlet */
        show: function show() {
            this.visible = true;
            this.$el.fadeIn("fast");
        },

        /** Hide portlet */
        hide: function hide() {
            this.visible = false;
            this.$el.hide();
        },

        /** Enable a particular button */
        enableButton: function enableButton(id) {
            this.$buttons.find("#" + id).prop("disabled", false);
        },

        /** Disable a particular button */
        disableButton: function disableButton(id) {
            this.$buttons.find("#" + id).prop("disabled", true);
        },

        /** Hide a particular operation */
        hideOperation: function hideOperation(id) {
            this.$operations.find("#" + id).hide();
        },

        /** Show a particular operation */
        showOperation: function showOperation(id) {
            this.$operations.find("#" + id).show();
        },

        /** Replaces the event callback of an existing operation */
        setOperation: function setOperation(id, callback) {
            this.$operations.find("#" + id).off("click").on("click", callback);
        },

        /** Change title */
        title: function title(new_title) {
            new_title && this.$title_text.html(new_title);
            return this.$title_text.html();
        },

        /** Collapse portlet */
        collapse: function collapse() {
            this.collapsed = true;
            this.$content.height("0%");
            this.$body.hide();
            this.collapsible_button.setIcon("fa-eye-slash");
        },

        /** Expand portlet */
        expand: function expand() {
            this.collapsed = false;
            this.$content.height("100%");
            this.$body.fadeIn("fast");
            this.collapsible_button.setIcon("fa-eye");
        },

        /** Disable content access */
        disable: function disable() {
            this.$backdrop.show();
        },

        /** Enable content access */
        enable: function enable() {
            this.$backdrop.hide();
        },

        _template: function _template() {
            return $("<div/>").append($("<div/>").addClass("portlet-header").append($("<div/>").addClass("portlet-operations")).append($("<div/>").addClass("portlet-title").append($("<i/>").addClass("portlet-title-icon")).append($("<span/>").addClass("portlet-title-text")))).append($("<div/>").addClass("portlet-content").append($("<div/>").addClass("portlet-body")).append($("<div/>").addClass("portlet-buttons"))).append($("<div/>").addClass("portlet-backdrop"));
        }
    });
    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/ui/ui-portlet.js.map
