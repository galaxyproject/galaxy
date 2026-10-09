import type { MonitoringData, MonitoringRequest } from "@/composables/persistentProgressMonitor";

export function getFakeMonitoringData(
    request: MonitoringRequest,
    overrides: Partial<Omit<MonitoringData, "request" | "taskType">> = {},
): MonitoringData {
    return {
        taskId: "task-id",
        taskType: request.taskType,
        request: { ...request, object: { ...request.object } },
        startedAt: new Date(),
        isFinal: false,
        ...overrides,
    };
}
