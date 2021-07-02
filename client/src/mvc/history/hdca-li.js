import _ from "underscore";
import STATES from "mvc/dataset/states";
import DC_LI from "mvc/collection/collection-li";
import DC_VIEW from "mvc/collection/collection-view";
import _l from "utils/localization";
import { mountNametags } from "components/Nametags";
import { mountCollectionJobStates } from "components/JobStates";

//==============================================================================
var _super = DC_LI.DCListItemView;
/** @class Read only view for HistoryDatasetCollectionAssociation (a dataset collection inside a history).
 */
var HDCAListItemView = _super.extend(
    /** @lends HDCAListItemView.prototype */ {
        className: `${_super.prototype.className} history-content`,

        render: function () {
            const result = _super.prototype.render.apply(this, arguments);
            this._mountNametags("initialize");
            return result;
        },

        /** event listeners */
        _setUpListeners: function () {
            _super.prototype._setUpListeners.call(this);
            var renderListen = (model, options) => {
                // We want this to swap immediately without extra animations.
                this.render(0);
                this._mountNametags("listener");
            };
            if (this.model.jobStatesSummary) {
                this.listenTo(this.model.jobStatesSummary, "change", renderListen);
            }
            this.listenTo(this.model, {
                "change:tags change:visible change:state": renderListen,
            });
        },

        _mountNametags(context) {
            const container = this.$el.find(".nametags")[0];
            if (container) {
                const { id, model_class, tags } = this.model.attributes;
                const storeKey = `${model_class}-${id}`;
                mountNametags({ storeKey, tags }, container);
            }
        },

        /** Override to provide the proper collections panels as the foldout */
        _getFoldoutPanelClass: function () {
            return DC_VIEW.CollectionView;
        },

        /** In this override, add the state as a class for use with state-based CSS */
        _swapNewRender: function ($newRender) {
            _super.prototype._swapNewRender.call(this, $newRender);
            //TODO: model currently has no state
            var state;
            var jobStatesSummary = this.model.jobStatesSummary;
            if (jobStatesSummary) {
                if (jobStatesSummary.new()) {
                    state = "loading";
                } else if (jobStatesSummary.errored()) {
                    state = "error";
                } else if (jobStatesSummary.terminal()) {
                    state = "ok";
                } else if (jobStatesSummary.running()) {
                    state = "running";
                } else {
                    state = "queued";
                }
            } else if (this.model.get("job_source_id")) {
                // Initial rendering - polling will fill in more details in a bit.
                state = "loading";
            } else {
                state = this.model.get("populated_state") ? STATES.OK : STATES.RUNNING;
            }
            this.$el.addClass(`state-${state}`);
            this.$el.attr("data-state", state);
            const collection = this.model;
            const stateContainer = this.$el.find(".state-description")[0];
            mountCollectionJobStates({ jobStatesSummary, collection }, stateContainer);
            return this.$el;
        },

        // ......................................................................... misc
        /** String representation */
        toString: function () {
            var modelString = this.model ? `${this.model}` : "(no model)";
            return `HDCAListItemView(${modelString})`;
        },
    }
);

/** underscore templates */
HDCAListItemView.prototype.templates = (() => {
    var warnings = _.extend({}, _super.prototype.templates.warnings, {
        hidden: (collection) => {
            collection.visible
                ? ""
                : `<div class="hidden-msg warningmessagesmall">${_l("This collection has been hidden")}</div>`;
        },
    });

    var titleBarTemplate = (collection) => `
        <div class="title-bar clear" tabindex="0">
            <span class="state-icon"></span>
            <div class="title content-title">
                <span class="hid">${collection.hid}</span>
                <span class="name">${_.escape(collection.name)}</span>
            </div>
            <div class="state-description">
            </div>
            <div class="nametags"><!-- Nametags mount here (hdca-li) --></div>
        </div>
    `;

    return _.extend({}, _super.prototype.templates, {
        warnings: warnings,
        titleBar: titleBarTemplate,
    });
})();

//==============================================================================
export default {
    HDCAListItemView: HDCAListItemView,
};
