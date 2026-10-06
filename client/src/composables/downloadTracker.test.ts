import { createTestingPinia } from "@pinia/testing";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useDownloadTracker } from "./downloadTracker";
import type { MonitoringData } from "./persistentProgressMonitor";

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
});
