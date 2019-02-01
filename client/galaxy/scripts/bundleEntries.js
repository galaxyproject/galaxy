/**
 * The big list of horrible globals we expose on window.bundleEntries.
 *
 * Everything that is exposed on this global variable is something that the python templates
 * require for their hardcoded initializations. These objects are going to have to continue
 * to exist until such time as we replace the overall application with a Vue component which
 * will handle initializations for components individually.
 */

import $ from "jquery";
import "bootstrap";
export { getGalaxyInstance, setGalaxyInstance } from "app";
import WorkflowView from "mvc/workflow/workflow-view";
import { TracksterUIView } from "viz/trackster";
export { TracksterUI } from "viz/trackster";
import Circster from "viz/circster";
export { PhylovizView as phyloviz } from "viz/phyloviz";
export { SweepsterVisualization, SweepsterVisualizationView } from "viz/sweepster";
import GalaxyLibrary from "galaxy.library";
import AdminToolshed from "admin.toolshed";
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

// Previously wandering around as window.thing = thing in the onload script
export { default as panels } from "layout/panel";
export { show_in_overlay, hide_modal, show_message, show_modal, Modal } from "layout/modal";
export { make_popupmenu, make_popup_menus } from "ui/popupmenu";
export { default as async_save_text } from "utils/async-save-text";

// Previously "chart"
import Client from "mvc/visualization/chart/chart-client";
import Datasets from "mvc/visualization/chart/utilities/datasets";
import Series from "mvc/visualization/chart/utilities/series";
import Jobs from "mvc/visualization/chart/utilities/jobs";

export function chart(options) {
    return new Client(options);
}

export let chartUtilities = {
    Datasets: Datasets,
    Jobs: Jobs,
    Series: Series
};

export { initMasthead } from "components/Masthead/initMasthead";
export { panelManagement } from "onload/globalInits/panelManagement";
export { init_tag_click_function } from "ui/autocom_tagging";

// Used in common.mako
export { default as store } from "store";
