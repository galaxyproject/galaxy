/**
 * This is an adapter for the History component. It's required since the previous
 * history provided the same interface for other components.
 */
import $ from "jquery";
import store from "store";
import { getGalaxyInstance } from "app";
import { mountVueComponent } from "utils/mountVueComponent";
import HistoryIndex from "components/History/Index";
import { buildCollectionModal } from "./buildCollectionModal";

// extend existing current history panel
export default class HistoryPanelProxy {
    constructor() {
        const Galaxy = getGalaxyInstance();
        Galaxy.currHistoryPanel = this;
        const model = (this.model = new Backbone.Model({}));
        this.collection = {
            constructor(models) {
                this.models = models;
            },
            getByHid(hid) {
                return store.getters.getHistoryItemByHid({ hid, historyId: model.id });
            },
            on(name, callback, context) {
                console.log("on called.", name);
            },
            off(name, callback, context) {
                console.log("off called.", name);
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
            (st, gets) => gets["betaHistory/currentHistory"],
            (history) => {
                this.model.id = history.id;
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
    buildCollection(collectionType, selection, hideSourceItems) {
        const selectionModel = {
            values() {
                return selection;
            },
        };
        buildCollectionModal(collectionType, this.model.id, selectionModel, hideSourceItems);
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
