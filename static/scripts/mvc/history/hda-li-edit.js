define("mvc/history/hda-li-edit", ["exports", "mvc/dataset/dataset-li-edit", "mvc/history/hda-li", "mvc/base-mvc", "utils/localization"], function(exports, _datasetLiEdit, _hdaLi, _baseMvc, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _datasetLiEdit2 = _interopRequireDefault(_datasetLiEdit);

    var _hdaLi2 = _interopRequireDefault(_hdaLi);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    //==============================================================================
    var _super = _datasetLiEdit2.default.DatasetListItemEdit;
    /** @class Editing view for HistoryDatasetAssociation.
     */
    var HDAListItemEdit = _super.extend(
        /** @lends HDAListItemEdit.prototype */
        {
            className: _super.prototype.className + " history-content",

            /** In this override, only get details if in the ready state, get rerunnable if in other states.
             *  Note: fetch with no 'change' event triggering to prevent automatic rendering.
             */
            _fetchModelDetails: function _fetchModelDetails() {
                var view = this;
                if (view.model.inReadyState() && !view.model.hasDetails()) {
                    return view.model.fetch({
                        silent: true
                    });

                    // special case the need for the rerunnable and creating_job attributes
                    // needed for rendering re-run button on queued, running datasets
                } else if (!view.model.has("rerunnable")) {
                    return view.model.fetch({
                        silent: true,
                        data: {
                            // only fetch rerunnable and creating_job to keep overhead down
                            keys: ["rerunnable", "creating_job"].join(",")
                        }
                    });
                }
                return jQuery.when();
            },

            /** event map */
            events: _.extend(_.clone(_super.prototype.events), {
                "click .unhide-link": function clickUnhideLink(ev) {
                    this.model.unhide();
                    return false;
                }
            }),

            /** string rep */
            toString: function toString() {
                var modelString = this.model ? "" + this.model : "(no model)";
                return "HDAListItemEdit(" + modelString + ")";
            }
        });

    // ............................................................................ TEMPLATES
    /** underscore templates */
    HDAListItemEdit.prototype.templates = function() {
        var warnings = _.extend({}, _super.prototype.templates.warnings, {
            hidden: _baseMvc2.default.wrapTemplate(["<% if( !dataset.visible ){ %>",
                // add a link to unhide a dataset
                '<div class="hidden-msg warningmessagesmall">', (0, _localization2.default)("This dataset has been hidden"), '<br /><a class="unhide-link" a href="javascript:void(0);">', (0, _localization2.default)("Unhide it"), "</a>", "</div>", "<% } %>"
            ], "dataset")
        });

        return _.extend({}, _super.prototype.templates, {
            //NOTE: *steal* the HDAListItemView titleBar
            titleBar: _hdaLi2.default.HDAListItemView.prototype.templates.titleBar,
            warnings: warnings
        });
    }();

    //==============================================================================
    exports.default = {
        HDAListItemEdit: HDAListItemEdit
    };
});
//# sourceMappingURL=../../../maps/mvc/history/hda-li-edit.js.map
