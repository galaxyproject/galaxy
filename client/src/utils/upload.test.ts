import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, test, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
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
    extractPairName,
    fetchDatasets,
    isGalaxyFileName,
    type LegacyUploadItem,
    parseContentToUploadItems,
    stripGalaxyFilePrefix,
    submitUpload,
    uploadItemDefaults,
} from "./upload";

// Mock the TUS upload functionality
vi.mock("./tusUpload", () => ({
    createTusUpload: vi.fn(),
    NamedBlob: class {},
}));

vi.mock("@/onload/loadConfig", () => ({
    getAppRoot: () => "/",
}));

// Helper to create a mock File object for testing
function createMockFile(name: string, content: string = "test content"): File {
    const blob = new Blob([content], { type: "text/plain" });
    return new File([blob], name, { lastModified: Date.now() });
}

// ============================================================================
// Payload Building Tests
// ============================================================================

describe("buildLegacyPayload", () => {
    test("basic validation", () => {
        expect(() => buildLegacyPayload([], "historyId")).toThrow("No upload items provided.");
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
                        fileMode: "unknown" as LegacyUploadItem["fileMode"],
                        fileName: "test",
                        fileSize: 1,
                    } as LegacyUploadItem,
                ],
                "historyId",
            ),
        ).toThrow("No valid upload items after conversion.");
    });

    test("empty fileContent validation", () => {
        expect(() =>
            buildLegacyPayload(
                [{ fileMode: "new", fileName: "test", fileContent: "", fileSize: 0 } as LegacyUploadItem],
                "historyId",
            ),
        ).toThrow("Content not available.");

        expect(() =>
            buildLegacyPayload(
                [{ fileMode: "new", fileName: "test", fileContent: "   ", fileSize: 0 } as LegacyUploadItem],
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

        const element = target.elements![0] as { src: string; paste_content: string };
        expect(element.src).toBe("pasted");
        expect(element.paste_content).toBe(" fileContent ");
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
        const element = target.elements![0] as { src: string; dbkey: string; ext: string };
        expect(element.src).toBe("files");
        expect(element.dbkey).toBe("hg38");
        expect(element.ext).toBe("txt");
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
        const element = target.elements![0] as { src: string; url: string; deferred: boolean };
        expect(element.src).toBe("url");
        expect(element.url).toBe("http://example.com/data.bed");
        expect(element.deferred).toBe(true);
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

        const elem1 = target.elements![0] as { src: string; url: string };
        const elem2 = target.elements![1] as { src: string; url: string };
        expect(elem1.src).toBe("url");
        expect(elem1.url).toBe("http://example.com/1.txt");
        expect(elem2.url).toBe("http://example.com/2.txt");
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
        const element = target.elements![0] as { name: string };
        expect(element.name).toBe("PreviousFile");
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
    test("recognizes Galaxy file names", () => {
        expect(isGalaxyFileName("Galaxy5-[MyFile].bed")).toBe(true);
        expect(isGalaxyFileName("Galaxy123-[Some File Name].txt")).toBe(true);
    });

    test("rejects non-Galaxy file names", () => {
        expect(isGalaxyFileName("myfile.txt")).toBe(false);
        expect(isGalaxyFileName("Galaxy-[NoNumber].txt")).toBe(false);
        expect(isGalaxyFileName(null)).toBe(false);
        expect(isGalaxyFileName(undefined)).toBe(false);
    });
});

describe("stripGalaxyFilePrefix", () => {
    test("strips Galaxy prefix", () => {
        expect(stripGalaxyFilePrefix("Galaxy5-[MyFile].bed")).toBe("MyFile");
        expect(stripGalaxyFilePrefix("Galaxy123-[Some File].txt")).toBe("Some File");
    });

    test("returns original if no match", () => {
        expect(stripGalaxyFilePrefix("myfile.txt")).toBe("myfile.txt");
    });
});

describe("cleanUrlFilename", () => {
    test("removes URL path and query parameters", () => {
        expect(cleanUrlFilename("http://example.com/path/to/file.pdf?download=1")).toBe("file.pdf");
    });

    test("decodes URL-encoded characters", () => {
        expect(cleanUrlFilename("file%20name.pdf")).toBe("file name.pdf");
        expect(cleanUrlFilename("Readme%20Statistical%20Downscaling.pdf")).toBe("Readme Statistical Downscaling.pdf");
        expect(cleanUrlFilename("special%26chars%3D.txt")).toBe("special&chars=.txt");
    });

    test("handles both encoding and query parameters", () => {
        expect(cleanUrlFilename("Readme%20Statistical%20Downscaling.pdf?download=1")).toBe(
            "Readme Statistical Downscaling.pdf",
        );
        expect(cleanUrlFilename("my%20file.txt?token=abc123")).toBe("my file.txt");
    });

    test("returns original for normal filenames", () => {
        expect(cleanUrlFilename("normal.txt")).toBe("normal.txt");
        expect(cleanUrlFilename("file-with-dashes.bed")).toBe("file-with-dashes.bed");
    });

    test("handles malformed URL encoding gracefully", () => {
        // Malformed percent encoding (invalid hex)
        expect(cleanUrlFilename("file%ZZname.txt")).toBe("file%ZZname.txt");
        // Incomplete percent encoding
        expect(cleanUrlFilename("file%2.txt")).toBe("file%2.txt");
    });

    test("handles empty query string", () => {
        expect(cleanUrlFilename("file.txt?")).toBe("file.txt");
    });

    test("returns null for empty filename", () => {
        expect(cleanUrlFilename("")).toBeNull();
    });

    test("returns null for URL with no filename", () => {
        expect(cleanUrlFilename("http://example.com/")).toBeNull();
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
        });

        expect(item.name).toBe("custom.bed");
        expect(item.dbkey).toBe("hg38");
        expect(item.ext).toBe("bed");
        expect(item.space_to_tab).toBe(true);
        expect(item.to_posix_lines).toBe(false);
        expect(item.deferred).toBe(true);
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
    });

    test("creates pasted upload item with custom name", () => {
        const item = createPastedUploadItem("content", "historyId", { name: "MyPaste.txt" });
        expect(item.name).toBe("MyPaste.txt");
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
        });

        expect(item.name).toBe("custom-name.bed");
        expect(item.deferred).toBe(true);
        expect(item.dbkey).toBe("hg38");
    });
});

describe("parseContentToUploadItems", () => {
    test("throws on empty content", () => {
        expect(() => parseContentToUploadItems("", "historyId")).toThrow("Content not available.");
        expect(() => parseContentToUploadItems("   ", "historyId")).toThrow("Content not available.");
    });

    test("parses plain text as pasted content", () => {
        const items = parseContentToUploadItems("some plain text\nwith multiple lines", "historyId");

        expect(items).toHaveLength(1);
        expect(items[0]!.src).toBe("pasted");
        expect((items[0] as { paste_content: string }).paste_content).toBe("some plain text\nwith multiple lines");
    });

    test("parses URLs when first line is a URL", () => {
        const items = parseContentToUploadItems(
            "http://example.com/file1.txt\nhttp://example.com/file2.txt",
            "historyId",
        );

        expect(items).toHaveLength(2);
        expect(items[0]!.src).toBe("url");
        expect((items[0] as { url: string }).url).toBe("http://example.com/file1.txt");
        expect(items[1]!.src).toBe("url");
        expect((items[1] as { url: string }).url).toBe("http://example.com/file2.txt");
    });

    test("throws on invalid URL in URL list", () => {
        expect(() => parseContentToUploadItems("http://example.com/valid.txt\ninvalid-not-a-url", "historyId")).toThrow(
            "Invalid URL: invalid-not-a-url",
        );
    });

    test("handles whitespace around URLs", () => {
        const items = parseContentToUploadItems("  http://example.com/file.txt  \n  ", "historyId");

        expect(items).toHaveLength(1);
        expect((items[0] as { url: string }).url).toBe("http://example.com/file.txt");
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
});

// ============================================================================
// Pair Name Extraction Tests
// ============================================================================

describe("extractPairName", () => {
    test("detects _R1/_R2 suffix", () => {
        expect(extractPairName("sample_R1.fastq", "sample_R2.fastq")).toBe("sample");
    });

    test("detects _1/_2 suffix", () => {
        expect(extractPairName("sample_1.fastq", "sample_2.fastq")).toBe("sample");
    });

    test("detects .R1/.R2 suffix", () => {
        expect(extractPairName("sample.R1.fastq", "sample.R2.fastq")).toBe("sample");
    });

    test("detects _F/_R suffix", () => {
        expect(extractPairName("sample_F.fastq", "sample_R.fastq")).toBe("sample");
    });

    test("detects _fwd/_rev suffix", () => {
        expect(extractPairName("sample_fwd.fastq", "sample_rev.fastq")).toBe("sample");
    });

    test("detects _forward/_reverse suffix", () => {
        expect(extractPairName("sample_forward.fastq", "sample_reverse.fastq")).toBe("sample");
    });

    test("falls back to common prefix", () => {
        expect(extractPairName("sampleA.fastq", "sampleB.fastq")).toBe("sample");
    });

    test("returns first file base name when no common pattern", () => {
        expect(extractPairName("alpha.txt", "beta.txt")).toBe("alpha");
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

        const elem1 = target.elements[0] as { src: string; url: string };
        const elem2 = target.elements[1] as { src: string; url: string };
        expect(elem1.src).toBe("url");
        expect(elem1.url).toBe("http://example.com/1.txt");
        expect(elem2.src).toBe("url");
        expect(elem2.url).toBe("http://example.com/2.txt");
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

        const elem1 = target.elements[0] as { src: string };
        const elem2 = target.elements[1] as { src: string };
        expect(elem1.src).toBe("files");
        expect(elem2.src).toBe("files");
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

        const fwd = pair.elements[0] as { name: string; src: string; url: string };
        const rev = pair.elements[1] as { name: string; src: string; url: string };
        expect(fwd.name).toBe("forward");
        expect(fwd.src).toBe("url");
        expect(rev.name).toBe("reverse");
        expect(rev.src).toBe("url");
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

        const elem1 = target.elements[0] as { src: string };
        const elem2 = target.elements[1] as { src: string };
        expect(elem1.src).toBe("files");
        expect(elem2.src).toBe("url");
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

        const elem1 = target.elements[0] as { src: string; paste_content: string };
        expect(elem1.src).toBe("pasted");
        expect(elem1.paste_content).toBe("content 1");
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
    const { server } = useServerMock();

    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe("fetchDatasets", () => {
        it("should successfully send payload to API", async () => {
            const mockResponse = { jobs: [{ id: "job123" }], outputs: [{ id: "dataset1" }] };
            const successCallback = vi.fn();

            server.use(
                http.post("/api/tools/fetch", () => {
                    return HttpResponse.json(mockResponse);
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

        it("should handle API errors", async () => {
            const errorCallback = vi.fn();

            server.use(
                http.post("/api/tools/fetch", () => {
                    return HttpResponse.json({ err_msg: "Upload failed" }, { status: 500 });
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

            expect(errorCallback).toHaveBeenCalled();
            const errorArg = errorCallback.mock.calls[0]?.[0];
            expect(errorArg).toBe("Upload failed");
        });
    });

    describe("submitUpload", () => {
        it("should immediately fail if error_message is present", async () => {
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

        it("should upload files via TUS when files are present", async () => {
            const mockFile = new File(["content"], "test.txt");
            const successCallback = vi.fn();
            const progressCallback = vi.fn();

            vi.mocked(createTusUpload).mockResolvedValue({
                sessionId: "session123",
                fileName: "test.txt",
            });

            server.use(
                http.post("/api/tools/fetch", () => {
                    return HttpResponse.json({ jobs: [{ id: "job789" }] });
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
                                    dbkey: "?",
                                    ext: "auto",
                                    space_to_tab: false,
                                    to_posix_lines: false,
                                    auto_decompress: false,
                                    deferred: false,
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

        it("should upload via TUS for composite uploads even without files", async () => {
            const successCallback = vi.fn();

            server.use(
                http.post("/api/tools/fetch", () => {
                    return HttpResponse.json({ jobs: [{ id: "job_composite" }] });
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

            // For composite with no files, should still go through TUS path
            expect(successCallback).toHaveBeenCalledWith({ jobs: [{ id: "job_composite" }] });
        });

        it("should directly submit URL uploads without TUS", async () => {
            const successCallback = vi.fn();

            server.use(
                http.post("/api/tools/fetch", () => {
                    return HttpResponse.json({ jobs: [{ id: "job_url" }] });
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
                                    dbkey: "?",
                                    ext: "auto",
                                    space_to_tab: false,
                                    to_posix_lines: false,
                                    auto_decompress: false,
                                    deferred: false,
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

        it("should convert pasted content to blob and upload via TUS", async () => {
            const successCallback = vi.fn();

            vi.mocked(createTusUpload).mockResolvedValue({
                sessionId: "session_paste",
                fileName: "pasted.txt",
            });

            server.use(
                http.post("/api/tools/fetch", () => {
                    return HttpResponse.json({ jobs: [{ id: "job_paste" }] });
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
                                    dbkey: "?",
                                    ext: "txt",
                                    space_to_tab: false,
                                    to_posix_lines: false,
                                    auto_decompress: false,
                                    deferred: false,
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

        it("should use custom chunk size if provided", async () => {
            const mockFile = new File(["content"], "chunked.txt");
            const customChunkSize = 5242880; // 5MB

            vi.mocked(createTusUpload).mockResolvedValue({
                sessionId: "session_chunk",
                fileName: "chunked.txt",
            });

            server.use(
                http.post("/api/tools/fetch", () => {
                    return HttpResponse.json({ jobs: [{ id: "job_chunk" }] });
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

        it("should handle multiple file uploads sequentially", async () => {
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
                http.post("/api/tools/fetch", () => {
                    return HttpResponse.json({ jobs: [{ id: "job_multi" }] });
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

        it("should invoke progress callback during upload", async () => {
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
                http.post("/api/tools/fetch", () => {
                    return HttpResponse.json({ jobs: [{ id: "job_progress" }] });
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

        it("should handle TUS upload errors", async () => {
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

            expect(errorCallback).toHaveBeenCalled();
        });

        it("should directly submit HDCA collection target with URLs (no TUS)", async () => {
            const successCallback = vi.fn();

            server.use(
                http.post("/api/tools/fetch", () => {
                    return HttpResponse.json({ jobs: [{ id: "job_hdca" }] });
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
                                    dbkey: "?",
                                    ext: "auto",
                                    space_to_tab: false,
                                    to_posix_lines: false,
                                    auto_decompress: false,
                                    deferred: false,
                                },
                                {
                                    src: "url",
                                    url: "https://example.com/2.txt",
                                    name: "2.txt",
                                    dbkey: "?",
                                    ext: "auto",
                                    space_to_tab: false,
                                    to_posix_lines: false,
                                    auto_decompress: false,
                                    deferred: false,
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

        it("should upload HDCA collection with local files via TUS", async () => {
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
                http.post("/api/tools/fetch", () => {
                    return HttpResponse.json({ jobs: [{ id: "job_hdca_files" }] });
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
                                    dbkey: "?",
                                    ext: "auto",
                                    space_to_tab: false,
                                    to_posix_lines: false,
                                    auto_decompress: false,
                                    deferred: false,
                                },
                                {
                                    src: "files",
                                    name: "file2.txt",
                                    dbkey: "?",
                                    ext: "auto",
                                    space_to_tab: false,
                                    to_posix_lines: false,
                                    auto_decompress: false,
                                    deferred: false,
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
