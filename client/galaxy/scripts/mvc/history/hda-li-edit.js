import $ from "jquery";
import _ from "underscore";
import DATASET_LI_EDIT from "mvc/dataset/dataset-li-edit";
import HDA_LI from "mvc/history/hda-li";
import BASE_MVC from "mvc/base-mvc";
import _l from "utils/localization";

//==============================================================================
var _super = DATASET_LI_EDIT.DatasetListItemEdit;
/** @class Editing view for HistoryDatasetAssociation.
 */
var HDAListItemEdit = _super.extend(
    /** @lends HDAListItemEdit.prototype */ {
        className: `${_super.prototype.className} history-content`,

        /** In this override, only get details if in the ready state, get rerunnable if in other states.
         *  Note: fetch with no 'change' event triggering to prevent automatic rendering.
         */
        _fetchModelDetails: function() {
            var view = this;
            if (view.model.inReadyState() && !view.model.hasDetails()) {
                return view.model.fetch({ silent: true });

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
            return $.when();
        },

        /** event map */
        events: _.extend(_.clone(_super.prototype.events), {
            "click .unhide-link": function(ev) {
                this.model.unhide();
                return false;
            }
        }),

        /** string rep */
        toString: function() {
            var modelString = this.model ? `${this.model}` : "(no model)";
            return `HDAListItemEdit(${modelString})`;
        }
    }
);

// ............................................................................ TEMPLATES
/** underscore templates */
HDAListItemEdit.prototype.templates = (() => {
    var warnings = _.extend({}, _super.prototype.templates.warnings, {
        hidden: BASE_MVC.wrapTemplate(
            [
                "<% if( !dataset.visible ){ %>",
                // add a link to unhide a dataset
                '<div class="hidden-msg warningmessagesmall">',
                _l("This dataset has been hidden"),
                '<br /><a class="unhide-link" a href="javascript:void(0);">',
                _l("Unhide it"),
                "</a>",
                "</div>",
                "<% } %>"
            ],
            "dataset"
        )
    });

    return _.extend({}, _super.prototype.templates, {
        //NOTE: *steal* the HDAListItemView titleBar
        titleBar: HDA_LI.HDAListItemView.prototype.templates.titleBar,
        warnings: warnings
    });
})();

//==============================================================================
export default {
    HDAListItemEdit: HDAListItemEdit
};
