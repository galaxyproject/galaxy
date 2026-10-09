import { beforeEach, describe, expect, it, test, vi } from "vitest";

import { GALAXY_RESPONSE_HEADERS, HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { CompositeDataElement, HdasUploadTarget, HdcaUploadTarget, NestedElement } from "@/api/tools";

import { createTusUpload } from "./tusUpload";
import {
    type ApiUploadItem,
    buildCollectionUploadPayload,
    buildLegacyPayload,
    buildUploadPayload,
    cleanUrlFilename,
    createFileUploadItem,
    createPastedUploadItem,
    createUrlUploadItem,
    fetchDatasets,
    isGalaxyFileName,
    type LegacyUploadItem,
    parseContentToUploadItems,
    stripGalaxyFilePrefix,
    submitUpload,
    uploadItemDefaults,
} from "./upload";

vi.mock("./tusUpload", () => ({
    createTusUpload: vi.fn(),
    NamedBlob: class {},
}));

vi.mock("@/onload/loadConfig", () => ({
    getAppRoot: () => "/",
}));

function createMockFile(name: string, content: string = "test content"): File {
    return new File([content], name, { lastModified: 0 });
}

/** Common element fields shared by all upload element types in tests. */
const commonElementDefaults = {
    dbkey: "?",
    ext: "auto",
    space_to_tab: false,
    to_posix_lines: false,
    auto_decompress: false,
    deferred: false,
} as const;

// ============================================================================
// Payload Building Tests
// ============================================================================

describe("buildLegacyPayload", () => {
    it("rejects an empty list", () => {
        expect(() => buildLegacyPayload([], "historyId")).toThrow("No upload items provided.");
    });

    it("rejects a new upload without content", () => {
        expect(() =>
            buildLegacyPayload([{ fileMode: "new", fileName: "", fileSize: 0 } as LegacyUploadItem], "historyId"),
        ).toThrow("Content not available.");
    });

    test("unknown file mode returns null and triggers validation error", () => {
        // An unknown fileMode causes fromLegacyUploadItem to return null,
        // which then triggers "No valid upload items after conversion" error
        expect(() =>
            buildLegacyPayload(
                [
                    {
                        fileMode: "unknown",
                        fileName: "test",
                        fileSize: 1,
                    } as LegacyUploadItem,
                ],
                "historyId",
            ),
        ).toThrow("No valid upload items after conversion.");
    });

    it.each([
        { name: "empty", content: "" },
        { name: "whitespace-only", content: "   " },
    ])("rejects $name pasted content", ({ content }) => {
        expect(() =>
            buildLegacyPayload(
                [{ fileMode: "new", fileName: "test", fileContent: content, fileSize: 0 } as LegacyUploadItem],
                "historyId",
            ),
        ).toThrow("Content not available.");
    });

    test("invalid URL validation", () => {
        expect(() =>
            buildLegacyPayload(
                [
                    {
                        dbKey: "dbKey",
                        deferred: false,
                        extension: "extension",
                        fileName: "3",
                        fileContent: " http://test.me.0 \n xyz://test.me.1",
                        fileMode: "new",
                        spaceToTab: false,
                        toPosixLines: false,
                        fileSize: 1,
                    } as LegacyUploadItem,
                ],
                "historyId",
            ),
        ).toThrow("Invalid URL: xyz://test.me.1");
    });

    test("pasted content payload", () => {
        const result = buildLegacyPayload(
            [
                {
                    fileContent: " fileContent ",
                    fileMode: "new",
                    fileName: "1",
                    fileSize: 1,
                } as LegacyUploadItem,
            ],
            "historyId",
        );

        expect(result.history_id).toBe("historyId");
        expect(result.auto_decompress).toBe(true);
        expect(result.files).toEqual([]);
        expect(result.targets).toHaveLength(1);

        const target = result.targets[0]!;
        expect(target.destination).toEqual({ type: "hdas" });
        expect(target.elements).toHaveLength(1);

        expect(target.elements![0]).toMatchObject({ src: "pasted", paste_content: " fileContent " });
    });

    test("local file payload", () => {
        const mockFile = createMockFile("test.txt");
        const result = buildLegacyPayload(
            [
                {
                    dbKey: "hg38",
                    extension: "txt",
                    fileData: mockFile,
                    fileMode: "local",
                    fileName: "test.txt",
                    fileSize: 100,
                    spaceToTab: true,
                    toPosixLines: true,
                } as LegacyUploadItem,
            ],
            "historyId",
        );

        expect(result.files).toHaveLength(1);
        expect(result.files[0]).toBe(mockFile);

        const target = result.targets[0]!;
        expect(target.elements![0]).toMatchObject({ src: "files", dbkey: "hg38", ext: "txt" });
    });

    test("URL payload", () => {
        const result = buildLegacyPayload(
            [
                {
                    dbKey: "hg38",
                    deferred: true,
                    extension: "bed",
                    fileName: "remote.bed",
                    fileUri: "http://example.com/data.bed",
                    fileMode: "url",
                    fileSize: 0,
                } as LegacyUploadItem,
            ],
            "historyId",
        );

        expect(result.files).toEqual([]);

        const target = result.targets[0]!;
        expect(target.elements![0]).toMatchObject({ src: "url", url: "http://example.com/data.bed", deferred: true });
    });

    test("multiple URLs from new mode", () => {
        const result = buildLegacyPayload(
            [
                {
                    fileMode: "new",
                    fileName: "urls",
                    fileContent: "http://example.com/1.txt\nhttp://example.com/2.txt",
                    fileSize: 1,
                } as LegacyUploadItem,
            ],
            "historyId",
        );

        const target = result.targets[0]!;
        expect(target.elements).toHaveLength(2);

        expect(target.elements![0]).toMatchObject({ src: "url", url: "http://example.com/1.txt" });
        expect(target.elements![1]).toMatchObject({ src: "url", url: "http://example.com/2.txt" });
    });

    test("Galaxy filename stripping", () => {
        const mockFile = createMockFile("Galaxy5-[PreviousFile].bed");
        const result = buildLegacyPayload(
            [
                {
                    fileData: mockFile,
                    fileMode: "local",
                    fileName: "Galaxy5-[PreviousFile].bed",
                    fileSize: 100,
                } as LegacyUploadItem,
            ],
            "historyId",
        );

        const target = result.targets[0]!;
        expect(target.elements![0]).toMatchObject({ name: "PreviousFile" });
    });

    test("composite payload", () => {
        const mockFile1 = createMockFile("file1.txt");
        const mockFile2 = createMockFile("file2.txt");

        const result = buildLegacyPayload(
            [
                {
                    fileContent: "fileContent",
                    fileMode: "new",
                    fileName: "1",
                    fileSize: 1,
                } as LegacyUploadItem,
                {
                    dbKey: "hg38",
                    extension: "txt",
                    fileData: mockFile1,
                    fileMode: "local",
                    fileName: "2",
                    fileSize: 100,
                } as LegacyUploadItem,
                {
                    dbKey: "hg38",
                    extension: "bed",
                    fileData: mockFile2,
                    fileMode: "local",
                    fileName: "Galaxy2-[PreviousFile].bed",
                    fileSize: 100,
                } as LegacyUploadItem,
            ],
            "historyId",
            true,
        );

        expect(result.files).toHaveLength(2);

        const target = result.targets[0] as HdasUploadTarget;
        // For composite uploads, elements are wrapped in a composite structure
        expect(target.elements).toBeDefined();
        expect(target.elements).toHaveLength(1);

        const compositeElement = target.elements![0]! as CompositeDataElement;
        expect(compositeElement.src).toBe("composite");
        // 3 elements: 1 pasted + 2 local files
        expect(compositeElement.composite.elements).toHaveLength(3);
    });
});

describe("isGalaxyFileName", () => {
    it.each([
        { name: "numbered Galaxy file", filename: "Galaxy5-[MyFile].bed", expected: true },
        { name: "Galaxy file containing spaces", filename: "Galaxy123-[Some File Name].txt", expected: true },
        { name: "ordinary filename", filename: "myfile.txt", expected: false },
        { name: "Galaxy filename without a number", filename: "Galaxy-[NoNumber].txt", expected: false },
        { name: "null filename", filename: null, expected: false },
        { name: "undefined filename", filename: undefined, expected: false },
    ])("classifies $name as Galaxy format: $expected", ({ filename, expected }) => {
        expect(isGalaxyFileName(filename)).toBe(expected);
    });
});

describe("stripGalaxyFilePrefix", () => {
    it.each([
        { name: "numbered Galaxy file", filename: "Galaxy5-[MyFile].bed", expected: "MyFile" },
        { name: "Galaxy file containing spaces", filename: "Galaxy123-[Some File].txt", expected: "Some File" },
        { name: "ordinary filename", filename: "myfile.txt", expected: "myfile.txt" },
    ])("extracts the name from $name", ({ filename, expected }) => {
        expect(stripGalaxyFilePrefix(filename)).toBe(expected);
    });
});

describe("cleanUrlFilename", () => {
    it.each([
        {
            name: "URL path and query",
            filename: "http://example.com/path/to/file.pdf?download=1",
            expected: "file.pdf",
        },
        { name: "encoded space", filename: "file%20name.pdf", expected: "file name.pdf" },
        {
            name: "multiple encoded spaces",
            filename: "Readme%20Statistical%20Downscaling.pdf",
            expected: "Readme Statistical Downscaling.pdf",
        },
        { name: "encoded punctuation", filename: "special%26chars%3D.txt", expected: "special&chars=.txt" },
        {
            name: "encoded spaces and download query",
            filename: "Readme%20Statistical%20Downscaling.pdf?download=1",
            expected: "Readme Statistical Downscaling.pdf",
        },
        { name: "encoded space and token query", filename: "my%20file.txt?token=abc123", expected: "my file.txt" },
        { name: "ordinary filename", filename: "normal.txt", expected: "normal.txt" },
        { name: "filename with dashes", filename: "file-with-dashes.bed", expected: "file-with-dashes.bed" },
        { name: "invalid percent-encoding hex", filename: "file%ZZname.txt", expected: "file%ZZname.txt" },
        { name: "incomplete percent encoding", filename: "file%2.txt", expected: "file%2.txt" },
        { name: "empty query string", filename: "file.txt?", expected: "file.txt" },
        { name: "empty filename", filename: "", expected: null },
        { name: "URL with no filename", filename: "http://example.com/", expected: null },
    ])("cleans $name", ({ filename, expected }) => {
        expect(cleanUrlFilename(filename)).toBe(expected);
    });
});

describe("createFileUploadItem", () => {
    test("creates file upload item with defaults", () => {
        const mockFile = createMockFile("test.txt", "content");
        const item = createFileUploadItem(mockFile, "historyId");

        expect(item.src).toBe("files");
        expect(item.fileData).toBe(mockFile);
        expect(item.historyId).toBe("historyId");
        expect(item.name).toBe("test.txt");
        expect(item.size).toBe(mockFile.size);
        expect(item.dbkey).toBe(uploadItemDefaults.dbkey);
        expect(item.ext).toBe(uploadItemDefaults.ext);
        expect(item.space_to_tab).toBe(uploadItemDefaults.space_to_tab);
        expect(item.to_posix_lines).toBe(uploadItemDefaults.to_posix_lines);
        expect(item.deferred).toBe(uploadItemDefaults.deferred);
        expect(item.auto_decompress).toBe(uploadItemDefaults.auto_decompress);
    });

    test("creates file upload item with custom options", () => {
        const mockFile = createMockFile("test.txt");
        const item = createFileUploadItem(mockFile, "historyId", {
            name: "custom.bed",
            dbkey: "hg38",
            ext: "bed",
            space_to_tab: true,
            to_posix_lines: false,
            deferred: true,
            auto_decompress: false,
        });

        expect(item.name).toBe("custom.bed");
        expect(item.dbkey).toBe("hg38");
        expect(item.ext).toBe("bed");
        expect(item.space_to_tab).toBe(true);
        expect(item.to_posix_lines).toBe(false);
        expect(item.deferred).toBe(true);
        expect(item.auto_decompress).toBe(false);
    });
});

describe("createPastedUploadItem", () => {
    test("creates pasted upload item with defaults", () => {
        const item = createPastedUploadItem("pasted content", "historyId");

        expect(item.src).toBe("pasted");
        expect(item.paste_content).toBe("pasted content");
        expect(item.historyId).toBe("historyId");
        expect(item.name).toBe("New File");
        expect(item.size).toBe("pasted content".length);
        expect(item.dbkey).toBe(uploadItemDefaults.dbkey);
        expect(item.ext).toBe(uploadItemDefaults.ext);
        expect(item.auto_decompress).toBe(uploadItemDefaults.auto_decompress);
    });

    test("creates pasted upload item with custom name", () => {
        const item = createPastedUploadItem("content", "historyId", { name: "MyPaste.txt" });
        expect(item.name).toBe("MyPaste.txt");
    });

    test("creates pasted upload item with custom auto_decompress", () => {
        const item = createPastedUploadItem("content", "historyId", { auto_decompress: false });
        expect(item.auto_decompress).toBe(false);
    });
});

describe("createUrlUploadItem", () => {
    test("creates URL upload item with defaults", () => {
        const item = createUrlUploadItem("http://example.com/data.bed", "historyId");

        expect(item.src).toBe("url");
        expect(item.url).toBe("http://example.com/data.bed");
        expect(item.historyId).toBe("historyId");
        expect(item.name).toBe("data.bed"); // extracted from URL
        expect(item.size).toBe(0);
        expect(item.dbkey).toBe(uploadItemDefaults.dbkey);
        expect(item.deferred).toBe(uploadItemDefaults.deferred);
        expect(item.auto_decompress).toBe(uploadItemDefaults.auto_decompress);
    });

    test("extracts filename from URL path", () => {
        const item = createUrlUploadItem("http://example.com/path/to/file.txt?query=param", "historyId");
        expect(item.name).toBe("file.txt");
    });

    test("creates URL upload item with custom options", () => {
        const item = createUrlUploadItem("http://example.com/data.bed", "historyId", {
            name: "custom-name.bed",
            deferred: true,
            dbkey: "hg38",
            auto_decompress: false,
        });

        expect(item.name).toBe("custom-name.bed");
        expect(item.deferred).toBe(true);
        expect(item.dbkey).toBe("hg38");
        expect(item.auto_decompress).toBe(false);
    });

    test("trims surrounding whitespace from URL", () => {
        const item = createUrlUploadItem("  http://example.com/data.bed\n", "historyId");

        expect(item.url).toBe("http://example.com/data.bed");
        expect(item.name).toBe("data.bed");
    });
});

describe("parseContentToUploadItems", () => {
    it.each([
        { name: "empty", content: "" },
        { name: "whitespace-only", content: "   " },
    ])("rejects $name content", ({ content }) => {
        expect(() => parseContentToUploadItems(content, "historyId")).toThrow("Content not available.");
    });

    test("parses plain text as pasted content", () => {
        const items = parseContentToUploadItems("some plain text\nwith multiple lines", "historyId");

        expect(items).toHaveLength(1);
        expect(items[0]).toMatchObject({ src: "pasted", paste_content: "some plain text\nwith multiple lines" });
    });

    test("parses URLs when first line is a URL", () => {
        const items = parseContentToUploadItems(
            "http://example.com/file1.txt\nhttp://example.com/file2.txt",
            "historyId",
        );

        expect(items).toHaveLength(2);
        expect(items).toMatchObject([
            { src: "url", url: "http://example.com/file1.txt" },
            { src: "url", url: "http://example.com/file2.txt" },
        ]);
    });

    test("throws on invalid URL in URL list", () => {
        expect(() => parseContentToUploadItems("http://example.com/valid.txt\ninvalid-not-a-url", "historyId")).toThrow(
            "Invalid URL: invalid-not-a-url",
        );
    });

    test("throws on network URL with empty DNS labels", () => {
        expect(() => parseContentToUploadItems("https://.../SRR1957099.fastq.gz", "historyId")).toThrow(
            "Invalid URL: https://.../SRR1957099.fastq.gz",
        );
    });

    test("accepts Galaxy file-source URIs", () => {
        const content = "gxfiles://myftp/file.txt\ndrs://example.org/abc\nzenodo://record/123";
        const items = parseContentToUploadItems(content, "historyId");

        expect(items).toHaveLength(3);
        expect(items[0]).toMatchObject({ url: "gxfiles://myftp/file.txt" });
        expect(items[1]).toMatchObject({ url: "drs://example.org/abc" });
        expect(items[2]).toMatchObject({ url: "zenodo://record/123" });
    });

    test("handles whitespace around URLs", () => {
        const items = parseContentToUploadItems("  http://example.com/file.txt  \n  ", "historyId");

        expect(items).toHaveLength(1);
        expect(items[0]).toMatchObject({ url: "http://example.com/file.txt" });
    });
});

describe("buildUploadPayload", () => {
    test("throws on empty items", () => {
        expect(() => buildUploadPayload([])).toThrow("No upload items provided.");
    });

    test("throws on mixed history IDs", () => {
        const file1 = createMockFile("file1.txt");
        const file2 = createMockFile("file2.txt");
        const items: ApiUploadItem[] = [
            createFileUploadItem(file1, "history1"),
            createFileUploadItem(file2, "history2"),
        ];

        expect(() => buildUploadPayload(items)).toThrow("All upload items must target the same history.");
    });

    test("builds payload with file upload items", () => {
        const mockFile = createMockFile("test.txt");
        const items: ApiUploadItem[] = [createFileUploadItem(mockFile, "historyId")];

        const result = buildUploadPayload(items);

        expect(result.history_id).toBe("historyId");
        expect(result.auto_decompress).toBe(true);
        expect(result.files).toHaveLength(1);
        expect(result.files[0]).toBe(mockFile);
        expect(result.targets).toHaveLength(1);
        expect(result.targets[0]!.destination).toEqual({ type: "hdas" });
        expect(result.targets[0]!.elements).toHaveLength(1);

        expect(result.targets[0]!.elements![0]).toMatchObject({ auto_decompress: true });
    });

    test("builds payload preserving item auto_decompress setting", () => {
        const items: ApiUploadItem[] = [
            createPastedUploadItem("content", "historyId", {
                name: "manual.txt",
                auto_decompress: false,
            }),
        ];

        const result = buildUploadPayload(items);
        expect(result.targets[0]!.elements![0]).toMatchObject({ auto_decompress: false });
    });

    test("builds composite payload", () => {
        const file1 = createMockFile("file1.txt");
        const file2 = createMockFile("file2.txt");
        const items: ApiUploadItem[] = [
            createFileUploadItem(file1, "historyId"),
            createFileUploadItem(file2, "historyId"),
        ];

        const result = buildUploadPayload(items, { composite: true });

        expect(result.files).toHaveLength(2);
        expect(result.targets[0]!.elements).toHaveLength(1);

        const compositeElement = result.targets[0]!.elements![0] as CompositeDataElement;
        expect(compositeElement.src).toBe("composite");
        expect(compositeElement.composite.elements).toHaveLength(2);
    });

    test("validates empty file data", () => {
        const emptyFile = new File([], "empty.txt");
        const items: ApiUploadItem[] = [createFileUploadItem(emptyFile, "historyId")];

        expect(() => buildUploadPayload(items)).toThrow("File data is empty for upload item: empty.txt");
    });

    test("validates empty pasted content", () => {
        const items: ApiUploadItem[] = [createPastedUploadItem("", "historyId", { name: "empty" })];

        expect(() => buildUploadPayload(items)).toThrow("No content for pasted upload item: empty");
    });

    test("validates invalid URL", () => {
        const items: ApiUploadItem[] = [createUrlUploadItem("not-a-valid-url", "historyId")];

        expect(() => buildUploadPayload(items)).toThrow("Invalid URL: not-a-valid-url");
    });

    test("rejects network URL with empty DNS labels", () => {
        const items: ApiUploadItem[] = [createUrlUploadItem("https://.../SRR1957099.fastq.gz", "historyId")];

        expect(() => buildUploadPayload(items)).toThrow("Invalid URL: https://.../SRR1957099.fastq.gz");
    });
});

// ============================================================================
// Collection Upload Payload Building Tests
// ============================================================================

describe("buildCollectionUploadPayload", () => {
    test("throws on empty items", () => {
        expect(() => buildCollectionUploadPayload([], { collectionName: "test", collectionType: "list" })).toThrow(
            "No upload items provided.",
        );
    });

    test("throws on mixed history IDs", () => {
        const items: ApiUploadItem[] = [
            createUrlUploadItem("http://example.com/1.txt", "history1"),
            createUrlUploadItem("http://example.com/2.txt", "history2"),
        ];

        expect(() => buildCollectionUploadPayload(items, { collectionName: "test", collectionType: "list" })).toThrow(
            "All upload items must target the same history.",
        );
    });

    test("builds list collection payload with URL items", () => {
        const items: ApiUploadItem[] = [
            createUrlUploadItem("http://example.com/1.txt", "historyId"),
            createUrlUploadItem("http://example.com/2.txt", "historyId"),
        ];

        const result = buildCollectionUploadPayload(items, {
            collectionName: "My List",
            collectionType: "list",
        });

        expect(result.history_id).toBe("historyId");
        expect(result.auto_decompress).toBe(true);
        expect(result.files).toEqual([]);
        expect(result.targets).toHaveLength(1);

        const target = result.targets[0] as HdcaUploadTarget;
        expect(target.destination).toEqual({ type: "hdca" });
        expect(target.collection_type).toBe("list");
        expect(target.name).toBe("My List");
        expect(target.elements).toHaveLength(2);

        // Elements are reversed to match history panel display order (newest HID first)
        expect(target.elements[0]).toMatchObject({ src: "url", url: "http://example.com/2.txt" });
        expect(target.elements[1]).toMatchObject({ src: "url", url: "http://example.com/1.txt" });
    });

    test("builds list collection payload with local file items", () => {
        const file1 = createMockFile("file1.txt");
        const file2 = createMockFile("file2.txt");
        const items: ApiUploadItem[] = [
            createFileUploadItem(file1, "historyId"),
            createFileUploadItem(file2, "historyId"),
        ];

        const result = buildCollectionUploadPayload(items, {
            collectionName: "File List",
            collectionType: "list",
        });

        expect(result.files).toHaveLength(2);
        expect(result.files[0]).toBe(file1);
        expect(result.files[1]).toBe(file2);

        const target = result.targets[0] as HdcaUploadTarget;
        expect(target.destination).toEqual({ type: "hdca" });
        expect(target.collection_type).toBe("list");
        expect(target.elements).toHaveLength(2);

        expect(target.elements[0]).toMatchObject({ src: "files" });
        expect(target.elements[1]).toMatchObject({ src: "files" });
    });

    test("builds list:paired collection payload with nested elements", () => {
        const items: ApiUploadItem[] = [
            createUrlUploadItem("http://example.com/sample_R1.fastq", "historyId", { name: "sample_R1.fastq" }),
            createUrlUploadItem("http://example.com/sample_R2.fastq", "historyId", { name: "sample_R2.fastq" }),
        ];

        const result = buildCollectionUploadPayload(items, {
            collectionName: "Paired List",
            collectionType: "list:paired",
        });

        const target = result.targets[0] as HdcaUploadTarget;
        expect(target.destination).toEqual({ type: "hdca" });
        expect(target.collection_type).toBe("list:paired");
        expect(target.name).toBe("Paired List");
        expect(target.elements).toHaveLength(1); // 1 pair

        const pair = target.elements[0] as NestedElement;
        expect(pair.name).toBe("sample");
        expect(pair.elements).toHaveLength(2);

        expect(pair.elements[0]).toMatchObject({ name: "forward", src: "url" });
        expect(pair.elements[1]).toMatchObject({ name: "reverse", src: "url" });
    });

    test("builds list:paired with multiple pairs", () => {
        const items: ApiUploadItem[] = [
            createUrlUploadItem("http://example.com/s1_R1.fastq", "historyId", { name: "s1_R1.fastq" }),
            createUrlUploadItem("http://example.com/s1_R2.fastq", "historyId", { name: "s1_R2.fastq" }),
            createUrlUploadItem("http://example.com/s2_R1.fastq", "historyId", { name: "s2_R1.fastq" }),
            createUrlUploadItem("http://example.com/s2_R2.fastq", "historyId", { name: "s2_R2.fastq" }),
        ];

        const result = buildCollectionUploadPayload(items, {
            collectionName: "Two Pairs",
            collectionType: "list:paired",
        });

        const target = result.targets[0] as HdcaUploadTarget;
        expect(target.elements).toHaveLength(2); // 2 pairs

        const pair1 = target.elements[0] as NestedElement;
        const pair2 = target.elements[1] as NestedElement;
        expect(pair1.name).toBe("s1");
        expect(pair2.name).toBe("s2");
    });

    test("files array order matches depth-first element traversal for list:paired", () => {
        const file1 = createMockFile("s1_R1.fastq");
        const file2 = createMockFile("s1_R2.fastq");
        const file3 = createMockFile("s2_R1.fastq");
        const file4 = createMockFile("s2_R2.fastq");

        const items: ApiUploadItem[] = [
            createFileUploadItem(file1, "historyId", { name: "s1_R1.fastq" }),
            createFileUploadItem(file2, "historyId", { name: "s1_R2.fastq" }),
            createFileUploadItem(file3, "historyId", { name: "s2_R1.fastq" }),
            createFileUploadItem(file4, "historyId", { name: "s2_R2.fastq" }),
        ];

        const result = buildCollectionUploadPayload(items, {
            collectionName: "Paired Files",
            collectionType: "list:paired",
        });

        // Files must be in order: pair1-fwd, pair1-rev, pair2-fwd, pair2-rev
        // This matches the backend's depth-first replace_file_srcs iteration
        expect(result.files).toHaveLength(4);
        expect(result.files[0]).toBe(file1);
        expect(result.files[1]).toBe(file2);
        expect(result.files[2]).toBe(file3);
        expect(result.files[3]).toBe(file4);
    });

    test("handles mixed element types (files + URLs)", () => {
        const file1 = createMockFile("local.txt");
        const items: ApiUploadItem[] = [
            createFileUploadItem(file1, "historyId"),
            createUrlUploadItem("http://example.com/remote.txt", "historyId"),
        ];

        const result = buildCollectionUploadPayload(items, {
            collectionName: "Mixed List",
            collectionType: "list",
        });

        expect(result.files).toHaveLength(1);
        expect(result.files[0]).toBe(file1);

        const target = result.targets[0] as HdcaUploadTarget;
        expect(target.elements).toHaveLength(2);

        // Elements are reversed to match history panel display order (newest HID first)
        expect(target.elements[0]).toMatchObject({ src: "url" });
        expect(target.elements[1]).toMatchObject({ src: "files" });
    });

    test("handles pasted content in collection", () => {
        const items: ApiUploadItem[] = [
            createPastedUploadItem("content 1", "historyId", { name: "paste1.txt" }),
            createPastedUploadItem("content 2", "historyId", { name: "paste2.txt" }),
        ];

        const result = buildCollectionUploadPayload(items, {
            collectionName: "Pasted List",
            collectionType: "list",
        });

        expect(result.files).toEqual([]);

        const target = result.targets[0] as HdcaUploadTarget;
        expect(target.elements).toHaveLength(2);

        // Elements are reversed to match history panel display order (newest HID first)
        expect(target.elements[0]).toMatchObject({ src: "pasted", paste_content: "content 2" });
    });

    test("validates empty file data", () => {
        const emptyFile = new File([], "empty.txt");
        const items: ApiUploadItem[] = [createFileUploadItem(emptyFile, "historyId")];

        expect(() => buildCollectionUploadPayload(items, { collectionName: "test", collectionType: "list" })).toThrow(
            "File data is empty for upload item: empty.txt",
        );
    });

    test("validates invalid URL", () => {
        const items: ApiUploadItem[] = [createUrlUploadItem("not-a-url", "historyId")];

        expect(() => buildCollectionUploadPayload(items, { collectionName: "test", collectionType: "list" })).toThrow(
            "Invalid URL: not-a-url",
        );
    });
});

// ============================================================================
// Upload Submission Tests
// ============================================================================

describe("upload submission", () => {
    const { server, http } = useServerMock();

    beforeEach(() => {
        vi.mocked(createTusUpload).mockReset();
    });

    describe("fetchDatasets", () => {
        it("sends the payload to the API", async () => {
            const mockResponse = { jobs: [{ id: "job123" }], outputs: [{ id: "dataset1" }] };
            const successCallback = vi.fn();

            server.use(
                http.post("/api/tools/fetch", ({ response }) => {
                    return response.untyped(HttpResponse.json(mockResponse));
                }),
            );

            await fetchDatasets(
                {
                    history_id: "hist123",
                    targets: [],
                    auto_decompress: true,
                },
                { success: successCallback },
            );

            expect(successCallback).toHaveBeenCalledWith(mockResponse);
        });

        it("reports API errors", async () => {
            const errorCallback = vi.fn();

            server.use(
                http.post("/api/tools/fetch", ({ response }) => {
                    return response.untyped(
                        HttpResponse.json(
                            { err_msg: "Upload failed" },
                            { status: 500, headers: GALAXY_RESPONSE_HEADERS },
                        ),
                    );
                }),
            );

            await fetchDatasets(
                {
                    history_id: "hist123",
                    targets: [],
                    auto_decompress: true,
                },
                { error: errorCallback },
            );

            expect(errorCallback).toHaveBeenCalledTimes(1);
            expect(errorCallback).toHaveBeenCalledWith("Upload failed");
        });
    });

    describe("submitUpload", () => {
        it("reports validation errors before starting TUS", async () => {
            const errorCallback = vi.fn();

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [],
                    auto_decompress: true,
                    error_message: "Validation failed",
                    files: [],
                },
                error: errorCallback,
            });

            expect(errorCallback).toHaveBeenCalledWith("Validation failed");
            expect(createTusUpload).not.toHaveBeenCalled();
        });

        it("uploads local files via TUS", async () => {
            const mockFile = new File(["content"], "test.txt");
            const successCallback = vi.fn();
            const progressCallback = vi.fn();

            vi.mocked(createTusUpload).mockResolvedValue({
                sessionId: "session123",
                fileName: "test.txt",
            });

            server.use(
                http.post("/api/tools/fetch", ({ response }) => {
                    return response.untyped(HttpResponse.json({ jobs: [{ id: "job789" }] }));
                }),
            );

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [
                        {
                            destination: { type: "hdas" },
                            elements: [
                                {
                                    src: "files",
                                    name: "test.txt",
                                    ...commonElementDefaults,
                                },
                            ],
                            auto_decompress: true,
                        },
                    ],
                    auto_decompress: true,
                    files: [mockFile],
                },
                success: successCallback,
                progress: progressCallback,
            });

            expect(createTusUpload).toHaveBeenCalledWith({
                file: mockFile,
                endpoint: "/api/upload/resumable_upload/",
                historyId: "hist123",
                chunkSize: 10485760,
                onProgress: expect.any(Function),
                onError: expect.any(Function),
            });

            expect(successCallback).toHaveBeenCalledWith({ jobs: [{ id: "job789" }] });
        });

        it("submits an empty composite payload", async () => {
            const successCallback = vi.fn();

            server.use(
                http.post("/api/tools/fetch", ({ response }) => {
                    return response.untyped(HttpResponse.json({ jobs: [{ id: "job_composite" }] }));
                }),
            );

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [],
                    auto_decompress: true,
                    files: [],
                },
                success: successCallback,
                isComposite: true,
            });

            expect(successCallback).toHaveBeenCalledWith({ jobs: [{ id: "job_composite" }] });
        });

        it("submits URL uploads without TUS", async () => {
            const successCallback = vi.fn();

            server.use(
                http.post("/api/tools/fetch", ({ response }) => {
                    return response.untyped(HttpResponse.json({ jobs: [{ id: "job_url" }] }));
                }),
            );

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [
                        {
                            destination: { type: "hdas" },
                            elements: [
                                {
                                    src: "url",
                                    url: "https://example.com/file.txt",
                                    name: "file.txt",
                                    ...commonElementDefaults,
                                },
                            ],
                            auto_decompress: true,
                        },
                    ],
                    auto_decompress: true,
                    files: [],
                },
                success: successCallback,
            });

            expect(createTusUpload).not.toHaveBeenCalled();
            expect(successCallback).toHaveBeenCalledWith({ jobs: [{ id: "job_url" }] });
        });

        it("uploads pasted content as a blob via TUS", async () => {
            const successCallback = vi.fn();

            vi.mocked(createTusUpload).mockResolvedValue({
                sessionId: "session_paste",
                fileName: "pasted.txt",
            });

            server.use(
                http.post("/api/tools/fetch", ({ response }) => {
                    return response.untyped(HttpResponse.json({ jobs: [{ id: "job_paste" }] }));
                }),
            );

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [
                        {
                            destination: { type: "hdas" },
                            elements: [
                                {
                                    src: "pasted",
                                    paste_content: "Hello, world!",
                                    name: "pasted.txt",
                                    ...commonElementDefaults,
                                    ext: "txt",
                                },
                            ],
                            auto_decompress: true,
                        },
                    ],
                    auto_decompress: true,
                    files: [],
                },
                success: successCallback,
            });

            expect(createTusUpload).toHaveBeenCalled();
            const tusCall = vi.mocked(createTusUpload).mock.calls[0];
            expect(tusCall?.[0].file).toBeInstanceOf(Blob);
            expect(successCallback).toHaveBeenCalledWith({ jobs: [{ id: "job_paste" }] });
        });

        it("keeps pasted upload tracking aligned with per-file signals", async () => {
            const cancelledFile = new AbortController();
            cancelledFile.abort();
            const activeFile = new AbortController();
            const successCallback = vi.fn();

            vi.mocked(createTusUpload).mockResolvedValue({
                sessionId: "session_active_paste",
                fileName: "active.txt",
            });

            server.use(
                http.post("/api/tools/fetch", ({ response }) => {
                    return response.untyped(HttpResponse.json({ jobs: [{ id: "job_paste_partial" }] }));
                }),
            );

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [
                        {
                            destination: { type: "hdas" },
                            elements: [
                                {
                                    src: "pasted",
                                    paste_content: "cancelled",
                                    name: "cancelled.txt",
                                    ...commonElementDefaults,
                                    ext: "txt",
                                    auto_decompress: true,
                                    to_posix_lines: true,
                                },
                                {
                                    src: "pasted",
                                    paste_content: "active",
                                    name: "active.txt",
                                    ...commonElementDefaults,
                                    ext: "txt",
                                    auto_decompress: true,
                                    to_posix_lines: true,
                                },
                            ],
                            auto_decompress: true,
                        },
                    ],
                    auto_decompress: true,
                    files: [],
                },
                uploadIds: ["cancelled", "active"],
                perFileProgress: vi.fn(),
                signals: [cancelledFile.signal, activeFile.signal],
                success: successCallback,
            });

            expect(createTusUpload).toHaveBeenCalledTimes(1);
            expect(createTusUpload).toHaveBeenCalledWith(
                expect.objectContaining({
                    file: expect.objectContaining({ name: "active.txt" }),
                    signal: activeFile.signal,
                }),
            );
            expect(successCallback).toHaveBeenCalledWith({ jobs: [{ id: "job_paste_partial" }] });
        });

        it("suppresses success when a later URL fails", async () => {
            const successCallback = vi.fn();
            const errorCallback = vi.fn();
            let requestCount = 0;

            server.use(
                http.post("/api/tools/fetch", ({ response }) => {
                    requestCount += 1;
                    if (requestCount === 2) {
                        return response.untyped(
                            HttpResponse.json(
                                { err_msg: "second URL failed" },
                                { status: 500, headers: GALAXY_RESPONSE_HEADERS },
                            ),
                        );
                    }
                    return response.untyped(HttpResponse.json({ jobs: [{ id: "job_url_first" }] }));
                }),
            );

            await expect(
                submitUpload({
                    data: {
                        history_id: "hist123",
                        targets: [
                            {
                                destination: { type: "hdas" },
                                elements: [
                                    {
                                        src: "url",
                                        url: "https://example.com/1.txt",
                                        name: "1.txt",
                                        ...commonElementDefaults,
                                        auto_decompress: true,
                                        to_posix_lines: true,
                                    },
                                    {
                                        src: "url",
                                        url: "https://example.com/2.txt",
                                        name: "2.txt",
                                        ...commonElementDefaults,
                                        auto_decompress: true,
                                        to_posix_lines: true,
                                    },
                                ],
                                auto_decompress: true,
                            },
                        ],
                        auto_decompress: true,
                        files: [],
                    },
                    signals: [new AbortController().signal, new AbortController().signal],
                    success: successCallback,
                    error: errorCallback,
                }),
            ).rejects.toThrow("second URL failed");

            expect(errorCallback).toHaveBeenCalledWith("second URL failed");
            expect(successCallback).not.toHaveBeenCalled();
        });

        it("uses the supplied TUS chunk size", async () => {
            const mockFile = new File(["content"], "chunked.txt");
            const customChunkSize = 5242880; // 5MB

            vi.mocked(createTusUpload).mockResolvedValue({
                sessionId: "session_chunk",
                fileName: "chunked.txt",
            });

            server.use(
                http.post("/api/tools/fetch", ({ response }) => {
                    return response.untyped(HttpResponse.json({ jobs: [{ id: "job_chunk" }] }));
                }),
            );

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [],
                    auto_decompress: true,
                    files: [mockFile],
                },
                chunkSize: customChunkSize,
            });

            expect(createTusUpload).toHaveBeenCalledWith(
                expect.objectContaining({
                    chunkSize: customChunkSize,
                }),
            );
        });

        it("uploads multiple files in sequence", async () => {
            const file1 = new File(["content1"], "file1.txt");
            const file2 = new File(["content2"], "file2.txt");
            const successCallback = vi.fn();

            vi.mocked(createTusUpload)
                .mockResolvedValueOnce({
                    sessionId: "session1",
                    fileName: "file1.txt",
                })
                .mockResolvedValueOnce({
                    sessionId: "session2",
                    fileName: "file2.txt",
                });

            server.use(
                http.post("/api/tools/fetch", ({ response }) => {
                    return response.untyped(HttpResponse.json({ jobs: [{ id: "job_multi" }] }));
                }),
            );

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [],
                    auto_decompress: true,
                    files: [file1, file2],
                },
                success: successCallback,
            });

            expect(createTusUpload).toHaveBeenCalledTimes(2);
            expect(successCallback).toHaveBeenCalledWith({ jobs: [{ id: "job_multi" }] });
        });

        it("skips a cancelled file and submits the remaining file", async () => {
            const file1 = new File(["content1"], "file1.txt");
            const file2 = new File(["content2"], "file2.txt");
            const successCallback = vi.fn();
            const fetchedBodies: unknown[] = [];

            vi.mocked(createTusUpload).mockResolvedValueOnce({
                sessionId: "session2",
                fileName: "file2.txt",
            });

            server.use(
                http.post("/api/tools/fetch", async ({ request, response }) => {
                    fetchedBodies.push(await request.json());
                    return response.untyped(HttpResponse.json({ jobs: [{ id: "job_partial" }] }));
                }),
            );

            const cancelledFile = new AbortController();
            cancelledFile.abort();

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [
                        {
                            destination: { type: "hdas" },
                            auto_decompress: true,
                            elements: [
                                {
                                    src: "files",
                                    name: "file1.txt",
                                    ...commonElementDefaults,
                                },
                                {
                                    src: "files",
                                    name: "file2.txt",
                                    ...commonElementDefaults,
                                },
                            ],
                        },
                    ],
                    auto_decompress: true,
                    files: [file1, file2],
                },
                uploadIds: ["upload1", "upload2"],
                perFileProgress: () => {},
                signals: [cancelledFile.signal, undefined],
                success: successCallback,
            });

            // Only the non-cancelled file is uploaded via TUS and submitted
            expect(createTusUpload).toHaveBeenCalledTimes(1);
            expect(successCallback).toHaveBeenCalledWith({ jobs: [{ id: "job_partial" }] });
            expect(fetchedBodies).toHaveLength(1);
            expect(fetchedBodies[0]).toMatchObject({
                "files_0|file_data": { session_id: "session2" },
                targets: [{ elements: [{ name: "file2.txt" }] }],
            });
        });

        it("skips submission when every file is cancelled", async () => {
            const file1 = new File(["content1"], "file1.txt");
            const successCallback = vi.fn();
            const errorCallback = vi.fn();
            const fetchSpy = vi.fn();

            server.use(
                http.post("/api/tools/fetch", ({ response }) => {
                    fetchSpy();
                    return response.untyped(HttpResponse.json({ jobs: [{ id: "job_none" }] }));
                }),
            );

            const cancelledFile = new AbortController();
            cancelledFile.abort();

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [],
                    auto_decompress: true,
                    files: [file1],
                },
                signals: [cancelledFile.signal],
                success: successCallback,
                error: errorCallback,
            });

            expect(createTusUpload).not.toHaveBeenCalled();
            expect(fetchSpy).not.toHaveBeenCalled();
            expect(successCallback).not.toHaveBeenCalled();
            expect(errorCallback).not.toHaveBeenCalled();
        });

        it("fails the submission on an upload error with per-file signals", async () => {
            const file1 = new File(["content1"], "file1.txt");
            const file2 = new File(["content2"], "file2.txt");
            const errorCallback = vi.fn();

            vi.mocked(createTusUpload).mockRejectedValue(new Error("Upload failed"));

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [],
                    auto_decompress: true,
                    files: [file1, file2],
                },
                signals: [new AbortController().signal, new AbortController().signal],
                error: errorCallback,
            });

            expect(errorCallback).toHaveBeenCalledWith(new Error("Upload failed"));
        });

        it("skips a file aborted during an earlier upload and submits the rest", async () => {
            const file1 = new File(["content1"], "file1.txt");
            const file2 = new File(["content2"], "file2.txt");
            const file3 = new File(["content3"], "file3.txt");
            const successCallback = vi.fn();
            const fetchedBodies: unknown[] = [];

            const controller2 = new AbortController();

            vi.mocked(createTusUpload)
                .mockImplementationOnce(async () => {
                    // File 1 uploads successfully; abort file 2 while file 1 is in-flight.
                    controller2.abort();
                    return { sessionId: "session1", fileName: "file1.txt" };
                })
                .mockResolvedValueOnce({ sessionId: "session3", fileName: "file3.txt" });

            server.use(
                http.post("/api/tools/fetch", async ({ request, response }) => {
                    fetchedBodies.push(await request.json());
                    return response.untyped(HttpResponse.json({ jobs: [{ id: "job_partial_mid" }] }));
                }),
            );

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [
                        {
                            destination: { type: "hdas" },
                            auto_decompress: true,
                            elements: [
                                {
                                    src: "files",
                                    name: "file1.txt",
                                    ...commonElementDefaults,
                                    auto_decompress: true,
                                    to_posix_lines: true,
                                },
                                {
                                    src: "files",
                                    name: "file2.txt",
                                    ...commonElementDefaults,
                                    auto_decompress: true,
                                    to_posix_lines: true,
                                },
                                {
                                    src: "files",
                                    name: "file3.txt",
                                    ...commonElementDefaults,
                                    auto_decompress: true,
                                    to_posix_lines: true,
                                },
                            ],
                        },
                    ],
                    auto_decompress: true,
                    files: [file1, file2, file3],
                },
                uploadIds: ["u1", "u2", "u3"],
                perFileProgress: () => {},
                signals: [undefined, controller2.signal, undefined],
                success: successCallback,
            });

            // File 2 was aborted mid-loop; files 1 and 3 should still be uploaded.
            expect(createTusUpload).toHaveBeenCalledTimes(2);
            expect(successCallback).toHaveBeenCalledWith({ jobs: [{ id: "job_partial_mid" }] });
            expect(fetchedBodies).toHaveLength(1);
            expect(fetchedBodies[0]).toMatchObject({
                "files_0|file_data": { session_id: "session1" },
                "files_1|file_data": { session_id: "session3" },
                targets: [{ elements: [{ name: "file1.txt" }, { name: "file3.txt" }] }],
            });
        });

        it("reports TUS progress through the callback", async () => {
            const mockFile = new File(["content"], "progress.txt");
            const progressCallback = vi.fn();

            vi.mocked(createTusUpload).mockImplementation(async (options) => {
                // Simulate progress updates
                options.onProgress(25);
                options.onProgress(50);
                options.onProgress(100);
                return {
                    sessionId: "session_progress",
                    fileName: "progress.txt",
                };
            });

            server.use(
                http.post("/api/tools/fetch", ({ response }) => {
                    return response.untyped(HttpResponse.json({ jobs: [{ id: "job_progress" }] }));
                }),
            );

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [],
                    auto_decompress: true,
                    files: [mockFile],
                },
                progress: progressCallback,
            });

            expect(progressCallback).toHaveBeenCalledWith(25);
            expect(progressCallback).toHaveBeenCalledWith(50);
            expect(progressCallback).toHaveBeenCalledWith(100);
        });

        it("reports TUS upload errors", async () => {
            const mockFile = new File(["content"], "error.txt");
            const errorCallback = vi.fn();

            vi.mocked(createTusUpload).mockRejectedValue(new Error("Upload failed"));

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [],
                    auto_decompress: true,
                    files: [mockFile],
                },
                error: errorCallback,
            });

            expect(errorCallback).toHaveBeenCalledWith(new Error("Upload failed"));
        });

        it("submits URL collections without TUS", async () => {
            const successCallback = vi.fn();

            server.use(
                http.post("/api/tools/fetch", ({ response }) => {
                    return response.untyped(HttpResponse.json({ jobs: [{ id: "job_hdca" }] }));
                }),
            );

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [
                        {
                            destination: { type: "hdca" },
                            collection_type: "list",
                            name: "My Collection",
                            auto_decompress: false,
                            elements: [
                                {
                                    src: "url",
                                    url: "https://example.com/1.txt",
                                    name: "1.txt",
                                    ...commonElementDefaults,
                                },
                                {
                                    src: "url",
                                    url: "https://example.com/2.txt",
                                    name: "2.txt",
                                    ...commonElementDefaults,
                                },
                            ],
                        },
                    ],
                    auto_decompress: true,
                    files: [],
                },
                success: successCallback,
            });

            expect(createTusUpload).not.toHaveBeenCalled();
            expect(successCallback).toHaveBeenCalledWith({ jobs: [{ id: "job_hdca" }] });
        });

        it("uploads local files in a collection via TUS", async () => {
            const file1 = new File(["content1"], "file1.txt");
            const file2 = new File(["content2"], "file2.txt");
            const successCallback = vi.fn();

            vi.mocked(createTusUpload)
                .mockResolvedValueOnce({
                    sessionId: "session1",
                    fileName: "file1.txt",
                })
                .mockResolvedValueOnce({
                    sessionId: "session2",
                    fileName: "file2.txt",
                });

            server.use(
                http.post("/api/tools/fetch", ({ response }) => {
                    return response.untyped(HttpResponse.json({ jobs: [{ id: "job_hdca_files" }] }));
                }),
            );

            await submitUpload({
                data: {
                    history_id: "hist123",
                    targets: [
                        {
                            destination: { type: "hdca" },
                            collection_type: "list",
                            name: "File Collection",
                            auto_decompress: false,
                            elements: [
                                {
                                    src: "files",
                                    name: "file1.txt",
                                    ...commonElementDefaults,
                                },
                                {
                                    src: "files",
                                    name: "file2.txt",
                                    ...commonElementDefaults,
                                },
                            ],
                        },
                    ],
                    auto_decompress: true,
                    files: [file1, file2],
                },
                success: successCallback,
            });

            expect(createTusUpload).toHaveBeenCalledTimes(2);
            expect(successCallback).toHaveBeenCalledWith({ jobs: [{ id: "job_hdca_files" }] });
        });
    });
});
