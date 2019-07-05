import $ from "jquery";
import _ from "underscore";
import HDCA_LI from "mvc/history/hdca-li";
import DC_VIEW_EDIT from "mvc/collection/collection-view-edit";
import _l from "utils/localization";

//==============================================================================
var _super = HDCA_LI.HDCAListItemView;
/** @class Editing view for HistoryDatasetCollectionAssociation.
 */
var HDCAListItemEdit = _super.extend(
    /** @lends HDCAListItemEdit.prototype */ {
        /** logger used to record this.log messages, commonly set to console */
        //logger              : console,
        /** set up: options */
        initialize: function(attributes) {
            _super.prototype.initialize.call(this, attributes);

            /** allow user purge of dataset files? */
            this.purgeAllowed = attributes.purgeAllowed || false;
        },

        /** Override to return editable versions of the collection panels */
        _getFoldoutPanelClass: function() {
            return DC_VIEW_EDIT.CollectionViewEdit;
        },

        // ......................................................................... delete
        /** In this override, add the delete button. */
        _renderPrimaryActions: function() {
            this.log(`${this}._renderPrimaryActions`);
            // render the display, edit attr and delete icon-buttons
            return _super.prototype._renderPrimaryActions.call(this).concat([this._renderDeleteButton()]);
        },

        _renderDeleteButton: function() {
            return $(`
                <div class="dropdown">
                    <a class="delete-btn icon-btn" title="${_l("Delete")}" data-toggle="dropdown">
                        <span class="fa fa-times"></span>
                    </a>
                    <div class="dropdown-menu" role="menu">
                            <a href="#" class="dropdown-item delete-collection">
                                ${_l("Collection Only")}
                            </a>
                            <a href="#" class="dropdown-item delete-collection-and-datasets">
                                ${_l("Delete Datasets")}
                            </a>
                            <a href="#" style="display: ${
                                this.purgeAllowed ? "inherit" : "none"
                            }" class="dropdown-item delete-collection-and-purge-datasets">
                                ${_l("Permanently Delete Datasets")}
                            </a>
                    </div>
                </div>`);
        },

        // ......................................................................... misc
        events: _.extend(_.clone(_super.prototype.events), {
            "click .delete-collection": function(ev) {
                this.model["delete"]();
            },
            "click .delete-collection-and-datasets": function(ev) {
                this.model["delete"](true);
            },
            "click .delete-collection-and-purge-datasets": function(ev) {
                this.model["delete"](true, true);
            }
        }),

        // ......................................................................... misc
        /** string rep */
        toString: function() {
            var modelString = this.model ? `${this.model}` : "(no model)";
            return `HDCAListItemEdit(${modelString})`;
        }
    }
);

//==============================================================================
export default {
    HDCAListItemEdit: HDCAListItemEdit
};
