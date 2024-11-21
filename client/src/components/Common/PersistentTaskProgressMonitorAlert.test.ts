import { shallowMount } from "@vue/test-utils";
import { type PropType, ref } from "vue";

import { type TaskMonitor } from "@/composables/genericTaskMonitor";
import {
    type MonitoringData,
    type MonitoringRequest,
    usePersistentProgressTaskMonitor,
} from "@/composables/persistentProgressMonitor";

import PersistentTaskProgressMonitorAlert from "@/components/Common/PersistentTaskProgressMonitorAlert.vue";

type ComponentUnderTestProps = Partial<PropType<typeof PersistentTaskProgressMonitorAlert>>;

const selectors = {
    ProgressAlert: ".progress-monitor-alert",
} as const;

const FAKE_MONITOR_REQUEST: MonitoringRequest = {
    source: "test",
    action: "testing",
    taskType: "task",
    object: { id: "1", type: "dataset" },
    description: "Test description",
};

const FAKE_EXPIRATION_TIME = 1000;

const FAKE_MONITOR: TaskMonitor = {
    waitForTask: jest.fn(),
    isRunning: ref(false),
    isCompleted: ref(false),
    hasFailed: ref(false),
    requestHasFailed: ref(false),
    taskStatus: ref(""),
    expirationTime: FAKE_EXPIRATION_TIME,
    isFinalState: jest.fn(),
    loadStatus: jest.fn(),
};

const mountComponent = (
    props: ComponentUnderTestProps = {
        monitorRequest: FAKE_MONITOR_REQUEST,
        useMonitor: FAKE_MONITOR,
    }
) => {
    return shallowMount(PersistentTaskProgressMonitorAlert as object, {
        propsData: {
            ...props,
        },
    });
};

describe("PersistentTaskProgressMonitorAlert.vue", () => {
    beforeEach(() => {
        usePersistentProgressTaskMonitor(FAKE_MONITOR_REQUEST, FAKE_MONITOR).reset();
    });

    it("does not render when no monitoring data is available", () => {
        const wrapper = mountComponent();
        expect(wrapper.find(selectors.ProgressAlert).exists()).toBe(false);
    });

    it("renders in progress when monitoring data is available and in progress", () => {
        const useMonitor = {
            ...FAKE_MONITOR,
            isRunning: ref(true),
        };
        const existingMonitoringData: MonitoringData = {
            taskId: "1",
            taskType: "task",
            request: FAKE_MONITOR_REQUEST,
            startedAt: new Date(),
        };
        usePersistentProgressTaskMonitor(FAKE_MONITOR_REQUEST, useMonitor, existingMonitoringData);

        const wrapper = mountComponent({
            monitorRequest: FAKE_MONITOR_REQUEST,
            useMonitor,
        });

        expect(wrapper.find(selectors.ProgressAlert).exists()).toBe(true);

        const inProgressAlert = wrapper.find('[variant="info"]');
        expect(inProgressAlert.exists()).toBe(true);
        expect(inProgressAlert.text()).toContain("Task is in progress");
    });

    it("renders completed when monitoring data is available and completed", () => {
        const useMonitor = {
            ...FAKE_MONITOR,
            isCompleted: ref(true),
        };
        const existingMonitoringData: MonitoringData = {
            taskId: "1",
            taskType: "task",
            request: FAKE_MONITOR_REQUEST,
            startedAt: new Date(),
        };
        usePersistentProgressTaskMonitor(FAKE_MONITOR_REQUEST, useMonitor, existingMonitoringData);

        const wrapper = mountComponent({
            monitorRequest: FAKE_MONITOR_REQUEST,
            useMonitor,
        });

        expect(wrapper.find(selectors.ProgressAlert).exists()).toBe(true);

        const completedAlert = wrapper.find('[variant="success"]');
        expect(completedAlert.exists()).toBe(true);
        expect(completedAlert.text()).toContain("Task completed");
    });

    it("renders failed when monitoring data is available and failed", () => {
        const useMonitor = {
            ...FAKE_MONITOR,
            hasFailed: ref(true),
        };
        const existingMonitoringData: MonitoringData = {
            taskId: "1",
            taskType: "task",
            request: FAKE_MONITOR_REQUEST,
            startedAt: new Date(),
        };
        usePersistentProgressTaskMonitor(FAKE_MONITOR_REQUEST, useMonitor, existingMonitoringData);

        const wrapper = mountComponent({
            monitorRequest: FAKE_MONITOR_REQUEST,
            useMonitor,
        });

        expect(wrapper.find(selectors.ProgressAlert).exists()).toBe(true);

        const failedAlert = wrapper.find('[variant="danger"]');
        expect(failedAlert.exists()).toBe(true);
        expect(failedAlert.text()).toContain("Task failed");
    });

    it("renders a link to download the task result when completed and task type is 'short_term_storage'", () => {
        const taskId = "fake-task-id";
        const monitoringRequest: MonitoringRequest = {
            ...FAKE_MONITOR_REQUEST,
            taskType: "short_term_storage",
        };
        const useMonitor = {
            ...FAKE_MONITOR,
            isCompleted: ref(true),
        };
        const existingMonitoringData: MonitoringData = {
            taskId: taskId,
            taskType: "short_term_storage",
            request: monitoringRequest,
            startedAt: new Date(),
        };
        usePersistentProgressTaskMonitor(monitoringRequest, useMonitor, existingMonitoringData);

        const wrapper = mountComponent({
            monitorRequest: monitoringRequest,
            useMonitor,
        });

        expect(wrapper.find(selectors.ProgressAlert).exists()).toBe(true);

        const completedAlert = wrapper.find('[variant="success"]');
        expect(completedAlert.exists()).toBe(true);

        const downloadLink = wrapper.find(".download-link");
        expect(downloadLink.exists()).toBe(true);
        expect(downloadLink.text()).toContain("Download here");
        expect(downloadLink.attributes("href")).toBe(`/api/short_term_storage/${taskId}`);
    });

    it("does not render a link to download the task result when completed and task type is 'task'", () => {
        const useMonitor = {
            ...FAKE_MONITOR,
            isCompleted: ref(true),
        };
        const existingMonitoringData: MonitoringData = {
            taskId: "1",
            taskType: "task",
            request: FAKE_MONITOR_REQUEST,
            startedAt: new Date(),
        };
        usePersistentProgressTaskMonitor(FAKE_MONITOR_REQUEST, useMonitor, existingMonitoringData);

        const wrapper = mountComponent({
            monitorRequest: FAKE_MONITOR_REQUEST,
            useMonitor,
        });

        expect(wrapper.find(selectors.ProgressAlert).exists()).toBe(true);

        const completedAlert = wrapper.find('[variant="success"]');
        expect(completedAlert.exists()).toBe(true);
        expect(completedAlert.text()).not.toContain("Download here");
    });

    it("should render a warning alert when the task has expired even if the status is running", () => {
        const useMonitor = {
            ...FAKE_MONITOR,
            isRunning: ref(true),
        };
        const existingMonitoringData: MonitoringData = {
            taskId: "1",
            taskType: "task",
            request: FAKE_MONITOR_REQUEST,
            startedAt: new Date(Date.now() - FAKE_EXPIRATION_TIME * 2), // Make sure the task has expired
        };
        usePersistentProgressTaskMonitor(FAKE_MONITOR_REQUEST, useMonitor, existingMonitoringData);

        const wrapper = mountComponent({
            monitorRequest: FAKE_MONITOR_REQUEST,
            useMonitor,
        });

        expect(wrapper.find(selectors.ProgressAlert).exists()).toBe(true);

        const warningAlert = wrapper.find('[variant="warning"]');
        expect(warningAlert.exists()).toBe(true);
        expect(warningAlert.text()).toContain("The testing task has expired and the result is no longer available");
    });
});
