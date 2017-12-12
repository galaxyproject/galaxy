define("mvc/history/hdca-li", ["exports", "mvc/dataset/states", "mvc/collection/collection-li", "mvc/collection/collection-view", "mvc/base-mvc", "mvc/history/history-item-li", "utils/localization"], function(exports, _states, _collectionLi, _collectionView, _baseMvc, _historyItemLi, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _states2 = _interopRequireDefault(_states);

    var _collectionLi2 = _interopRequireDefault(_collectionLi);

    var _collectionView2 = _interopRequireDefault(_collectionView);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _historyItemLi2 = _interopRequireDefault(_historyItemLi);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    //==============================================================================
    var _super = _collectionLi2.default.DCListItemView;
    /** @class Read only view for HistoryDatasetCollectionAssociation (a dataset collection inside a history).
     */
    var HDCAListItemView = _super.extend(
        /** @lends HDCAListItemView.prototype */
        {
            className: _super.prototype.className + " history-content",

            /** event listeners */
            _setUpListeners: function _setUpListeners() {
                var _this = this;

                _super.prototype._setUpListeners.call(this);
                var renderListen = function renderListen(model, options) {
                    _this.render();
                };
                if (this.model.jobStatesSummary) {
                    this.listenTo(this.model.jobStatesSummary, "change", renderListen);
                }
                this.listenTo(this.model, {
                    "change:tags change:visible change:state": renderListen
                });
            },

            /** Override to provide the proper collections panels as the foldout */
            _getFoldoutPanelClass: function _getFoldoutPanelClass() {
                return _collectionView2.default.CollectionView;
            },

            /** In this override, add the state as a class for use with state-based CSS */
            _swapNewRender: function _swapNewRender($newRender) {
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
                    state = this.model.get("populated_state") ? _states2.default.OK : _states2.default.RUNNING;
                }
                this.$el.addClass("state-" + state);
                var stateDescription = this.stateDescription();
                this.$(".state-description").html(stateDescription);
                return this.$el;
            },

            stateDescription: function stateDescription() {
                var collection = this.model;
                var elementCount = collection.get("element_count");
                var jobStateSource = collection.get("job_source_type");
                var collectionType = this.model.get("collection_type");
                var collectionTypeDescription = _collectionView2.default.collectionTypeDescription(collection);
                var simpleDescription = _collectionView2.default.collectionDescription(collection);
                var jobStatesSummary = collection.jobStatesSummary;
                if (!jobStateSource || jobStateSource == "Job") {
                    return simpleDescription;
                } else if (!jobStatesSummary || !jobStatesSummary.hasDetails()) {
                    return "\n                    <div class=\"progress state-progress\">\n                        <span class=\"note\">Loading job data for " + collectionTypeDescription + ".<span class=\"blinking\">..</span></span>\n                        <div class=\"progress-bar info\" style=\"width:100%\">\n                    </div>";
                } else {
                    var isNew = jobStatesSummary.new();
                    var jobCount = isNew ? null : jobStatesSummary.jobCount();
                    if (isNew) {
                        return "\n                        <div class=\"progress state-progress\">\n                            <span class=\"note\">Creating jobs.<span class=\"blinking\">..</span></span>\n                            <div class=\"progress-bar info\" style=\"width:100%\">\n                        </div>";
                    } else if (jobStatesSummary.errored()) {
                        var errorCount = jobStatesSummary.numInError();
                        return "a " + collectionTypeDescription + " with " + errorCount + " / " + jobCount + " jobs in error";
                    } else if (jobStatesSummary.terminal()) {
                        return simpleDescription;
                    } else {
                        var running = jobStatesSummary.states()["running"] || 0;
                        var ok = jobStatesSummary.states()["ok"] || 0;
                        var okPercent = ok / (jobCount * 1.0);
                        var runningPercent = running / (jobCount * 1.0);
                        var otherPercent = 1.0 - okPercent - runningPercent;
                        var jobsStr = jobCount && jobCount > 1 ? jobCount + " jobs" : "a job";
                        return "\n                        <div class=\"progress state-progress\">\n                            <span class=\"note\">" + jobsStr + " generating a " + collectionTypeDescription + "</span>\n                            <div class=\"progress-bar ok\" style=\"width:" + okPercent * 100.0 + "%\"></div>\n                            <div class=\"progress-bar running\" style=\"width:" + runningPercent * 100.0 + "%\"></div>\n                            <div class=\"progress-bar new\" style=\"width:" + otherPercent * 100.0 + "%\">\n                        </div>";
                    }
                }
            },

            // ......................................................................... misc
            /** String representation */
            toString: function toString() {
                var modelString = this.model ? "" + this.model : "(no model)";
                return "HDCAListItemView(" + modelString + ")";
            }
        });

    /** underscore templates */
    HDCAListItemView.prototype.templates = function() {
        var warnings = _.extend({}, _super.prototype.templates.warnings, {
            hidden: function hidden(collection) {
                collection.visible ? "" : "<div class=\"hidden-msg warningmessagesmall\">" + (0, _localization2.default)("This collection has been hidden") + "</div>";
            }
        });

        var titleBarTemplate = function titleBarTemplate(collection) {
            return "\n        <div class=\"title-bar clear\" tabindex=\"0\">\n            <span class=\"state-icon\"></span>\n            <div class=\"title\">\n                <span class=\"hid\">" + collection.hid + "</span>\n                <span class=\"name\">" + _.escape(collection.name) + "</span>\n            </div>\n            <div class=\"state-description\">\n            </div>\n            " + _historyItemLi2.default.nametagTemplate(collection) + "\n        </div>\n    ";
        };

        return _.extend({}, _super.prototype.templates, {
            warnings: warnings,
            titleBar: titleBarTemplate
        });
    }();

    //==============================================================================
    exports.default = {
        HDCAListItemView: HDCAListItemView
    };
});
//# sourceMappingURL=../../../maps/mvc/history/hdca-li.js.map
