import { ref, readonly } from "vue";
import axios from "axios";
import { safePath } from "utils/redirect";
import { rethrowSimple } from "utils/simple-error";

const DEFAULT_POLL_DELAY = 1000;
const EXPORT_PARAMS = {
    model_store_format: "rocrate.zip",
    include_files: false,
    include_deleted: false,
    include_hidden: false,
};
const DEFAULT_OPTIONS = { exportParams: EXPORT_PARAMS, pollDelayInMs: DEFAULT_POLL_DELAY };

/**
 * Composable to simplify and reuse the logic for downloading objects using Galaxy's Short Term Storage system.
 */
export function useShortTermStorage() {
    let timeout = null;
    let pollDelay = DEFAULT_POLL_DELAY;

    const isPreparing = ref(false);

    function downloadHistory(historyId, options = DEFAULT_OPTIONS) {
        return prepareObjectDownload(historyId, "histories", options);
    }

    function downloadWorkflowInvocation(invocationId, options = DEFAULT_OPTIONS) {
        return prepareObjectDownload(invocationId, "invocations", options);
    }

    function downloadObjectByRequestId(storageRequestId) {
        const url = safePath(`/api/short_term_storage/${storageRequestId}`);
        window.location.assign(url);
    }

    function prepareObjectDownload(object_id, object_api, options = DEFAULT_OPTIONS) {
        const finalOptions = Object.assign(DEFAULT_OPTIONS, options);
        resetTimeout();
        isPreparing.value = true;
        pollDelay = finalOptions.pollDelayInMs;
        const url = safePath(`/api/${object_api}/${object_id}/prepare_store_download`);
        axios.post(url, finalOptions.exportParams).then(handleInitialize).catch(handleError);
    }

    function handleInitialize(response) {
        const storageRequestId = response.data.storage_request_id;
        pollStorageRequestId(storageRequestId);
    }

    function pollStorageRequestId(storageRequestId) {
        const url = safePath(`/api/short_term_storage/${storageRequestId}/ready`);
        axios
            .get(url)
            .then((r) => {
                handlePollResponse(r, storageRequestId);
            })
            .catch(handleError);
    }

    function handlePollResponse(response, storageRequestId) {
        const ready = response.data;
        if (ready) {
            isPreparing.value = false;
            downloadObjectByRequestId(storageRequestId);
        } else {
            pollAfterDelay(storageRequestId);
        }
    }

    function handleError(err) {
        rethrowSimple(err);
        isPreparing.value = false;
    }

    function pollAfterDelay(storageRequestId) {
        resetTimeout();
        timeout = setTimeout(() => {
            pollStorageRequestId(storageRequestId);
        }, pollDelay);
    }

    function resetTimeout() {
        if (timeout) {
            clearTimeout(timeout);
            timeout = null;
        }
    }

    return {
        /**
         * Starts preparing a history download file. When `isPreparing` is false the download will start automatically.
         * @param {String} historyId The ID of the history to be downloaded
         * @param {Object} options Options for the download preparation
         */
        downloadHistory,
        /**
         * Starts preparing a workflow invocation download file. When `isPreparing` is false the download will start automatically.
         * @param {String} invocationId The ID of the workflow invocation to be downloaded
         * @param {Object} options Options for the download preparation
         */
        downloadWorkflowInvocation,
        /**
         * Starts a direct download of the object associated with the given `storageRequestId`.
         * For the download to succeed, the associated `storageRequestId` must be `ready` and not in failure state.
         * @param {String} storageRequestId The storage request ID associated to the object to be downloaded
         */
        downloadObjectByRequestId,
        /**
         * Whether the download is still being prepared.
         */
        isPreparing: readonly(isPreparing),
    };
}
