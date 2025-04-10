import { getGalaxyInstance } from "app";
import { FilesDialog } from "components/FilesDialog";

import { getCurrentGalaxyHistory, mountSelectionDialog } from "./dataModalUtils";

import DatasetCollectionDialog from "components/SelectionDialog/DatasetCollectionDialog.vue";

/**
 * Opens a modal dialog for dataset collection selection
 * @param {function} callback - Result function called with selection
 */
export function datasetCollectionDialog(callback, options = {}) {
    getCurrentGalaxyHistory(getGalaxyInstance()).then((history_id) => {
        Object.assign(options, {
            callback: callback,
            history: history_id,
        });
        mountSelectionDialog(DatasetCollectionDialog, options);
    });
}

export function filesDialog(callback, options = {}) {
    Object.assign(options, {
        callback: callback,
    });
    mountSelectionDialog(FilesDialog, options);
}
