import { useGlobalUploadModal } from "composables/globalUploadModal";

import { uploadPayload } from "@/utils/upload-payload.js";
import { uploadSubmit } from "@/utils/upload-submit.js";
import { startWatchingHistory } from "@/watch/watchHistory";

import { getCurrentGalaxyHistory, mountSelectionDialog } from "./dataModalUtils";

import DataDialog from "components/DataDialog/DataDialog.vue";

/**
 * Opens a modal dialog for data selection
 * @param {function} callback - Result function called with selection
 */
export function dialog(galaxy, callback, options = {}) {
    getCurrentGalaxyHistory(galaxy).then((history_id) => {
        Object.assign(options, {
            callback: callback,
            history: history_id,
        });
        if (options.new) {
            const { openGlobalUploadModal } = useGlobalUploadModal();
            openGlobalUploadModal(options);
        } else {
            mountSelectionDialog(DataDialog, options);
        }
    });
}

/**
 * Creates a history dataset by submitting an upload request
 * TODO: This should live somewhere else.
 */
export function create(galaxy, options) {
    async function getHistory() {
        if (!options.history_id) {
            return getCurrentGalaxyHistory();
        }
        return options.history_id;
    }
    getHistory().then((history_id) => {
        uploadSubmit({
            success: (response) => {
                startWatchingHistory(galaxy);
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
