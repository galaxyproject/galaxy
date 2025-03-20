import { computed, readonly, type Ref, ref } from "vue";

import { errorMessageAsString } from "@/utils/simple-error";

const DEFAULT_POLL_DELAY = 10000;

/**
 * Represents a task monitor that can be used to wait for a background task to complete or
 * check its status.
 */
export interface TaskMonitor {
    /**
     * Waits for a particular task ID to be completed.
     * While the task is pending, the state will be updated every `pollDelayInMs` by polling the server.
     * @param taskId The task ID
     * @param pollDelayInMs The time (milliseconds) between poll requests to update the task state.
     */
    waitForTask: (taskId: string, pollDelayInMs?: number) => Promise<void>;

    /**
     * Whether the task is currently running.
     */
    isRunning: Readonly<Ref<boolean>>;

    /**
     * Whether the task has been completed successfully.
     */
    isCompleted: Readonly<Ref<boolean>>;

    /**
     * Indicates the task has failed and will not yield results.
     */
    hasFailed: Readonly<Ref<boolean>>;

    /**
     * If true, the status of the task cannot be determined because of a request error.
     */
    requestHasFailed: Readonly<Ref<boolean>>;

    /**
     * The current status of the task.
     * The meaning of the status string is up to the monitor implementation.
     * In case of an error, this will be the error message.
     */
    taskStatus: Readonly<Ref<string | undefined>>;

    /**
     * Loads the status of the task from a stored value.
     * @param storedStatus The status string to load.
     */
    loadStatus: (storedStatus: string) => void;

    /**
     * Determines if the status represents a final state.
     * @param status The status string to check.
     * @returns True if the status is a final state and is not expected to change.
     */
    isFinalState: (status?: string) => boolean;

    /**
     * If defined, the time (in milliseconds) after which the task should be considered expired.
     * Requests to check the task status after this time should be avoided. As they are not guaranteed to return the correct status.
     */
    expirationTime?: number;
}

/**
 * Composable for waiting (polling) on generic background tasks or processes.
 */
export function useGenericMonitor(options: {
    /** Function to fetch the status of a task or process.
     * The function should return a string representing the current status of the task.
     * The meaning of the status string is determined by the `completedCondition` and `failedCondition` functions.
     */
    fetchStatus: (taskId: string) => Promise<string>;

    /** Function to determine if the task has finished. */
    completedCondition: (status?: string) => boolean;

    /** Function to determine if the task has failed. */
    failedCondition: (status?: string) => boolean;

    /** Default delay between polling requests in milliseconds.
     * By default, this is set to 10 seconds.
     * The delay can be overridden when calling `waitForTask`.
     */
    defaultPollDelay?: number;

    /** Optional expiration time for the task in milliseconds.
     * After this time, the task should be considered expired.
     * Requests to check the task status after this time should be avoided.
     */
    expirationTime?: number;
}): TaskMonitor {
    let timeout: NodeJS.Timeout | null = null;
    let pollDelay = options.defaultPollDelay ?? DEFAULT_POLL_DELAY;

    const isRunning = ref(false);
    const taskStatus = ref<string>();
    const requestId = ref<string>();
    const requestHasFailed = ref(false);

    const isCompleted = computed(() => options.completedCondition(taskStatus.value));
    const hasFailed = computed(() => options.failedCondition(taskStatus.value));

    function isFinalState(status?: string) {
        return options.completedCondition(status) || options.failedCondition(status);
    }

    function loadStatus(storedStatus: string) {
        taskStatus.value = storedStatus;
    }

    async function waitForTask(taskId: string, pollDelayInMs?: number) {
        pollDelay = pollDelayInMs ?? pollDelay;
        resetState();
        requestId.value = taskId;
        isRunning.value = true;
        return fetchTaskStatus(taskId);
    }

    async function fetchTaskStatus(taskId: string) {
        try {
            const result = await options.fetchStatus(taskId);
            taskStatus.value = result;
            if (isCompleted.value || hasFailed.value) {
                isRunning.value = false;
            } else {
                pollAfterDelay(taskId);
            }
        } catch (err) {
            handleError(errorMessageAsString(err));
        }
    }

    function pollAfterDelay(id: string) {
        resetTimeout();
        timeout = setTimeout(() => {
            fetchTaskStatus(id);
        }, pollDelay);
    }

    function handleError(err: string) {
        taskStatus.value = err.toString();
        requestHasFailed.value = true;
        isRunning.value = false;
        resetTimeout();
    }

    function resetTimeout() {
        if (timeout) {
            clearTimeout(timeout);
            timeout = null;
        }
    }

    function resetState() {
        resetTimeout();
        taskStatus.value = undefined;
        requestHasFailed.value = false;
        isRunning.value = false;
    }

    return {
        waitForTask,
        isFinalState,
        loadStatus,
        isRunning: readonly(isRunning),
        isCompleted: readonly(isCompleted),
        hasFailed: readonly(hasFailed),
        requestHasFailed: readonly(requestHasFailed),
        taskStatus: readonly(taskStatus),
        expirationTime: options.expirationTime,
    };
}
