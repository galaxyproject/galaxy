import { describe, expect, it } from "vitest";

import { makeLocalFileItem, makeRemoteFilesItem, makeUrlItem } from "@/composables/upload/testHelpers/uploadFixtures";
import type { NewUploadItem } from "@/composables/upload/uploadItemTypes";

import { getFileStatusMessage, getUploadItemDisplayInfo } from "./uploadProgressUi";

function withState<T extends NewUploadItem>(item: T) {
    return {
        ...item,
        id: "upload-1",
        status: "queued" as const,
        progress: 0,
        createdAt: 0,
        datasetIds: [] as string[],
    };
}

describe("getUploadItemDisplayInfo sourceUrl", () => {
    it.each([
        ["paste-links", withState(makeUrlItem())],
        ["remote-files", withState(makeRemoteFilesItem())],
    ])("exposes the URL for %s uploads", (_, item) => {
        expect(getUploadItemDisplayInfo(item).sourceUrl).toBe("url" in item ? item.url : undefined);
    });

    it("omits the URL for local-file uploads", () => {
        expect(getUploadItemDisplayInfo(withState(makeLocalFileItem())).sourceUrl).toBeUndefined();
    });
});

describe("getFileStatusMessage for imports from another Galaxy", () => {
    const linkItem: NewUploadItem = {
        uploadMode: "galaxy-link",
        name: "reads.bed",
        sourceHost: "usegalaxy.eu",
        size: 0,
        targetHistoryId: "hist_1",
        dbkey: "?",
        extension: "auto",
        spaceToTab: false,
        toPosixLines: false,
        autoDecompress: false,
        deferred: false,
    };

    it.each([
        ["queued", "Starting the import from usegalaxy.eu"],
        ["processing", "Importing from usegalaxy.eu"],
        ["completed", "Imported from usegalaxy.eu"],
    ] as const)("says what a %s import is doing", (status, message) => {
        expect(getFileStatusMessage({ ...withState(linkItem), status })).toBe(message);
    });
});
