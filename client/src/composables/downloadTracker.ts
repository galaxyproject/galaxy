import type { Ref } from "vue";
import { computed, readonly } from "vue";

import type { MonitoringData, MonitoringRequest } from "./persistentProgressMonitor";
import { getPersistentKey, getStoredProgressDataByKey, storeProgressData } from "./persistentProgressMonitor";
import { useUserLocalStorage } from "./userLocalStorage";

/**
 * This composable stores in local storage the progress of downloads/exports initiated by the user.
 * It allows tracking the export/download progress across page navigations and refreshes for short-term storage requests.
 *
 * @returns An object with methods to track download requests, untrack them, and retrieve all download monitoring data.
 */
export function useDownloadTracker() {
    const downloadProgressKeys: Ref<string[]> = useUserLocalStorage("download-tracker", []);

    const downloadMonitoringData = computed<MonitoringData[]>(() => {
        return downloadProgressKeys.value
            .map((key) => getStoredProgressDataByKey(key))
            .filter((data) => data !== null)
            .sort((a, b) => {
                // Sort by most recent first
                return new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime();
            });
    });

    function trackDownloadRequest(request: MonitoringRequest) {
        if (request.taskType !== "short_term_storage") {
            console.warn("Download tracking is only supported for short-term storage requests.");
            return;
        }
        const persistedProgressKey = getPersistentKey(request);
        trackKey(persistedProgressKey);
    }

    function trackDownloadRequestWithData(monitoringData: MonitoringData) {
        if (monitoringData.taskType !== "short_term_storage") {
            console.warn("Download tracking is only supported for short-term storage requests.");
            return;
        }
        storeProgressData(monitoringData);
        const persistedProgressKey = getPersistentKey(monitoringData.request);
        trackKey(persistedProgressKey);
    }

    function trackKey(key: string) {
        if (!downloadProgressKeys.value.includes(key)) {
            downloadProgressKeys.value.push(key);
        }
        downloadProgressKeys.value = [...new Set(downloadProgressKeys.value)];
    }

    function untrackDownloadRequest(request: MonitoringRequest) {
        const persistedProgressKey = getPersistentKey(request);
        const index = downloadProgressKeys.value.indexOf(persistedProgressKey);
        if (index !== -1) {
            downloadProgressKeys.value.splice(index, 1);
        }
    }

    return {
        trackDownloadRequest,
        trackDownloadRequestWithData,
        untrackDownloadRequest,
        downloadMonitoringData: readonly(downloadMonitoringData),
    };
}
