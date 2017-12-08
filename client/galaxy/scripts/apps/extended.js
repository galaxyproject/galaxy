import WorkflowView from "mvc/workflow/workflow-view";
import Trackster from "viz/trackster";
import Circster from "viz/circster";
import Phyloviz from "viz/phyloviz";
import GalaxyLibrary from "galaxy.library";
import AdminToolshed from "admin.toolshed";
import Masthead from "layout/masthead";
import user from "mvc/user/user-model";
import Modal from "mvc/ui/ui-modal";
import pagesEditorOnload from "galaxy.pages";
import Data from "mvc/dataset/data";
import History from "mvc/history/history-model";
import MultiPanel from "mvc/history/multi-panel";

export function mastheadEntry(options) {
    if (!Galaxy.user) {
        Galaxy.user = new user.User(options.user_json);
    }
    if (!Galaxy.masthead) {
        Galaxy.masthead = new Masthead.View(options);
        Galaxy.modal = new Modal.View();
        $("#masthead").replaceWith(Galaxy.masthead.render().$el);
    }
}

export function adminToolshedEntry(options) {
    new AdminToolshed.GalaxyApp(options);
}

export function tracksterEntry(options) {
    new Trackster.GalaxyApp(options);
}

export function circsterEntry(options) {
    new Circster.GalaxyApp(options);
}

export function workflowEntry(options) {
    new WorkflowView(options);
}

export function libraryEntry(options) {
    new GalaxyLibrary.GalaxyApp(options);
}

export function multiHistoryEntry(options) {
    let histories = new History.HistoryCollection([], {
        includeDeleted: options.includingDeleted,
        order: options.order,
        limitOnFirstFetch: options.limit,
        limitPerFetch: options.limit,
        currentHistoryId: options.current_history_id
    });

    let multipanel = new MultiPanel.MultiPanelColumns({
        el: $("#center").get(0),
        histories: histories
    });

    histories.fetchFirst({ silent: true }).done(function() {
        multipanel.createColumns();
        multipanel.render(0);
    });
}

export const bundleEntries = {
    library: libraryEntry,
    masthead: mastheadEntry,
    workflow: workflowEntry,
    trackster: tracksterEntry,
    circster: circsterEntry,
    adminToolshed: adminToolshedEntry,
    pages: pagesEditorOnload,
    phyloviz: Phyloviz.PhylovizView,
    createTabularDatasetChunkedView: Data.createTabularDatasetChunkedView,
    multiHistory: multiHistoryEntry
};

window.bundleEntries = bundleEntries;
