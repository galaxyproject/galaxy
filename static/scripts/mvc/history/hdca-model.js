define("mvc/history/hdca-model", ["exports", "mvc/collection/collection-model", "mvc/history/history-content-model", "utils/localization"], function(exports, _collectionModel, _historyContentModel, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _collectionModel2 = _interopRequireDefault(_collectionModel);

    var _historyContentModel2 = _interopRequireDefault(_historyContentModel);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /*==============================================================================
    
    Models for DatasetCollections contained within a history.
    
    ==============================================================================*/
    var hcontentMixin = _historyContentModel2.default.HistoryContentMixin;

    var DC = _collectionModel2.default.DatasetCollection;

    //==============================================================================
    /** @class Backbone model for List Dataset Collection within a History.
     */
    var HistoryDatasetCollection = DC.extend(hcontentMixin).extend(
        /** @lends HistoryDatasetCollection.prototype */
        {
            defaults: _.extend(_.clone(DC.prototype.defaults), {
                history_content_type: "dataset_collection",
                model_class: "HistoryDatasetCollectionAssociation"
            }),

            //==============================================================================
            /** Override to post to contents route w/o id. */
            save: function save(attributes, options) {
                if (this.isNew()) {
                    options = options || {};
                    options.url = this.urlRoot + this.get("history_id") + "/contents";
                    attributes = attributes || {};
                    attributes.type = "dataset_collection";
                }
                return DC.prototype.save.call(this, attributes, options);
            },

            /** String representation. */
            toString: function toString() {
                return "History" + DC.prototype.toString.call(this);
            }
        });

    //==============================================================================
    exports.default = {
        HistoryDatasetCollection: HistoryDatasetCollection
    };
});
//# sourceMappingURL=../../../maps/mvc/history/hdca-model.js.map
