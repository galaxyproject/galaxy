import STATES from "mvc/dataset/states";
import DC_LI from "mvc/collection/collection-li";
import DC_VIEW from "mvc/collection/collection-view";
import BASE_MVC from "mvc/base-mvc";
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
                this.render();
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
            var collectionType = this.model.get("collection_type");
            switch (collectionType) {
                case "list":
                    return DC_VIEW.ListCollectionView;
                case "paired":
                    return DC_VIEW.PairCollectionView;
                case "list:paired":
                    return DC_VIEW.ListOfPairsCollectionView;
                case "list:list":
                    return DC_VIEW.ListOfListsCollectionView;
            }
            throw new TypeError(`Unknown collection_type: ${collectionType}`);
        },

        /** In this override, add the state as a class for use with state-based CSS */
        _swapNewRender: function($newRender) {
            _super.prototype._swapNewRender.call(this, $newRender);
            //TODO: model currently has no state
            var state;
            var jobStatesSummary = this.model.jobStatesSummary;
            if (jobStatesSummary) {
                if (jobStatesSummary.new()) {
                    state = "new";
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
                state = STATES.NEW;
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
            var elementCount = collection.get("element_count");
            var jobStateSource = collection.get("job_source_type");
            var collectionType = this.model.get("collection_type");
            var collectionTypeDescription;
            if (collectionType == "list") {
                collectionTypeDescription = "list";
            } else if (collectionType == "paired") {
                collectionTypeDescription = "dataset pair";
            } else if (collectionType == "list:paired") {
                collectionTypeDescription = "list of pairs";
            } else {
                collectionTypeDescription = "nested list";
            }
            var itemsDescription = "";
            if (elementCount == 1) {
                itemsDescription = ` with 1 item`;
            } else if (elementCount) {
                itemsDescription = ` with ${elementCount} items`;
            }
            var jobStatesSummary = collection.jobStatesSummary;
            var simpleDescription = `${collectionTypeDescription}${itemsDescription}`;
            if (!jobStateSource || jobStateSource == "Job") {
                return `a ${simpleDescription}`;
            } else if (!jobStatesSummary || !jobStatesSummary.hasDetails()) {
                return `
                    <div class="progress state-progress">
                        <span class="note">Loading job data for ${collectionTypeDescription}...</span>
                        <div class="progress-bar info" style="width:100%">
                    </div>`;
            } else {
                var isNew = jobStatesSummary.new();
                var jobCount = isNew ? null : jobStatesSummary.jobCount();
                if (isNew) {
                    return `
                        <div class="progress state-progress">
                            <span class="note">Creating jobs...</span>
                            <div class="progress-bar info" style="width:100%">
                        </div>`;
                } else if (jobStatesSummary.errored()) {
                    var errorCount = jobStatesSummary.numInError();
                    return `a ${collectionTypeDescription} with ${errorCount} / ${jobCount} jobs in error`;
                } else if (jobStatesSummary.terminal()) {
                    return `a ${simpleDescription}`;
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
