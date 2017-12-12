define("mvc/history/hdca-li-edit", ["exports", "mvc/history/hdca-li", "mvc/collection/collection-view-edit", "ui/fa-icon-button", "utils/localization"], function(exports, _hdcaLi, _collectionViewEdit, _faIconButton, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _hdcaLi2 = _interopRequireDefault(_hdcaLi);

    var _collectionViewEdit2 = _interopRequireDefault(_collectionViewEdit);

    var _faIconButton2 = _interopRequireDefault(_faIconButton);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    //==============================================================================
    var _super = _hdcaLi2.default.HDCAListItemView;
    /** @class Editing view for HistoryDatasetCollectionAssociation.
     */
    var HDCAListItemEdit = _super.extend(
        /** @lends HDCAListItemEdit.prototype */
        {
            /** logger used to record this.log messages, commonly set to console */
            //logger              : console,

            /** Override to return editable versions of the collection panels */
            _getFoldoutPanelClass: function _getFoldoutPanelClass() {
                return _collectionViewEdit2.default.CollectionViewEdit;
            },

            // ......................................................................... delete
            /** In this override, add the delete button. */
            _renderPrimaryActions: function _renderPrimaryActions() {
                this.log(this + "._renderPrimaryActions");
                // render the display, edit attr and delete icon-buttons
                return _super.prototype._renderPrimaryActions.call(this).concat([this._renderDeleteButton()]);
            },

            /** Render icon-button to delete this collection. */
            _renderDeleteButton: function _renderDeleteButton() {
                var _this = this;

                var deleted = this.model.get("deleted");
                return (0, _faIconButton2.default)({
                    title: deleted ? (0, _localization2.default)("Dataset collection is already deleted") : (0, _localization2.default)("Delete"),
                    classes: "delete-btn",
                    faIcon: "fa-times",
                    disabled: deleted,
                    onclick: function onclick() {
                        // ...bler... tooltips being left behind in DOM (hover out never called on deletion)
                        _this.$el.find(".icon-btn.delete-btn").trigger("mouseout");
                        _this.model["delete"]();
                    }
                });
            },

            // ......................................................................... misc
            /** string rep */
            toString: function toString() {
                var modelString = this.model ? "" + this.model : "(no model)";
                return "HDCAListItemEdit(" + modelString + ")";
            }
        });

    //==============================================================================
    exports.default = {
        HDCAListItemEdit: HDCAListItemEdit
    };
});
//# sourceMappingURL=../../../maps/mvc/history/hdca-li-edit.js.map
