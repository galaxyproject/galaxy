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
                title: "Convert spaces to tabs"
            },
            {
                id: "to_posix_lines",
                title: "Use POSIX standard"
            }
        ]
    },

    initialize: function(options) {
        this.model = options.model;
        this.setElement($("<div/>").addClass("upload-settings"));
        this.$el.append($("<div/>").addClass("upload-settings-cover"));
        this.$el.append(
            $("<table/>")
                .addClass("upload-settings-table grid")
                .append("<tbody/>")
        );
        this.$cover = this.$(".upload-settings-cover");
        this.$table = this.$(".upload-settings-table > tbody");
        this.listenTo(this.model, "change", this.render, this);
        this.model.trigger("change");
    },

    render: function() {
        this.$table.empty();
        _.each(this.options.parameters, parameter => {
            var $checkbox = $("<div/>")
                .addClass(`upload-${parameter.id} fa`)
                .addClass((this.model.get(parameter.id) && this.options.class_check) || this.options.class_uncheck);
            const $row = $("<tr/>")
                .append($("<td/>").append($checkbox))
                .append($("<td/>").append(parameter.title))
                .on("click", () => {
                    this.model.get("enabled") && this.model.set(parameter.id, !this.model.get(parameter.id));
                });
            this.$table.append($row);
        });
        this.$cover[(this.model.get("enabled") && "hide") || "show"]();
    }
});
