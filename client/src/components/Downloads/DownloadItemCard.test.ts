import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import { ref } from "vue";

import type { TaskMonitor } from "@/composables/genericTaskMonitor";
import type { MonitoringData, PersistentProgressTaskMonitorResult } from "@/composables/persistentProgressMonitor";

import DownloadItemCard from "./DownloadItemCard.vue";

const localVue = getLocalVue(true);

jest.mock("@/components/TagsMultiselect/StatelessTags.vue", () => ({
    name: "StatelessTags",
    render: () => null,
}));

jest.mock("@/composables/persistentProgressMonitor", () => ({
    usePersistentProgressTaskMonitor: (...args: unknown[]) => mockUsePersistentProgressTaskMonitor(...args),
}));

const fakeTaskId = "mock-task-id";
const requestStartDate = new Date();
const expirationTime = 1000 * 60 * 60; // 1 hour
const expirationDate = new Date(requestStartDate.getTime() + expirationTime);
const baseMonitoringData: MonitoringData = {
    taskId: fakeTaskId,
    taskType: "short_term_storage",
    request: {
        source: "test",
        action: "download",
        taskType: "short_term_storage",
        object: { id: "obj1", type: "history", name: "Test History" },
        description: "Test download description",
    },
    startedAt: requestStartDate,
    isFinal: false,
};

const defaultMonitor: TaskMonitor = {
    waitForTask: jest.fn(),
    isRunning: ref(false),
    isCompleted: ref(false),
    hasFailed: ref(false),
    failureReason: ref(""),
    requestHasFailed: ref(false),
    taskStatus: ref(""),
    expirationTime: expirationTime,
    isFinalState: jest.fn(),
    loadStatus: jest.fn(),
};

const defaultPersistentProgressTaskMonitor: PersistentProgressTaskMonitorResult = {
    ...defaultMonitor,
    hasMonitoringData: ref(true),
    monitoringData: ref(baseMonitoringData),
    expirationDate: ref(expirationDate),
    canExpire: ref(true),
    hasExpired: ref(false),
    storedTaskId: fakeTaskId,
    status: ref(""),
    start: jest.fn(),
    reset: jest.fn(),
    checkStatus: jest.fn(),
};

const mockUsePersistentProgressTaskMonitor = jest.fn().mockReturnValue(defaultPersistentProgressTaskMonitor);

const badgeIds = {
    inProgress: "in-progress",
    readyToDownload: "ready-to-download",
    expirationDate: "expiration-date",
    downloadRequestExpired: "download-request-expired",
    failedPreparation: "failed-preparation",
} as const;

const actionsIds = {
    goToObject: "go-to-object",
    download: "download",
    copyDownloadLink: "copy-download-link",
    remove: "remove",
} as const;

describe("DownloadItemCard.vue", () => {
    function mountDownloadItemCard(options: { monitoringData?: MonitoringData } = {}) {
        const monitoringData = options.monitoringData || baseMonitoringData;
        return mount(DownloadItemCard as object, {
            propsData: { monitoringData },
            localVue,
        });
    }

    afterEach(() => {
        jest.clearAllMocks();
    });

    it("always renders title and description and go to object action", async () => {
        const wrapper = mountDownloadItemCard();

        const actualTitle = wrapper.find("#g-card-title-text-mock-task-id").text();
        const actualDescription = wrapper.find("#g-card-description-mock-task-id").text();

        expect(actualTitle).toContain("Download History - Test History");
        expect(actualDescription).toContain("Test download description");

        expect(getActionButtonById(wrapper, actionsIds.goToObject).exists()).toBe(true);
    });

    it("shows 'running' state when isRunning", async () => {
        updateProgressMonitor({
            isRunning: ref(true),
        });
        const wrapper = mountDownloadItemCard();

        expect(getBadgeById(wrapper, badgeIds.inProgress).exists()).toBe(true);
        expect(getBadgeById(wrapper, badgeIds.expirationDate).exists()).toBe(true);
        expect(getBadgeById(wrapper, badgeIds.readyToDownload).exists()).toBe(false);

        expect(getActionButtonById(wrapper, actionsIds.goToObject).exists()).toBe(true);
        expect(getActionButtonById(wrapper, actionsIds.copyDownloadLink).exists()).toBe(false);
        expect(getActionButtonById(wrapper, actionsIds.download).exists()).toBe(false);
        expect(getActionButtonById(wrapper, actionsIds.remove).exists()).toBe(false);

        expect(wrapper.text()).toContain("Preparing History for download");
    });

    it("shows 'ready' state when is available to download", async () => {
        updateProgressMonitor({
            isRunning: ref(false),
            isCompleted: ref(true),
            hasExpired: ref(false),
        });
        const wrapper = mountDownloadItemCard();

        expect(getBadgeById(wrapper, badgeIds.inProgress).exists()).toBe(false);
        expect(getBadgeById(wrapper, badgeIds.expirationDate).exists()).toBe(true);
        expect(getBadgeById(wrapper, badgeIds.readyToDownload).exists()).toBe(true);

        expect(getActionButtonById(wrapper, actionsIds.goToObject).exists()).toBe(true);
        expect(getActionButtonById(wrapper, actionsIds.copyDownloadLink).exists()).toBe(true);
        expect(getActionButtonById(wrapper, actionsIds.download).exists()).toBe(true);
        expect(getActionButtonById(wrapper, actionsIds.remove).exists()).toBe(false);
    });

    it("shows 'expired' state when hasExpired", async () => {
        updateProgressMonitor({
            isRunning: ref(false),
            isCompleted: ref(true),
            hasExpired: ref(true),
        });
        const wrapper = mountDownloadItemCard();

        expect(getBadgeById(wrapper, badgeIds.inProgress).exists()).toBe(false);
        expect(getBadgeById(wrapper, badgeIds.expirationDate).exists()).toBe(false);
        expect(getBadgeById(wrapper, badgeIds.readyToDownload).exists()).toBe(false);

        expect(getActionButtonById(wrapper, actionsIds.goToObject).exists()).toBe(true);
        expect(getActionButtonById(wrapper, actionsIds.copyDownloadLink).exists()).toBe(false);
        expect(getActionButtonById(wrapper, actionsIds.download).exists()).toBe(false);
        expect(getActionButtonById(wrapper, actionsIds.remove).exists()).toBe(true);

        expect(wrapper.text()).toContain("The download request has expired and the result is no longer available");
    });

    it("shows 'failed' state when hasFailed", async () => {
        const expectedFailureReason = "Failed to prepare download";
        updateProgressMonitor({
            isRunning: ref(false),
            isCompleted: ref(false),
            hasFailed: ref(true),
            failureReason: ref(expectedFailureReason),
        });
        const wrapper = mountDownloadItemCard();

        expect(getBadgeById(wrapper, badgeIds.inProgress).exists()).toBe(false);
        expect(getBadgeById(wrapper, badgeIds.expirationDate).exists()).toBe(false);
        expect(getBadgeById(wrapper, badgeIds.readyToDownload).exists()).toBe(false);
        expect(getBadgeById(wrapper, badgeIds.failedPreparation).exists()).toBe(true);

        expect(getActionButtonById(wrapper, actionsIds.goToObject).exists()).toBe(true);
        expect(getActionButtonById(wrapper, actionsIds.copyDownloadLink).exists()).toBe(false);
        expect(getActionButtonById(wrapper, actionsIds.download).exists()).toBe(false);
        expect(getActionButtonById(wrapper, actionsIds.remove).exists()).toBe(true);

        expect(wrapper.text()).toContain(expectedFailureReason);
    });

    it("emits onGoTo when Go to object is clicked", async () => {
        const wrapper = mountDownloadItemCard();

        const goToButton = getActionButtonById(wrapper, actionsIds.goToObject);
        await goToButton.trigger("click");

        expect(wrapper.emitted("onGoTo")).toBeTruthy();
        expect(wrapper.emitted("onGoTo")?.[0][0]).toContain(baseMonitoringData.request.object.id);
    });

    it("emits onDownload when Download is clicked", async () => {
        updateProgressMonitor({
            isRunning: ref(false),
            isCompleted: ref(true),
            hasExpired: ref(false),
        });
        const wrapper = mountDownloadItemCard();

        const downloadButton = getActionButtonById(wrapper, actionsIds.download);
        await downloadButton.trigger("click");

        expect(wrapper.emitted("onDownload")).toBeTruthy();
        expect(wrapper.emitted("onDownload")?.[0][0]).toContain(fakeTaskId);
    });

    it("emits onDelete when Remove is clicked", async () => {
        updateProgressMonitor({
            isRunning: ref(false),
            isCompleted: ref(true),
            hasExpired: ref(true),
        });
        const wrapper = mountDownloadItemCard();

        const removeButton = getActionButtonById(wrapper, actionsIds.remove);
        await removeButton.trigger("click");

        expect(wrapper.emitted("onDelete")).toBeTruthy();
        expect(wrapper.emitted("onDelete")?.[0][0]).toBe(baseMonitoringData.request);
    });

    it("copies the download link to the clipboard when Copy Download Link is clicked", async () => {
        const writeText = jest.fn().mockResolvedValue(undefined);

        Object.assign(navigator, {
            clipboard: {
                writeText,
            },
        });
        updateProgressMonitor({
            isRunning: ref(false),
            isCompleted: ref(true),
            hasExpired: ref(false),
        });
        const wrapper = mountDownloadItemCard();

        const copyLinkButton = getActionButtonById(wrapper, actionsIds.copyDownloadLink);
        await copyLinkButton.trigger("click");

        expect(writeText).toHaveBeenCalledTimes(1);
        expect(writeText).toHaveBeenCalledWith(expect.stringContaining(fakeTaskId));
    });
});

function updateProgressMonitor(stateChanges: Partial<PersistentProgressTaskMonitorResult>) {
    mockUsePersistentProgressTaskMonitor.mockReturnValue({
        ...defaultPersistentProgressTaskMonitor,
        ...stateChanges,
    });
}

function getBadgeById(wrapper: ReturnType<typeof mount>, badgeId: string) {
    return wrapper.find(`#g-card-badge-${badgeId}-${fakeTaskId}`);
}

function getActionButtonById(wrapper: ReturnType<typeof mount>, actionId: string) {
    return wrapper.find(`#g-card-action-${actionId}-${fakeTaskId}`);
}
