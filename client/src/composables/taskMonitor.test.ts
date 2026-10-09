import { suppressDebugConsole } from "@tests/vitest/helpers";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { useTaskMonitor } from "@/composables/taskMonitor";

import type { StoredTaskStatus } from "./genericTaskMonitor";

const PENDING_TASK_ID = "pending-fake-task-id";
const COMPLETED_TASK_ID = "completed-fake-task-id";
const FAILED_TASK_ID = "failed-fake-task-id";
const REQUEST_FAILED_TASK_ID = "request-failed-fake-task-id";

const { server, http } = useServerMock();

describe("useTaskMonitor", () => {
    const monitors: ReturnType<typeof useTaskMonitor>[] = [];

    function createMonitor() {
        const monitor = useTaskMonitor();
        monitors.push(monitor);
        return monitor;
    }

    afterEach(() => {
        monitors.forEach((monitor) => monitor.stopWaitingForTask());
        monitors.length = 0;
        vi.restoreAllMocks();
    });

    function mockTaskState(taskId: string, state: "PENDING" | "SUCCESS" | "FAILURE") {
        server.use(
            http.get("/api/tasks/{task_id}/state", ({ response, params }) => {
                expect(params.task_id).toBe(taskId);
                return response(200).json(state);
            }),
        );
    }

    function mockFailureReason(taskId: string) {
        server.use(
            http.get("/api/tasks/{task_id}/result", ({ response, params }) => {
                expect(params.task_id).toBe(taskId);
                return response(200).json({ state: "FAILURE", result: "The failure reason" });
            }),
        );
    }

    it("keeps monitoring a PENDING task", async () => {
        const { waitForTask, isRunning, taskStatus } = createMonitor();

        mockTaskState(PENDING_TASK_ID, "PENDING");

        expect(isRunning.value).toBe(false);
        await waitForTask(PENDING_TASK_ID);
        expect(isRunning.value).toBe(true);
        expect(taskStatus.value).toBe("PENDING");
    });

    it("marks a SUCCESS task complete and stops monitoring", async () => {
        const { waitForTask, isRunning, isCompleted, taskStatus } = createMonitor();

        mockTaskState(COMPLETED_TASK_ID, "SUCCESS");

        expect(isCompleted.value).toBe(false);
        await waitForTask(COMPLETED_TASK_ID);
        expect(isCompleted.value).toBe(true);
        expect(isRunning.value).toBe(false);
        expect(taskStatus.value).toBe("SUCCESS");
    });

    it("marks a FAILURE task failed and retrieves its reason", async () => {
        const { waitForTask, isRunning, hasFailed, taskStatus, failureReason } = createMonitor();

        mockTaskState(FAILED_TASK_ID, "FAILURE");
        mockFailureReason(FAILED_TASK_ID);

        expect(hasFailed.value).toBe(false);
        await waitForTask(FAILED_TASK_ID);
        expect(hasFailed.value).toBe(true);
        expect(isRunning.value).toBe(false);
        expect(taskStatus.value).toBe("FAILURE");
        expect(failureReason.value).toBe("The failure reason");
    });

    it("reports a failed status request without marking the task complete", async () => {
        const { waitForTask, requestHasFailed, isRunning, isCompleted, taskStatus } = createMonitor();
        suppressDebugConsole();
        server.use(
            http.get("/api/tasks/{task_id}/state", ({ response, params }) => {
                expect(params.task_id).toBe(REQUEST_FAILED_TASK_ID);
                return response("5XX").json({ err_msg: "Request failed", err_code: 500 }, { status: 500 });
            }),
        );

        expect(requestHasFailed.value).toBe(false);
        await waitForTask(REQUEST_FAILED_TASK_ID);
        expect(requestHasFailed.value).toBe(true);
        expect(isRunning.value).toBe(false);
        expect(isCompleted.value).toBe(false);
        expect(taskStatus.value).toBe("Request failed");
    });

    it("restores a completed task from stored status", () => {
        const { loadStatus, isRunning, isCompleted, hasFailed, taskStatus } = createMonitor();
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

    it("restores a failed task and its stored failure reason", () => {
        const { loadStatus, isRunning, isCompleted, hasFailed, taskStatus, failureReason } = createMonitor();
        const expectedStatus = "FAILURE";
        const expectedFailureReason = "The stored failure reason";
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
        it("recognizes a completed task as final", async () => {
            const { waitForTask, isFinalState, isRunning, isCompleted, hasFailed, taskStatus } = createMonitor();

            mockTaskState(COMPLETED_TASK_ID, "SUCCESS");

            expect(isFinalState(taskStatus.value)).toBe(false);
            await waitForTask(COMPLETED_TASK_ID);
            expect(isFinalState(taskStatus.value)).toBe(true);
            expect(isRunning.value).toBe(false);
            expect(isCompleted.value).toBe(true);
            expect(hasFailed.value).toBe(false);
        });

        it("recognizes a failed task as final", async () => {
            const { waitForTask, isFinalState, isRunning, isCompleted, hasFailed, taskStatus } = createMonitor();

            mockTaskState(FAILED_TASK_ID, "FAILURE");
            mockFailureReason(FAILED_TASK_ID);

            expect(isFinalState(taskStatus.value)).toBe(false);
            await waitForTask(FAILED_TASK_ID);
            expect(isFinalState(taskStatus.value)).toBe(true);
            expect(isRunning.value).toBe(false);
            expect(isCompleted.value).toBe(false);
            expect(hasFailed.value).toBe(true);
        });
    });
});
