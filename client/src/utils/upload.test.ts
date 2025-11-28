import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, test, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { CompositeDataElement, HdasUploadTarget } from "@/api/tools";

import { createTusUpload } from "./tusUpload";
import {
    buildLegacyPayload,
    buildUploadPayload,
    createFileUploadItem,
    createPastedUploadItem,
    createUrlUploadItem,
    fetchDatasets,
    isGalaxyFileName,
    type LegacyUploadItem,
    parseContentToUploadItems,
    stripGalaxyFilePrefix,
    submitUpload,
    type UploadItem,
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
        const items: UploadItem[] = [createFileUploadItem(file1, "history1"), createFileUploadItem(file2, "history2")];

        expect(() => buildUploadPayload(items)).toThrow("All upload items must target the same history.");
    });

    test("builds payload with file upload items", () => {
        const mockFile = createMockFile("test.txt");
        const items: UploadItem[] = [createFileUploadItem(mockFile, "historyId")];

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
        const items: UploadItem[] = [
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
        const items: UploadItem[] = [createFileUploadItem(emptyFile, "historyId")];

        expect(() => buildUploadPayload(items)).toThrow("File data is empty for upload item: empty.txt");
    });

    test("validates empty pasted content", () => {
        const items: UploadItem[] = [createPastedUploadItem("", "historyId", { name: "empty" })];

        expect(() => buildUploadPayload(items)).toThrow("No content for pasted upload item: empty");
    });

    test("validates invalid URL", () => {
        const items: UploadItem[] = [createUrlUploadItem("not-a-valid-url", "historyId")];

        expect(() => buildUploadPayload(items)).toThrow("Invalid URL: not-a-valid-url");
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
    });
});
