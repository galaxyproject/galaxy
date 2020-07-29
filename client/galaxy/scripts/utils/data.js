import $ from "jquery";
import axios from "axios";
import Vue from "vue";
import DataDialog from "components/DataDialog/DataDialog.vue";
import { FilesDialog } from "components/FilesDialog";
import WorkflowDialog from "components/SelectionDialog/WorkflowDialog.vue";
import DatasetCollectionDialog from "components/SelectionDialog/DatasetCollectionDialog.vue";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";

// This should be moved more centrally (though still hanging off Galaxy for
// external use?), and populated from the store; just using this as a temporary
// interface.
async function getCurrentGalaxyHistory() {
    const galaxy = getGalaxyInstance();
    if (galaxy.currHistoryPanel && galaxy.currHistoryPanel.model.id) {
        // TODO: use central store (vuex) for this.
        return galaxy.currHistoryPanel.model.id;
    } else {
        // Otherwise manually fetch the current history json and use that id.
        return axios
            .get(`${getAppRoot()}history/current_history_json`)
            .then((response) => {
                return response.data.id;
            })
            .catch((err) => {
                console.error("Error fetching current user history:", err);
                return null;
            });
    }
}

/**
 * Opens a modal dialog for data selection
 * @param {function} callback - Result function called with selection
 */
export function dialog(callback, options = {}) {
    const galaxy = getGalaxyInstance();
    const host = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
    getCurrentGalaxyHistory().then((history_id) => {
        Object.assign(options, {
            callback: callback,
            history: history_id,
            root: galaxy.root,
            host: host,
        });
        _mountSelectionDialog(DataDialog, options);
    });
}

/**
 * Opens a modal dialog for workflow selection
 * @param {function} callback - Result function called with selection
 */
export function workflowDialog(callback, options = {}) {
    Object.assign(options, {
        callback: callback,
    });
    _mountSelectionDialog(WorkflowDialog, options);
}

/**
 * Opens a modal dialog for dataset collection selection
 * @param {function} callback - Result function called with selection
 */
export function datasetCollectionDialog(callback, options = {}) {
    getCurrentGalaxyHistory().then((history_id) => {
        Object.assign(options, {
            callback: callback,
            history: history_id,
        });
        _mountSelectionDialog(DatasetCollectionDialog, options);
    });
}

export function filesDialog(callback, options = {}) {
    Object.assign(options, {
        callback: callback,
    });
    _mountSelectionDialog(FilesDialog, options);
}

function _mountSelectionDialog(clazz, options) {
    const instance = Vue.extend(clazz);
    const vm = document.createElement("div");
    $("body").append(vm);
    new instance({
        propsData: options,
    }).$mount(vm);
}

/**
 * Creates a history dataset by submitting an upload request
 * TODO: This should live somewhere else.
 */
export function create(options) {
    const Galaxy = getGalaxyInstance();
    const history_panel = Galaxy.currHistoryPanel;
    async function getHistory() {
        if (!options.history_id) {
            return getCurrentGalaxyHistory();
        }
        return options.history_id;
    }
    getHistory().then((history_id) => {
        $.uploadpost({
            url: `${getAppRoot()}api/tools`,
            success: (response) => {
                if (history_panel) {
                    history_panel.refreshContents();
                }
                if (options.success) {
                    options.success(response);
                }
            },
            error: options.error,
            data: {
                payload: {
                    tool_id: "upload1",
                    history_id: history_id,
                    inputs: JSON.stringify({
                        "files_0|type": "upload_dataset",
                        "files_0|NAME": options.file_name,
                        "files_0|space_to_tab": options.space_to_tab ? "Yes" : null,
                        "files_0|to_posix_lines": options.to_posix_lines ? "Yes" : null,
                        "files_0|dbkey": options.genome || "?",
                        "files_0|file_type": options.extension || "auto",
                        "files_0|url_paste": options.url_paste,
                    }),
                },
            },
        });
    });
}
