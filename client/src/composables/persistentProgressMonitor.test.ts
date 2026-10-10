import { getFakeMonitoringData } from "@tests/test-data/monitoring";
import { getFakeTaskMonitor } from "@tests/vitest/fakeTaskMonitor";
import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { type MonitoringRequest, usePersistentProgressTaskMonitor } from "@/composables/persistentProgressMonitor";

vi.mock("@vueuse/core", () => ({
    useLocalStorage: vi.fn().mockImplementation((key, initialValue) => ref(initialValue)),
    StorageSerializers: {
        object: {
            read: (value: string) => JSON.parse(value),
            write: (value: unknown) => JSON.stringify(value),
        },
    },
}));

const MOCK_REQUEST: MonitoringRequest = {
    source: "testSource",
    action: "export",
    taskType: "task",
    object: {
        id: "1",
        type: "history",
    },
    description: "Test description",
};

const EXPIRATION_TIME = 1000;

describe("usePersistentProgressTaskMonitor", () => {
    it("has no monitoring data when none is provided or stored", () => {
        const { hasMonitoringData } = usePersistentProgressTaskMonitor(
            MOCK_REQUEST,
            getFakeTaskMonitor({ expirationTime: EXPIRATION_TIME }),
        );

        expect(hasMonitoringData.value).toBe(false);
    });

    it("starts waiting for the provided task and exposes the monitor's running state", async () => {
        const isRunning = ref(false);
        const waitForTask = vi.fn(async () => {
            isRunning.value = true;
        });
        const monitor = getFakeTaskMonitor({ expirationTime: EXPIRATION_TIME, isRunning, waitForTask });
        const monitoringData = getFakeMonitoringData(MOCK_REQUEST, { taskId: "123" });

        const { start, isRunning: monitoredIsRunning } = usePersistentProgressTaskMonitor(
            MOCK_REQUEST,
            monitor,
            monitoringData,
        );
        await start();

        expect(waitForTask).toHaveBeenCalledWith("123");
        expect(monitoredIsRunning.value).toBe(true);
    });

    it("refuses to start without provided or stored monitoring data", async () => {
        const { start } = usePersistentProgressTaskMonitor(
            MOCK_REQUEST,
            getFakeTaskMonitor({ expirationTime: EXPIRATION_TIME }),
        );

        await expect(start()).rejects.toThrow(
            "No monitoring data provided or stored. Cannot start monitoring progress.",
        );
    });

    it("clears the monitoring data on reset", () => {
        const monitoringData = getFakeMonitoringData(MOCK_REQUEST, { taskId: "123" });
        const { reset, hasMonitoringData } = usePersistentProgressTaskMonitor(
            MOCK_REQUEST,
            getFakeTaskMonitor({ expirationTime: EXPIRATION_TIME }),
            monitoringData,
        );
        expect(hasMonitoringData.value).toBe(true);

        reset();

        expect(hasMonitoringData.value).toBe(false);
    });
});
