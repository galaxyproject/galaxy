import { getFakeMonitoringData } from "@tests/test-data/monitoring";
import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { PersistentProgressTaskMonitorResult } from "@/composables/persistentProgressMonitor";

import DownloadItemCard from "./DownloadItemCard.vue";

enableAutoUnmount(afterEach);

vi.mock("@/components/TagsMultiselect/StatelessTags.vue", () => ({
    default: {
        name: "StatelessTags",
        render: () => null,
    },
}));

vi.mock("@/composables/persistentProgressMonitor", () => ({
    usePersistentProgressTaskMonitor: (...args: unknown[]) => mockUsePersistentProgressTaskMonitor(...args),
}));

const fakeTaskId = "mock-task-id";
const mockUsePersistentProgressTaskMonitor = vi.fn();

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
    function mountDownloadItemCard(state: Partial<PersistentProgressTaskMonitorResult> = {}) {
        const monitoringData = getFakeMonitoringData(
            {
                source: "test",
                action: "download",
                taskType: "short_term_storage",
                object: { id: "obj1", type: "history", name: "Test History" },
                description: "Test download description",
            },
            { taskId: fakeTaskId, startedAt: new Date("2024-01-01T00:00:00.000Z") },
        );
        const monitor: PersistentProgressTaskMonitorResult = {
            isRunning: ref(false),
            isCompleted: ref(false),
            hasFailed: ref(false),
            failureReason: ref(""),
            requestHasFailed: ref(false),
            hasMonitoringData: ref(true),
            monitoringData: ref(monitoringData),
            expirationDate: ref(new Date("2024-01-01T01:00:00.000Z")),
            canExpire: ref(true),
            hasExpired: ref(false),
            storedTaskId: fakeTaskId,
            status: ref(""),
            start: vi.fn(),
            stop: vi.fn(),
            reset: vi.fn(),
            checkStatus: vi.fn(),
            ...state,
        };
        mockUsePersistentProgressTaskMonitor.mockReturnValue(monitor);
        return mount(DownloadItemCard, {
            props: { monitoringData },
            global: getLocalVue(true),
        });
    }

    afterEach(() => {
        mockUsePersistentProgressTaskMonitor.mockReset();
        vi.restoreAllMocks();
    });

    it("renders the history title, description, and navigation action", () => {
        const wrapper = mountDownloadItemCard();

        const actualTitle = wrapper.find("#g-card-title-text-mock-task-id").text();
        const actualDescription = wrapper.find("#g-card-description-mock-task-id").text();

        expect(actualTitle).toContain("Download History - Test History");
        expect(actualDescription).toContain("Test download description");

        expect(getActionButtonById(wrapper, actionsIds.goToObject).exists()).toBe(true);
    });

    it("shows preparation progress while the download is running", () => {
        const wrapper = mountDownloadItemCard({
            isRunning: ref(true),
        });

        expect(getBadgeById(wrapper, badgeIds.inProgress).exists()).toBe(true);
        expect(getBadgeById(wrapper, badgeIds.expirationDate).exists()).toBe(true);
        expect(getBadgeById(wrapper, badgeIds.readyToDownload).exists()).toBe(false);

        expect(getActionButtonById(wrapper, actionsIds.goToObject).exists()).toBe(true);
        expect(getActionButtonById(wrapper, actionsIds.copyDownloadLink).exists()).toBe(false);
        expect(getActionButtonById(wrapper, actionsIds.download).exists()).toBe(false);
        expect(getActionButtonById(wrapper, actionsIds.remove).exists()).toBe(false);

        expect(wrapper.text()).toContain("Preparing History for download");
    });

    it("offers download and copy actions after preparation completes", () => {
        const wrapper = mountDownloadItemCard({
            isRunning: ref(false),
            isCompleted: ref(true),
            hasExpired: ref(false),
        });

        expect(getBadgeById(wrapper, badgeIds.inProgress).exists()).toBe(false);
        expect(getBadgeById(wrapper, badgeIds.expirationDate).exists()).toBe(true);
        expect(getBadgeById(wrapper, badgeIds.readyToDownload).exists()).toBe(true);

        expect(getActionButtonById(wrapper, actionsIds.goToObject).exists()).toBe(true);
        expect(getActionButtonById(wrapper, actionsIds.copyDownloadLink).exists()).toBe(true);
        expect(getActionButtonById(wrapper, actionsIds.download).exists()).toBe(true);
        expect(getActionButtonById(wrapper, actionsIds.remove).exists()).toBe(false);
    });

    it("offers removal instead of download actions after expiration", () => {
        const wrapper = mountDownloadItemCard({
            isRunning: ref(false),
            isCompleted: ref(true),
            hasExpired: ref(true),
        });

        expect(getBadgeById(wrapper, badgeIds.inProgress).exists()).toBe(false);
        expect(getBadgeById(wrapper, badgeIds.expirationDate).exists()).toBe(false);
        expect(getBadgeById(wrapper, badgeIds.readyToDownload).exists()).toBe(false);

        expect(getActionButtonById(wrapper, actionsIds.goToObject).exists()).toBe(true);
        expect(getActionButtonById(wrapper, actionsIds.copyDownloadLink).exists()).toBe(false);
        expect(getActionButtonById(wrapper, actionsIds.download).exists()).toBe(false);
        expect(getActionButtonById(wrapper, actionsIds.remove).exists()).toBe(true);

        expect(wrapper.text()).toContain("The download request has expired and the result is no longer available");
    });

    it("shows the failure reason and offers removal when preparation fails", () => {
        const expectedFailureReason = "Failed to prepare download";
        const wrapper = mountDownloadItemCard({
            isRunning: ref(false),
            isCompleted: ref(false),
            hasFailed: ref(true),
            failureReason: ref(expectedFailureReason),
        });

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
        expect(emittedArg(wrapper, "onGoTo")).toBe("/histories/view?id=obj1");
    });

    it("emits onDownload when Download is clicked", async () => {
        const wrapper = mountDownloadItemCard({
            isRunning: ref(false),
            isCompleted: ref(true),
            hasExpired: ref(false),
        });

        const downloadButton = getActionButtonById(wrapper, actionsIds.download);
        await downloadButton.trigger("click");

        expect(wrapper.emitted("onDownload")).toBeTruthy();
        expect(emittedArg(wrapper, "onDownload")).toContain(fakeTaskId);
    });

    it("emits onDelete when Remove is clicked", async () => {
        const wrapper = mountDownloadItemCard({
            isRunning: ref(false),
            isCompleted: ref(true),
            hasExpired: ref(true),
        });

        const removeButton = getActionButtonById(wrapper, actionsIds.remove);
        await removeButton.trigger("click");

        expect(wrapper.emitted("onDelete")).toBeTruthy();
        expect(emittedArg(wrapper, "onDelete")).toEqual(wrapper.props("monitoringData").request);
    });

    it("copies the download link to the clipboard when Copy Download Link is clicked", async () => {
        const writeText = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);
        const wrapper = mountDownloadItemCard({
            isRunning: ref(false),
            isCompleted: ref(true),
            hasExpired: ref(false),
        });

        const copyLinkButton = getActionButtonById(wrapper, actionsIds.copyDownloadLink);
        await copyLinkButton.trigger("click");

        expect(writeText).toHaveBeenCalledTimes(1);
        expect(writeText).toHaveBeenCalledWith(expect.stringContaining(fakeTaskId));
    });
});

function getBadgeById(wrapper: ReturnType<typeof mount>, badgeId: string) {
    return wrapper.find(`#g-card-badge-${badgeId}-${fakeTaskId}`);
}

function getActionButtonById(wrapper: ReturnType<typeof mount>, actionId: string) {
    return wrapper.find(`#g-card-action-${actionId}-${fakeTaskId}`);
}
