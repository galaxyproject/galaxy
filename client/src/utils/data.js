import { getGalaxyInstance } from "app";
import axios from "axios";
import { FilesDialog } from "components/FilesDialog";
import { useGlobalUploadModal } from "composables/globalUploadModal";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";

import { uploadPayload } from "@/utils/upload-payload.js";
import { uploadSubmit } from "@/utils/upload-submit.js";
import { startWatchingHistory } from "@/watch/watchHistory";

import DataDialog from "components/DataDialog/DataDialog.vue";
import DatasetCollectionDialog from "components/SelectionDialog/DatasetCollectionDialog.vue";

// This should be moved more centrally (though still hanging off Galaxy for
// external use?), and populated from the store; just using this as a temporary
// interface.
export async function getCurrentGalaxyHistory() {
    const galaxy = getGalaxyInstance();
    if (galaxy.currHistoryPanel && galaxy.currHistoryPanel.model.id) {
        // TODO: use central store for this.
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
    getCurrentGalaxyHistory().then((history_id) => {
        Object.assign(options, {
            callback: callback,
            history: history_id,
        });
        if (options.new) {
            const { openGlobalUploadModal } = useGlobalUploadModal();
            openGlobalUploadModal(options);
        } else {
            _mountSelectionDialog(DataDialog, options);
        }
    });
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
    async function getHistory() {
        if (!options.history_id) {
            return getCurrentGalaxyHistory();
        }
        return options.history_id;
    }
    getHistory().then((history_id) => {
        uploadSubmit({
            success: (response) => {
                startWatchingHistory();
                if (options.success) {
                    options.success(response);
                }
            },
            error: options.error,
            data: {
                payload: uploadPayload([options], history_id),
            },
        });
    });
}
