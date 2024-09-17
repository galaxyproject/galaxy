import { ref } from "vue";

import { type TaskMonitor } from "@/composables/genericTaskMonitor";
import {
    type MonitoringData,
    type MonitoringRequest,
    usePersistentProgressTaskMonitor,
} from "@/composables/persistentProgressMonitor";

// Mocks for dependencies
jest.mock("@vueuse/core", () => ({
    useLocalStorage: jest.fn().mockImplementation((key, initialValue) => ref(initialValue)),
    StorageSerializers: {
        object: {
            read: (value: string) => JSON.parse(value),
            write: (value: any) => JSON.stringify(value),
        },
    },
}));

function useMonitorMock(): TaskMonitor {
    const isRunning = ref(false);
    const status = ref();

    return {
        waitForTask: jest.fn().mockImplementation(() => {
            isRunning.value = true;
        }),
        isRunning,
        isCompleted: ref(false),
        hasFailed: ref(false),
        requestHasFailed: ref(false),
        status,
        expirationTime: 1000,
        isFinalState: jest.fn(),
        loadStatus(storedStatus) {
            status.value = storedStatus;
        },
    };
}
const mockUseMonitor = useMonitorMock();

const MOCK_REQUEST: MonitoringRequest = {
    source: "testSource",
    action: "export",
    taskType: "task",
    object: {
        id: "1",
        type: "dataset",
    },
    description: "Test description",
};

describe("usePersistentProgressTaskMonitor", () => {
    it("should initialize with no monitoring data if none is provided or stored", () => {
        const { hasMonitoringData } = usePersistentProgressTaskMonitor(MOCK_REQUEST, mockUseMonitor);
        expect(hasMonitoringData.value).toBeFalsy();
    });

    it("should start monitoring with provided monitoring data", async () => {
        const monitoringData: MonitoringData = {
            taskId: "123",
            taskType: "task",
            request: MOCK_REQUEST,
            startedAt: new Date(),
        };

        const { start, isRunning } = usePersistentProgressTaskMonitor(MOCK_REQUEST, mockUseMonitor, monitoringData);

        await start();
        expect(isRunning.value).toBeTruthy();
    });

    it("should throw an error if trying to start monitoring without monitoring data", async () => {
        const { start } = usePersistentProgressTaskMonitor(MOCK_REQUEST, mockUseMonitor);
        await expect(start()).rejects.toThrow(
            "No monitoring data provided or stored. Cannot start monitoring progress."
        );
    });

    it("should reset monitoring data", () => {
        const monitoringData: MonitoringData = {
            taskId: "123",
            taskType: "task",
            request: MOCK_REQUEST,
            startedAt: new Date(),
        };

        const { reset, hasMonitoringData } = usePersistentProgressTaskMonitor(
            MOCK_REQUEST,
            mockUseMonitor,
            monitoringData
        );
        expect(hasMonitoringData.value).toBeTruthy();
        reset();
        expect(hasMonitoringData.value).toBeFalsy();
    });
});
