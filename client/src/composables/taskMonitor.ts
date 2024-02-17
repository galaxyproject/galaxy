import { computed, readonly, ref } from "vue";

import { fetcher } from "@/api/schema";
import { errorMessageAsString } from "@/utils/simple-error";

const SUCCESS_STATE = "SUCCESS";
const FAILURE_STATE = "FAILURE";
const TASK_READY_STATES = [SUCCESS_STATE, FAILURE_STATE];
const DEFAULT_POLL_DELAY = 10000;

const getTaskStatus = fetcher.path("/api/tasks/{task_id}/state").method("get").create();

/**
 * Composable for waiting on Galaxy background tasks.
 */
export function useTaskMonitor() {
    let timeout: NodeJS.Timeout | null = null;
    let pollDelay = DEFAULT_POLL_DELAY;

    const isRunning = ref(false);
    const status = ref<string>();
    const currentTaskId = ref<string>();
    const requestHasFailed = ref(false);

    const isCompleted = computed(() => status.value === SUCCESS_STATE);
    const hasFailed = computed(() => status.value === FAILURE_STATE);

    async function waitForTask(taskId: string, pollDelayInMs = DEFAULT_POLL_DELAY) {
        pollDelay = pollDelayInMs;
        resetState();
        currentTaskId.value = taskId;
        isRunning.value = true;
        return fetchTaskStatus(taskId);
    }

    async function fetchTaskStatus(taskId: string) {
        try {
            const { data } = await getTaskStatus({ task_id: taskId });
            status.value = data;
            const isReady = TASK_READY_STATES.includes(status.value);
            if (isReady) {
                isRunning.value = false;
            } else {
                pollAfterDelay(taskId);
            }
        } catch (err) {
            handleError(errorMessageAsString(err));
        }
    }

    function pollAfterDelay(taskId: string) {
        resetTimeout();
        timeout = setTimeout(() => {
            fetchTaskStatus(taskId);
        }, pollDelay);
    }

    function handleError(err: string) {
        status.value = err;
        requestHasFailed.value = true;
        isRunning.value = false;
        resetTimeout();
    }

    function resetTimeout() {
        if (timeout) {
            clearTimeout(timeout);
        }
    }

    function resetState() {
        resetTimeout();
        status.value = undefined;
    }

    return {
        /**
         * Waits for a particular task ID to be completed.
         * While the task is pending, the state will be updated every `pollDelayInMs` by polling the server.
         * @param {string} taskId The task ID
         * @param {Number} pollDelayInMs The time (milliseconds) between poll requests to update the task state.
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
    };
}
