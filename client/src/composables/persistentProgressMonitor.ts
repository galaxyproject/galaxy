import { StorageSerializers, useLocalStorage } from "@vueuse/core";
import { computed, readonly, watch } from "vue";

import type { StoredTaskStatus, TaskMonitor } from "./genericTaskMonitor";

type TaskType = "task" | "short_term_storage";

/**
 * Represents an object that is being processed in the background.
 * Used to provide more context to the user when displaying the progress.
 */
interface ProcessedObject {
    /** The ID of the object. */
    id: string;

    /**
     * The type of the object.
     * For example, "history", "dataset", "workflow", "invocation", etc.
     */
    type: string;

    /**
     * The name of the object.
     * If the name is not provided, the ID will be used instead.
     */
    name?: string;
}

/**
 * Provides information about a long-running asynchronous process that persists across page navigation or refresh.
 * This information can be used to display progress to the user.
 */
export interface MonitoringRequest {
    /**
     * The component that initiated the task.
     * This can be used to provide more context to the user when displaying the progress.
     */
    source: string;

    /**
     * The action of the task.
     * This can be used to provide more context to the user when displaying the progress.
     * For example, "import", "export", "delete", etc.
     */
    action: string;

    /**
     * The type of the task to monitor.
     * This can be either a task or a short-term storage request.
     */
    taskType: TaskType;

    /**
     * The object being processed by the task.
     * This can be used to provide more context to the user when displaying the progress.
     */
    object: ProcessedObject;

    /**
     * A human-readable description of the task.
     * This is optional and can be used to provide more context to the user
     * when displaying the progress.
     */
    description?: string;

    /**
     * The remote URI associated with the task.
     *
     * This is optional and indicates the task is associated with a remote resource.
     */
    remoteUri?: string;
}

export interface MonitoringData extends StoredTaskStatus {
    /**
     * The ID of the task or short-term storage request to monitor.
     */
    taskId: string;

    /**
     * The type of the task to monitor.
     * This can be either a task or a short-term storage request.
     */
    taskType: TaskType;

    /**
     * The information about the task.
     */
    request: MonitoringRequest;

    /**
     * The time when the task was started.
     */
    startedAt: Date;
}

/**
 * This composable is used to store the information about a long-running asynchronous process
 * that persists across page navigation or refresh.
 *
 * It supports both task and short-term storage monitoring. The actual monitoring is done by the provided `useMonitor` composable.
 */
export function usePersistentProgressTaskMonitor(
    request: MonitoringRequest,
    useMonitor: TaskMonitor,
    monitoringData: MonitoringData | null = null
) {
    const {
        waitForTask,
        isFinalState,
        loadStatus,
        isRunning,
        isCompleted,
        hasFailed,
        failureReason,
        requestHasFailed,
        taskStatus,
        expirationTime,
    } = useMonitor;

    const localStorageKey = getPersistentKey(request);

    const currentMonitoringData = useLocalStorage<MonitoringData | null>(localStorageKey, monitoringData, {
        serializer: StorageSerializers.object,
    });

    const hasMonitoringData = computed(() => {
        return Boolean(currentMonitoringData.value);
    });

    const canExpire = computed(() => {
        return Boolean(expirationTime);
    });

    const hasExpired = computed(() => {
        return isDataExpired(currentMonitoringData.value, expirationTime);
    });

    const expirationDate = computed(() => {
        if (!currentMonitoringData.value || !expirationTime) {
            return undefined;
        }

        const startedAt = new Date(currentMonitoringData.value.startedAt);
        return new Date(startedAt.getTime() + expirationTime);
    });

    watch(
        () => taskStatus.value,
        (newStatus) => {
            if (newStatus && currentMonitoringData.value) {
                currentMonitoringData.value = {
                    ...currentMonitoringData.value,
                    taskStatus: newStatus,
                };
            }
        },
        { immediate: true }
    );

    watch(
        () => failureReason.value,
        (newReason) => {
            if (newReason && currentMonitoringData.value) {
                currentMonitoringData.value = {
                    ...currentMonitoringData.value,
                    failureReason: newReason,
                };
            }
        },
        { immediate: true }
    );

    async function start(monitoringData?: MonitoringData) {
        if (monitoringData) {
            currentMonitoringData.value = monitoringData;
        }

        if (!currentMonitoringData.value) {
            throw new Error("No monitoring data provided or stored. Cannot start monitoring progress.");
        }

        if (isFinalState(currentMonitoringData.value.taskStatus)) {
            // The task has already finished no need to start monitoring again.
            // Instead, reload the stored status to update the UI.
            return loadStatus(currentMonitoringData.value);
        }

        if (hasExpired.value) {
            // The monitoring data has expired. Requesting the status again will likely
            // return incorrect results. Reset the monitoring data to start fresh.
            return;
        }

        return waitForTask(currentMonitoringData.value.taskId);
    }

    function reset() {
        currentMonitoringData.value = null;
    }

    return {
        /**
         * Start monitoring the background process.
         * If no monitoring data is provided, it will use the stored one.
         * @param monitoringData Optional monitoring data to override the stored one.
         */
        start,

        /**
         * Clears the monitoring data in the local storage.
         */
        reset,

        /**
         * The task is still running.
         */
        isRunning,

        /**
         * The task has been completed successfully.
         */
        isCompleted,

        /**
         * Indicates the task has failed and will not yield results.
         */
        hasFailed,

        /**
         * The reason why the task has failed.
         */
        failureReason,

        /**
         * If true, the status of the task cannot be determined because of a request error.
         */
        requestHasFailed,

        /**
         * Indicates that there is monitoring data stored.
         */
        hasMonitoringData,

        /**
         * The task ID stored in the monitoring data or undefined if no monitoring data is available.
         */
        storedTaskId: currentMonitoringData.value?.taskId,

        /**
         * The current status of the task.
         * The meaning of the status string is up to the monitor implementation.
         */
        status: taskStatus,

        /**
         * True if the monitoring data can expire.
         */
        canExpire,

        /**
         * True if the monitoring data has expired.
         * The monitoring data expires after the expiration time has passed since the task was started.
         */
        hasExpired,

        /**
         * The expiration date for the monitoring data.
         * After this date, the monitoring data is considered expired and should not be used.
         */
        expirationDate,

        /**
         * The monitoring data stored in the local storage.
         */
        monitoringData: readonly(currentMonitoringData),
    };
}

/**
 * Retrieves task progress data from the local storage associated with the
 * monitoring request information provided if it exists.
 * @param request The monitoring request information.
 * @returns The associated task progress data or null if there is no stored data.
 */
export function getStoredProgressData(request: MonitoringRequest): MonitoringData | null {
    const localStorageKey = getPersistentKey(request);
    const currentMonitoringData = useLocalStorage<MonitoringData | null>(localStorageKey, null, {
        serializer: StorageSerializers.object,
    });

    return currentMonitoringData.value;
}

function getPersistentKey(request: MonitoringRequest) {
    return `persistent-progress-${request.taskType}-${request.source}-${request.action}-${request.object.type}-${request.object.id}`;
}

/**
 * Checks if the monitoring data has expired.
 * @param monitoringData The monitoring data to check for expiration.
 * @param expirationTime The expiration time in milliseconds.
 * @returns True if the monitoring data has expired, false otherwise.
 */
export function isDataExpired(monitoringData: MonitoringData | null, expirationTime?: number): boolean {
    if (!monitoringData || !expirationTime) {
        return false;
    }

    const now = new Date();
    const startedAt = new Date(monitoringData.startedAt);
    const elapsedTimeInMs = now.getTime() - startedAt.getTime();
    return elapsedTimeInMs > expirationTime;
}
