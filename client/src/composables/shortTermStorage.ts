import { readonly, ref, watch } from "vue";

import { fetcher } from "@/api/schema";
import { type ExportParams, type StoreExportPayload } from "@/components/Common/models/exportRecordModel";
import { withPrefix } from "@/utils/redirect";

import { useShortTermStorageMonitor } from "./shortTermStorageMonitor";

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

const DEFAULT_POLL_DELAY = 3000;
const DEFAULT_OPTIONS: Options = { exportParams: DEFAULT_EXPORT_PARAMS, pollDelayInMs: DEFAULT_POLL_DELAY };

const startPreparingHistoryDownload = fetcher
    .path("/api/histories/{history_id}/prepare_store_download")
    .method("post")
    .create();
const startPreparingInvocationDownload = fetcher
    .path("/api/invocations/{invocation_id}/prepare_store_download")
    .method("post")
    .create();

/**
 * Composable to simplify and reuse the logic for downloading objects using Galaxy's Short Term Storage system.
 */
export function useShortTermStorage() {
    const { waitForTask, isRunning } = useShortTermStorageMonitor();

    const isPreparing = ref(false);

    watch(isRunning, (running) => {
        if (!running) {
            isPreparing.value = false;
        }
    });

    const forHistory: StartPreparingDownloadCallback = async (id: string, params: StoreExportPayload) => {
        const { data } = await startPreparingHistoryDownload({ history_id: id, ...params });
        return data;
    };

    const forInvocation: StartPreparingDownloadCallback = async (id: string, params: StoreExportPayload) => {
        const { data } = await startPreparingInvocationDownload({ invocation_id: id, ...params });
        return data;
    };

    async function prepareHistoryDownload(historyId: string, options = DEFAULT_OPTIONS) {
        return prepareObjectDownload(forHistory, historyId, options);
    }

    async function prepareWorkflowInvocationDownload(invocationId: string, options = DEFAULT_OPTIONS) {
        return prepareObjectDownload(forInvocation, invocationId, options);
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
        options = DEFAULT_OPTIONS
    ) {
        isPreparing.value = true;
        const finalOptions = Object.assign(DEFAULT_OPTIONS, options);
        const exportParams: StoreExportPayload = {
            model_store_format: finalOptions.exportParams.modelStoreFormat,
            include_files: finalOptions.exportParams.includeFiles,
            include_deleted: finalOptions.exportParams.includeDeleted,
            include_hidden: finalOptions.exportParams.includeHidden,
        };

        try {
            const response = await startPreparingDownloadAsync(objectId, exportParams);
            const storageRequestId = response.storage_request_id;
            waitForTask(storageRequestId, finalOptions.pollDelayInMs);
        } catch (err) {
            isPreparing.value = false;
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
         * Starts preparing a workflow invocation download file in the short term storage.
         * @param {String} invocationId The ID of the workflow invocation to be prepared for download
         * @param {Object} options Options for the download preparation
         */
        prepareWorkflowInvocationDownload,
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
