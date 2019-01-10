import _ from "underscore";
import DATASET from "mvc/dataset/dataset-model";
import HISTORY_CONTENT from "mvc/history/history-content-model";
import BASE_MVC from "mvc/base-mvc";

//==============================================================================
var _super = DATASET.DatasetAssociation;

var hcontentMixin = HISTORY_CONTENT.HistoryContentMixin;
/** @class (HDA) model for a Galaxy dataset contained in and related to a history.
 */
var HistoryDatasetAssociation = _super.extend(
    BASE_MVC.mixin(
        hcontentMixin,
        /** @lends HistoryDatasetAssociation.prototype */ {
            /** default attributes for a model */
            defaults: _.extend({}, _super.prototype.defaults, hcontentMixin.defaults, {
                history_content_type: "dataset",
                model_class: "HistoryDatasetAssociation"
            })
        }
    )
);

//==============================================================================
export default {
    HistoryDatasetAssociation: HistoryDatasetAssociation
};
