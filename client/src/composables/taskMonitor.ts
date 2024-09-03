import { GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

import { useGenericMonitor } from "./genericTaskMonitor";

const SUCCESS_STATE = "SUCCESS";
const FAILURE_STATE = "FAILURE";
const DEFAULT_POLL_DELAY = 10000;
const DEFAULT_EXPIRATION_TIME = 1000 * 60 * 60 * 24; // 24 hours

/**
 * Composable for waiting on Galaxy background tasks.
 */
export function useTaskMonitor() {
    const fetchStatus = async (taskId: string) => {
        const { data, error } = await GalaxyApi().GET("/api/tasks/{task_id}/state", {
            params: { path: { task_id: taskId } },
        });

        if (error) {
            rethrowSimple(error);
        }

        return data;
    };
    return useGenericMonitor({
        fetchStatus,
        completedCondition: (status?: string) => status === SUCCESS_STATE,
        failedCondition: (status?: string) => status === FAILURE_STATE,
        defaultPollDelay: DEFAULT_POLL_DELAY,
        expirationTime: DEFAULT_EXPIRATION_TIME,
    });
}
