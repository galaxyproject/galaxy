import { createTestingPinia } from "@pinia/testing";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useDownloadTracker } from "./downloadTracker";
import { useHashedUserId } from "./hashedUserIdFromUserStore";
import { getPersistentKey, type MonitoringData, storeProgressData } from "./persistentProgressMonitor";

// The list is shared with other tabs through local storage, so use the real storage here.
vi.unmock("@/composables/userLocalStorage");

function exportOf(id: string, type: "history" | "dataset"): MonitoringData {
    return {
        taskId: `request-${id}`,
        taskType: "short_term_storage",
        request: {
            source: "test",
            taskType: "short_term_storage",
            action: "export",
            object: { id, type },
        },
        startedAt: new Date(),
        isFinal: false,
    };
}

describe("useDownloadTracker", () => {
    beforeEach(() => {
        localStorage.clear();
        setActivePinia(createTestingPinia({ createSpy: vi.fn, stubActions: false }));
    });

    it("keeps the downloads tracked from different places on the page", async () => {
        const historyExport = useDownloadTracker();
        const datasetExport = useDownloadTracker();

        historyExport.trackDownloadRequestWithData(exportOf("h1", "history"));
        datasetExport.trackDownloadRequestWithData(exportOf("d1", "dataset"));
        // The records reach local storage on the next tick.
        await flushPromises();

        const tracked = useDownloadTracker().downloadMonitoringData.value.map((data) => data.request.object.id);
        expect(tracked.sort()).toEqual(["d1", "h1"]);
    });

    it("picks up exports tracked in another tab and keeps them when tracking one here", async () => {
        setActivePinia(
            createTestingPinia({
                createSpy: vi.fn,
                stubActions: false,
                initialState: { userStore: { currentUser: { id: "u1" } } },
            }),
        );
        const tracker = useDownloadTracker();
        const { hashedUserId } = useHashedUserId();
        await vi.waitFor(() => expect(hashedUserId.value).toBeTruthy());
        const listKey = `download-tracker-${hashedUserId.value}`;

        // Another tab stores its export and writes the list, which this tab hears about as a storage event.
        const otherTabExport = exportOf("h2", "history");
        storeProgressData(otherTabExport);
        await flushPromises();
        const otherTabList = JSON.stringify([getPersistentKey(otherTabExport.request)]);
        localStorage.setItem(listKey, otherTabList);
        window.dispatchEvent(new StorageEvent("storage", { key: listKey, newValue: otherTabList }));
        expect(tracker.downloadMonitoringData.value.map((data) => data.request.object.id)).toEqual(["h2"]);

        tracker.trackDownloadRequestWithData(exportOf("d1", "dataset"));
        await flushPromises();
        expect(JSON.parse(localStorage.getItem(listKey) ?? "[]")).toHaveLength(2);
    });
});
