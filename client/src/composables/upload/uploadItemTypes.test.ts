import { describe, expect, it } from "vitest";

import {
    makeLibraryItem,
    makeLocalFileItem,
    makePastedItem,
    makeRemoteFilesItem,
    makeUrlItem,
} from "@/composables/upload/testHelpers/uploadFixtures";
import type { NewUploadItem } from "@/composables/upload/uploadItemTypes";

import { validateUploadItem } from "./uploadItemTypes";

describe("validateUploadItem", () => {
    it.each([
        ["paste-content", makePastedItem()],
        ["paste-links", makeUrlItem()],
        ["remote-files", makeRemoteFilesItem()],
        ["data-library", makeLibraryItem()],
        ["local-file", makeLocalFileItem()],
    ] as [string, NewUploadItem][])("accepts a valid %s item", (_mode, item) => {
        expect(validateUploadItem(item)).toBeUndefined();
    });

    it("rejects paste-content with empty content", () => {
        expect(validateUploadItem(makePastedItem({ content: "   " }))).toMatch(/No content provided/);
    });

    it("rejects paste-links with missing URL", () => {
        expect(validateUploadItem(makeUrlItem({ url: "" }))).toMatch(/No URL provided/);
    });

    it("rejects remote-files with missing URL", () => {
        expect(validateUploadItem(makeRemoteFilesItem({ url: "  " }))).toMatch(/No URL provided/);
    });

    it("rejects data-library with no lddaId", () => {
        expect(validateUploadItem(makeLibraryItem({ lddaId: "" }))).toMatch(/No library dataset ID/);
    });

    it("rejects local-file with no file data", () => {
        const item: NewUploadItem = {
            uploadMode: "local-file",
            name: "missing.txt",
            size: 0,
            targetHistoryId: "hist_1",
            dbkey: "?",
            extension: "auto",
            spaceToTab: false,
            toPosixLines: false,
            deferred: false,
        };
        expect(validateUploadItem(item)).toMatch(/No file selected/);
    });

    it("rejects local-file with an empty file", () => {
        const emptyFile = new File([], "empty.txt");
        const item: NewUploadItem = {
            uploadMode: "local-file",
            name: "empty.txt",
            size: 0,
            targetHistoryId: "hist_1",
            dbkey: "?",
            extension: "auto",
            spaceToTab: false,
            toPosixLines: false,
            deferred: false,
            fileData: emptyFile,
        };
        expect(validateUploadItem(item)).toMatch(/is empty/);
    });

    it("rejects an unknown upload mode", () => {
        const item = { ...makePastedItem(), uploadMode: "unknown-mode" } as unknown as NewUploadItem;
        expect(validateUploadItem(item)).toMatch(/Unknown upload mode/);
    });
});
