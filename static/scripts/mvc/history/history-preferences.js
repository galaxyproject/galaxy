define("mvc/history/history-preferences", ["exports", "mvc/base-mvc"], function(exports, _baseMvc) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var logNamespace = "history";

    // ============================================================================
    /** session storage for individual history preferences */
    var HistoryPrefs = _baseMvc2.default.SessionStorageModel.extend(
        /** @lends HistoryPrefs.prototype */
        {
            //TODO:?? move to user prefs?
            defaults: {
                //TODO:?? expandedIds to array?
                expandedIds: {},
                show_deleted: false,
                show_hidden: false
            },

            /** add an hda id to the hash of expanded hdas */
            addExpanded: function addExpanded(model) {
                //TODO: use type_id and not model
                var current = this.get("expandedIds");
                current[model.id] = model.get("id");
                this.save("expandedIds", current);
            },

            /** remove an hda id from the hash of expanded hdas */
            removeExpanded: function removeExpanded(model) {
                var current = this.get("expandedIds");
                delete current[model.id];
                this.save("expandedIds", current);
            },

            isExpanded: function isExpanded(contentId) {
                return _.result(this.get("expandedIds"), contentId, false);
            },

            allExpanded: function allExpanded() {
                return _.values(this.get("expandedIds"));
            },

            clearExpanded: function clearExpanded() {
                this.set("expandedIds", {});
            },

            includeDeleted: function includeDeleted(val) {
                // moving the invocation here so other components don't need to know the key
                // TODO: change this key later
                if (!_.isUndefined(val)) {
                    this.set("show_deleted", val);
                }
                return this.get("show_deleted");
            },

            includeHidden: function includeHidden(val) {
                // TODO: change this key later
                if (!_.isUndefined(val)) {
                    this.set("show_hidden", val);
                }
                return this.get("show_hidden");
            },

            toString: function toString() {
                return "HistoryPrefs(" + this.id + ")";
            }
        }, {
            // ........................................................................ class vars
            // class lvl for access w/o instantiation
            storageKeyPrefix: "history:",

            /** key string to store each histories settings under */
            historyStorageKey: function historyStorageKey(historyId) {
                if (!historyId) {
                    throw new Error("HistoryPrefs.historyStorageKey needs valid id: " + historyId);
                }
                // single point of change
                return HistoryPrefs.storageKeyPrefix + historyId;
            },

            /** return the existing storage for the history with the given id (or create one if it doesn't exist) */
            get: function get(historyId) {
                return new HistoryPrefs({
                    id: HistoryPrefs.historyStorageKey(historyId)
                });
            },

            /** clear all history related items in sessionStorage */
            clearAll: function clearAll(historyId) {
                for (var key in sessionStorage) {
                    if (key.indexOf(HistoryPrefs.storageKeyPrefix) === 0) {
                        sessionStorage.removeItem(key);
                    }
                }
            }
        });

    //==============================================================================
    exports.default = {
        HistoryPrefs: HistoryPrefs
    };
});
//# sourceMappingURL=../../../maps/mvc/history/history-preferences.js.map
