import _ from "underscore";
import STATES from "mvc/dataset/states";
import DC_LI from "mvc/collection/collection-li";
import DC_VIEW from "mvc/collection/collection-view";
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
            var renderListen = (model, options) => {
                // We want this to swap immediately without extra animations.
                this.render(0);
            };
            if (this.model.jobStatesSummary) {
                this.listenTo(this.model.jobStatesSummary, "change", renderListen);
            }
            this.listenTo(this.model, {
                "change:tags change:visible change:state": renderListen
            });
        },

        /** Override to provide the proper collections panels as the foldout */
        _getFoldoutPanelClass: function() {
            return DC_VIEW.CollectionView;
        },

        /** In this override, add the state as a class for use with state-based CSS */
        _swapNewRender: function($newRender) {
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
            var stateDescription = this.stateDescription();
            this.$(".state-description").html(stateDescription);
            return this.$el;
        },

        stateDescription: function() {
            var collection = this.model;
            var jobStateSource = collection.get("job_source_type");
            var collectionTypeDescription = DC_VIEW.collectionTypeDescription(collection);
            var simpleDescription = DC_VIEW.collectionDescription(collection);
            var jobStatesSummary = collection.jobStatesSummary;
            if (!jobStateSource || jobStateSource == "Job") {
                return simpleDescription;
            } else if (!jobStatesSummary || !jobStatesSummary.hasDetails()) {
                return `
                    <div class="progress state-progress">
                        <span class="note">Loading job data for ${collectionTypeDescription}.<span class="blinking">..</span></span>
                        <div class="progress-bar info" style="width:100%">
                    </div>`;
            } else {
                var isNew = jobStatesSummary.new();
                var jobCount = isNew ? null : jobStatesSummary.jobCount();
                if (isNew) {
                    return `
                        <div class="progress state-progress">
                            <span class="note">Creating jobs.<span class="blinking">..</span></span>
                            <div class="progress-bar info" style="width:100%">
                        </div>`;
                } else if (jobStatesSummary.errored()) {
                    var errorCount = jobStatesSummary.numInError();
                    return `a ${collectionTypeDescription} with ${errorCount} / ${jobCount} jobs in error`;
                } else if (jobStatesSummary.terminal()) {
                    return simpleDescription;
                } else {
                    var running = jobStatesSummary.states()["running"] || 0;
                    var ok = jobStatesSummary.states()["ok"] || 0;
                    var okPercent = ok / (jobCount * 1.0);
                    var runningPercent = running / (jobCount * 1.0);
                    var otherPercent = 1.0 - okPercent - runningPercent;
                    var jobsStr = jobCount && jobCount > 1 ? `${jobCount} jobs` : `a job`;
                    return `
                        <div class="progress state-progress">
                            <span class="note">${jobsStr} generating a ${collectionTypeDescription}</span>
                            <div class="progress-bar ok" style="width:${okPercent * 100.0}%"></div>
                            <div class="progress-bar running" style="width:${runningPercent * 100.0}%"></div>
                            <div class="progress-bar new" style="width:${otherPercent * 100.0}%">
                        </div>`;
                }
            }
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

    var titleBarTemplate = collection => `
        <div class="title-bar clear" tabindex="0">
            <span class="state-icon"></span>
            <div class="title">
                <span class="hid">${collection.hid}</span>
                <span class="name">${_.escape(collection.name)}</span>
            </div>
            <div class="state-description">
            </div>
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
