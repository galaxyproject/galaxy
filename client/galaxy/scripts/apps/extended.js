import _l from "utils/localization";
import GalaxyApp from "galaxy";
import WorkflowView from "mvc/workflow/workflow-view";
import Trackster from "viz/trackster";
import Circster from "viz/circster";
import Phyloviz from "viz/phyloviz";
import Sweepster from "viz/sweepster";
import GalaxyLibrary from "galaxy.library";
import AdminToolshed from "admin.toolshed";
import Masthead from "layout/masthead";
import user from "mvc/user/user-model";
import Modal from "mvc/ui/ui-modal";
import pagesEditorOnload from "galaxy.pages";
import Data from "mvc/dataset/data";
import History from "mvc/history/history-model";
import StructureView from "mvc/history/history-structure-view";
import HistoryContents from "mvc/history/history-contents";
import MultiPanel from "mvc/history/multi-panel";
import HistoryView from "mvc/history/history-view";
import HistoryViewEdit from "mvc/history/history-view-edit";
import HistoryViewAnnotated from "mvc/history/history-view-annotated";
import HistoryCopyDialog from "mvc/history/copy-dialog";
import HDAListItemEdit from "mvc/history/hda-li-edit";
import HDAModel from "mvc/history/hda-model";
import addLogging from "utils/add-logging";
import LegacyGridView from "legacy/grid/grid-view";
import * as run_stats from "reports/run_stats";
import ToolshedGroups from "toolshed/toolshed.groups";

if (window.Galaxy && window.Galaxy.debug === undefined) {
    //TODO: (kind of a temporary hack?) Must have Galaxy.logging for some of the imports
    //here; remove when imports are all fixed.
    addLogging(window.Galaxy, "GalaxyApp");
}

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

export function historyEntry(options) {
    $("#toggle-deleted").modeButton({
        initialMode: options.initialModeDeleted,
        modes: [
            { mode: "showing_deleted", html: _l("Exclude deleted") },
            { mode: "not_showing_deleted", html: _l("Include deleted") }
        ]
    });
    $("#toggle-hidden").modeButton({
        initialMode: options.initialModeHidden,
        modes: [
            { mode: "showing_hidden", html: _l("Exclude hidden") },
            { mode: "not_showing_hidden", html: _l("Include hidden") }
        ]
    });
    $("#switch").click(function() {
        //##HACK:ity hack hack
        //##TODO: remove when out of iframe
        var hview =
            Galaxy.currHistoryPanel || (window.top.Galaxy && window.top.Galaxy.currHistoryPanel)
                ? window.top.Galaxy.currHistoryPanel
                : null;
        if (hview) {
            hview.switchToHistory("${ history[ 'id' ] }");
        } else {
            window.location = "${ switch_to_url }";
        }
    });
    // use_panels effects where the the center_panel() is rendered:
    //  w/o it renders to the body, w/ it renders to #center - we need to adjust a few things for scrolling to work
    if (options.hasMasthead) {
        $("#center").addClass("flex-vertical-container");
    }

    let viewClass = options.userIsOwner ? HistoryViewEdit.HistoryViewEdit : HistoryView.HistoryView;
    let historyModel = new History.History(options.historyJSON);

    // attach the copy dialog to the import button now that we have a history
    $("#import").click(function() {
        HistoryCopyDialog(historyModel, {
            useImport: true,
            // use default datasets option to match the toggle-deleted button
            allDatasets: $("#toggle-deleted").modeButton("getMode").mode === "showing_deleted"
        }).done(function() {
            if (window === window.parent) {
                window.location = Galaxy.root;
            } else if (Galaxy.currHistoryPanel) {
                Galaxy.currHistoryPanel.loadCurrentHistory();
            }
        });
    });

    let historyView = new viewClass({
        el: $("#history-" + options.historyJSON.id),
        className: viewClass.prototype.className + " wide",
        $scrollContainer: options.hasMasthead
            ? function() {
                  return this.$el.parent();
              }
            : undefined,
        model: historyModel,
        show_deleted: options.showDeletedJson,
        show_hidden: options.showHiddenJson,
        purgeAllowed: options.allow_user_dataset_purge
    });
    historyView.trigger("loading");
    historyModel
        .fetchContents({ silent: true })
        .fail(function() {
            alert("Galaxy history failed to load");
        })
        .done(function() {
            historyView.trigger("loading-done");
            historyView.render();
        });
    $("#toggle-deleted").on("click", function() {
        historyView.toggleShowDeleted();
    });
    $("#toggle-hidden").on("click", function() {
        historyView.toggleShowHidden();
    });
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
    multiHistory: multiHistoryEntry,
    history: historyEntry,
    History: History.History,
    HistoryContents: HistoryContents.HistoryContents,
    SweepsterVisualization: Sweepster.SweepsterVisualization,
    SweepsterVisualizationView: Sweepster.SweepsterVisualizationView,
    HistoryCopyDialog,
    HistoryViewAnnotated,
    Trackster,
    StructureView,
    HDAListItemEdit,
    HDAModel,
    GalaxyApp,
    LegacyGridView,
    run_stats,
    ToolshedGroups
};

window.bundleEntries = bundleEntries;
