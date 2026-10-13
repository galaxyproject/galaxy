import { suppressDebugConsole } from "@tests/vitest/helpers";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import { useShortTermStorageMonitor } from "@/composables/shortTermStorageMonitor";

import type { StoredTaskStatus } from "./genericTaskMonitor";

const PENDING_TASK_ID = "pending-fake-task-id";
const COMPLETED_TASK_ID = "completed-fake-task-id";
const REQUEST_FAILED_TASK_ID = "request-failed-fake-task-id";
const IN_FLIGHT_TASK_ID = "in-flight-fake-task-id";

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
            }),
        );
    });

    it("should indicate the task is running when it is still not ready", async () => {
        const { waitForTask, isRunning, taskStatus } = useShortTermStorageMonitor();

        expect(isRunning.value).toBe(false);
        waitForTask(PENDING_TASK_ID);
        await flushPromises();
        expect(isRunning.value).toBe(true);
        expect(taskStatus.value).toBe("PENDING");
    });

    it("should indicate the task is successfully completed when the state is ready", async () => {
        const { waitForTask, isRunning, isCompleted, taskStatus } = useShortTermStorageMonitor();

        expect(isCompleted.value).toBe(false);
        waitForTask(COMPLETED_TASK_ID);
        await flushPromises();
        expect(isCompleted.value).toBe(true);
        expect(isRunning.value).toBe(false);
        expect(taskStatus.value).toBe("READY");
    });

    it("should indicate the task status request failed when the request failed", async () => {
        suppressDebugConsole(); // expected API failure
        const { waitForTask, requestHasFailed, isRunning, isCompleted, taskStatus } = useShortTermStorageMonitor();

        expect(requestHasFailed.value).toBe(false);
        waitForTask(REQUEST_FAILED_TASK_ID);
        await flushPromises();
        expect(requestHasFailed.value).toBe(true);
        expect(isRunning.value).toBe(false);
        expect(isCompleted.value).toBe(false);
        expect(taskStatus.value).toBe("Request failed");
    });

    it("should load the status from the stored monitoring data", async () => {
        const { loadStatus, isRunning, isCompleted, hasFailed, taskStatus } = useShortTermStorageMonitor();
        const expectedStatus = "READY";
        const storedStatus: StoredTaskStatus = {
            taskStatus: expectedStatus,
        };

        loadStatus(storedStatus);

        expect(taskStatus.value).toBe(expectedStatus);
        expect(isRunning.value).toBe(false);
        expect(isCompleted.value).toBe(true);
        expect(hasFailed.value).toBe(false);
    });

    describe("stopping while a status request is in flight", () => {
        let statusRequests: number;
        let releasePendingRequest: () => void;

        beforeEach(() => {
            statusRequests = 0;
            const pendingRequest = new Promise<void>((resolve) => (releasePendingRequest = resolve));
            server.use(
                http.get("/api/short_term_storage/{storage_request_id}/ready", async ({ response, params }) => {
                    if (params.storage_request_id !== IN_FLIGHT_TASK_ID) {
                        return response("4XX").json({ err_msg: "Not found", err_code: 404 }, { status: 404 });
                    }
                    statusRequests += 1;
                    await pendingRequest;
                    return response(200).json(false);
                }),
            );
        });

        async function expectNoFurtherPolling() {
            vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
            try {
                releasePendingRequest();
                await flushPromises();
                vi.advanceTimersByTime(1000);
                await flushPromises();
                expect(statusRequests).toBe(1);
            } finally {
                vi.useRealTimers();
            }
        }

        it("should not resume polling after stopWaitingForTask", async () => {
            const { waitForTask, stopWaitingForTask } = useShortTermStorageMonitor();

            waitForTask(IN_FLIGHT_TASK_ID, 100);
            await vi.waitFor(() => expect(statusRequests).toBe(1));
            stopWaitingForTask();

            await expectNoFurtherPolling();
        });

        it("should not resume polling after its effect scope is disposed", async () => {
            const scope = effectScope();
            const { waitForTask, taskStatus } = scope.run(() => useShortTermStorageMonitor())!;

            waitForTask(IN_FLIGHT_TASK_ID, 100);
            await vi.waitFor(() => expect(statusRequests).toBe(1));
            scope.stop();

            await expectNoFurtherPolling();
            expect(taskStatus.value).toBeUndefined();
        });

        it("should not start polling once its effect scope is disposed", async () => {
            const scope = effectScope();
            const { waitForTask } = scope.run(() => useShortTermStorageMonitor())!;
            scope.stop();

            waitForTask(IN_FLIGHT_TASK_ID, 100);
            await flushPromises();
            expect(statusRequests).toBe(0);
        });
    });

    describe("isFinalState", () => {
        it("should indicate is final state when the task is completed", async () => {
            const { waitForTask, isFinalState, isRunning, isCompleted, hasFailed, taskStatus } =
                useShortTermStorageMonitor();

            expect(isFinalState(taskStatus.value)).toBe(false);
            waitForTask(COMPLETED_TASK_ID);
            await flushPromises();
            expect(isFinalState(taskStatus.value)).toBe(true);
            expect(isRunning.value).toBe(false);
            expect(isCompleted.value).toBe(true);
            expect(hasFailed.value).toBe(false);
        });

        it("should indicate is final state when the task has failed", async () => {
            suppressDebugConsole(); // expected API failure
            const { waitForTask, isFinalState, isRunning, isCompleted, hasFailed, taskStatus } =
                useShortTermStorageMonitor();

            expect(isFinalState(taskStatus.value)).toBe(false);
            waitForTask(REQUEST_FAILED_TASK_ID);
            await flushPromises();
            expect(isFinalState(taskStatus.value)).toBe(true);
            expect(isRunning.value).toBe(false);
            expect(isCompleted.value).toBe(false);
            expect(hasFailed.value).toBe(true);
        });
    });
});
