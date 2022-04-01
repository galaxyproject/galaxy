/**
 * This is an adapter for the History component. It's required since the previous
 * history provided the same interface for other components.
 */
import $ from "jquery";
import store from "store";
import { getGalaxyInstance } from "app";
import { mountVueComponent } from "utils/mountVueComponent";
import HistoryIndex from "components/History/Index";

// extend existing current history panel
export default class HistoryPanelProxy {
    constructor() {
        const Galaxy = getGalaxyInstance();
        Galaxy.currHistoryPanel = this;
        this.model = new Backbone.Model({});
    }
    refreshContents() {
        // to be removed after disabling legacy history
    }
    loadCurrentHistory() {
        this.switchToHistory(this.model.id);
    }
    switchToHistory(historyId) {
        this.model.id = historyId;
        store.dispatch("betaHistory/loadCurrentHistory");
    }
    on(name, callback, context) {
        console.log("on called.", name);
    }
    off(name, callback, context) {
        console.log("off called.", name);
    }
    createCollection(type, models, flag) {
        // calls build collection?
        console.log("createCollection called.");
    }
    getAll() {
        console.log("getAll called.");
        return [];
    }
    buildCollection(rules, selection, flag) {
        console.log("buildCollection called.");
    }
    getByHid(hid) {
        console.log("getByHid called.");
        return {};
    }
    render() {
        const container = document.createElement("div");
        $("#right > .unified-panel-header").remove();
        $("#right > .unified-panel-controls").remove();
        $("#right > .unified-panel-body").remove();
        $("#right").addClass("beta").prepend(container);
        const mountFn = mountVueComponent(HistoryIndex);
        console.log(mountFn({}, container));
    }
    listeners() {
        /*/ fetch to update the quota meter adding 'current' for any anon-user's id
        Galaxy.listenTo(this.historyView, "history-size-change", () => {
            Galaxy.user.fetch({
                url: `${Galaxy.user.urlRoot()}/${Galaxy.user.id || "current"}`,
            });
        });

        // Watch the store, change the fake history model when it changs
        store.watch(
            (st, gets) => gets["betaHistory/currentHistory"],
            (history) => {
                const panel = Galaxy.currHistoryPanel;
                const existingId = panel?.model?.id || undefined;
                if (existingId != history.id) {
                    panel.setModel(new History({ id: history.id }));
                }
            }
        );*/
    }
}
