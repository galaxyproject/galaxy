define("mvc/collection/collection-li-edit", ["exports", "mvc/collection/collection-li", "mvc/dataset/dataset-li-edit", "mvc/base-mvc", "utils/localization"], function(exports, _collectionLi, _datasetLiEdit, _baseMvc, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _collectionLi2 = _interopRequireDefault(_collectionLi);

    var _datasetLiEdit2 = _interopRequireDefault(_datasetLiEdit);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    //==============================================================================
    var DCListItemView = _collectionLi2.default.DCListItemView;
    /** @class Edit view for DatasetCollection.
     */
    var DCListItemEdit = DCListItemView.extend(
        /** @lends DCListItemEdit.prototype */
        {
            /** override to add linkTarget */
            initialize: function initialize(attributes) {
                DCListItemView.prototype.initialize.call(this, attributes);
            },

            // ......................................................................... misc
            /** String representation */
            toString: function toString() {
                var modelString = this.model ? "" + this.model : "(no model)";
                return "DCListItemEdit(" + modelString + ")";
            }
        });

    //==============================================================================
    var DCEListItemView = _collectionLi2.default.DCEListItemView;
    /** @class Read only view for DatasetCollectionElement.
     */
    var DCEListItemEdit = DCEListItemView.extend(
        /** @lends DCEListItemEdit.prototype */
        {
            //TODO: this might be expendable - compacted with HDAListItemView

            /** set up */
            initialize: function initialize(attributes) {
                DCEListItemView.prototype.initialize.call(this, attributes);
            },

            // ......................................................................... misc
            /** String representation */
            toString: function toString() {
                var modelString = this.model ? "" + this.model : "(no model)";
                return "DCEListItemEdit(" + modelString + ")";
            }
        });

    //==============================================================================
    // NOTE: this does not inherit from DatasetDCEListItemView as you would expect
    //TODO: but should - if we can find something simpler than using diamond
    /** @class Editable view for a DatasetCollectionElement that is also an DatasetAssociation
     *      (a dataset contained in a dataset collection).
     */
    var DatasetDCEListItemEdit = _datasetLiEdit2.default.DatasetListItemEdit.extend(
        /** @lends DatasetDCEListItemEdit.prototype */
        {
            /** set up */
            initialize: function initialize(attributes) {
                _datasetLiEdit2.default.DatasetListItemEdit.prototype.initialize.call(this, attributes);
            },

            // NOTE: this does not inherit from DatasetDCEListItemView - so we duplicate this here
            //TODO: fix
            /** In this override, only get details if in the ready state.
             *  Note: fetch with no 'change' event triggering to prevent automatic rendering.
             */
            _fetchModelDetails: function _fetchModelDetails() {
                var view = this;
                if (view.model.inReadyState() && !view.model.hasDetails()) {
                    return view.model.fetch({
                        silent: true
                    });
                }
                return jQuery.when();
            },

            /** Override to remove delete button */
            _renderDeleteButton: function _renderDeleteButton() {
                return null;
            },

            // ......................................................................... misc
            /** String representation */
            toString: function toString() {
                var modelString = this.model ? "" + this.model : "(no model)";
                return "DatasetDCEListItemEdit(" + modelString + ")";
            }
        });

    // ............................................................................ TEMPLATES
    /** underscore templates */
    DatasetDCEListItemEdit.prototype.templates = function() {
        return _.extend({}, _datasetLiEdit2.default.DatasetListItemEdit.prototype.templates, {
            titleBar: _collectionLi2.default.DatasetDCEListItemView.prototype.templates.titleBar
        });
    }();

    //==============================================================================
    /** @class Read only view for a DatasetCollectionElement that is also a DatasetCollection
     *      (a nested DC).
     */
    var NestedDCDCEListItemEdit = _collectionLi2.default.NestedDCDCEListItemView.extend(
        /** @lends NestedDCDCEListItemEdit.prototype */
        {
            /** String representation */
            toString: function toString() {
                var modelString = this.model ? "" + this.model : "(no model)";
                return "NestedDCDCEListItemEdit(" + modelString + ")";
            }
        });

    //==============================================================================
    exports.default = {
        DCListItemEdit: DCListItemEdit,
        DCEListItemEdit: DCEListItemEdit,
        DatasetDCEListItemEdit: DatasetDCEListItemEdit,
        NestedDCDCEListItemEdit: NestedDCDCEListItemEdit
    };
});
//# sourceMappingURL=../../../maps/mvc/collection/collection-li-edit.js.map
