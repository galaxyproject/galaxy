/** This renders the content of the settings popup, allowing users to specify flags i.e. for space-to-tab conversion **/
import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
export default Backbone.View.extend({
    options: {
        class_check: "fa-check-square-o",
        class_uncheck: "fa-square-o",
        parameters: [
            {
                id: "space_to_tab",
                title: "Convert spaces to tabs",
            },
            {
                id: "to_posix_lines",
                title: "Use POSIX standard",
            },
            {
                id: "deferred",
                title: "Defer dataset resolution",
            },
        ],
    },

    initialize: function (options) {
        this.model = options.model;
        this.setElement($("<div/>").addClass("upload-settings"));
        this.$el.append($("<div/>").addClass("upload-settings-cover"));
        this.$el.append($("<table/>").addClass("upload-settings-table grid").append("<tbody/>"));
        this.$cover = this.$(".upload-settings-cover");
        this.$table = this.$(".upload-settings-table > tbody");
        this.listenTo(this.model, "change", this.render, this);
        this.model.trigger("change");
    },

    render: function () {
        var self = this;
        this.$table.empty();
        _.each(this.options.parameters, (parameter) => {
            var $checkbox = $("<div/>")
                .addClass(`upload-${parameter.id} fa`)
                .addClass((self.model.get(parameter.id) && self.options.class_check) || self.options.class_uncheck);
            const $row = $("<tr/>")
                .append($("<td/>").append($checkbox))
                .append($("<td/>").append(parameter.title))
                .on("click", () => {
                    self.model.get("enabled") && self.model.set(parameter.id, !self.model.get(parameter.id));
                });
            self.$table.append($row);
        });
        this.$cover[(this.model.get("enabled") && "hide") || "show"]();
    },
});
