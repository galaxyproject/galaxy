define("mvc/history/hda-li", ["exports", "mvc/dataset/dataset-li", "mvc/base-mvc", "mvc/history/history-item-li", "utils/localization"], function(exports, _datasetLi, _baseMvc, _historyItemLi, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _datasetLi2 = _interopRequireDefault(_datasetLi);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _historyItemLi2 = _interopRequireDefault(_historyItemLi);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    //==============================================================================
    var _super = _datasetLi2.default.DatasetListItemView;
    /** @class Read only view for HistoryDatasetAssociation.
     *      Since there are no controls on the HDAView to hide the dataset,
     *      the primary thing this class does (currently) is override templates
     *      to render the HID.
     */
    var HDAListItemView = _super.extend(
        /** @lends HDAListItemView.prototype */
        {
            className: _super.prototype.className + " history-content",

            initialize: function initialize(attributes, options) {
                _super.prototype.initialize.call(this, attributes, options);
            },

            // ......................................................................... misc
            /** String representation */
            toString: function toString() {
                var modelString = this.model ? "" + this.model : "(no model)";
                return "HDAListItemView(" + modelString + ")";
            }
        });

    // ............................................................................ TEMPLATES
    /** underscore templates */
    HDAListItemView.prototype.templates = function() {
        var titleBarTemplate = function titleBarTemplate(dataset) {
            return "\n        <div class=\"title-bar clear\" tabindex=\"0\">\n            <span class=\"state-icon\"></span>\n            <div class=\"title\">\n                <span class=\"hid\">" + dataset.hid + "</span>\n                <span class=\"name\">" + _.escape(dataset.name) + "</span>\n            </div>\n            </br>\n            " + _historyItemLi2.default.nametagTemplate(dataset) + "\n        </div>\n    ";
        };

        var warnings = _.extend({}, _super.prototype.templates.warnings, {
            hidden: _baseMvc2.default.wrapTemplate([
                // add a warning when hidden
                "<% if( !dataset.visible ){ %>", '<div class="hidden-msg warningmessagesmall">', (0, _localization2.default)("This dataset has been hidden"), "</div>", "<% } %>"
            ], "dataset")
        });

        return _.extend({}, _super.prototype.templates, {
            titleBar: titleBarTemplate,
            warnings: warnings
        });
    }();

    //==============================================================================
    exports.default = {
        HDAListItemView: HDAListItemView
    };
});
//# sourceMappingURL=../../../maps/mvc/history/hda-li.js.map
