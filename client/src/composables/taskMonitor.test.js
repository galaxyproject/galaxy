import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { useTaskMonitor } from "composables/taskMonitor";

const PENDING_TASK_ID = "pending-fake-task-id";
const COMPLETED_TASK_ID = "completed-fake-task-id";
const FAILED_TASK_ID = "failed-fake-task-id";
const REQUEST_FAILED_TASK_ID = "request-failed-fake-task-id";

describe("useTaskMonitor", () => {
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(async () => {
        axiosMock.reset();
    });

    it("should indicate the task is running when it is still pending", async () => {
        axiosMock.onGet(`/api/tasks/${PENDING_TASK_ID}/state`).reply(200, "PENDING");
        const { waitForTask, isRunning } = useTaskMonitor();

        expect(isRunning.value).toBe(false);
        waitForTask(PENDING_TASK_ID);
        await flushPromises();
        expect(isRunning.value).toBe(true);
    });

    it("should indicate the task is successfully completed when the state is SUCCESS", async () => {
        axiosMock.onGet(`/api/tasks/${COMPLETED_TASK_ID}/state`).reply(200, "SUCCESS");
        const { waitForTask, isRunning, isCompleted } = useTaskMonitor();

        expect(isCompleted.value).toBe(false);
        waitForTask(COMPLETED_TASK_ID);
        await flushPromises();
        expect(isCompleted.value).toBe(true);
        expect(isRunning.value).toBe(false);
    });

    it("should indicate the task has failed when the state is FAILED", async () => {
        axiosMock.onGet(`/api/tasks/${FAILED_TASK_ID}/state`).reply(200, "FAILURE");
        const { waitForTask, isRunning, hasFailed } = useTaskMonitor();

        expect(hasFailed.value).toBe(false);
        waitForTask(FAILED_TASK_ID);
        await flushPromises();
        expect(hasFailed.value).toBe(true);
        expect(isRunning.value).toBe(false);
    });

    it("should indicate the task status request failed when the request failed", async () => {
        axiosMock.onGet(`/api/tasks/${REQUEST_FAILED_TASK_ID}/state`).reply(400, "UNKNOWN");
        const { waitForTask, requestHasFailed } = useTaskMonitor();

        expect(requestHasFailed.value).toBe(false);
        waitForTask(REQUEST_FAILED_TASK_ID);
        await flushPromises();
        expect(requestHasFailed.value).toBe(true);
    });
});
