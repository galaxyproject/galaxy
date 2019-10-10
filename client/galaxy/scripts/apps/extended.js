import $ from "jquery";
import "bootstrap";
// export { GalaxyApp } from "app";
import { getGalaxyInstance } from "app";
export { getGalaxyInstance, setGalaxyInstance } from "app";
import WorkflowView from "mvc/workflow/workflow-view";
import { TracksterUIView } from "viz/trackster";
export { TracksterUI } from "viz/trackster";
import Circster from "viz/circster";
export { PhylovizView as phyloviz } from "viz/phyloviz";
export { SweepsterVisualization, SweepsterVisualizationView } from "viz/sweepster";
import GalaxyLibrary from "galaxy.library";
import AdminToolshed from "admin.toolshed";
import Masthead from "layout/masthead";
import user from "mvc/user/user-model";
import Modal from "mvc/ui/ui-modal";
export { default as pages } from "galaxy.pages";
export { createTabularDatasetChunkedView } from "mvc/dataset/data";
import { HistoryCollection } from "mvc/history/history-model";
export { History } from "mvc/history/history-model";
export { HistoryContents } from "mvc/history/history-contents";
import MultiPanel from "mvc/history/multi-panel";
export { historyEntry as history } from "mvc/history/history-view";
export { default as HistoryViewAnnotated } from "mvc/history/history-view-annotated";
export { default as HistoryCopyDialog } from "mvc/history/copy-dialog";
export { default as HDAListItemEdit } from "mvc/history/hda-li-edit";
export { default as HDAModel } from "mvc/history/hda-model";
export { default as LegacyGridView } from "legacy/grid/grid-view";
export { create_chart, create_histogram } from "reports/run_stats";
export { default as ToolshedGroups } from "toolshed/toolshed.groups";
export { chart, chartUtilities } from "./chart";

export function masthead(options) {
    let Galaxy = getGalaxyInstance();
    if (!Galaxy.user) {
        Galaxy.user = new user.User(options.user_json);
    }
    if (!Galaxy.masthead) {
        Galaxy.masthead = new Masthead.View(options);
        Galaxy.modal = new Modal.View();
        $("#masthead").replaceWith(Galaxy.masthead.render().$el);
    }
}

export function adminToolshed(options) {
    new AdminToolshed.GalaxyApp(options);
}

export function trackster(options) {
    new TracksterUIView(options);
}

export function circster(options) {
    new Circster.GalaxyApp(options);
}

export function workflow(options) {
    new WorkflowView(options);
}

export function library(options) {
    new GalaxyLibrary.GalaxyApp(options);
}

export function multiHistory(options) {
    let histories = new HistoryCollection([], {
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

// Used in common.mako
export { default as store } from "store";
