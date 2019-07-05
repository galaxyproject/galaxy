import _ from "underscore";
import DC_MODEL from "mvc/collection/collection-model";
import HISTORY_CONTENT from "mvc/history/history-content-model";

/*==============================================================================

Models for DatasetCollections contained within a history.

==============================================================================*/
var hcontentMixin = HISTORY_CONTENT.HistoryContentMixin;

var DC = DC_MODEL.DatasetCollection;

//==============================================================================
/** @class Backbone model for List Dataset Collection within a History.
 */
var HistoryDatasetCollection = DC.extend(hcontentMixin).extend(
    /** @lends HistoryDatasetCollection.prototype */ {
        defaults: _.extend(_.clone(DC.prototype.defaults), {
            history_content_type: "dataset_collection",
            model_class: "HistoryDatasetCollectionAssociation"
        }),

        //==============================================================================
        /** Override to post to contents route w/o id. */
        save: function(attributes, options) {
            if (this.isNew()) {
                options = options || {};
                options.url = `${this.urlRoot + this.get("history_id")}/contents`;
                attributes = attributes || {};
                attributes.type = "dataset_collection";
            }
            return DC.prototype.save.call(this, attributes, options);
        },

        /** String representation. */
        toString: function() {
            return `History${DC.prototype.toString.call(this)}`;
        }
    }
);

//==============================================================================
export default {
    HistoryDatasetCollection: HistoryDatasetCollection
};
