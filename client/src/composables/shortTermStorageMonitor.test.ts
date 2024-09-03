import flushPromises from "flush-promises";

import { useServerMock } from "@/api/client/__mocks__";
import { useShortTermStorageMonitor } from "@/composables/shortTermStorageMonitor";

const PENDING_TASK_ID = "pending-fake-task-id";
const COMPLETED_TASK_ID = "completed-fake-task-id";
const REQUEST_FAILED_TASK_ID = "request-failed-fake-task-id";

const { server, http } = useServerMock();

describe("useShortTermStorageMonitor", () => {
    beforeEach(() => {
        server.use(
            http.get("/api/short_term_storage/{storage_request_id}/ready", ({ response, params }) => {
                switch (params.storage_request_id) {
                    case PENDING_TASK_ID:
                        return response(200).json(false);

                    case COMPLETED_TASK_ID:
                        return response(200).json(true);

                    case REQUEST_FAILED_TASK_ID:
                        return response("5XX").json({ err_msg: "Request failed", err_code: 500 }, { status: 500 });

                    default:
                        return response("4XX").json({ err_msg: "Not found", err_code: 404 }, { status: 404 });
                }
            })
        );
    });

    it("should indicate the task is running when it is still not ready", async () => {
        const { waitForTask, isRunning, status } = useShortTermStorageMonitor();

        expect(isRunning.value).toBe(false);
        waitForTask(PENDING_TASK_ID);
        await flushPromises();
        expect(isRunning.value).toBe(true);
        expect(status.value).toBe("PENDING");
    });

    it("should indicate the task is successfully completed when the state is ready", async () => {
        const { waitForTask, isRunning, isCompleted, status } = useShortTermStorageMonitor();

        expect(isCompleted.value).toBe(false);
        waitForTask(COMPLETED_TASK_ID);
        await flushPromises();
        expect(isCompleted.value).toBe(true);
        expect(isRunning.value).toBe(false);
        expect(status.value).toBe("READY");
    });

    it("should indicate the task status request failed when the request failed", async () => {
        const { waitForTask, requestHasFailed, isRunning, isCompleted, status } = useShortTermStorageMonitor();

        expect(requestHasFailed.value).toBe(false);
        waitForTask(REQUEST_FAILED_TASK_ID);
        await flushPromises();
        expect(requestHasFailed.value).toBe(true);
        expect(isRunning.value).toBe(false);
        expect(isCompleted.value).toBe(false);
        expect(status.value).toBe("Request failed");
    });

    it("should load the status from the stored monitoring data", async () => {
        const { loadStatus, isRunning, isCompleted, hasFailed, status } = useShortTermStorageMonitor();
        const storedStatus = "READY";

        loadStatus(storedStatus);

        expect(status.value).toBe(storedStatus);
        expect(isRunning.value).toBe(false);
        expect(isCompleted.value).toBe(true);
        expect(hasFailed.value).toBe(false);
    });

    describe("isFinalState", () => {
        it("should indicate is final state when the task is completed", async () => {
            const { waitForTask, isFinalState, isRunning, isCompleted, hasFailed, status } =
                useShortTermStorageMonitor();

            expect(isFinalState(status.value)).toBe(false);
            waitForTask(COMPLETED_TASK_ID);
            await flushPromises();
            expect(isFinalState(status.value)).toBe(true);
            expect(isRunning.value).toBe(false);
            expect(isCompleted.value).toBe(true);
            expect(hasFailed.value).toBe(false);
        });

        it("should indicate is final state when the task has failed", async () => {
            const { waitForTask, isFinalState, isRunning, isCompleted, hasFailed, status } =
                useShortTermStorageMonitor();

            expect(isFinalState(status.value)).toBe(false);
            waitForTask(REQUEST_FAILED_TASK_ID);
            await flushPromises();
            expect(isFinalState(status.value)).toBe(true);
            expect(isRunning.value).toBe(false);
            expect(isCompleted.value).toBe(false);
            expect(hasFailed.value).toBe(true);
        });
    });
});
