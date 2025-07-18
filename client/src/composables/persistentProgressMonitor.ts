import { StorageSerializers, useLocalStorage } from "@vueuse/core";
import { computed, readonly, type Ref, watch } from "vue";

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
     * The type of the object being processed.
     * For example, "history", "invocation", etc.
     */
    type: "history" | "invocation" | "collection";

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

    /**
     * Indicates whether the task is in a final state.
     * A final state means that the task has either completed successfully, has failed or has expired.
     * This is used to determine if the task can be monitored further or not.
     */
    isFinal: boolean;
}

interface CheckStatusOptions {
    /**
     * If true, the status of the task will be fetched from the server unless the task is already in a final state.
     * If false, the status will be loaded from the stored data.
     * Defaults to true.
     */
    enableFetch?: boolean;
}

/**
 * The return type of usePersistentProgressTaskMonitor composable.
 */
export interface PersistentProgressTaskMonitorResult {
    /** Start monitoring the background process. */
    start: (monitoringData?: MonitoringData) => Promise<void>;
    /** Stops monitoring the background process. */
    stop: () => void;
    /** Clears the monitoring data in the local storage. */
    reset: () => void;
    /**
     * Fetches the current status of the task from the server and updates the internal state.
     * If the task is already in a final state, no request will be made and the stored status will be used instead.
     */
    checkStatus: (options?: CheckStatusOptions) => Promise<void>;
    /** The task is still running. */
    isRunning: Ref<boolean>;
    /** The task has been completed successfully. */
    isCompleted: Ref<boolean>;
    /** Indicates the task has failed and will not yield results. */
    hasFailed: Ref<boolean>;
    /** The reason why the task has failed. */
    failureReason: Ref<string | undefined>;
    /** If true, the status of the task cannot be determined because of a request error. */
    requestHasFailed: Ref<boolean>;
    /** Indicates that there is monitoring data stored. */
    hasMonitoringData: Ref<boolean>;
    /** The task ID stored in the monitoring data or undefined if no monitoring data is available. */
    storedTaskId: string | undefined;
    /** The current status of the task. */
    status: Ref<string | undefined>;
    /** True if the monitoring data can expire. */
    canExpire: Ref<boolean>;
    /** True if the monitoring data has expired. */
    hasExpired: Ref<boolean>;
    /** The expiration date for the monitoring data. */
    expirationDate: Ref<Date | undefined>;
    /** The monitoring data stored in the local storage. */
    monitoringData: Readonly<Ref<MonitoringData | null>>;
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
): PersistentProgressTaskMonitorResult {
    const {
        waitForTask,
        stopWaitingForTask,
        isFinalState,
        loadStatus,
        fetchTaskStatus,
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

        const isFinal = isFinalState(currentMonitoringData.value.taskStatus) || hasExpired.value;
        currentMonitoringData.value.isFinal = isFinal;

        if (isFinal) {
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

    function stop() {
        stopWaitingForTask();
    }

    async function checkStatus(options: CheckStatusOptions = { enableFetch: true }) {
        if (!currentMonitoringData.value) {
            throw new Error("No monitoring data stored available to check status.");
        }

        const isFinal = isFinalState(currentMonitoringData.value.taskStatus) || hasExpired.value;
        currentMonitoringData.value.isFinal = isFinal;

        if (isFinal || !options.enableFetch) {
            return loadStatus(currentMonitoringData.value);
        }

        try {
            await fetchTaskStatus(currentMonitoringData.value.taskId, { keepPolling: false });
        } catch (error) {
            console.error("Failed to fetch task status:", error);
        }
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
         * Stops monitoring the background process.
         * This will stop polling requests.
         */
        stop,

        /**
         * Clears the monitoring data in the local storage.
         */
        reset,

        /**
         * Fetches the current status of the task from the server and updates the internal state.
         * If the task is already in a final state, no request will be made and the stored status will be used instead.
         * @param options Optional parameters to control the fetch behavior.
         */
        checkStatus,

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
    return getStoredProgressDataByKey(localStorageKey);
}

/**
 * Retrieves task progress data from the local storage by the provided key.
 * @param key The key to retrieve the stored progress data.
 * @returns The associated task progress data or null if there is no stored data.
 */
export function getStoredProgressDataByKey(key: string): MonitoringData | null {
    const currentMonitoringData = useLocalStorage<MonitoringData | null>(key, null, {
        serializer: StorageSerializers.object,
    });
    return currentMonitoringData.value;
}

/**
 * Stores the provided monitoring data in the local storage under a persistent key
 * derived from the monitoring request information.
 * @param monitoringData The monitoring data to store.
 */
export function storeProgressData(monitoringData: MonitoringData) {
    const localStorageKey = getPersistentKey(monitoringData.request);
    const currentMonitoringData = useLocalStorage<MonitoringData | null>(localStorageKey, null, {
        serializer: StorageSerializers.object,
    });
    currentMonitoringData.value = monitoringData;
}

/**
 * Builds a persistent key for the monitoring request.
 * @param request The monitoring request information.
 * @returns A string key that uniquely identifies the monitoring request.
 */
export function getPersistentKey(request: MonitoringRequest) {
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
