import _ from "underscore";
import DATASET_LI from "mvc/dataset/dataset-li";
import BASE_MVC from "mvc/base-mvc";
import _l from "utils/localization";

//==============================================================================
var _super = DATASET_LI.DatasetListItemView;
/** @class Read only view for HistoryDatasetAssociation.
 *      Since there are no controls on the HDAView to hide the dataset,
 *      the primary thing this class does (currently) is override templates
 *      to render the HID.
 */
var HDAListItemView = _super.extend(
    /** @lends HDAListItemView.prototype */ {
        className: `${_super.prototype.className} history-content`,

        initialize: function (attributes, options) {
            _super.prototype.initialize.call(this, attributes, options);
        },

        // ......................................................................... misc
        /** String representation */
        toString: function () {
            var modelString = this.model ? `${this.model}` : "(no model)";
            return `HDAListItemView(${modelString})`;
        },
    }
);

// ............................................................................ TEMPLATES
/** underscore templates */
HDAListItemView.prototype.templates = (() => {
    var titleBarTemplate = (dataset) => `
        <div class="title-bar clear" tabindex="0">
            <span class="state-icon"></span>
            <div class="title content-title">
                <span class="hid">${dataset.hid}</span>
                <span class="name">${_.escape(dataset.name)}</span>
            </div>
            </br>
            <div class="nametags"></div>
        </div>
    `;

    var warnings = _.extend({}, _super.prototype.templates.warnings, {
        hidden: BASE_MVC.wrapTemplate(
            [
                // add a warning when hidden
                "<% if( !dataset.visible ){ %>",
                '<div class="hidden-msg warningmessagesmall">',
                _l("This dataset has been hidden"),
                "</div>",
                "<% } %>",
            ],
            "dataset"
        ),
    });

    return _.extend({}, _super.prototype.templates, {
        titleBar: titleBarTemplate,
        warnings: warnings,
    });
})();

//==============================================================================
export default {
    HDAListItemView: HDAListItemView,
};
