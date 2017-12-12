define("mvc/ui/ui-tabs", ["exports"], function(exports) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });
    /**
     *  Renders tabs e.g. used in the charts editor, behaves similar to repeat and section rendering
     */
    var View = exports.View = Backbone.View.extend({
        initialize: function initialize(options) {
            this.collection = new Backbone.Collection();
            this.model = options && options.model || new Backbone.Model({
                onchange: null,
                visible: true
            }).set(options);
            this.setElement($(this._template()));
            this.$nav = this.$(".tab-navigation");
            this.$content = this.$(".tab-content");
            this.$el.on("click", function() {
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

        render: function render() {
            var id = this.model.get("current");
            id = this.$("#" + id).length > 0 ? id : this.first();
            if (id) {
                this.$nav.children().removeClass("active");
                this.$content.children().removeClass("active");
                this.$("#tab-" + id).addClass("active");
                this.$("#" + id).addClass("active");
            }
            this.$el[this.model.get("visible") ? "fadeIn" : "fadeOut"]("fast");
            this.$nav[this.size() > 1 ? "show" : "hide"]();
        },

        /** Returns tab id for currently shown tab */
        current: function current() {
            return this.model.get("current");
        },

        /** Show tab view and highlight a tab by id */
        show: function show(id) {
            if (id) {
                this.model.set({
                    current: id,
                    visible: true
                });
                this.model.get("onchange") && this.model.get("onchange")(id);
            }
        },

        /** Hide tab view */
        hide: function hide() {
            this.model.set("visible", false);
        },

        /** Returns first tab */
        first: function first() {
            var model = this.collection.first();
            return model && model.id;
        },

        /** Returns current number of tabs */
        size: function size() {
            return this.collection.length;
        },

        /** Adds a new tab */
        add: function add(options) {
            this.collection.add(options);
        },

        /** Delete tab */
        del: function del(id) {
            this.collection.remove(id);
        },

        /** Delete all tabs */
        delAll: function delAll() {
            this.collection.reset();
        },

        /** Show tab */
        showTab: function showTab(id) {
            this.collection.get(id).set("hidden", false);
        },

        /** Hide tab */
        hideTab: function hideTab(id) {
            this.collection.get(id).set("hidden", true);
        },

        /** Adds a new tab */
        _add: function _add(tab_model) {
            var self = this;
            var options = tab_model.attributes;
            this.$content.append($("<div/>").attr("id", options.id).addClass("tab-pane").append(options.$el));
            this.$nav.append($(this._template_tab(options)).show().tooltip({
                title: options.tooltip,
                placement: "bottom",
                container: self.$el
            }).on("click", function(e) {
                e.preventDefault();
                self.show(options.id);
            }));
            if (this.size() == 1) {
                this.show(options.id);
            }
        },

        /** Delete tab */
        _remove: function _remove(tab_model) {
            this.$("#tab-" + tab_model.id).remove();
            this.$("#" + tab_model.id).remove();
        },

        /** Reset collection */
        _reset: function _reset() {
            this.$nav.empty();
            this.$content.empty();
        },

        /** Change tab */
        _change: function _change(tab_model) {
            this.$("#tab-" + tab_model.id)[tab_model.get("hidden") ? "hide" : "show"]();
        },

        /** Main template */
        _template: function _template() {
            return $("<div/>").addClass("ui-tabs tabbable tabs-left").append($("<ul/>").addClass("tab-navigation nav nav-tabs")).append($("<div/>").addClass("tab-content"));
        },

        /** Tab template */
        _template_tab: function _template_tab(options) {
            var $tmpl = $("<li/>").addClass("tab-element").attr("id", "tab-" + options.id).append($("<a/>").attr("id", "tab-title-link-" + options.id));
            var $href = $tmpl.find("a");
            options.icon && $href.append($("<i/>").addClass("tab-icon fa").addClass(options.icon));
            $href.append($("<span/>").attr("id", "tab-title-text-" + options.id).addClass("tab-title-text").append(options.title));
            return $tmpl;
        }
    });

    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/ui/ui-tabs.js.map
