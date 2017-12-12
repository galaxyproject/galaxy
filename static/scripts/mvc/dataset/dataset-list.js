define("mvc/dataset/dataset-list", ["exports", "mvc/list/list-view", "mvc/dataset/dataset-li", "mvc/base-mvc", "utils/localization"], function(exports, _listView, _datasetLi, _baseMvc, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _listView2 = _interopRequireDefault(_listView);

    var _datasetLi2 = _interopRequireDefault(_datasetLi);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var logNamespace = "dataset";
    /* =============================================================================
    TODO:
    
    ============================================================================= */
    var _super = _listView2.default.ListPanel;
    /** @class  non-editable, read-only View/Controller for a list of datasets.
     */
    var DatasetList = _super.extend(
        /** @lends DatasetList.prototype */
        {
            _logNamespace: logNamespace,

            /** class to use for constructing the sub-views */
            viewClass: _datasetLi2.default.DatasetListItemView,
            className: _super.prototype.className + " dataset-list",

            /** string to no hdas match the search terms */
            noneFoundMsg: (0, _localization2.default)("No matching datasets found"),

            // ......................................................................... SET UP
            /** Set up the view, set up storage, bind listeners to HistoryContents events
             *  @param {Object} attributes optional settings for the panel
             */
            initialize: function initialize(attributes) {
                _super.prototype.initialize.call(this, attributes);
            },

            /** Return a string rep of the history */
            toString: function toString() {
                return "DatasetList(" + this.collection + ")";
            }
        });

    //==============================================================================
    exports.default = {
        DatasetList: DatasetList
    };
});
//# sourceMappingURL=../../../maps/mvc/dataset/dataset-list.js.map
