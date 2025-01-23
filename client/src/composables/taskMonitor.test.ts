import flushPromises from "flush-promises";
import { suppressDebugConsole } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { useTaskMonitor } from "@/composables/taskMonitor";

import type { StoredTaskStatus } from "./genericTaskMonitor";

const PENDING_TASK_ID = "pending-fake-task-id";
const COMPLETED_TASK_ID = "completed-fake-task-id";
const FAILED_TASK_ID = "failed-fake-task-id";
const REQUEST_FAILED_TASK_ID = "request-failed-fake-task-id";

const { server, http } = useServerMock();

describe("useTaskMonitor", () => {
    beforeEach(() => {
        server.use(
            http.get("/api/tasks/{task_id}/state", ({ response, params }) => {
                switch (params.task_id) {
                    case PENDING_TASK_ID:
                        return response(200).json("PENDING");

                    case COMPLETED_TASK_ID:
                        return response(200).json("SUCCESS");

                    case FAILED_TASK_ID:
                        return response(200).json("FAILURE");

                    case REQUEST_FAILED_TASK_ID:
                        return response("5XX").json({ err_msg: "Request failed", err_code: 500 }, { status: 500 });

                    default:
                        return response("4XX").json({ err_msg: "Not found", err_code: 404 }, { status: 404 });
                }
            }),
            http.get("/api/tasks/{task_id}/result", ({ response, params }) => {
                switch (params.task_id) {
                    case PENDING_TASK_ID:
                        return response(200).json({ state: "PENDING", result: "" });

                    case COMPLETED_TASK_ID:
                        return response(200).json({ state: "SUCCESS", result: "" });

                    case FAILED_TASK_ID:
                        return response(200).json({ state: "FAILURE", result: "The failure reason" });

                    case REQUEST_FAILED_TASK_ID:
                        return response("5XX").json({ err_msg: "Request failed", err_code: 500 }, { status: 500 });

                    default:
                        return response("4XX").json({ err_msg: "Not found", err_code: 404 }, { status: 404 });
                }
            })
        );
    });

    it("should indicate the task is running when it is still pending", async () => {
        const { waitForTask, isRunning, taskStatus } = useTaskMonitor();

        expect(isRunning.value).toBe(false);
        waitForTask(PENDING_TASK_ID);
        await flushPromises();
        expect(isRunning.value).toBe(true);
        expect(taskStatus.value).toBe("PENDING");
    });

    it("should indicate the task is successfully completed when the state is SUCCESS", async () => {
        const { waitForTask, isRunning, isCompleted, taskStatus } = useTaskMonitor();

        expect(isCompleted.value).toBe(false);
        waitForTask(COMPLETED_TASK_ID);
        await flushPromises();
        expect(isCompleted.value).toBe(true);
        expect(isRunning.value).toBe(false);
        expect(taskStatus.value).toBe("SUCCESS");
    });

    it("should indicate the task has failed when the state is FAILED", async () => {
        const { waitForTask, isRunning, hasFailed, taskStatus } = useTaskMonitor();

        expect(hasFailed.value).toBe(false);
        waitForTask(FAILED_TASK_ID);
        await flushPromises();
        expect(hasFailed.value).toBe(true);
        expect(isRunning.value).toBe(false);
        expect(taskStatus.value).toBe("FAILURE");
    });

    it("should indicate the task status request failed when the request failed", async () => {
        const { waitForTask, requestHasFailed, isRunning, isCompleted, taskStatus } = useTaskMonitor();
        suppressDebugConsole();

        expect(requestHasFailed.value).toBe(false);
        waitForTask(REQUEST_FAILED_TASK_ID);
        await flushPromises();
        expect(requestHasFailed.value).toBe(true);
        expect(isRunning.value).toBe(false);
        expect(isCompleted.value).toBe(false);
        expect(taskStatus.value).toBe("Request failed");
    });

    it("should load the status from the stored monitoring data", async () => {
        const { loadStatus, isRunning, isCompleted, hasFailed, taskStatus } = useTaskMonitor();
        const expectedStatus = "SUCCESS";
        const storedStatus: StoredTaskStatus = {
            taskStatus: expectedStatus,
        };

        loadStatus(storedStatus);

        expect(taskStatus.value).toBe(expectedStatus);
        expect(isRunning.value).toBe(false);
        expect(isCompleted.value).toBe(true);
        expect(hasFailed.value).toBe(false);
    });

    it("should load the status from the stored monitoring data with failure reason", async () => {
        const { loadStatus, isRunning, isCompleted, hasFailed, taskStatus, failureReason } = useTaskMonitor();
        const expectedStatus = "FAILURE";
        const expectedFailureReason = "The failure reason";
        const storedStatus: StoredTaskStatus = {
            taskStatus: expectedStatus,
            failureReason: expectedFailureReason,
        };

        loadStatus(storedStatus);

        expect(taskStatus.value).toBe(expectedStatus);
        expect(isRunning.value).toBe(false);
        expect(isCompleted.value).toBe(false);
        expect(hasFailed.value).toBe(true);
        expect(failureReason.value).toBe(expectedFailureReason);
    });

    describe("isFinalState", () => {
        it("should indicate is final state when the task is completed", async () => {
            const { waitForTask, isFinalState, isRunning, isCompleted, hasFailed, taskStatus } = useTaskMonitor();

            expect(isFinalState(taskStatus.value)).toBe(false);
            waitForTask(COMPLETED_TASK_ID);
            await flushPromises();
            expect(isFinalState(taskStatus.value)).toBe(true);
            expect(isRunning.value).toBe(false);
            expect(isCompleted.value).toBe(true);
            expect(hasFailed.value).toBe(false);
        });

        it("should indicate is final state when the task has failed", async () => {
            const { waitForTask, isFinalState, isRunning, isCompleted, hasFailed, taskStatus } = useTaskMonitor();

            expect(isFinalState(taskStatus.value)).toBe(false);
            waitForTask(FAILED_TASK_ID);
            await flushPromises();
            expect(isFinalState(taskStatus.value)).toBe(true);
            expect(isRunning.value).toBe(false);
            expect(isCompleted.value).toBe(false);
            expect(hasFailed.value).toBe(true);
        });
    });
});
