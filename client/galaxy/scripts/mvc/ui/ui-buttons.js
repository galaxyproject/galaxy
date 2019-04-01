/** This module contains all button views. */
import $ from "jquery";
import Utils from "utils/utils";
import Backbone from "backbone";

/** This renders the default button which is used e.g. at the bottom of the upload modal. */
var Button = Backbone.View.extend({
    initialize: function(options) {
        this.model =
            (options && options.model) ||
            new Backbone.Model({
                id: Utils.uid(),
                title: "",
                icon: "",
                cls: "btn btn-secondary",
                wait: false,
                wait_text: "Sending...",
                wait_cls: "btn btn-info",
                disabled: false,
                percentage: -1,
                visible: true
            }).set(options);
        this.setElement(
            $("<button/>")
                .attr("type", "button")
                .append((this.$icon = $("<i/>")))
                .append((this.$title = $("<span/>")))
                .append((this.$progress = $("<div/>").append((this.$progress_bar = $("<div/>")))))
        );
        this.listenTo(this.model, "change", this.render, this);
        this.render();
    },

    render: function() {
        var options = this.model.attributes;
        this.$el
            .removeClass()
            .addClass("ui-button-default")
            .addClass(options.disabled && "disabled")
            .attr("id", options.id)
            .attr("disabled", options.disabled)
            .css("display", options.visible ? "inline-block" : "none")
            .off("click")
            .on("click", () => {
                $(".tooltip").hide();
                options.onclick && !this.disabled && options.onclick();
            })
            .tooltip({ title: options.tooltip || "", placement: "bottom" });
        this.$progress.addClass("progress").css("display", options.percentage !== -1 ? "block" : "none");
        this.$progress_bar.addClass("progress-bar").css({ width: `${options.percentage}%` });
        this.$icon.removeClass().addClass("icon fa");
        this.$title.removeClass().addClass("title");
        if (options.wait) {
            this.$el.addClass(options.wait_cls).prop("disabled", true);
            this.$icon.addClass("fa-spinner fa-spin mr-1");
            this.$title.html(options.wait_text);
        } else {
            this.$el.addClass(options.cls);
            this.$icon.addClass(options.icon);
            if (options.title) {
                this.$title.html(options.title);
                if (options.icon) {
                    this.$icon.addClass("mr-1");
                }
            }
        }
    },

    /** Show button */
    show: function() {
        this.model.set("visible", true);
    },

    /** Hide button */
    hide: function() {
        this.model.set("visible", false);
    },

    /** Disable button */
    disable: function() {
        this.model.set("disabled", true);
    },

    /** Enable button */
    enable: function() {
        this.model.set("disabled", false);
    },

    /** Show spinner to indicate that the button is not ready to be clicked */
    wait: function() {
        this.model.set("wait", true);
    },

    /** Hide spinner to indicate that the button is ready to be clicked */
    unwait: function() {
        this.model.set("wait", false);
    },

    /** Change icon */
    setIcon: function(icon) {
        this.model.set("icon", icon);
    }
});

/** This button allows the right-click/open-in-new-tab feature, its used e.g. for panel buttons. */
var ButtonLink = Button.extend({
    initialize: function(options) {
        this.model =
            (options && options.model) ||
            new Backbone.Model({
                id: Utils.uid(),
                visible: true,
                title: "",
                icon: "",
                cls: ""
            }).set(options);
        this.setElement($("<a/>").append((this.$icon = $("<span/>"))));
        this.listenTo(this.model, "change", this.render, this);
        this.render();
    },

    render: function() {
        var options = this.model.attributes;
        this.$el
            .removeClass()
            .addClass(options.cls)
            .attr({
                id: options.id,
                href: options.href || "javascript:void(0)",
                title: options.title,
                target: options.target || "_top",
                disabled: options.disabled
            })
            .css("display", options.visible ? "inline-block" : "none")
            .tooltip({ placement: "bottom" })
            .off("click")
            .on("click", () => {
                options.onclick && !options.disabled && options.onclick();
            });
        this.$icon.removeClass().addClass(options.icon);
    }
});

/** The check button is used in the tool form and allows to distinguish between multiple states e.g. all, partially and nothing selected. */
var ButtonCheck = Backbone.View.extend({
    initialize: function(options) {
        this.model =
            (options && options.model) ||
            new Backbone.Model({
                id: Utils.uid(),
                title: "Select/Unselect all",
                icons: ["fa-square-o", "fa-minus-square-o", "fa-check-square-o"],
                value: 0,
                visible: true,
                onchange: function() {}
            }).set(options);
        this.setElement(
            $("<div/>")
                .addClass("mb-2")
                .append((this.$icon = $("<span/>")))
                .append((this.$title = $("<span/>")))
        );
        this.listenTo(this.model, "change", this.render, this);
        this.render();
    },

    render: function(options) {
        options = this.model.attributes;
        this.$el
            .addClass("ui-button-check")
            .css("display", options.visible ? "inline-block" : "none")
            .off("click")
            .on("click", () => {
                this.model.set("value", (this.model.get("value") === 0 && 2) || 0);
                options.onclick && options.onclick();
            });
        this.$title.html(options.title);
        this.$icon
            .removeClass()
            .addClass("icon fa mr-1")
            .addClass(options.icons[options.value]);
    },

    /* Sets a new value and/or returns the value.
     * @param{Integer}   new_val - Set a new value 0=unchecked, 1=partial and 2=checked.
     * OR:
     * @param{Integer}   new_val - Number of selected options.
     * @param{Integer}   total   - Total number of available options.
     */
    value: function(new_val, total) {
        if (new_val !== undefined) {
            if (total && new_val !== 0) {
                new_val = (new_val !== total && 1) || 2;
            }
            this.model.set("value", new_val);
            this.model.get("onchange")(this.model.get("value"));
        }
        return this.model.get("value");
    }
});

/** This class creates a button with dropdown menu. */
var ButtonMenu = Backbone.View.extend({
    $menu: null,
    initialize: function(options) {
        this.model =
            (options && options.model) ||
            new Backbone.Model({
                id: "",
                title: "",
                pull: "right",
                icon: null,
                onclick: null,
                cls: "btn btn-secondary float-right",
                tooltip: "",
                target: "",
                href: "",
                onunload: null,
                visible: true,
                tag: ""
            }).set(options);
        this.collection = new Backbone.Collection();
        this.setElement(
            $("<div/>").append(
                (this.$root = $("<button/>")
                    .append((this.$icon = $("<i/>")))
                    .append((this.$title = $("<span/>"))))
            )
        );
        this.listenTo(this.model, "change", this.render, this);
        this.listenTo(this.collection, "change add remove reset", this.render, this);
        this.render();
    },

    render: function() {
        var options = this.model.attributes;
        this.$el
            .removeClass()
            .addClass("dropdown")
            .attr("id", options.id)
            .css({
                display: options.visible && this.collection.where({ visible: true }).length > 0 ? "block" : "none"
            });
        this.$root
            .addClass(options.cls)
            .attr("data-toggle", "dropdown")
            .tooltip({ title: options.tooltip || "", placement: "bottom" })
            .off("click")
            .on("click", e => {
                $(".tooltip").hide();
                e.preventDefault();
                options.onclick && options.onclick();
            });
        this.$icon
            .removeClass()
            .addClass("icon fa")
            .addClass(options.icon);
        options.title &&
            this.$title
                .removeClass()
                .addClass("title ml-1")
                .html(options.title);
        this.$menu && this.$menu.remove();
        if (this.collection.length > 0) {
            this.$menu = $("<ul/>")
                .addClass("menu dropdown-menu dropdown-menu-right")
                .addClass(`pull-${this.model.get("pull")}`)
                .attr("role", "menu");
            this.$el.append(this.$menu);
        }
        this.collection.each(submodel => {
            var suboptions = submodel.attributes;
            if (suboptions.visible) {
                var $link = $("<a/>")
                    .addClass("dropdown-item")
                    .attr({
                        href: suboptions.href,
                        target: suboptions.target
                    })
                    .append(
                        $("<i/>")
                            .addClass("fa mr-2")
                            .addClass(suboptions.icon)
                            .css("display", suboptions.icon ? "inline-block" : "none")
                    )
                    .append(suboptions.title)
                    .on("click", e => {
                        if (suboptions.onclick) {
                            e.preventDefault();
                            suboptions.onclick();
                        }
                    });
                this.$menu.append($("<li/>").append($link));
                suboptions.divider && this.$menu.append($("<li/>").addClass("divider"));
            }
        });
    },

    /** Add a new menu item */
    addMenu: function(options) {
        this.collection.add(
            Utils.merge(options, {
                title: "",
                target: "",
                href: "",
                onclick: null,
                divider: false,
                visible: true,
                icon: null,
                cls: "button-menu btn-group"
            })
        );
    }
});

export default {
    Button: Button,
    ButtonLink: ButtonLink,
    ButtonCheck: ButtonCheck,
    ButtonMenu: ButtonMenu
};
