import { computed, ref, readonly } from "vue";
import axios from "axios";

const SUCCESS_STATE = "SUCCESS";
const FAILURE_STATE = "FAILURE";
const TASK_READY_STATES = [SUCCESS_STATE, FAILURE_STATE];
const POLL_DELAY = 1000;

/**
 * Composable for waiting on Galaxy background tasks.
 */
export function useTaskMonitor() {
    let timeout = null;

    const isRunning = ref(false);
    const status = ref(null);
    const currentTaskId = ref(null);
    const requestHasFailed = ref(false);

    const isCompleted = computed(() => status.value === SUCCESS_STATE);
    const hasFailed = computed(() => status.value === FAILURE_STATE);
    const queryStateUrl = computed(() => `/api/tasks/${currentTaskId.value}/state`);

    /**
     * Waits for a particular task ID to be completed.
     * @param {string} taskId The task ID
     */
    function waitForTask(taskId) {
        resetState();
        currentTaskId.value = taskId;
        isRunning.value = true;
        fetchTaskStatus();
    }

    function fetchTaskStatus() {
        axios.get(queryStateUrl.value).then(handleStatusResponse).catch(handleError);
    }

    function handleStatusResponse(response) {
        status.value = response.data;
        const isReady = TASK_READY_STATES.includes(status.value);
        if (isReady) {
            isRunning.value = false;
        } else {
            pollAfterDelay();
        }
    }

    function pollAfterDelay(taskId) {
        resetTimeout();
        timeout = setTimeout(() => {
            fetchTaskStatus(taskId);
        }, POLL_DELAY);
    }

    function handleError(err) {
        status.value = err;
        requestHasFailed.value = true;
        isRunning.value = false;
    }

    function resetTimeout() {
        if (timeout) {
            clearTimeout(timeout);
        }
    }

    function resetState() {
        resetTimeout();
        status.value = null;
    }

    return {
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
        waitForTask,
    };
}
