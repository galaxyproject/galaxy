import flushPromises from "flush-promises";

import { mockFetcher } from "@/api/schema/__mocks__";
import { useTaskMonitor } from "@/composables/taskMonitor";

jest.mock("@/api/schema");

const PENDING_TASK_ID = "pending-fake-task-id";
const COMPLETED_TASK_ID = "completed-fake-task-id";
const FAILED_TASK_ID = "failed-fake-task-id";
const REQUEST_FAILED_TASK_ID = "request-failed-fake-task-id";

function getMockedTaskStatus({ task_id }: { task_id: string }) {
    switch (task_id) {
        case PENDING_TASK_ID:
            return { data: "PENDING", status: 200 };

        case COMPLETED_TASK_ID:
            return { data: "SUCCESS", status: 200 };

        case FAILED_TASK_ID:
            return { data: "FAILURE", status: 200 };

        case REQUEST_FAILED_TASK_ID:
            throw new Error("Request failed");

        default:
            return { data: "UNKNOWN", status: 404 };
    }
}

mockFetcher.path("/api/tasks/{task_id}/state").method("get").mock(getMockedTaskStatus);

describe("useTaskMonitor", () => {
    it("should indicate the task is running when it is still pending", async () => {
        const { waitForTask, isRunning } = useTaskMonitor();

        expect(isRunning.value).toBe(false);
        waitForTask(PENDING_TASK_ID);
        await flushPromises();
        expect(isRunning.value).toBe(true);
    });

    it("should indicate the task is successfully completed when the state is SUCCESS", async () => {
        const { waitForTask, isRunning, isCompleted } = useTaskMonitor();

        expect(isCompleted.value).toBe(false);
        waitForTask(COMPLETED_TASK_ID);
        await flushPromises();
        expect(isCompleted.value).toBe(true);
        expect(isRunning.value).toBe(false);
    });

    it("should indicate the task has failed when the state is FAILED", async () => {
        const { waitForTask, isRunning, hasFailed } = useTaskMonitor();

        expect(hasFailed.value).toBe(false);
        waitForTask(FAILED_TASK_ID);
        await flushPromises();
        expect(hasFailed.value).toBe(true);
        expect(isRunning.value).toBe(false);
    });

    it("should indicate the task status request failed when the request failed", async () => {
        const { waitForTask, requestHasFailed } = useTaskMonitor();

        expect(requestHasFailed.value).toBe(false);
        waitForTask(REQUEST_FAILED_TASK_ID);
        await flushPromises();
        expect(requestHasFailed.value).toBe(true);
    });
});
