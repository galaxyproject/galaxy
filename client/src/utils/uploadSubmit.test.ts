import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import { createTusUpload } from "./tusUpload";
import { sendPayload, submitDatasetUpload } from "./uploadSubmit";

// Mock the TUS upload functionality
vi.mock("./tusUpload", () => ({
    createTusUpload: vi.fn(),
    NamedBlob: class {},
}));

vi.mock("@/onload/loadConfig", () => ({
    getAppRoot: () => "/",
}));

describe("uploadSubmit", () => {
    const { server } = useServerMock();

    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe("sendPayload", () => {
        it("should successfully send payload to API", async () => {
            const mockResponse = { jobs: [{ id: "job123" }], outputs: [{ id: "dataset1" }] };
            const successCallback = vi.fn();

            server.use(
                http.post("/api/tools/fetch", () => {
                    return HttpResponse.json(mockResponse);
                }),
            );

            await sendPayload(
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

            await sendPayload(
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

    describe("submitDatasetUpload", () => {
        it("should immediately fail if error_message is present", async () => {
            const errorCallback = vi.fn();

            await submitDatasetUpload({
                data: {
                    history_id: "hist123",
                    targets: [],
                    auto_decompress: true,
                    error_message: "Validation failed",
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

            await submitDatasetUpload({
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

            await submitDatasetUpload({
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

            await submitDatasetUpload({
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

            await submitDatasetUpload({
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

            await submitDatasetUpload({
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

            await submitDatasetUpload({
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

            await submitDatasetUpload({
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

            await submitDatasetUpload({
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
