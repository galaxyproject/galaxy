import { computed, readonly, ref } from "vue";

import { fetcher } from "@/api/schema";
import { errorMessageAsString } from "@/utils/simple-error";

const DEFAULT_POLL_DELAY = 10000;

const getTempStorageRequestReady = fetcher
    .path("/api/short_term_storage/{storage_request_id}/ready")
    .method("get")
    .create();

const READY_STATE = "READY";
const PENDING_STATE = "PENDING";
const VALID_STATES = [READY_STATE, PENDING_STATE];

export function useShortTermStorageMonitor() {
    let timeout: NodeJS.Timeout | null = null;
    let pollDelay = DEFAULT_POLL_DELAY;

    const isRunning = ref(false);
    const status = ref<string>();
    const currentStorageRequestId = ref<string>();
    const requestHasFailed = ref(false);

    const isCompleted = computed(() => status.value === READY_STATE);
    const hasFailed = computed(() => {
        return typeof status.value === "string" && !VALID_STATES.includes(status.value);
    });

    async function waitForTask(storageRequestId: string, pollDelayInMs = DEFAULT_POLL_DELAY) {
        pollDelay = pollDelayInMs;
        resetState();
        currentStorageRequestId.value = storageRequestId;
        isRunning.value = true;
        return fetchTaskStatus(storageRequestId);
    }

    async function fetchTaskStatus(storageRequestId: string) {
        try {
            const { data: isReady } = await getTempStorageRequestReady({ storage_request_id: storageRequestId });
            status.value = isReady ? READY_STATE : PENDING_STATE;

            if (isReady) {
                isRunning.value = false;
            } else {
                pollAfterDelay(storageRequestId);
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
        waitForTask,
        isRunning: readonly(isRunning),
        isCompleted: readonly(isCompleted),
        hasFailed: readonly(hasFailed),
        requestHasFailed: readonly(requestHasFailed),
        status: readonly(status),
    };
}
