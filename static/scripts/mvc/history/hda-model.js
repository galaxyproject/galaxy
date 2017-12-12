define("mvc/history/hda-model", ["exports", "mvc/dataset/dataset-model", "mvc/history/history-content-model", "mvc/base-mvc", "utils/localization"], function(exports, _datasetModel, _historyContentModel, _baseMvc, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _datasetModel2 = _interopRequireDefault(_datasetModel);

    var _historyContentModel2 = _interopRequireDefault(_historyContentModel);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    //==============================================================================
    var _super = _datasetModel2.default.DatasetAssociation;

    var hcontentMixin = _historyContentModel2.default.HistoryContentMixin;
    /** @class (HDA) model for a Galaxy dataset contained in and related to a history.
     */
    var HistoryDatasetAssociation = _super.extend(_baseMvc2.default.mixin(hcontentMixin,
        /** @lends HistoryDatasetAssociation.prototype */
        {
            /** default attributes for a model */
            defaults: _.extend({}, _super.prototype.defaults, hcontentMixin.defaults, {
                history_content_type: "dataset",
                model_class: "HistoryDatasetAssociation"
            })
        }));

    //==============================================================================
    exports.default = {
        HistoryDatasetAssociation: HistoryDatasetAssociation
    };
});
//# sourceMappingURL=../../../maps/mvc/history/hda-model.js.map
