import { useGlobalUploadModal } from "composables/globalUploadModal";

import { uploadPayload } from "@/utils/upload-payload.js";
import { uploadSubmit } from "@/utils/upload-submit.js";
import { startWatchingHistory } from "@/watch/watchHistory";

import DataDialog from "components/DataDialog/DataDialog.vue";

import { useHistoryStore } from "stores/historyStore";

import { appendVueComponent } from "utils/mountVueComponent";

/**
 * Opens a modal dialog for data selection
 * @param {function} callback - Result function called with selection
 */
export async function dialog(galaxy, callback, options = {}) {
    const { loadCurrentHistoryId } = useHistoryStore();
    const historyId = await loadCurrentHistoryId();
    Object.assign(options, {
        callback: callback,
        history: historyId,
    });
    if (options.new) {
        const { openGlobalUploadModal } = useGlobalUploadModal();
        openGlobalUploadModal(options);
    } else {
        appendVueComponent(DataDialog, options);
    }
}

/**
 * Creates a history dataset by submitting an upload request
 * TODO: This should live somewhere else.
 */
export async function create(galaxy, options) {
    const { loadCurrentHistoryId } = useHistoryStore();
    const historyId = await loadCurrentHistoryId();
    uploadSubmit({
        success: (response) => {
            startWatchingHistory(galaxy);
            if (options.success) {
                options.success(response);
            }
        },
        error: options.error,
        data: {
            payload: uploadPayload([options], historyId),
        },
    });
}
