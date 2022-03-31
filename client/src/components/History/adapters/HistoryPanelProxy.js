/**
 * This is a backbone view adapter for a Vue component. It's just
 * a Vue mount function with the interface of a backbone view so
 * that it can fit into the existing backbone layout scheme.
 */

import { mountVueComponent } from "utils/mountVueComponent";
import HistoryIndex from "components/History/Index";

// mvc nonsense
import $ from "jquery";
import { getGalaxyInstance } from "app";
import Backbone from "backbone";
import CurrentHistoryView from "mvc/history/history-view-edit-current";
import "./HistoryPanelProxy.scss";
// import store from "store";

// extend existing current history panel
export default class HistoryPanelProxy {
    constructor(page, options) {
        const Galaxy = getGalaxyInstance();
        Galaxy.currHistoryPanel = this;
        this.userIsAnonymous = Galaxy.user.isAnonymous();
        this.purgeAllowed = this.allow_user_dataset_purge = options.config.allow_user_dataset_purge;
        this.root = options.root;
        this.fakeHistoryViewModel = true;
        this.className = `fake ${CurrentHistoryView.CurrentHistoryView.prototype.className} middle`;
        this.linkTarget = "galaxy_main";
        this.model = new Backbone.Model({});
        this.model.UPDATE_DELAY = 1000;
    }
    refreshContents() {
        console.log("refreshContents called.");
    }
    loadCurrentHistory() {
        console.log("loadCurrentHistory called.");
    }
    switchToHistory(historyId) {
        console.log("switchToHistory called.", historyId);
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
