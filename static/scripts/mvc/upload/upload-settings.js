define("mvc/upload/upload-settings", ["exports", "utils/utils"], function(exports, _utils) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _utils2 = _interopRequireDefault(_utils);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    exports.default = Backbone.View.extend({
        options: {
            class_check: "fa-check-square-o",
            class_uncheck: "fa-square-o",
            parameters: [{
                id: "space_to_tab",
                title: "Convert spaces to tabs"
            }, {
                id: "to_posix_lines",
                title: "Use POSIX standard"
            }]
        },

        initialize: function initialize(options) {
            var self = this;
            this.model = options.model;
            this.setElement($("<div/>").addClass("upload-settings"));
            this.$el.append($("<div/>").addClass("upload-settings-cover"));
            this.$el.append($("<table/>").addClass("upload-settings-table ui-table-striped").append("<tbody/>"));
            this.$cover = this.$(".upload-settings-cover");
            this.$table = this.$(".upload-settings-table > tbody");
            this.listenTo(this.model, "change", this.render, this);
            this.model.trigger("change");
        },

        render: function render() {
            var self = this;
            this.$table.empty();
            _.each(this.options.parameters, function(parameter) {
                var $checkbox = $("<div/>").addClass("upload-" + parameter.id + " upload-icon-button fa").addClass(self.model.get(parameter.id) && self.options.class_check || self.options.class_uncheck).on("click", function() {
                    self.model.get("enabled") && self.model.set(parameter.id, !self.model.get(parameter.id));
                });
                self.$table.append($("<tr/>").append($("<td/>").append($checkbox)).append($("<td/>").append(parameter.title)));
            });
            this.$cover[this.model.get("enabled") && "hide" || "show"]();
        }
    });
});
//# sourceMappingURL=../../../maps/mvc/upload/upload-settings.js.map
