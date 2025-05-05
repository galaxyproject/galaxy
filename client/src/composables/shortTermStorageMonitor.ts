import { GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

import { useGenericMonitor } from "./genericTaskMonitor";

const DEFAULT_POLL_DELAY = 10000;
const DEFAULT_EXPIRATION_TIME = 1000 * 60 * 60 * 24; // 24 hours

const READY_STATE = "READY";
const PENDING_STATE = "PENDING";
const VALID_STATES = [READY_STATE, PENDING_STATE];

/**
 * Composable for waiting on Galaxy Short Term Storage requests.
 */
export function useShortTermStorageMonitor() {
    const fetchStatus = async (taskId: string) => {
        const { data, error } = await GalaxyApi().GET("/api/short_term_storage/{storage_request_id}/ready", {
            params: { path: { storage_request_id: taskId } },
        });

        if (error) {
            rethrowSimple(error);
        }

        return data ? READY_STATE : PENDING_STATE;
    };

    return useGenericMonitor({
        fetchStatus,
        completedCondition: (status?: string) => status === READY_STATE,
        failedCondition: (status?: string) => typeof status === "string" && !VALID_STATES.includes(status),
        fetchFailureReason: fetchStatus, // The error message is the status itself for short-term storage requests
        defaultPollDelay: DEFAULT_POLL_DELAY,
        expirationTime: DEFAULT_EXPIRATION_TIME,
    });
}
