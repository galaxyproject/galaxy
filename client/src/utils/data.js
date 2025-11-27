import { useGlobalUploadModal } from "@/composables/globalUploadModal";
import { useHistoryStore } from "@/stores/historyStore";
import { appendVueComponent } from "@/utils/mountVueComponent";
import { buildLegacyPayload } from "@/utils/uploadPayload";
import { submitDatasetUpload } from "@/utils/uploadSubmit";

import DataDialog from "@/components/DataDialog/DataDialog.vue";

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
    submitDatasetUpload({
        success: (response) => {
            const historyStore = useHistoryStore();
            historyStore.startWatchingHistory();
            if (options.success) {
                options.success(response);
            }
        },
        error: options.error,
        data: {
            payload: buildLegacyPayload([options], historyId),
        },
    });
}
