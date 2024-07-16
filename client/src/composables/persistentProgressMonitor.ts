import { StorageSerializers, useLocalStorage } from "@vueuse/core";
import { computed, watch } from "vue";

import type { TaskMonitor } from "./genericTaskMonitor";

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
}

export interface MonitoringData {
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
     * The status of the task when it was last checked.
     * The meaning of the status string is up to the monitor implementation.
     * In case of an error, this will be the error message.
     */
    status?: string;
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
    const localStorageKey = getPersistentKey(request);

    const currentMonitoringData = useLocalStorage<MonitoringData | null>(localStorageKey, monitoringData, {
        serializer: StorageSerializers.object,
    });

    const hasMonitoringData = computed(() => {
        return Boolean(currentMonitoringData.value);
    });

    const { waitForTask, isRunning, isCompleted, hasFailed, requestHasFailed, status } = useMonitor;

    watch(
        status,
        (newStatus) => {
            if (currentMonitoringData.value) {
                currentMonitoringData.value = {
                    ...currentMonitoringData.value,
                    status: newStatus,
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

        return waitForTask(currentMonitoringData.value.taskId);
    }

    function reset() {
        currentMonitoringData.value = null;
    }

    function getPersistentKey(request: MonitoringRequest) {
        return `persistent-progress-${request.taskType}-${request.source}-${request.action}-${request.object.type}-${request.object.id}`;
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
        isRunning,
        isCompleted,
        hasFailed,
        requestHasFailed,
        hasMonitoringData,
        storedTaskId: currentMonitoringData.value?.taskId,
        status,
    };
}
