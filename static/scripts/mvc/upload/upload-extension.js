define("mvc/upload/upload-extension", ["exports", "utils/utils", "mvc/ui/ui-popover"], function(exports, _utils, _uiPopover) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _utils2 = _interopRequireDefault(_utils);

    var _uiPopover2 = _interopRequireDefault(_uiPopover);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    exports.default = Backbone.View.extend({
        initialize: function initialize(options) {
            this.model = new Backbone.Model(options);
            this.setElement("<div/>");
            this.render();
        },

        render: function render() {
            var self = this;
            var options = this.model.attributes;
            var description = _.findWhere(options.list, {
                id: options.extension
            });
            this.extension_popup && this.extension_popup.remove();
            this.extension_popup = new _uiPopover2.default.View({
                placement: options.placement || "bottom",
                container: options.$el
            });
            this.extension_popup.title(options.title);
            this.extension_popup.empty();
            this.extension_popup.append(this._templateDescription(description));
            this.extension_popup.show();
        },

        /** Template for extensions description */
        _templateDescription: function _templateDescription(options) {
            if (options.description) {
                var tmpl = options.description;
                if (options.description_url) {
                    tmpl += "&nbsp;(<a href=\"" + options.description_url + "\" target=\"_blank\">read more</a>)";
                }
                return tmpl;
            } else {
                return "There is no description available for this file extension.";
            }
        }
    });
});
//# sourceMappingURL=../../../maps/mvc/upload/upload-extension.js.map
