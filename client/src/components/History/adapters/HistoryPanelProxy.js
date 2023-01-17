/**
 * This is an adapter for the History component. It's required since the previous
 * history provided the same interface for other components.
 */
import Backbone from "backbone";
import store from "store";
import { useHistoryItemsStore } from "stores/history/historyItemsStore";
import { buildCollectionModal } from "./buildCollectionModal";
import { createDatasetCollection } from "components/History/model/queries";
import { watchHistory } from "store/historyStore/model/watchHistory";

// extend existing current history panel
export class HistoryPanelProxy {
    constructor() {
        const model = (this.model = new Backbone.Model({}));
        const historyItemsStore = useHistoryItemsStore();
        this.collection = {
            each(callback, filterText = "") {
                const historyItems = historyItemsStore.getHistoryItems(model.id, filterText);
                historyItems.forEach((model) => {
                    callback(new Backbone.Model(model));
                });
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
        // to be removed after disabling legacy history, present to provide uniform interface
        // with History Panel Backbone View.
    }
    loadCurrentHistory() {
        store.dispatch("history/loadCurrentHistory");
    }
    switchToHistory(historyId) {
        this.model.id = historyId;
        store.dispatch("history/setCurrentHistory", historyId);
    }
    async buildCollection(collectionType, selection, historyId = null, fromRulesInput = false) {
        let selectionContent = null;
        historyId = historyId || this.model.id;
        if (fromRulesInput) {
            selectionContent = selection;
        } else {
            selectionContent = new Map();
            selection.models.forEach((obj) => {
                selectionContent.set(obj.id, obj);
            });
        }
        const modalResult = await buildCollectionModal(collectionType, selectionContent, historyId, fromRulesInput);
        if (modalResult) {
            console.debug("Submitting collection build request.", modalResult);
            await createDatasetCollection({ id: historyId }, modalResult);
        }
    }
}
