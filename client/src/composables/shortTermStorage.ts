import { readonly, ref } from "vue";

import { fetcher } from "@/api/schema";
import { ExportParams, StoreExportPayload } from "@/components/Common/models/exportRecordModel";
import { withPrefix } from "@/utils/redirect";

export const DEFAULT_EXPORT_PARAMS: ExportParams = {
    modelStoreFormat: "rocrate.zip",
    includeFiles: true,
    includeDeleted: false,
    includeHidden: false,
};

interface Options {
    exportParams: ExportParams;
    pollDelayInMs: number;
}

interface StorageRequestResponse {
    storage_request_id: string;
}

type StartPreparingDownloadCallback = (objectId: string, params: StoreExportPayload) => Promise<StorageRequestResponse>;

const DEFAULT_POLL_DELAY = 1000;
const DEFAULT_OPTIONS: Options = { exportParams: DEFAULT_EXPORT_PARAMS, pollDelayInMs: DEFAULT_POLL_DELAY };

const startPreparingHistoryDownload = fetcher
    .path("/api/histories/{history_id}/prepare_store_download")
    .method("post")
    .create();
const startPreparingInvocationDownload = fetcher
    .path("/api/invocations/{invocation_id}/prepare_store_download")
    .method("post")
    .create();
const getTempStorageRequestReady = fetcher
    .path("/api/short_term_storage/{storage_request_id}/ready")
    .method("get")
    .create();

/**
 * Composable to simplify and reuse the logic for downloading objects using Galaxy's Short Term Storage system.
 */
export function useShortTermStorage() {
    let timeout: NodeJS.Timeout | null = null;
    let pollDelay = DEFAULT_POLL_DELAY;

    const isPreparing = ref(false);

    const forHistory: StartPreparingDownloadCallback = async (id: string, params: StoreExportPayload) => {
        const { data } = await startPreparingHistoryDownload({ history_id: id, ...params });
        return data;
    };

    const forInvocation: StartPreparingDownloadCallback = async (id: string, params: StoreExportPayload) => {
        const { data } = await startPreparingInvocationDownload({ invocation_id: id, ...params });
        return data;
    };

    async function prepareHistoryDownload(historyId: string, options = DEFAULT_OPTIONS) {
        return prepareObjectDownload(forHistory, historyId, options, false);
    }
    async function downloadHistory(historyId: string, options = DEFAULT_OPTIONS) {
        return prepareObjectDownload(forHistory, historyId, options, true);
    }

    async function prepareWorkflowInvocationDownload(invocationId: string, options = DEFAULT_OPTIONS) {
        return prepareObjectDownload(forInvocation, invocationId, options, false);
    }

    async function downloadWorkflowInvocation(invocationId: string, options = DEFAULT_OPTIONS) {
        return prepareObjectDownload(forInvocation, invocationId, options, true);
    }

    function getDownloadObjectUrl(storageRequestId: string) {
        const url = withPrefix(`/api/short_term_storage/${storageRequestId}`);
        return url;
    }

    function downloadObjectByRequestId(storageRequestId: string) {
        const url = getDownloadObjectUrl(storageRequestId);
        window.location.assign(url);
    }

    async function prepareObjectDownload(
        startPreparingDownloadAsync: StartPreparingDownloadCallback,
        objectId: string,
        options = DEFAULT_OPTIONS,
        downloadWhenReady = true
    ) {
        resetTimeout();
        isPreparing.value = true;
        const finalOptions = Object.assign(DEFAULT_OPTIONS, options);
        pollDelay = finalOptions.pollDelayInMs;
        const exportParams: StoreExportPayload = {
            model_store_format: finalOptions.exportParams.modelStoreFormat,
            include_files: finalOptions.exportParams.includeFiles,
            include_deleted: finalOptions.exportParams.includeDeleted,
            include_hidden: finalOptions.exportParams.includeHidden,
        };

        try {
            const response = await startPreparingDownloadAsync(objectId, exportParams);
            const storageRequestId = response.storage_request_id;
            pollStorageRequestId(storageRequestId, downloadWhenReady);
        } catch (err) {
            stopPreparing();
        }
    }

    async function pollStorageRequestId(storageRequestId: string, downloadWhenReady: boolean) {
        try {
            const { data: ready } = await getTempStorageRequestReady({ storage_request_id: storageRequestId });
            if (ready) {
                isPreparing.value = false;
                if (downloadWhenReady) {
                    downloadObjectByRequestId(storageRequestId);
                }
            } else {
                pollAfterDelay(storageRequestId, downloadWhenReady);
            }
        } catch (err) {
            stopPreparing();
        }
    }

    function stopPreparing() {
        isPreparing.value = false;
    }

    function pollAfterDelay(storageRequestId: string, downloadWhenReady: boolean) {
        resetTimeout();
        timeout = setTimeout(() => {
            pollStorageRequestId(storageRequestId, downloadWhenReady);
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
         * Starts preparing a history download file in the short term storage.
         * @param {String} historyId The ID of the history to be prepared for download
         * @param {Object} options Options for the download preparation
         */
        prepareHistoryDownload,
        /**
         * Prepares a history download file in the short term storage and starts the download when ready.
         * @param {String} historyId The ID of the history to be downloaded
         * @param {Object} options Options for the download preparation
         */
        downloadHistory,
        /**
         * Starts preparing a workflow invocation download file in the short term storage.
         * @param {String} invocationId The ID of the workflow invocation to be prepared for download
         * @param {Object} options Options for the download preparation
         */
        prepareWorkflowInvocationDownload,
        /**
         * Starts preparing a workflow invocation download file in the short term storage and starts the download when ready.
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
        /**
         * Given a storageRequestId it returns the download URL for that object.
         * @param {String} storageRequestId The storage request ID associated to the object to be downloaded
         */
        getDownloadObjectUrl,
    };
}
