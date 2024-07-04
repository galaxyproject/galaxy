import { computed, readonly, ref } from "vue";

import { errorMessageAsString } from "@/utils/simple-error";

const DEFAULT_POLL_DELAY = 10000;

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
}) {
    let timeout: NodeJS.Timeout | null = null;
    let pollDelay = options.defaultPollDelay ?? DEFAULT_POLL_DELAY;

    const isRunning = ref(false);
    const status = ref<string>();
    const requestId = ref<string>();
    const requestHasFailed = ref(false);

    const isCompleted = computed(() => options.completedCondition(status.value));
    const hasFailed = computed(() => options.failedCondition(status.value));

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
            status.value = result;
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
        status.value = err.toString();
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
        status.value = undefined;
        requestHasFailed.value = false;
        isRunning.value = false;
    }

    return {
        /**
         * Waits for a particular task ID to be completed.
         * While the task is pending, the state will be updated every `pollDelayInMs` by polling the server.
         * @param taskId The task ID
         * @param pollDelayInMs The time (milliseconds) between poll requests to update the task state.
         */
        waitForTask,
        /**
         * Whether the task is currently running.
         */
        isRunning: readonly(isRunning),
        /**
         * Whether the task has been completed successfully.
         */
        isCompleted: readonly(isCompleted),
        /**
         * Indicates the task has failed and will not yield results.
         */
        hasFailed: readonly(hasFailed),
        /**
         * If true, the status of the task cannot be determined because of a request error.
         */
        requestHasFailed: readonly(requestHasFailed),
        /**
         * The current status of the task.
         */
        status: readonly(status),
    };
}
