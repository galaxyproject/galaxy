import { describe, expect, it } from "vitest";

import {
    makeLibraryItem,
    makeLocalFileItem,
    makeRemoteFilesItem,
    makeUrlItem,
    withUploadState,
} from "@/composables/upload/testHelpers/uploadFixtures";

import { getUploadItemDisplayInfo } from "./uploadProgressUi";

describe("getUploadItemDisplayInfo sourceUrl", () => {
    it.each([
        ["paste-links", makeUrlItem({ url: "http://example.com/file.txt" }), "http://example.com/file.txt"],
        ["remote-files", makeRemoteFilesItem({ url: "ftp://server/file.txt" }), "ftp://server/file.txt"],
    ])("exposes the URL for %s uploads", (_mode, item, expectedUrl) => {
        expect(getUploadItemDisplayInfo(withUploadState(item)).sourceUrl).toBe(expectedUrl);
    });

    it("omits the URL for local-file uploads", () => {
        expect(getUploadItemDisplayInfo(withUploadState(makeLocalFileItem())).sourceUrl).toBeUndefined();
    });

    it("omits the API URL of data-library uploads", () => {
        const item = makeLibraryItem({ url: "/api/libraries/lib_1/datasets/ldda_1" });

        expect(getUploadItemDisplayInfo(withUploadState(item)).sourceUrl).toBeUndefined();
    });
});
