import Backbone from "backbone";
import _l from "utils/localization";
import { getGalaxyInstance } from "app";
import Ui from "mvc/ui/ui-misc";
import historyOptionsMenu from "mvc/history/options-menu";
import CurrentHistoryView from "mvc/history/history-view-edit-current";

/** the right hand panel in the analysis page that shows the current history */
const HistoryPanel = Backbone.View.extend({
    initialize: function (page, options) {
        const Galaxy = getGalaxyInstance();
        const panelHeaderButtons = [];

        this.userIsAnonymous = Galaxy.user.isAnonymous();
        this.allow_user_dataset_purge = options.config.allow_user_dataset_purge;
        this.root = options.root;

        // view of the current history
        this.historyView = new CurrentHistoryView.CurrentHistoryView({
            className: `${CurrentHistoryView.CurrentHistoryView.prototype.className} middle`,
            purgeAllowed: this.allow_user_dataset_purge,
            linkTarget: "galaxy_main",
        });

        // add history panel to Galaxy object
        Galaxy.currHistoryPanel = this.historyView;
        Galaxy.currHistoryPanel.listenToGalaxy(Galaxy);

        // build buttons
        this.buttonRefresh = new Ui.ButtonLink({
            id: "history-refresh-button",
            title: _l("Refresh history"),
            cls: "panel-header-button history-refresh-button",
            icon: "fa fa-sync",
            onclick: () => {
                this.historyView.loadCurrentHistory();
            },
        });
        panelHeaderButtons.push(this.buttonRefresh);

        if (!this.userIsAnonymous) {
            this.buttonNew = new Ui.ButtonLink({
                id: "history-new-button",
                title: _l("Create new history"),
                cls: "panel-header-button history-new-button",
                icon: "fa fa-plus",
                onclick: function () {
                    Galaxy.currHistoryPanel.createNewHistory();
                },
            });
            panelHeaderButtons.push(this.buttonNew);
        }

        this.buttonViewMulti = new Ui.ButtonLink({
            id: "history-view-multi-button",
            title: _l("View all histories"),
            cls: "panel-header-button history-view-multi-button",
            icon: "fa fa-columns",
            href: `${this.root}history/view_multiple`,
        });
        panelHeaderButtons.push(this.buttonViewMulti);

        this.buttonOptions = new Ui.ButtonLink({
            id: "history-options-button",
            title: _l("History options"),
            cls: "panel-header-button menu-expand-button",
            target: "galaxy_main",
            icon: "fa fa-cog",
            href: `${this.root}root/history_options`,
            description: "history options",
        });
        panelHeaderButtons.push(this.buttonOptions);

        this.model = new Backbone.Model({
            // define components
            cls: "history-right-panel details",
            title: _l("History"),
            buttons: panelHeaderButtons,
        });

        // build body template and connect history view
        this.setElement(this._template());
        this.historyView.setElement(this.$el);
        this.historyView.connectToQuotaMeter(Galaxy.quotaMeter);
        this.historyView.loadCurrentHistory();

        // fetch to update the quota meter adding 'current' for any anon-user's id
        Galaxy.listenTo(this.historyView, "history-size-change", () => {
            Galaxy.user.fetch({
                url: `${Galaxy.user.urlRoot()}/${Galaxy.user.id || "current"}`,
            });
        });
    },

    render: function () {
        this.optionsMenu = historyOptionsMenu(this.buttonOptions.$el, {
            anonymous: this.userIsAnonymous,
            purgeAllowed: this.allow_user_dataset_purge,
            root: this.root,
        });
        this.buttonViewMulti.$el[!this.userIsAnonymous ? "show" : "hide"]();
    },

    /** add history view div */
    _template: function (data) {
        return ['<div id="current-history-panel" class="history-panel middle"/>'].join("");
    },

    toString: function () {
        return "historyPanel";
    },
});

export default HistoryPanel;
