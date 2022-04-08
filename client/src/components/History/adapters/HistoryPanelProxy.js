/**
 * This is an adapter for the History component. It's required since the previous
 * history provided the same interface for other components.
 */
import $ from "jquery";
import Backbone from "backbone";
import store from "store";
import { getGalaxyInstance } from "app";
import { mountVueComponent } from "utils/mountVueComponent";
import HistoryIndex from "components/History/Index";
import { buildCollectionModal } from "./buildCollectionModal";
import { createDatasetCollection } from "components/History/model/queries";

// extend existing current history panel
export default class HistoryPanelProxy {
    constructor() {
        const Galaxy = getGalaxyInstance();
        Galaxy.currHistoryPanel = this;
        const model = (this.model = new Backbone.Model({}));
        this.collection = {
            constructor(models) {
                this.models = models;
                this.unwatch = null;
            },
            each(callback) {
                const historyItems = store.getters.getHistoryItems({ historyId: model.id, filterText: "" });
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

        /*/ fetch to update the quota meter adding 'current' for any anon-user's id
        Galaxy.listenTo(this.historyView, "history-size-change", () => {
            Galaxy.user.fetch({
                url: `${Galaxy.user.urlRoot()}/${Galaxy.user.id || "current"}`,
            });
        });*/

        // Watch the store, update history id
        store.watch(
            (state, getters) => getters["betaHistory/currentHistory"],
            (history) => {
                this.model.id = history.id;
                this.model.set("name", history.name);
            }
        );
    }
    refreshContents() {
        // to be removed after disabling legacy history
    }
    loadCurrentHistory() {
        this.switchToHistory(this.model.id);
    }
    switchToHistory(historyId) {
        this.model.id = historyId;
        store.dispatch("betaHistory/loadHistoryById", historyId);
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
        $("#right > .unified-panel-header").remove();
        $("#right > .unified-panel-controls").remove();
        $("#right > .unified-panel-body").remove();
        $("#right").addClass("beta").prepend(container);
        const mountFn = mountVueComponent(HistoryIndex);
        mountFn({}, container);
    }
}
