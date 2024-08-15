import { fetcher } from "@/api/schema";

import { useGenericMonitor } from "./genericTaskMonitor";

const DEFAULT_POLL_DELAY = 10000;
const DEFAULT_EXPIRATION_TIME = 1000 * 60 * 60 * 24; // 24 hours

const getTempStorageRequestReady = fetcher
    .path("/api/short_term_storage/{storage_request_id}/ready")
    .method("get")
    .create();

const READY_STATE = "READY";
const PENDING_STATE = "PENDING";
const VALID_STATES = [READY_STATE, PENDING_STATE];

/**
 * Composable for waiting on Galaxy Short Term Storage requests.
 */
export function useShortTermStorageMonitor() {
    const fetchStatus = async (taskId: string) => {
        const { data } = await getTempStorageRequestReady({ storage_request_id: taskId });
        return data ? READY_STATE : PENDING_STATE;
    };

    return useGenericMonitor({
        fetchStatus,
        completedCondition: (status?: string) => status === READY_STATE,
        failedCondition: (status?: string) => typeof status === "string" && !VALID_STATES.includes(status),
        defaultPollDelay: DEFAULT_POLL_DELAY,
        expirationTime: DEFAULT_EXPIRATION_TIME,
    });
}
