import DatasetCollectionDialog from "components/SelectionDialog/DatasetCollectionDialog.vue";

import { FilesDialog } from "components/FilesDialog";

import { useHistoryStore } from "stores/historyStore";

import { appendVueComponent } from "utils/mountVueComponent";

/**
 * Opens a modal dialog for dataset collection selection
 * @param {function} callback - Result function called with selection
 */
export async function datasetCollectionDialog(callback, options = {}) {
    const { loadCurrentHistoryId } = useHistoryStore();
    const historyId = await loadCurrentHistoryId();

    Object.assign(options, {
        callback: callback,
        history: history_id,
    });

    appendVueComponent(DatasetCollectionDialog, options);
}

export function filesDialog(callback, options = {}, routePush) {
    Object.assign(options, {
        callback: callback,
        routePush: routePush,
    });

    appendVueComponent(FilesDialog, options);
}
