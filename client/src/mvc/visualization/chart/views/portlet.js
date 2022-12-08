import $ from "jquery";
import Backbone from "backbone";
import Utils from "utils/utils";
import Ui from "mvc/ui/ui-misc";

export var View = Backbone.View.extend({
    visible: false,
    initialize: function (options) {
        var self = this;
        this.model =
            (options && options.model) ||
            new Backbone.Model({
                id: Utils.uid(),
                cls: "ui-portlet",
                title: "",
                icon: "",
                buttons: null,
                body: null,
                scrollable: true,
                operations: null,
                collapsible: false,
                collapsible_button: true,
                collapsed: false,
                onchange_title: null,
            }).set(options);
        this.setElement(this._template());
        this.section = options.section;

        // link all dom elements
        this.$body = this.$(".portlet-body");
        this.$title = this.$(".portlet-title");
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
        this.collapsible_button = new Ui.Button({
            icon: "fa-eye",
            tooltip: "Collapse/Expand",
            cls: "ui-button-icon-plain",
            onclick: function () {
                self[self.collapsed ? "expand" : "collapse"]();
            },
        });
        this.render();
    },

    render: function () {
        var self = this;
        var options = this.model.attributes;
        this.$el.removeClass().addClass(options.cls).attr("id", options.id);
        this.$header[options.title ? "show" : "hide"]();
        this.$title_text.html(options.title);
        if (options.title_id) {
            this.$title.attr("id", options.title_id);
        }

        // render title icon
        if (options.icon) {
            this.$title_icon.removeClass().addClass("portlet-title-icon fa mr-1").addClass(options.icon).show();
        } else {
            this.$title_icon.hide();
        }

        // make portlet collapsible
        this.$title_text[options.collapsible ? "addClass" : "removeClass"]("no-highlight collapsible").off();
        if (options.collapsible) {
            this.$title_text.on("click", () => {
                self[self.collapsed ? "expand" : "collapse"]();
            });
            options.collapsed ? this.collapse() : this.expand();
        }

        // allow title editing
        this.$title_text.prop("disabled", !options.onchange_title);
        options.onchange_title &&
            this.$title_text.make_text_editable({
                on_finish: function (new_title) {
                    options.onchange_title(new_title);
                },
            });

        // render buttons
        if (options.buttons) {
            this.$buttons.empty().show();
            $.each(this.model.get("buttons"), (name, item) => {
                if (item) {
                    item.$el.prop("id", name);
                    self.$buttons.append(item.$el);
                }
            });
        } else {
            this.$buttons.hide();
        }

        // render operations
        this.$operations.empty;
        if (options.collapsible && options.collapsible_button) {
            this.$operations.append(this.collapsible_button.$el);
        }
        if (options.operations) {
            $.each(options.operations, (name, item) => {
                item.$el.prop("id", name);
                self.$operations.append(item.$el);
            });
        }
        return this;
    },

    /** Append new doms to body */
    append: function ($el) {
        this.$body.append($el);
    },

    /** Remove all content */
    empty: function () {
        this.$body.empty();
    },

    /** Return header element */
    header: function () {
        return this.$header;
    },

    /** Return body element */
    body: function () {
        return this.$body;
    },

    /** Show portlet */
    show: function () {
        this.visible = true;
        this.$el.fadeIn("fast");
    },

    /** Hide portlet */
    hide: function () {
        this.visible = false;
        this.$el.hide();
    },

    /** Enable a particular button */
    enableButton: function (id) {
        this.$buttons.find(`#${id}`).prop("disabled", false);
    },

    /** Disable a particular button */
    disableButton: function (id) {
        this.$buttons.find(`#${id}`).prop("disabled", true);
    },

    /** Hide a particular operation */
    hideOperation: function (id) {
        this.$operations.find(`#${id}`).hide();
    },

    /** Show a particular operation */
    showOperation: function (id) {
        this.$operations.find(`#${id}`).show();
    },

    /** Replaces the event callback of an existing operation */
    setOperation: function (id, callback) {
        this.$operations.find(`#${id}`).off("click").on("click", callback);
    },

    /** Change title */
    title: function (new_title) {
        new_title && this.$title_text.html(new_title);
        return this.$title_text.html();
    },

    /** Collapse portlet */
    collapse: function () {
        this.collapsed = true;
        this.$content.hide();
        this.collapsible_button.setIcon("fa-eye-slash");
    },

    /** Expand portlet */
    expand: function () {
        this.collapsed = false;
        if (this.section) {
            this.section.renderOnce();
        }
        this.$content.show();
        this.collapsible_button.setIcon("fa-eye");
    },

    /** Disable content access */
    disable: function () {
        this.$backdrop.show();
    },

    /** Enable content access */
    enable: function () {
        this.$backdrop.hide();
    },

    _template: function () {
        return $("<div/>")
            .append(
                $("<div/>")
                    .addClass("portlet-header")
                    .append($("<div/>").addClass("portlet-operations"))
                    .append(
                        $("<div/>")
                            .addClass("portlet-title")
                            .append($("<i/>").addClass("portlet-title-icon"))
                            .append($("<span/>").addClass("portlet-title-text"))
                    )
            )
            .append(
                $("<div/>")
                    .addClass("portlet-content")
                    .append($("<div/>").addClass("portlet-body"))
                    .append($("<div/>").addClass("portlet-buttons mt-3 mb-3"))
            )
            .append($("<div/>").addClass("portlet-backdrop"));
    },
});
export default {
    View: View,
};
