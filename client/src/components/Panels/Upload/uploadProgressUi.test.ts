import { describe, expect, it } from "vitest";

import { makeLocalFileItem, makeRemoteFilesItem, makeUrlItem } from "@/composables/upload/testHelpers/uploadFixtures";
import type { NewUploadItem } from "@/composables/upload/uploadItemTypes";

import { getUploadItemDisplayInfo } from "./uploadProgressUi";

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
