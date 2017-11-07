import DC_MODEL from "mvc/collection/collection-model";
import HISTORY_CONTENT from "mvc/history/history-content-model";
import _l from "utils/localization";

/*==============================================================================

Models for DatasetCollections contained within a history.

TODO:
    these might be compactable to one class if some duplication with
    collection-model is used.

==============================================================================*/
var hcontentMixin = HISTORY_CONTENT.HistoryContentMixin;

var ListDC = DC_MODEL.ListDatasetCollection;
var PairDC = DC_MODEL.PairDatasetCollection;
var ListPairedDC = DC_MODEL.ListPairedDatasetCollection;
var ListOfListsDC = DC_MODEL.ListOfListsDatasetCollection;

//==============================================================================
/** Override to post to contents route w/o id. */
function buildHDCASave(_super) {
    return function _save(attributes, options) {
        if (this.isNew()) {
            options = options || {};
            options.url = `${this.urlRoot + this.get("history_id")}/contents`;
            attributes = attributes || {};
            attributes.type = "dataset_collection";
        }
        return _super.call(this, attributes, options);
    };
}

//==============================================================================
/** @class Backbone model for List Dataset Collection within a History.
 */
var HistoryListDatasetCollection = ListDC.extend(hcontentMixin).extend(
    /** @lends HistoryListDatasetCollection.prototype */ {
        defaults: _.extend(_.clone(ListDC.prototype.defaults), {
            history_content_type: "dataset_collection",
            collection_type: "list",
            model_class: "HistoryDatasetCollectionAssociation"
        }),

        /** Override to post to contents route w/o id. */
        save: buildHDCASave(ListDC.prototype.save),

        /** String representation. */
        toString: function() {
            return `History${ListDC.prototype.toString.call(this)}`;
        }
    }
);

//==============================================================================
/** @class Backbone model for Pair Dataset Collection within a History.
 *  @constructs
 */
var HistoryPairDatasetCollection = PairDC.extend(hcontentMixin).extend(
    /** @lends HistoryPairDatasetCollection.prototype */ {
        defaults: _.extend(_.clone(PairDC.prototype.defaults), {
            history_content_type: "dataset_collection",
            collection_type: "paired",
            model_class: "HistoryDatasetCollectionAssociation"
        }),

        /** Override to post to contents route w/o id. */
        save: buildHDCASave(PairDC.prototype.save),

        /** String representation. */
        toString: function() {
            return `History${PairDC.prototype.toString.call(this)}`;
        }
    }
);

//==============================================================================
/** @class Backbone model for List of Pairs Dataset Collection within a History. */
var HistoryListPairedDatasetCollection = ListPairedDC.extend(hcontentMixin).extend({
    defaults: _.extend(_.clone(ListPairedDC.prototype.defaults), {
        history_content_type: "dataset_collection",
        collection_type: "list:paired",
        model_class: "HistoryDatasetCollectionAssociation"
    }),

    /** Override to post to contents route w/o id. */
    save: buildHDCASave(ListPairedDC.prototype.save),

    /** String representation. */
    toString: function() {
        return `History${ListPairedDC.prototype.toString.call(this)}`;
    }
});

//==============================================================================
/** @class Backbone model for List of Lists Dataset Collection within a History. */
var HistoryListOfListsDatasetCollection = ListOfListsDC.extend(hcontentMixin).extend({
    defaults: _.extend(_.clone(ListOfListsDC.prototype.defaults), {
        history_content_type: "dataset_collection",
        collection_type: "list:list",
        model_class: "HistoryDatasetCollectionAssociation"
    }),

    /** Override to post to contents route w/o id. */
    save: buildHDCASave(ListOfListsDC.prototype.save),

    /** String representation. */
    toString: function() {
        return ["HistoryListOfListsDatasetCollection(", this.get("name"), ")"].join("");
    }
});

//==============================================================================
export default {
    HistoryListDatasetCollection: HistoryListDatasetCollection,
    HistoryPairDatasetCollection: HistoryPairDatasetCollection,
    HistoryListPairedDatasetCollection: HistoryListPairedDatasetCollection,
    HistoryListOfListsDatasetCollection: HistoryListOfListsDatasetCollection
};
