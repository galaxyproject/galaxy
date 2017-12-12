define("mvc/upload/upload-button", ["exports", "utils/localization"], function(exports, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /** View for upload/progress bar button */

    var View = Backbone.View.extend({
        initialize: function initialize(options) {
            var self = this;
            this.model = options && options.model || new Backbone.Model({
                icon: "fa-upload",
                tooltip: (0, _localization2.default)("Download from URL or upload files from disk"),
                label: "Load Data",
                percentage: 0,
                status: "",
                onunload: function onunload() {},
                onclick: function onclick() {}
            }).set(options);
            this.setElement(this._template());
            this.$progress = this.$(".progress-bar");
            this.listenTo(this.model, "change", this.render, this);
            this.render();
            $(window).on("beforeunload", function() {
                return self.model.get("onunload")();
            });
        },

        render: function render() {
            var self = this;
            var options = this.model.attributes;
            this.$el.off("click").on("click", function(e) {
                options.onclick(e);
            }).tooltip({
                title: this.model.get("tooltip"),
                placement: "bottom"
            });
            this.$progress.removeClass().addClass("progress-bar").addClass("progress-bar-notransition").addClass(options.status != "" && "progress-bar-" + options.status).css({
                width: options.percentage + "%"
            });
        },

        /** Template */
        _template: function _template() {
            return '<div class="upload-button">' + '<div class="progress">' + '<div class="progress-bar"/>' + '<a class="panel-header-button" href="javascript:void(0)" id="tool-panel-upload-button">' + '<span class="fa fa-upload"/>' + "</a>" + "</div>" + "</div>";
        }
    });
    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/upload/upload-button.js.map
