import { getGalaxyInstance } from "app";
import DC_VIEW from "mvc/collection/collection-view";
import DC_EDIT from "mvc/collection/collection-li-edit";
import TAGS from "mvc/tag";
import _l from "utils/localization";
import "ui/editable-text";

/* =============================================================================
TODO:

============================================================================= */
/** @class editable View/Controller for a dataset collection.
 */
var _super = DC_VIEW.CollectionView;
var CollectionViewEdit = _super.extend(
    /** @lends CollectionView.prototype */ {
        //MODEL is either a DatasetCollection (or subclass) or a DatasetCollectionElement (list of pairs)

        /** logger used to record this.log messages, commonly set to console */
        //logger              : console,

        /** sub view class used for datasets */
        DatasetDCEViewClass: DC_EDIT.DatasetDCEListItemEdit,
        /** sub view class used for nested collections */
        NestedDCDCEViewClass: DC_EDIT.NestedDCDCEListItemEdit,

        getNestedDCDCEViewClass: function() {
            return DC_EDIT.NestedDCDCEListItemEdit.extend({
                foldoutPanelClass: CollectionViewEdit
            });
        },

        // ......................................................................... SET UP
        /** Set up the view, set up storage, bind listeners to HistoryContents events
         *  @param {Object} attributes optional settings for the panel
         */
        initialize: function(attributes) {
            _super.prototype.initialize.call(this, attributes);
        },

        /** In this override, make the collection name editable
         */
        _setUpBehaviors: function($where) {
            $where = $where || this.$el;
            _super.prototype._setUpBehaviors.call(this, $where);
            if (!this.model) {
                return;
            }

            // anon users shouldn't have access to any of the following
            let Galaxy = getGalaxyInstance();
            if (!Galaxy.user || Galaxy.user.isAnonymous()) {
                return;
            }

            this.tagsEditorShown = true;

            //TODO: extract
            var panel = this;

            var nameSelector = "> .controls .name";
            $where
                .find(nameSelector)
                .attr("title", _l("Click to rename collection"))
                .tooltip({ placement: "bottom" })
                .make_text_editable({
                    on_finish: function(newName) {
                        var previousName = panel.model.get("name");
                        if (newName && newName !== previousName) {
                            panel.$el.find(nameSelector).text(newName);
                            panel.model.save({ name: newName }).fail(() => {
                                panel.$el.find(nameSelector).text(panel.model.previous("name"));
                            });
                        } else {
                            panel.$el.find(nameSelector).text(previousName);
                        }
                    }
                });
            this.tagsEditor = new TAGS.TagsEditor({
                model: this.model,
                el: $where.find(".tags-display"),
                onshowFirstTime: function() {
                    this.render();
                },
                usePrompt: false
            });
            this.tagsEditor.toggle(true);
        },

        // ........................................................................ misc
        /** string rep */
        toString: function() {
            return `CollectionViewEdit(${this.model ? this.model.get("name") : ""})`;
        }
    }
);

//==============================================================================
export default {
    CollectionViewEdit: CollectionViewEdit
};
