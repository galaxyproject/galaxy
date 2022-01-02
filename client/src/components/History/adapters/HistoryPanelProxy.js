/**
 * This is a backbone view adapter for a Vue component. It's just
 * a Vue mount function with the interface of a backbone view so
 * that it can fit into the existing backbone layout scheme.
 */

import { mountVueComponent } from "utils/mountVueComponent";
import CurrentHistoryPanel from "../CurrentHistoryPanel";
// import { genericProxy } from "utils/proxy";

// mvc nonsense
import { getGalaxyInstance } from "app";
import Backbone from "backbone";
import CurrentHistoryView from "mvc/history/history-view-edit-current";
import { History } from "mvc/history/history-model";
import "./HistoryPanelProxy.scss";
import store from "store";

// bypass polling while using the beta panel, skips contents loading
const FakeHistoryViewModel = CurrentHistoryView.CurrentHistoryView.extend({
    loadHistory: function (historyId, options) {
        this.setModel(new History({ id: historyId }));
        this.trigger("loading");
        options.view = "dev-detailed";
        return this.model.fetch(options);
    },
});

// extend existing current history panel
export const HistoryPanelProxy = Backbone.View.extend({
    initialize(page, options) {
        const Galaxy = getGalaxyInstance();

        this.userIsAnonymous = Galaxy.user.isAnonymous();
        this.allow_user_dataset_purge = options.config.allow_user_dataset_purge;
        this.root = options.root;

        // fake view of the current history
        this.historyView = new FakeHistoryViewModel({
            fakeHistoryViewModel: true,
            className: `fake ${CurrentHistoryView.CurrentHistoryView.prototype.className} middle`,
            purgeAllowed: this.allow_user_dataset_purge,
            linkTarget: "galaxy_main",
        });

        // add history panel to Galaxy object
        // Galaxy.currHistoryPanel = genericProxy("Galaxy.currHistoryPanel", this.historyView);
        Galaxy.currHistoryPanel = this.historyView;
        Galaxy.currHistoryPanel.listenToGalaxy(Galaxy);

        this.model = new Backbone.Model({});
        this.setElement("<div/>");
        this.historyView.setElement(this.$el);
        this.historyView.connectToQuotaMeter(Galaxy.quotaMeter);
        // this.historyView.loadCurrentHistory();

        // fetch to update the quota meter adding 'current' for any anon-user's id
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
        );
    },
    render() {
        // Hack: For now, remove unused "unified-panel" elements until we can
        // completely re-work the layout container. Unfortunately the
        // layout/page and sidepanel views are super-rigid and expect an
        // explicit header and controls element that I'd rather be managed by by
        // the component, so I'm just chopping those elements out manually.

        // TODO: Rework layout/page and sidepanel to avoid this arrangement
        document.querySelector("#right > .unified-panel-header").parentNode.removeChild();
        document.querySelector("#right > .unified-panel-controls").parentNode.removeChild();
        document.querySelector("#right > .unified-panel-body").parentNode.removeChild();
        document.querySelector("#right").addClass("beta").prepend(this.$el);

        const container = this.$el[0];
        const mountHistory = mountVueComponent(CurrentHistoryPanel);
        mountHistory({}, container);

        return this;
    },
});

export default HistoryPanelProxy;
