import STATES from "mvc/dataset/states";
import DC_LI from "mvc/collection/collection-li";
import DC_VIEW from "mvc/collection/collection-view";
import BASE_MVC from "mvc/base-mvc";
import HISTORY_ITEM_LI from "mvc/history/history-item-li";
import _l from "utils/localization";

//==============================================================================
var _super = DC_LI.DCListItemView;
/** @class Read only view for HistoryDatasetCollectionAssociation (a dataset collection inside a history).
 */
var HDCAListItemView = _super.extend(
    /** @lends HDCAListItemView.prototype */ {
        className: `${_super.prototype.className} history-content`,

        /** event listeners */
        _setUpListeners: function() {
            _super.prototype._setUpListeners.call(this);
            this.listenTo(this.model, {
                "change:tags change:populated change:visible": function(model, options) {
                    this.render();
                }
            });
        },

        /** Override to provide the proper collections panels as the foldout */
        _getFoldoutPanelClass: function() {
            var collectionType = this.model.get("collection_type");
            switch (collectionType) {
                case "list":
                    return DC_VIEW.ListCollectionView;
                case "paired":
                    return DC_VIEW.PairCollectionView;
                case "list:paired":
                    return DC_VIEW.ListOfPairsCollectionView;
                case "list:list":
                    return DC_VIEW.ListOfListsCollectionView;
            }
            throw new TypeError(`Unknown collection_type: ${collectionType}`);
        },

        /** In this override, add the state as a class for use with state-based CSS */
        _swapNewRender: function($newRender) {
            _super.prototype._swapNewRender.call(this, $newRender);
            //TODO: model currently has no state
            var state = !this.model.get("populated") ? STATES.RUNNING : STATES.OK;
            //if( this.model.has( 'state' ) ){
            this.$el.addClass(`state-${state}`);
            //}
            return this.$el;
        },

        // ......................................................................... misc
        /** String representation */
        toString: function() {
            var modelString = this.model ? `${this.model}` : "(no model)";
            return `HDCAListItemView(${modelString})`;
        }
    }
);

/** underscore templates */
HDCAListItemView.prototype.templates = (() => {
    var warnings = _.extend({}, _super.prototype.templates.warnings, {
        hidden: collection => {
            collection.visible
                ? ""
                : `<div class="hidden-msg warningmessagesmall">${_l("This collection has been hidden")}</div>`;
        }
    });

    // could steal this from hda-base (or use mixed content)
    var titleBarTemplate = collection => `
        <div class="title-bar clear" tabindex="0">
            <span class="state-icon"></span>
            <div class="title">
                <span class="hid">${collection.hid}</span>
                <span class="name">${collection.name}</span>
            </div>
            <div class="subtitle"></div>
            ${HISTORY_ITEM_LI.nametagTemplate(collection)}
        </div>
    `;

    return _.extend({}, _super.prototype.templates, {
        warnings: warnings,
        titleBar: titleBarTemplate
    });
})();

//==============================================================================
export default {
    HDCAListItemView: HDCAListItemView
};
