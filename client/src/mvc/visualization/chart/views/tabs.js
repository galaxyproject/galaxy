/**
 *  Renders tabs e.g. used in the charts editor, behaves similar to repeat and section rendering
 */
import Backbone from "backbone";
import $ from "jquery";

export var View = Backbone.View.extend({
    initialize: function (options) {
        this.collection = new Backbone.Collection();
        this.model =
            (options && options.model) ||
            new Backbone.Model({
                onchange: null,
                visible: true,
            }).set(options);
        this.setElement($(this._template()));
        this.$nav = this.$(".tab-navigation");
        this.$content = this.$(".tab-content");
        this.$el.on("click", () => {
            $(".tooltip").hide();
        });
        this.render();
        this.listenTo(this.model, "change", this.render, this);
        this.listenTo(this.collection, "add", this._add, this);
        this.listenTo(this.collection, "remove", this._remove, this);
        this.listenTo(this.collection, "change", this._change, this);
        this.listenTo(this.collection, "reset", this._reset, this);
        this.listenTo(this.collection, "add remove reset", this.render, this);
    },

    render: function () {
        var id = this.model.get("current");
        id = this.$(`#${id}`).length > 0 ? id : this.first();
        if (id) {
            this.$nav.find(".nav-link.active").removeClass("active");
            this.$content.children().removeClass("active");
            this.$(`#tab-${id} .nav-link`).addClass("active");
            this.$(`#${id}`).addClass("active");
        }
        this.$el[this.model.get("visible") ? "fadeIn" : "fadeOut"]("fast");
        this.$nav[this.size() > 1 ? "show" : "hide"]();
    },

    /** Returns tab id for currently shown tab */
    current: function () {
        return this.model.get("current");
    },

    /** Show tab view and highlight a tab by id */
    show: function (id) {
        if (id) {
            this.model.set({ current: id, visible: true });
            this.model.get("onchange") && this.model.get("onchange")(id);
        }
    },

    /** Hide tab view */
    hide: function () {
        this.model.set("visible", false);
    },

    /** Returns first tab */
    first: function () {
        var model = this.collection.first();
        return model && model.id;
    },

    /** Returns current number of tabs */
    size: function () {
        return this.collection.length;
    },

    /** Adds a new tab */
    add: function (options) {
        this.collection.add(options);
    },

    /** Delete tab */
    del: function (id) {
        this.collection.remove(id);
    },

    /** Delete all tabs */
    delAll: function () {
        this.collection.reset();
    },

    /** Show tab */
    showTab: function (id) {
        this.collection.get(id).set("hidden", false);
    },

    /** Hide tab */
    hideTab: function (id) {
        this.collection.get(id).set("hidden", true);
    },

    /** Adds a new tab */
    _add: function (tab_model) {
        var self = this;
        var options = tab_model.attributes;
        this.$content.append($("<div/>").attr("id", options.id).addClass("tab-pane").append(options.$el));
        this.$nav.append(
            $(this._template_tab(options))
                .show()
                .tooltip({
                    title: options.tooltip || "",
                    placement: "bottom",
                    container: self.$el,
                })
                .on("click", (e) => {
                    e.preventDefault();
                    self.show(options.id);
                })
        );
        if (this.size() == 1) {
            this.show(options.id);
        }
    },

    /** Delete tab */
    _remove: function (tab_model) {
        this.$(`#tab-${tab_model.id}`).remove();
        this.$(`#${tab_model.id}`).remove();
    },

    /** Reset collection */
    _reset: function () {
        this.$nav.empty();
        this.$content.empty();
    },

    /** Change tab */
    _change: function (tab_model) {
        this.$(`#tab-${tab_model.id}`)[tab_model.get("hidden") ? "hide" : "show"]();
    },

    /** Main template */
    _template: function () {
        return $("<div/>")
            .addClass("tabbable tabs-left")
            .append($("<ul/>").attr("style", "display: flex").addClass("tab-navigation nav nav-tabs"))
            .append($("<div/>").addClass("tab-content"));
    },

    /** Tab template */
    _template_tab: function (options) {
        var $tmpl = $("<li/>")
            .addClass("nav-item")
            .attr("id", `tab-${options.id}`)
            .append(
                $("<a/>")
                    .addClass("nav-link")
                    .attr("id", `tab-title-link-${options.id}`)
                    .attr("href", "javascript:void(0);")
            );
        var $href = $tmpl.find("a");
        options.icon && $href.append($("<i/>").addClass("fa").addClass(options.icon));
        options.title &&
            $href.append(
                $("<span/>")
                    .attr("id", `tab-title-text-${options.id}`)
                    .addClass("tab-title-text ml-1")
                    .append(options.title)
            );
        return $tmpl;
    },
});

export default { View: View };
