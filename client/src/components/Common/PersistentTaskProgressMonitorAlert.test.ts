import { shallowMount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { TaskMonitor } from "@/composables/genericTaskMonitor";
import { getPersistentKey, type MonitoringData, type MonitoringRequest } from "@/composables/persistentProgressMonitor";

import PersistentTaskProgressMonitorAlert from "@/components/Common/PersistentTaskProgressMonitorAlert.vue";

type ComponentUnderTestProps = Partial<InstanceType<typeof PersistentTaskProgressMonitorAlert>["$props"]>;

const selectors = {
    ProgressAlert: ".progress-monitor-alert",
} as const;

const FAKE_MONITOR_REQUEST: MonitoringRequest = {
    source: "test",
    action: "testing",
    taskType: "task",
    object: { id: "1", type: "history" },
    description: "Test description",
};

const FAKE_EXPIRATION_TIME = 1000;

const FAKE_MONITOR: TaskMonitor = {
    waitForTask: vi.fn(),
    stopWaitingForTask: vi.fn(),
    isRunning: ref(false),
    isCompleted: ref(false),
    hasFailed: ref(false),
    failureReason: ref(""),
    requestHasFailed: ref(false),
    taskStatus: ref(""),
    expirationTime: FAKE_EXPIRATION_TIME,
    isFinalState: vi.fn(),
    loadStatus: vi.fn(),
    fetchTaskStatus: vi.fn(),
};

// Seed the monitoring data this component reads directly via localStorage, rather than
// through usePersistentProgressTaskMonitor(). That composable's useLocalStorage() call
// registers a "storage" event listener that's only torn down when its owning effect
// scope is disposed, and a call made at the top level of a test (outside any component
// or effectScope) has no such scope, so the listener leaks for the rest of the file.
// With enough of those piled up, a later localStorage write fans out across all of them
// at once and the test run runs out of memory.
function seedMonitoringData(request: MonitoringRequest, monitoringData: MonitoringData) {
    localStorage.setItem(getPersistentKey(request), JSON.stringify(monitoringData));
}

// Each mounted component also owns one such listener (via its own internal
// usePersistentProgressTaskMonitor() call), scoped to the component instance this time --
// so it's cleaned up by unmounting rather than by avoiding the composable. Track and
// unmount every wrapper between tests for the same reason.
const mountedWrappers: VueWrapper[] = [];

const mountComponent = (
    props: ComponentUnderTestProps = {
        monitorRequest: FAKE_MONITOR_REQUEST,
        useMonitor: FAKE_MONITOR,
    },
) => {
    const wrapper = shallowMount(PersistentTaskProgressMonitorAlert as object, {
        props: {
            ...props,
        },
        global: {
            stubs: {
                // Assertions read the alert text out of GAlert's default slot, and the
                // `variant` prop as a plain attribute. VTU's auto-stub with
                // `renderStubDefaultSlot: true` crashes (runs out of memory) for this
                // component, so stub it explicitly instead.
                GAlert: { template: "<div><slot /></div>" },
                // VTU's auto-stub for bootstrap-vue's BLink (a legacy Vue.extend
                // component) crashes the same way once this component's full
                // composable graph is mounted around it -- stub it explicitly too.
                // `class` and `href` fall through onto the root element as usual.
                BLink: { template: "<a><slot /></a>" },
            },
        },
    });
    mountedWrappers.push(wrapper as unknown as VueWrapper);
    return wrapper;
};

describe("PersistentTaskProgressMonitorAlert.vue", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    afterEach(() => {
        mountedWrappers.splice(0).forEach((wrapper) => wrapper.unmount());
        localStorage.clear();
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
            isFinal: false,
        };
        seedMonitoringData(FAKE_MONITOR_REQUEST, existingMonitoringData);

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
            isFinal: true,
        };
        seedMonitoringData(FAKE_MONITOR_REQUEST, existingMonitoringData);

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
            isFinal: true,
        };
        seedMonitoringData(FAKE_MONITOR_REQUEST, existingMonitoringData);

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
            isFinal: true,
        };
        seedMonitoringData(monitoringRequest, existingMonitoringData);

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
            isFinal: true,
        };
        seedMonitoringData(FAKE_MONITOR_REQUEST, existingMonitoringData);

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
            isFinal: true,
        };
        seedMonitoringData(FAKE_MONITOR_REQUEST, existingMonitoringData);

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
