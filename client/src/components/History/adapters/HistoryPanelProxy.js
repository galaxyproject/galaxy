/**
 * This is an adapter for the History component. It's required since the previous
 * history provided the same interface for other components.
 */
import Backbone from "backbone";
import store from "store";
import { getGalaxyInstance } from "app";
import { mountVueComponent } from "utils/mountVueComponent";
import HistoryIndex from "components/History/Index";
import { buildCollectionModal } from "./buildCollectionModal";
import { createDatasetCollection } from "components/History/model/queries";
import { watchHistory } from "store/historyStore/model/watchHistory";

// extend existing current history panel
export class HistoryPanelProxy {
    constructor() {
        const Galaxy = getGalaxyInstance();
        Galaxy.currHistoryPanel = this;
        const model = (this.model = new Backbone.Model({}));
        this.collection = {
            each(callback, filterText = "") {
                const historyItems = store.getters.getHistoryItems({ historyId: model.id, filterText: filterText });
                historyItems.forEach((model) => {
                    callback(new Backbone.Model(model));
                });
            },
            on(name, callback) {
                this.off();
                this.unwatch = store.watch(
                    (state, getters) => getters.getLatestCreateTime(),
                    () => {
                        callback();
                        console.debug("History change watcher detected a change.", name);
                    }
                );
                console.debug("History change watcher enabled.", name);
            },
            off(name) {
                if (this.unwatch) {
                    this.unwatch();
                    console.debug("History change watcher disabled.", name);
                }
            },
        };

        // watch the store, update history id
        store.watch(
            (state, getters) => getters["history/currentHistory"],
            (history) => {
                this.model.id = history.id;
                this.model.set("name", history.name);
            }
        );

        // start watching the history with continuous queries
        watchHistory();
    }
    refreshContents() {
        // to be removed after disabling legacy history
    }
    loadCurrentHistory() {
        store.dispatch("history/loadCurrentHistory");
    }
    switchToHistory(historyId) {
        this.model.id = historyId;
        store.dispatch("history/setCurrentHistoryId", historyId);
    }
    async buildCollection(collectionType, selection, hideSourceItems, fromRulesInput = false) {
        let selectionContent = null;
        if (fromRulesInput) {
            selectionContent = selection;
        } else {
            selectionContent = new Map();
            selection.models.forEach((obj) => {
                selectionContent.set(obj.id, obj);
            });
        }
        const modalResult = await buildCollectionModal(
            collectionType,
            this.model.id,
            selectionContent,
            hideSourceItems,
            fromRulesInput
        );
        if (modalResult) {
            console.debug("Submitting collection build request.", modalResult);
            await createDatasetCollection({ id: this.model.id }, modalResult);
        }
    }
    render() {
        const container = document.createElement("div");
        document.querySelector("#right > .unified-panel-header").remove();
        document.querySelector("#right > .unified-panel-controls").remove();
        document.querySelector("#right > .unified-panel-body").remove();
        const parent = document.querySelector("#right");
        parent.classList.add("beta");
        parent.prepend(container);
        const mountFn = mountVueComponent(HistoryIndex);
        mountFn({}, container);
    }
}
